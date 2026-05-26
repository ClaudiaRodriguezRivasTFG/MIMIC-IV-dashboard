from pymongo import MongoClient
import pandas as pd
import streamlit as st

client = MongoClient("mongodb://localhost:27017")
db = client["MIMIC_IV"]
col_lab = db["firstday_vitalsign_lab"] 

def obtener_datos_vitals():
    # campos nuevos.
    query = {"_id": 0} # 
    docs = list(col_lab.find({}, query))
    df = pd.DataFrame(docs)
   
    if df.empty:
        return pd.DataFrame()


    # Convertir a numérico todas las columnas excepto los IDs
    for col in df.columns:
        if col not in ['subject_id', 'stay_id']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
   
    return df

def obtener_datos_investigador():
    """
    Une Laboratorio y Estancias usando la LLAVE DOBLE (subject_id + stay_id)
    para garantizar que los datos demográficos correspondan a la estancia exacta.
    """
    # Datos de estancias con stay_id incluido
    docs_stay = list(
        db["icu_stay"].find(
            {},
            {
                "_id": 0,
                "subject_id": 1,
                "stay_id": 1,  
                "gender": 1,
                "anchor_age": 1,
                "first_careunit": 1
            }
        )
    )

    # Datos laboratorio
    docs_lab = list(
        col_lab.find(
            {},
            {
                "_id": 0,
                "subject_id": 1,
                "stay_id": 1,
                "wbc_max": 1, "wbc_min": 1,
                "platelets_max": 1, "platelets_min": 1,
                "bilirubin_total_max": 1, "bilirubin_total_min": 1,
                "creatinine_max": 1, "creatinine_min": 1,
                "lactate_max": 1, "lactate_min": 1,
                "ph_max": 1, "ph_min": 1,
                "so2_max": 1, "so2_min": 1,
                "temperature_max": 1, "temperature_min": 1,
                "heart_rate_max": 1, "heart_rate_min": 1,
            }
        )
    )

    if not docs_stay or not docs_lab:
        return pd.DataFrame()

    df_stay = pd.DataFrame(docs_stay)
    df_lab = pd.DataFrame(docs_lab)

    #Conversión de tipos antes del merge
    # Asegurar que los IDs sean del mismo tipo 
    for df in [df_stay, df_lab]:
        df["subject_id"] = df["subject_id"].astype(str)
        df["stay_id"] = df["stay_id"].astype(str)

    df_stay["anchor_age"] = pd.to_numeric(df_stay["anchor_age"], errors="coerce")

    # 
    df_final = pd.merge(df_lab, df_stay, on=["subject_id", "stay_id"], how="inner")

    return df_final.dropna(subset=["anchor_age"])

    

def estadisticas_vitals():
    df = obtener_datos_vitals()
    if df.empty: return None
    
    resumen = []
    # Lista completa de variables 
    variables = [
        ('heart_rate', 'Frec. Cardíaca'),
        ('mbp', 'Presión Media (MBP)'),
        ('sbp', 'Presión Sistólica (SBP)'),
        ('resp_rate', 'Frec. Respiratoria'),
        ('temperature', 'Temperatura'),
        ('spo2', 'Saturación O2'),
        ('wbc', 'Leucocitos'),
        ('platelets', 'Plaquetas'),
        ('bilirubin_total', 'Bilirrubina'),
        ('creatinine', 'Creatinina'),
        ('lactate', 'Lactato'),
        ('ph', 'pH'),
        ('so2', 'SO2 Arterial')
    ]
    
    for prefijo, nombre in variables:
        col_min = f"{prefijo}_min"
        col_max = f"{prefijo}_max"
        
        if col_min in df.columns and col_max in df.columns:
            # Calculamos medias 
            m_min = df[col_min].mean()
            m_max = df[col_max].mean()
            resumen.append({
                "Variable": nombre,
                "Media Min": m_min,
                "Media Max": m_max,
                "Amplitud Media": m_max - m_min
            })
    
    return pd.DataFrame(resumen)

def obtener_df_para_graficos():
    df = obtener_datos_vitals()
    if df.empty: return df
    
    # Identificamos todas las columnas que terminan en _min o _max
    cols_interes = [c for c in df.columns if c.endswith('_min') or c.endswith('_max')]
    
    
    df_melted = df.melt(
        id_vars=['subject_id', 'stay_id'],
        value_vars=cols_interes,
        var_name='Parametro',
        value_name='Valor'
    )
    return df_melted

# UMBRALES (ZONAS DE ALERTA MÉDICA)
UMBRALES_CRITICOS = {
    'heart_rate_max': {'critico_alto': 130, 'alerta_alto': 110},
    'heart_rate_min': {'critico_bajo': 40, 'alerta_bajo': 50},
    'mbp_min': {'critico_bajo': 60, 'alerta_bajo': 65},
    'resp_rate_max': {'critico_alto': 30, 'alerta_alto': 25},
    'lactate_max': {'critico_alto': 4.0, 'alerta_alto': 2.0},
    'creatinine_max': {'critico_alto': 2.0, 'alerta_alto': 1.5}, # mg/dL
    'ph_min': {'critico_bajo': 7.20, 'alerta_bajo': 7.30},
    'ph_max': {'critico_alto': 7.55, 'alerta_alto': 7.45},
    'spo2_min': {'critico_bajo': 88, 'alerta_bajo': 92},
    'wbc_max': {'critico_alto': 20.0, 'alerta_alto': 12.0}, 
    'platelets_min': {'critico_bajo': 50, 'alerta_bajo': 100} 
}

