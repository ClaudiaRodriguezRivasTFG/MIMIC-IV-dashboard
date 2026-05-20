from pymongo import MongoClient
import pandas as pd

client = MongoClient("mongodb://localhost:27017")
db = client["MIMIC_IV"]
col = db["icu_stay"]


def obtener_unidades_uci():
    unidades = col.distinct("first_careunit")
    unidades = sorted([u for u in unidades if u])
    return ["(Todas)"] + unidades


def obtener_df_ocupacion(careunit="(Todas)"):
    query = {}

    if careunit != "(Todas)":
        query["first_careunit"] = careunit

    projection = {
        "_id": 0,
        "subject_id": 1,
        "hadm_id": 1,
        "stay_id": 1,
        "first_careunit": 1,
        "los_icu": 1,
        "anchor_year_group": 1,
        "admission_type": 1,
        "gender": 1,
        "anchor_age":1
    }

    docs = list(col.find(query, projection))
    df = pd.DataFrame(docs)

    if df.empty:
        return df

    df["los_icu"] = pd.to_numeric(df["los_icu"], errors="coerce")
    df["anchor_age"] = pd.to_numeric(df["anchor_age"], errors="coerce")
    df = df.dropna(subset=["first_careunit", "los_icu", "anchor_year_group"])

    return df


def ingresos_por_unidad(careunit="(Todas)"):
    df = obtener_df_ocupacion(careunit)

    if df.empty:
        return pd.DataFrame()

    res = (
        df["first_careunit"]
        .value_counts()
        .reset_index()
    )
    res.columns = ["Unidad UCI", "Ingresos"]
    return res


def estancia_media_por_unidad(careunit="(Todas)"):
    df = obtener_df_ocupacion(careunit)

    if df.empty:
        return pd.DataFrame()

    res = (
        df.groupby("first_careunit", as_index=False)["los_icu"]
        .mean()
        .sort_values("los_icu", ascending=False)
    )
    res.columns = ["Unidad UCI", "Estancia media UCI"]
    res["Estancia media UCI"] = res["Estancia media UCI"].round(2)
    return res


def ingresos_por_periodo(careunit="(Todas)"):
    df = obtener_df_ocupacion(careunit)

    if df.empty:
        return pd.DataFrame()

    res = (
        df["anchor_year_group"]
        .value_counts()
        .sort_index()
        .reset_index()
    )
    res.columns = ["Periodo", "Ingresos"]
    return res


def ocupacion_unidad_periodo(careunit="(Todas)"):
    df = obtener_df_ocupacion(careunit)

    if df.empty:
        return pd.DataFrame()

    res = (
        df.groupby(["anchor_year_group", "first_careunit"])
        .size()
        .reset_index(name="Ingresos")
    )
    res.columns = ["Periodo", "Unidad UCI", "Ingresos"]
    return res

def distribucion_tipo_ingreso(careunit):
    df = obtener_df_ocupacion(careunit)

    if df.empty:
        return pd.DataFrame()

    res = (
        df["admission_type"]
        .value_counts()
        .reset_index()
    )
    res.columns = ["Tipo de ingreso", "Ingresos"]
    return res


def distribucion_sexo(careunit):
    df = obtener_df_ocupacion(careunit)

    if df.empty:
        return pd.DataFrame()

    res = (
        df["gender"]
        .value_counts()
        .reset_index()
    )
    res.columns = ["Sexo", "Ingresos"]
    return res

def distribucion_estancia_por_grupos(careunit):
    df = obtener_df_ocupacion(careunit)

    if df.empty:
        return pd.DataFrame()

    bins = [0, 1, 3, 7, 14, 1000]
    labels = ["0–1 días", "1–3 días", "3–7 días", "7–14 días", "14+ días"]

    df["grupo_estancia"] = pd.cut(
        df["los_icu"],
        bins=bins,
        labels=labels,
        right=False,
        include_lowest=True
    )

    df["grupo_estancia"] = pd.Categorical(
        df["grupo_estancia"],
        categories=labels,
        ordered=True
    )

    res = (
        df.groupby("grupo_estancia",observed=False)
        .size()
        .reindex(labels, fill_value=0)
        .reset_index(name="Ingresos")
    )
        
    
    res.columns = ["Grupo de estancia", "Ingresos"]
    return res


def distribucion_edad_por_grupos(careunit):
    df = obtener_df_ocupacion(careunit)

    if df.empty:
        return pd.DataFrame()

    
    if "anchor_age" not in df.columns:
        return pd.DataFrame()

    df["anchor_age"] = pd.to_numeric(df["anchor_age"], errors="coerce")
    df = df.dropna(subset=["anchor_age"])

    bins = [18, 30, 40, 50, 60, 70, 80, 90, 200]
    labels = ["18–29", "30–39", "40–49", "50–59", "60–69", "70–79", "80–89", "90+"]

    df["grupo_edad"] = pd.cut(
        df["anchor_age"],
        bins=bins,
        labels=labels,
        right=False,
        include_lowest=True
    )

    res = (
        df["grupo_edad"]
        .value_counts()
        .sort_index()
        .reset_index()
    )

    res.columns = ["Grupo de edad", "Ingresos"]
    return res

def carga_asistencial_por_unidad():
    df_ing = ingresos_por_unidad("(Todas)")
    df_est = estancia_media_por_unidad("(Todas)")

    if df_ing.empty or df_est.empty:
        return pd.DataFrame()

    df = pd.merge(df_ing, df_est, on="Unidad UCI", how="inner")

    df["Carga asistencial"] = (
        df["Ingresos"] * df["Estancia media UCI"]
    ).round(2)

    df = df.sort_values("Carga asistencial", ascending=False)

    return df


def charlson_por_unidad():
    col_diag = db["diagnosis_icu"]
    col_icu = db["icu_stay"]

    docs_diag = list(
        col_diag.find(
            {},
            {
                "_id": 0,
                "subject_id": 1,
                "hadm_id": 1,
                "charlson_index": 1
            }
        )
    )

    docs_icu = list(
        col_icu.find(
            {},
            {
                "_id": 0,
                "subject_id": 1,
                "hadm_id": 1,
                "stay_id": 1,
                "first_careunit": 1
            }
        )
    )

    if not docs_diag or not docs_icu:
        return pd.DataFrame()

    df_diag = pd.DataFrame(docs_diag)
    df_icu = pd.DataFrame(docs_icu)

    df_diag["charlson_index"] = pd.to_numeric(df_diag["charlson_index"], errors="coerce")

    # Para no repetir Charlson muchas veces por cada diagnóstico del mismo ingreso
    df_diag = df_diag.dropna(subset=["charlson_index"])
    df_diag = df_diag.drop_duplicates(subset=["subject_id", "hadm_id"])

    df_icu = df_icu.dropna(subset=["first_careunit"])
    df_icu = df_icu.drop_duplicates(subset=["subject_id", "hadm_id", "stay_id"])

    df = pd.merge(df_icu, df_diag, on=["subject_id", "hadm_id"], how="inner")

    if df.empty:
        return pd.DataFrame()

    res = (
        df.groupby("first_careunit", as_index=False)["charlson_index"]
        .mean()
        .sort_values("charlson_index", ascending=False)
    )

    res.columns = ["Unidad UCI", "Charlson medio"]
    res["Charlson medio"] = res["Charlson medio"].round(2)

    return res


def carga_y_charlson_por_unidad():
    df_carga = carga_asistencial_por_unidad()
    df_charlson = charlson_por_unidad()

    if df_carga.empty or df_charlson.empty:
        return pd.DataFrame()

    df = pd.merge(df_carga, df_charlson, on="Unidad UCI", how="left")
    return df


def benchmark_unidades(unidad_a, unidad_b):
    df = carga_y_charlson_por_unidad()

    if df.empty:
        return pd.DataFrame()

    df = df[df["Unidad UCI"].isin([unidad_a, unidad_b])].copy()

    return df[[
        "Unidad UCI",
        "Ingresos",
        "Estancia media UCI",
        "Carga asistencial",
        "Charlson medio"
    ]]


def crecimiento_por_unidad():
    df = obtener_df_ocupacion("(Todas)")

    if df.empty:
        return pd.DataFrame()

    df_count = (
        df.groupby(["first_careunit", "anchor_year_group"])
        .size()
        .reset_index(name="Ingresos")
    )

    periodos = sorted(df_count["anchor_year_group"].dropna().unique())

    resultados = []

    for unidad in df_count["first_careunit"].unique():
        df_u = df_count[df_count["first_careunit"] == unidad]

        primer_periodo = periodos[0]
        ultimo_periodo = periodos[-1]

        ingresos_inicio = df_u[df_u["anchor_year_group"] == primer_periodo]["Ingresos"].sum()
        ingresos_final = df_u[df_u["anchor_year_group"] == ultimo_periodo]["Ingresos"].sum()

        if ingresos_inicio > 0:
            crecimiento_pct = ((ingresos_final - ingresos_inicio) / ingresos_inicio) * 100
        else:
            crecimiento_pct = None

        resultados.append({
            "Unidad UCI": unidad,
            "Periodo inicial": primer_periodo,
            "Ingresos iniciales": ingresos_inicio,
            "Periodo final": ultimo_periodo,
            "Ingresos finales": ingresos_final,
            "Crecimiento (%)": round(crecimiento_pct, 1) if crecimiento_pct is not None else None
        })

    df_res = pd.DataFrame(resultados)
    df_res = df_res.dropna(subset=["Crecimiento (%)"])
    df_res = df_res.sort_values("Crecimiento (%)", ascending=False)

    return df_res
