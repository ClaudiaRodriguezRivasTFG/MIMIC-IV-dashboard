from pymongo import MongoClient
import pandas as pd

client = MongoClient("mongodb://localhost:27017")
db = client["MIMIC_IV"]
col = db["icu_stay"]


#MÓDULOS DE PACIENTES Y DIAGNÓSTICOS 

#PACIENTES
def obtener_tipos_admision():
    tipos = col.distinct("admission_type")
    tipos = sorted([t for t in tipos if t])
    return ["(Todos)"] + tipos


def obtener_sexo_y_edad(admission_type="(Todos)"):
    query = {}

    if admission_type != "(Todos)":
        query["admission_type"] = admission_type

    projection = {
        "_id": 0,
        "gender": 1,
        "anchor_age": 1,
        "admission_type": 1
    }

    docs = list(col.find(query, projection))
    df = pd.DataFrame(docs)

    if df.empty:
        return df

    df["anchor_age"] = pd.to_numeric(df["anchor_age"], errors="coerce")
    df = df.dropna(subset=["gender", "anchor_age"])

    return df


def contar_tipos_admision():
    pipeline = [
        {
            "$match": {
                "admission_type": {"$ne": None}
            }
        },
        {
            "$group": {
                "_id": "$admission_type",
                "total": {"$sum": 1}
            }
        },
        {
            "$sort": {"total": -1}
        }
    ]

    return list(col.aggregate(pipeline))


#DIAGNÓSTICOS
def obtener_top_diagnosticos(limit=10):

    docs = list(
        db["diagnoses_top"]
        .find({}, {"_id":0, "icd_long_title":1, "n_admissions":1})
        .sort("n_admissions", -1)
        .limit(limit)
    )

    df = pd.DataFrame(docs)

    df = df.rename(columns={
        "icd_long_title": "Diagnóstico",
        "n_admissions": "Ingresos"
    })

    return df

def obtener_lista_diagnosticos():
    """
    Devuelve la lista de diagnósticos únicos de diagnosis_icu
    para usarla en el selector.
    """
    col_diag = db["diagnosis_icu"]
    diagnosticos = col_diag.distinct("icd_long_title")
    diagnosticos = sorted([d for d in diagnosticos if d])
    return diagnosticos


def obtener_resumen_diagnostico(diagnostico):
    """
    Para un diagnóstico concreto devuelve:
    - número de ingresos
    - mortalidad (%)
    - Charlson medio
    """
    col_diag = db["diagnosis_icu"]

    pipeline = [
        {
            "$match": {
                "icd_long_title": diagnostico
            }
        },
        {
            "$group": {
                "_id": "$icd_long_title",
                "n_ingresos": {"$sum": 1},
                "mortalidad_media": {"$avg": "$hospital_expire_flag"},
                "charlson_medio": {"$avg": "$charlson_index"}
            }
        }
    ]

    resultado = list(col_diag.aggregate(pipeline))

    if not resultado:
        return None

    resumen = resultado[0]

    return {
        "diagnostico": resumen["_id"],
        "n_ingresos": resumen["n_ingresos"],
        "mortalidad_pct": round(resumen["mortalidad_media"] * 100, 1),
        "charlson_medio": round(resumen["charlson_medio"], 2)
    }

def obtener_edad_y_estancia_por_diagnostico(diagnostico):
    """
    Para un diagnóstico concreto, cruza diagnosis_icu con icu_stay
    y devuelve:
    - edad media
    - estancia media en UCI
    """
    col_diag = db["diagnosis_icu"]
    col_icu = db["icu_stay"]

    # Sacar ingresos con ese diagnóstico
    docs_diag = list(
        col_diag.find(
            {"icd_long_title": diagnostico},
            {"_id": 0, "subject_id": 1, "hadm_id": 1}
        )
    )

    if not docs_diag:
        return None

    df_diag = pd.DataFrame(docs_diag)

    # quitar duplicados por si el mismo ingreso aparece varias veces
    df_diag = df_diag.drop_duplicates(subset=["subject_id", "hadm_id"])

    # Sacar datos de icu_stay
    docs_icu = list(
        col_icu.find(
            {},
            {
                "_id": 0,
                "subject_id": 1,
                "hadm_id": 1,
                "anchor_age": 1,
                "los_icu": 1
            }
        )
    )

    if not docs_icu:
        return None

    df_icu = pd.DataFrame(docs_icu)
    df_icu = df_icu.drop_duplicates(subset=["subject_id", "hadm_id"])

    df_icu["anchor_age"] = pd.to_numeric(df_icu["anchor_age"], errors="coerce")
    df_icu["los_icu"] = pd.to_numeric(df_icu["los_icu"], errors="coerce")

    # Cruce entre ambas tablas
    df_merge = pd.merge(df_diag, df_icu, on=["subject_id", "hadm_id"], how="inner")

    if df_merge.empty:
        return None
    
    # Limpiar
    df_merge = df_merge.dropna(subset=["anchor_age", "los_icu"])

    if df_merge.empty:
        return None

    # Calcular medias
    edad_media = round(df_merge["anchor_age"].mean(), 1)
    estancia_media = round(df_merge["los_icu"].mean(), 2)

    # Distribución por grupos de edad
    bins = [18, 30, 40, 50, 60, 70, 80, 90, 200]
    labels = ["18–29", "30–39", "40–49", "50–59", "60–69", "70–79", "80–89", "90+"]

    df_merge["grupo_edad"] = pd.cut(
        df_merge["anchor_age"],
        bins=bins,
        labels=labels,
        right=False,
        include_lowest=True
    )

    distribucion_edad = (
        df_merge["grupo_edad"]
        .value_counts()
        .sort_index()
        .reset_index()
    )

    distribucion_edad.columns = ["Grupo de edad", "Ingresos"]

    return {
        "edad_media": edad_media,
        "estancia_media_uci": estancia_media,
        "distribucion_edad": distribucion_edad
    }

def obtener_sexo_por_diagnostico(diagnostico):
    """
    Cruza diagnosis_icu con la colección patients para obtener
    la distribución por sexo de un diagnóstico.
    """
    col_diag = db["diagnosis_icu"]
    col_icu = db["icu_stay"]

    # Obtener subject_id únicos con ese diagnóstico
    docs_diag = list(
        col_diag.find(
            {"icd_long_title": diagnostico},
            {"_id": 0, "subject_id": 1,"hadm_id": 1}
        )
    )

    if not docs_diag:
        return pd.DataFrame(columns=["Sexo", "Valor"])

    # Convertimos a DF y quitamos duplicados de pacientes 
    df_diag = pd.DataFrame(docs_diag).drop_duplicates(subset=["subject_id","hadm_id"])

    # Obtener datos de sexo de la colección patients
    # traemos los campos necesarios
    docs_icu= list(
        col_icu.find(
            {}, 
            {"_id": 0, "subject_id": 1, "gender": 1,"hadm_id": 1}
        )
    )

    if not docs_icu:
        return pd.DataFrame(columns=["Sexo", "Valor"])

    df_icu = pd.DataFrame(docs_icu)
    df_icu = df_icu.drop_duplicates(subset=["subject_id", "hadm_id"])

    # Cruce (Merge)
    df_merge = pd.merge(df_diag, df_icu, on=["subject_id","hadm_id"], how="inner")

    if df_merge.empty:
        return pd.DataFrame(columns=["Sexo", "Valor"])

    # Conteo y formato para el gráfico
    conteo = df_merge["gender"].value_counts().reset_index()
    conteo.columns = ["Sexo", "Valor"]
    
    # Mapeo 
    conteo["Sexo"] = conteo["Sexo"].map({"M": "Masculino", "F": "Femenino"})
    
    return conteo
    
def obtener_evolucion_diagnostico_por_year_group(diagnostico):
    """
    Devuelve la evolución del número de ingresos en UCI
    para un diagnóstico concreto según anchor_year_group,
    evitando $lookup en Mongo.
    """
    col_diag = db["diagnosis_icu"]
    col_icu = db["icu_stay"]

    # Sacar solo hadm_id/subject_id del diagnóstico elegido
    docs_diag = list(
        col_diag.find(
            {"icd_long_title": diagnostico},
            {"_id": 0, "subject_id": 1, "hadm_id": 1}
        )
    )

    if not docs_diag:
        return pd.DataFrame()

    df_diag = pd.DataFrame(docs_diag).drop_duplicates(subset=["subject_id", "hadm_id"])

    # Sacar solo hadm_id/subject_id + anchor_year_group de icu_stay
    docs_icu = list(
        col_icu.find(
            {},
            {"_id": 0, "subject_id": 1, "hadm_id": 1, "anchor_year_group": 1}
        )
    )

    if not docs_icu:
        return pd.DataFrame()

    df_icu = pd.DataFrame(docs_icu).drop_duplicates(subset=["subject_id", "hadm_id"])

    # Cruce con merge
    df_merge = pd.merge(df_diag, df_icu, on=["subject_id", "hadm_id"], how="inner")

    if df_merge.empty:
        return pd.DataFrame()

    # Contar por periodo
    df_result = (
        df_merge["anchor_year_group"]
        .value_counts()
        .sort_index()
        .reset_index()
    )

    df_result.columns = ["Periodo", "Ingresos"]
    return df_result



def obtener_top_diagnostico_por_periodo():
    """
    Lee la colección preagregada top_diagnosis_year_group.
    """
    col_top = db["top_diagnosis_year_group"]

    docs = list(
        col_top.find(
            {},
            {"_id": 0, "Periodo": 1, "Diagnóstico": 1, "Ingresos": 1}
        ).sort("Periodo", 1)
    )

    return pd.DataFrame(docs)    


#MEDICO
def obtener_datos_complejidad_diagnostico(diagnostico):
    """
    Extrae edad e índice de Charlson para cada ingreso con el diagnóstico dado.
    """
    col_diag = db["diagnosis_icu"]
    col_icu = db["icu_stay"]
    
    # Buscamos ingresos
    docs_diag = list(col_diag.find({"icd_long_title": diagnostico}, {"_id": 0, "subject_id": 1, "hadm_id": 1, "charlson_index":1}))
    if not docs_diag: return pd.DataFrame()
    
    df_diag = pd.DataFrame(docs_diag).drop_duplicates(subset=["subject_id", "hadm_id"])
    
    #  Buscamos edad y charlson en icu_stay 
    docs_icu = list(col_icu.find({}, {"_id": 0, "subject_id": 1, "hadm_id": 1, "anchor_age": 1, "los_icu": 1}))
    df_icu = pd.DataFrame(docs_icu)
    
    # Merge
    df_res = pd.merge(df_diag, df_icu, on=["subject_id", "hadm_id"], how="inner")
    return df_res.dropna(subset=["anchor_age", "charlson_index"])


def obtener_mortalidad_por_edad(diagnostico):
    """
    Calcula el % de mortalidad para cada grupo de edad 
    específicamente para el diagnóstico seleccionado.
    """
    col_diag = db["diagnosis_icu"]
    col_icu = db["icu_stay"]

    # Obtener ingresos y su flag de mortalidad
    docs_diag = list(col_diag.find(
        {"icd_long_title": diagnostico},
        {"_id": 0, "subject_id": 1, "hadm_id": 1, "hospital_expire_flag": 1}
    ))
    if not docs_diag: return pd.DataFrame()
    df_diag = pd.DataFrame(docs_diag).drop_duplicates(subset=["hadm_id"])

    # Obtener edades
    docs_icu = list(col_icu.find({}, {"_id": 0, "hadm_id": 1, "anchor_age": 1}))
    df_icu = pd.DataFrame(docs_icu).drop_duplicates(subset=["hadm_id"])

    # Cruzar
    df_merge = pd.merge(df_diag, df_icu, on="hadm_id", how="inner")

    # Crear grupos de edad (Bins)
    bins = [18, 40, 60, 70, 80, 200]
    labels = ["18-39", "40-59", "60-69", "70-79", "80+"]
    df_merge["rango_edad"] = pd.cut(df_merge["anchor_age"], bins=bins, labels=labels)

    # Calcular mortalidad por grupo
    # La media de hospital_expire_flag (0 o 1) multiplicada por 100 (%)
    df_mort = df_merge.groupby("rango_edad")["hospital_expire_flag"].mean().reset_index()
    df_mort["hospital_expire_flag"] = (df_mort["hospital_expire_flag"] * 100).round(1)
    df_mort.columns = ["Rango de Edad", "% Mortalidad"]
    
    return df_mort



#INVESTIGADOR

def obtener_analisis_reingresos(diagnostico):
    """
    Calcula la frecuencia de ingresos por paciente (subject_id) 
    para un diagnóstico específico.
    """
    col_diag = db["diagnosis_icu"]
    
    #Obtener todos los ingresos para ese diagnóstico
    docs = list(col_diag.find(
        {"icd_long_title": diagnostico}, 
        {"_id": 0, "subject_id": 1, "hadm_id": 1}
    ))
    
    if not docs:
        return pd.DataFrame()
    
    df = pd.DataFrame(docs)
    
    # Contar cuántos hadm_id (ingresos) tiene cada subject_id (paciente)
    reingresos_por_paciente = df.groupby("subject_id")["hadm_id"].count().reset_index()
    reingresos_por_paciente.columns = ["subject_id", "num_ingresos"]
    
    # Agrupar por el número de ingresos para ver la distribución
    distribucion = reingresos_por_paciente["num_ingresos"].value_counts().reset_index()
    distribucion.columns = ["Nº de Ingresos", "Cantidad de Pacientes"]
    distribucion = distribucion.sort_values(by="Nº de Ingresos")
    
    return distribucion

def obtener_distribucion_unidades(diagnostico):
    """
    Muestra en qué unidades de cuidados (MICU, SICU, CCU, etc.) 
    aterriza más el diagnóstico seleccionado.
    """
    col_diag = db["diagnosis_icu"]
    col_icu = db["icu_stay"]
    
    docs_diag = list(col_diag.find({"icd_long_title": diagnostico}, {"hadm_id": 1}))
    df_diag = pd.DataFrame(docs_diag).drop_duplicates()
    
    docs_icu = list(col_icu.find({}, {"hadm_id": 1, "first_careunit": 1}))
    df_icu = pd.DataFrame(docs_icu).drop_duplicates()
    
    df_res = pd.merge(df_diag, df_icu, on="hadm_id", how="inner")
    return df_res["first_careunit"].value_counts().reset_index()







