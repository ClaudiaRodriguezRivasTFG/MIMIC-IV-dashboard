from pymongo import MongoClient
import pandas as pd

client = MongoClient("mongodb://localhost:27017")
db = client["MIMIC_IV"]
col_vent = db["icu_ventilation"]

def obtener_datos_ventilacion():
    # Traemos los campos de tu captura
    query = {
        "_id": 0, "stay_id": 1,
        "ventilation_status": 1, "o2_flow": 1,
        "o2_delivery_device_1": 1, "starttime": 1, "endtime": 1
    }
    docs = list(col_vent.find({}, query))
    df = pd.DataFrame(docs)
    
    if df.empty:
        return df

    # Convertir fechas para calcular duración
    df['starttime'] = pd.to_datetime(df['starttime'])
    df['endtime'] = pd.to_datetime(df['endtime'])
    df['duracion_horas'] = (df['endtime'] - df['starttime']).dt.total_seconds() / 3600
    
    # Limpiar o2_flow
    df['o2_flow'] = pd.to_numeric(df['o2_flow'], errors='coerce')
    
    return df

def estadisticas_resumen_vent():
    df = obtener_datos_ventilacion()
    if df.empty: return None
    
    resumen = df.groupby('ventilation_status').agg({
        'stay_id': 'count',
        'duracion_horas': 'mean',
        'o2_flow': 'mean'
    }).reset_index()
    
    resumen.columns = ['Estado', 'Total_Registros', 'Media_Horas', 'Media_Flujo_O2']
    # ASEGURAR TIPOS DE DATOS PARA ALTAIR
    resumen['Total_Registros'] = resumen['Total_Registros'].astype(int)
    resumen['Media_Horas'] = resumen['Media_Horas'].fillna(0).astype(float)
    return resumen

col_stay = db["icu_stay"] # Nueva colección necesaria

def obtener_datos_escalada():
    """Trae los datos cronológicos para ver cómo cambia el soporte."""
    docs = list(col_vent.find({}, {"_id":0, "stay_id":1, "ventilation_status":1, "starttime":1}))
    df = pd.DataFrame(docs)
    if df.empty: return df
    
    df['starttime'] = pd.to_datetime(df['starttime'])
    # Orden por estancia y tiempo para ver la evolución
    df = df.sort_values(['stay_id', 'starttime'])
    return df

def obtener_relacion_estancia():
    """Cruza duración de ventilación con estancia total en UCI."""
    # Cálculo duración total de Ventilación Invasiva por stay_id
    pipeline = [
        {"$match": {"ventilation_status": "InvasiveVent"}},
        {"$project": {
            "stay_id": 1,
            "duration": {
                "$divide": [
                    {"$subtract": ["$endtime", "$starttime"]},
                    3600000 # Convertir ms a horas
                ]
            }
        }},
        {"$group": {"_id": "$stay_id", "total_vent_horas": {"$sum": "$duration"}}}
    ]
    vent_data = list(col_vent.aggregate(pipeline))
    df_vent = pd.DataFrame(vent_data).rename(columns={"_id": "stay_id"})
    
    # 2. Traemos la estancia total (los_icu) de la tabla icu_stay
    stay_data = list(col_stay.find({}, {"_id":0, "stay_id":1, "los_icu":1})) # 'los' suele estar en días
    df_stay = pd.DataFrame(stay_data)
    
    if df_vent.empty or df_stay.empty: return pd.DataFrame()
    
    # Unimos ambos
    df_final = pd.merge(df_vent, df_stay, on="stay_id")
    if not df_final.empty:
        # Aseguramos que 'los' y 'total_vent_horas' sean números reales
        df_final['los_icu'] = pd.to_numeric(df_final['los_icu'], errors='coerce')
        df_final['total_vent_horas'] = pd.to_numeric(df_final['total_vent_horas'], errors='coerce')
        
        # Eliminamos filas que se hayan quedado vacías tras la limpieza
        df_final = df_final.dropna(subset=['los_icu', 'total_vent_horas'])

    return df_final