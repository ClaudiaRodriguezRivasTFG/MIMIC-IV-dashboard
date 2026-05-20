from pymongo import MongoClient
import pandas as pd

client = MongoClient("mongodb://localhost:27017")
db = client["MIMIC_IV"]

col_aki = db["sepsis + aki"]
col_lab = db["firstday_vitalsign_lab"]


def obtener_df_aki():
    """
    Une las colecciones de AKI y laboratorio para analizar:
    - aki_stage
    - urineoutput
    - creatinine_max
    """
    docs_aki = list(
        col_aki.find(
            {},
            {
                "_id": 0,
                "subject_id": 1,
                "stay_id": 1,
                "aki_stage": 1,
                "urineoutput": 1
            }
        )
    )

    docs_lab = list(
        col_lab.find(
            {},
            {
                "_id": 0,
                "subject_id": 1,
                "stay_id": 1,
                "creatinine_max": 1
            }
        )
    )

    if not docs_aki or not docs_lab:
        return pd.DataFrame()

    df_aki = pd.DataFrame(docs_aki)
    df_lab = pd.DataFrame(docs_lab)

    df_aki["aki_stage"] = pd.to_numeric(df_aki["aki_stage"], errors="coerce")
    df_aki["urineoutput"] = pd.to_numeric(df_aki["urineoutput"], errors="coerce")
    df_lab["creatinine_max"] = pd.to_numeric(df_lab["creatinine_max"], errors="coerce")

    df = pd.merge(df_aki, df_lab, on=["subject_id", "stay_id"], how="inner")

    df = df.dropna(subset=["aki_stage"])
    return df


def resumen_aki():
    df = obtener_df_aki()

    if df.empty:
        return None

    total = len(df)
    aki_23 = len(df[df["aki_stage"].isin([2, 3])])
    pct_aki_23 = round((aki_23 / total) * 100, 1) if total > 0 else 0

    creat_media = round(df["creatinine_max"].mean(), 2) if "creatinine_max" in df.columns else None
    diuresis_media = round(df["urineoutput"].mean(), 2) if "urineoutput" in df.columns else None

    return {
        "total": total,
        "pct_aki_23": pct_aki_23,
        "creatinina_media": creat_media,
        "diuresis_media": diuresis_media
    }


def distribucion_aki_stage():
    df = obtener_df_aki()

    if df.empty:
        return pd.DataFrame()

    res = (
        df["aki_stage"]
        .value_counts()
        .sort_index()
        .reset_index()
    )
    res.columns = ["AKI stage", "Pacientes"]
    return res


def creatinina_por_stage():
    df = obtener_df_aki()

    if df.empty:
        return pd.DataFrame()

    res = (
        df.groupby("aki_stage", as_index=False)["creatinine_max"]
        .mean()
        .sort_values("aki_stage")
    )
    res.columns = ["AKI stage", "Creatinina media"]
    res["Creatinina media"] = res["Creatinina media"].round(2)
    return res


def diuresis_por_stage():
    df = obtener_df_aki()

    if df.empty:
        return pd.DataFrame()

    res = (
        df.groupby("aki_stage", as_index=False)["urineoutput"]
        .mean()
        .sort_values("aki_stage")
    )
    res.columns = ["AKI stage", "Diuresis media"]
    res["Diuresis media"] = res["Diuresis media"].round(2)
    return res


from pymongo import MongoClient
import pandas as pd

client = MongoClient("mongodb://localhost:27017")
db = client["MIMIC_IV"]

col_sepsis = db["sepsis + aki"]
col_lab = db["firstday_vitalsign_lab"]


def obtener_df_sepsis():
    """
    Une las colecciones de sepsis y laboratorio para analizar:
    - sepsis3
    - sofa_score
    - antibiotico
    - lactate_max
    - wbc_max
    - bilirubin_total_max
    """
    docs_sepsis = list(
        col_sepsis.find(
            {},
            {
                "_id": 0,
                "subject_id": 1,
                "stay_id": 1,
                "sepsis3": 1,
                "sofa_score": 1,
                "soi_antibiotic": 1
            }
        )
    )

    docs_lab = list(
        col_lab.find(
            {},
            {
                "_id": 0,
                "subject_id": 1,
                "stay_id": 1,
                "lactate_max": 1,
                "wbc_max": 1,
                "bilirubin_total_max": 1
            }
        )
    )

    if not docs_sepsis or not docs_lab:
        return pd.DataFrame()

    df_sepsis = pd.DataFrame(docs_sepsis)
    df_lab = pd.DataFrame(docs_lab)

    # convertir tipos
    df_sepsis["sofa_score"] = pd.to_numeric(df_sepsis["sofa_score"], errors="coerce")
    df_lab["lactate_max"] = pd.to_numeric(df_lab["lactate_max"], errors="coerce")
    df_lab["wbc_max"] = pd.to_numeric(df_lab["wbc_max"], errors="coerce")
    df_lab["bilirubin_total_max"] = pd.to_numeric(df_lab["bilirubin_total_max"], errors="coerce")

    df = pd.merge(df_sepsis, df_lab, on=["subject_id", "stay_id"], how="inner")

    if df.empty:
        return df

    return df


def resumen_sepsis():
    df = obtener_df_sepsis()

    if df.empty:
        return None

    total = len(df)

    sofa_medio = round(df["sofa_score"].mean(), 2) if "sofa_score" in df.columns else None
    lactato_medio = round(df["lactate_max"].mean(), 2) if "lactate_max" in df.columns else None
    wbc_medio = round(df["wbc_max"].mean(), 2) if "wbc_max" in df.columns else None

    return {
        "total": total,
        "sofa_medio": sofa_medio,
        "lactato_medio": lactato_medio,
        "wbc_medio": wbc_medio
    }

def distribucion_sepsis3():
    df = obtener_df_sepsis()

    if df.empty:
        return pd.DataFrame()

    res = (
        df["sepsis3"]
        .astype(str)
        .value_counts()
        .reset_index()
    )
    res.columns = ["Sepsis3", "Pacientes"]
    return res


def distribucion_sofa():
    df = obtener_df_sepsis()

    if df.empty:
        return pd.DataFrame()

    df = df.dropna(subset=["sofa_score"])

    bins = [0, 2, 4, 6, 8, 10, 50]
    labels = ["0–1", "2–3", "4–5", "6–7", "8–9", "10+"]

    df["grupo_sofa"] = pd.cut(
        df["sofa_score"],
        bins=bins,
        labels=labels,
        right=False,
        include_lowest=True
    )

    df["grupo_sofa"] = pd.Categorical(
        df["grupo_sofa"],
        categories=labels,
        ordered=True
    )

    res = (
        df.groupby("grupo_sofa", observed=False)
        .size()
        .reindex(labels, fill_value=0)
        .reset_index(name="Pacientes")
    )

    res.columns = ["Grupo SOFA", "Pacientes"]
    return res


def top_antibioticos(limit=10):
    df = obtener_df_sepsis()

    if df.empty:
        return pd.DataFrame()

    df = df.dropna(subset=["soi_antibiotic"])

    res = (
        df["soi_antibiotic"]
        .value_counts()
        .head(limit)
        .reset_index()
    )

    res.columns = ["Antibiótico", "Pacientes"]
    return res


def biomarcadores_sepsis():
    df = obtener_df_sepsis()

    if df.empty:
        return pd.DataFrame()

    res = pd.DataFrame({
        "Biomarcador": ["Lactato máximo", "WBC máximo", "Bilirrubina total máxima"],
        "Valor medio": [
            round(df["lactate_max"].mean(), 2),
            round(df["wbc_max"].mean(), 2),
            round(df["bilirubin_total_max"].mean(), 2)
        ]
    })

    return res

