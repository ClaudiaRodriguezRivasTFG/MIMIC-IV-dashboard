import streamlit as st
import pandas as pd
import altair as alt



st.set_page_config(
    page_title="MIMIC-IV Dashboard",
    layout="wide"
)

# Inicializamos el estado del perfil si no existe
if 'perfil' not in st.session_state:
    st.session_state.perfil = None

# PANTALLA DE SELECCIÓN DE PERFIL 
def mostrar_seleccion_perfil():
    st.title(" MIMIC-IV Analytics Platform")
    st.subheader("Bienvenido al sistema de análisis de datos. Por favor, seleccione su perfil:")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("### Perfil Médico")
        st.write("Enfoque en el paciente individual, alertas críticas y soporte a la decisión clínica.")
        if st.button("Acceder como Médico", use_container_width=True):
            st.session_state.perfil = "Médico"
            st.rerun()
            
    with col2:
        st.success("### Perfil Investigador")
        st.write("Enfoque en tendencias poblacionales, estadística avanzada y análisis de cohortes.")
        if st.button("Acceder como Investigador", use_container_width=True):
            st.session_state.perfil = "Investigador"
            st.rerun()

def cambiar_a_modulo(nombre_modulo):
    
    st.session_state.modulo_actual = nombre_modulo
    st.session_state.navegador_principal_key = nombre_modulo

# SIDEBAR DINÁMICO
def configurar_sidebar():
    st.sidebar.title("MIMIC-IV Dashboard")
    
    # Selector de perfil en el sidebar para cambiar rápido
    perfil_actual = st.session_state.perfil
    nuevo_perfil = st.sidebar.selectbox(
        "Cambiar Perfil:",
        ["Médico", "Investigador"],
        index=0 if perfil_actual == "Médico" else 1
    )
    
    # Si el usuario cambia el selector, actualiza la sesión
    if nuevo_perfil != perfil_actual:
        st.session_state.perfil = nuevo_perfil
        st.rerun()
    
    st.sidebar.divider()
    
    # Menú de navegación ( barra lateral)
    st.sidebar.header("Módulos Disponibles")
    opciones = ["Inicio", "Pacientes", "Diagnósticos", "UCI / Estancias", "AKI", "Sepsis", "Laboratorio / Constantes", "Ventilación"]
    
    # Inicializamos el estado del módulo si no existe
    if "modulo_actual" not in st.session_state:
        st.session_state.modulo_actual = "Inicio"

    modulo_seleccionado = st.sidebar.selectbox(
        "Seleccione un módulo:", 
        opciones, 
        #index=idx,
        key="modulo_actual"
    )



    return modulo_seleccionado
            
def mostrar_inicio():
    st.title(" MIMIC-IV Dashboard")
    st.markdown("""
    #### Aplicación interactiva para el análisis de datos clínicos de **MIMIC-IV** utilizando **MongoDB (NoSQL)** y **Streamlit**.

    #### Utilice el menú lateral para navegar entre los distintos módulos.
    """)

from accesory import (
    obtener_tipos_admision,
    obtener_sexo_y_edad,
    contar_tipos_admision,
    obtener_top_diagnosticos,
    obtener_lista_diagnosticos,
    obtener_resumen_diagnostico,
    obtener_edad_y_estancia_por_diagnostico
)

from accesory import( obtener_evolucion_diagnostico_por_year_group)
    #obtener_top_diagnostico_por_year_group

# MÓDULO PACIENTES
def mostrar_modulo_pacientes():
    st.title(" Análisis de pacientes ingresados en UCI")

    st.sidebar.header("Filtros de pacientes")
    tipos = obtener_tipos_admision()
    tipo_sel = st.sidebar.selectbox("Tipo de admisión", tipos)

    df = obtener_sexo_y_edad(admission_type=tipo_sel)

    st.info(f"**Filtro aplicado:** {tipo_sel}")

    if df.empty:
        st.warning("No hay datos con ese filtro.")
        st.stop()

    # KPIs
    total_ingresos = len(df)
    edad_media = round(df["anchor_age"].mean(), 1)

    hombres = (df["gender"] == "M").sum()
    mujeres = (df["gender"] == "F").sum()

    pct_hombres = round((hombres / total_ingresos) * 100, 1) if total_ingresos > 0 else 0
    pct_mujeres = round((mujeres / total_ingresos) * 100, 1) if total_ingresos > 0 else 0

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Ingresos UCI", total_ingresos)
    kpi2.metric("Edad media", edad_media)
    kpi3.metric("% Hombres", pct_hombres)
    kpi4.metric("% Mujeres", pct_mujeres)

    st.divider()

    col1, col2 = st.columns(2)

    # Gráfico sexo
    with col1:
        st.subheader("Distribución por sexo")
        sex_counts = df["gender"].value_counts()
        
        sex_df = sex_counts.reset_index()
        sex_df.columns = ["Sexo", "Ingresos"]

        # Gráfico tipo donut
        chart = alt.Chart(sex_df).mark_arc(innerRadius=60).encode(
            theta=alt.Theta(field="Ingresos", type="quantitative"),
            color=alt.Color(field="Sexo", type="nominal", 
                                   scale=alt.Scale(range=['#1f77b4', '#ff7f0e'])),
            tooltip=[
                alt.Tooltip("Sexo:N", title="Sexo"),
                alt.Tooltip("Ingresos:Q", title="Número de ingresos")
            ]
        ).properties(height=300)

        st.altair_chart(chart, use_container_width=True)

    # Gráfico edad
    with col2:
        st.subheader("Distribución por grupos de edad")

        bins = [18, 30, 40, 50, 60, 70, 80, 90, 200]
        labels = ["18–29", "30–39", "40–49", "50–59", "60–69", "70–79", "80–89", "90+"]

        df["grupo_edad"] = pd.cut(
            df["anchor_age"],
            bins=bins,
            labels=labels,
            right=False,
            include_lowest=True
        )

        age_counts = df["grupo_edad"].value_counts().sort_index()
        age_df = age_counts.reset_index()
        age_df.columns = ["Grupo de edad", "Ingresos"]

        chart = alt.Chart(age_df).mark_bar().encode(
            x=alt.X("Grupo de edad:N", title="Grupo de edad"),
            y=alt.Y("Ingresos:Q", title="Número de ingresos"),
            tooltip=[
                alt.Tooltip("Grupo de edad:N", title="Grupo de edad"),
                alt.Tooltip("Ingresos:Q", title="Número de ingresos")
            ]
        )

        st.altair_chart(chart, use_container_width=True)

    # Mostrar distribución de tipo de admisión solo si no hay filtro específico
    if tipo_sel == "(Todos)":
        st.divider()
        st.subheader("Distribución por tipo de admisión")

        adm_data = contar_tipos_admision()
        adm_df = pd.DataFrame(adm_data)

        if not adm_df.empty:
            adm_df = adm_df.rename(columns={"_id": "Tipo de admisión", "total": "Ingresos"})
            st.bar_chart(adm_df.set_index("Tipo de admisión")["Ingresos"])


# MÓDULO DIAGNÓSTICOS
from accesory import (crear_top_diagnostico_por_periodo,obtener_top_diagnostico_por_periodo, obtener_sexo_por_diagnostico,
                      obtener_datos_complejidad_diagnostico,obtener_mortalidad_por_edad,obtener_analisis_reingresos,
                      obtener_distribucion_unidades)
@st.cache_data
def cargar_evolucion_diagnostico(diagnostico):
    return obtener_evolucion_diagnostico_por_year_group(diagnostico)

@st.cache_data
def cargar_top_diagnostico_por_periodo():
    return obtener_top_diagnostico_por_periodo()

def mostrar_modulo_diagnosticos():
    st.title("Análisis de diagnósticos")

    st.subheader("Top 10 diagnósticos más frecuentes")

    df_diag = obtener_top_diagnosticos()

    if not df_diag.empty:
        # Gráfico barras horizontales (Altair)
        chart_top = alt.Chart(df_diag).mark_bar().encode(
            x=alt.X('Ingresos:Q', title="Número de Ingresos"),
            y=alt.Y('Diagnóstico:N', sort='-x', title=""),
            color=alt.value("#007bff")
        ).properties(height=300)
        st.altair_chart(chart_top, use_container_width=True)

    st.divider()

    st.subheader("Búsqueda de diagnóstico")
    #buscador diagnósticos
    lista_diagnosticos = obtener_lista_diagnosticos()
    diagnostico_sel = st.selectbox(
        "Selecciona un diagnóstico",
        lista_diagnosticos
    )

    resumen = obtener_resumen_diagnostico(diagnostico_sel)
    edad_estancia = obtener_edad_y_estancia_por_diagnostico(diagnostico_sel)
    df_sexo = obtener_sexo_por_diagnostico(diagnostico_sel)

    if resumen is None:
        st.warning("No hay información disponible para este diagnóstico.")
        return

    st.info(f"Diagnóstico seleccionado: {diagnostico_sel}")

    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
    kpi1.metric("Diagnósticos en ingresos con UCI", resumen["n_ingresos"])
    kpi2.metric("Mortalidad (%)", resumen["mortalidad_pct"])
    kpi3.metric("Charlson medio", resumen["charlson_medio"])

    if edad_estancia is not None:
        kpi4.metric("Edad media", edad_estancia["edad_media"])
        kpi5.metric("Estancia media UCI", edad_estancia["estancia_media_uci"])

        
    
    st.write(f"### Análisis Demográfico: {diagnostico_sel}")
        
        # DEMOGRAFÍA (Sexo y Edad)
    col_left, col_right = st.columns(2)

    with col_left:
        st.write("**Distribución por Sexo**")
        if not df_sexo.empty:
            donut = alt.Chart(df_sexo).mark_arc(innerRadius=50).encode(
                theta=alt.Theta(field="Valor", type="quantitative"),
                color=alt.Color(field="Sexo", type="nominal", 
                                   scale=alt.Scale(range=['#1f77b4', '#ff7f0e'])),
                tooltip=["Sexo", "Valor"]
            ).properties(height=250)
            st.altair_chart(donut, use_container_width=True)
        else:
            st.warning("No hay datos de sexo disponibles.")

    with col_right:
        st.write("**Distribución por Grupos de Edad**")
        if edad_estancia and not edad_estancia["distribucion_edad"].empty:
            bar_edad = alt.Chart(edad_estancia["distribucion_edad"]).mark_bar(color='#2ca02c').encode(
                x=alt.X('Grupo de edad:N', title="Rango de Edad", sort=None),
                y=alt.Y('Ingresos:Q', title="Pacientes"),
                tooltip=['Grupo de edad', 'Ingresos']
            ).properties(height=250)
            st.altair_chart(bar_edad, use_container_width=True)

    

        # EVOLUCIÓN 
    st.write("### Evolución de ingresos del diagnóstico por periodo")
    df_evol = obtener_evolucion_diagnostico_por_year_group(diagnostico_sel)

    if not df_evol.empty:
        line_evol = alt.Chart(df_evol).mark_line(point=True, color='red').encode(
            x=alt.X('Periodo:N', title="Periodo"),
            y=alt.Y('Ingresos:Q', title="Nº de Ingresos"),
             tooltip=['Periodo', 'Ingresos']
        ).properties(height=300).interactive()
        st.altair_chart(line_evol, use_container_width=True)
    else:
        st.info("No hay información temporal disponible.")


    
    st.divider()
    
    
    if st.session_state.perfil == "Médico":
        st.subheader(" Panel de Decisión Clínica")
        t1, t2, t3 = st.tabs(["Complejidad y Riesgo", "Benchmark Clínico", "Riesgo por edad"])

        with t1:
            col_a, col_b = st.columns([2, 1])
            
            with col_a:
                st.write("**Relación Edad vs. Comorbilidad (Charlson)**")
                df_comp = obtener_datos_complejidad_diagnostico(diagnostico_sel)
                
                if not df_comp.empty:
                    # Gráfico de dispersión para ver "fragilidad"
                    scatter = alt.Chart(df_comp).mark_point(opacity=0.5, color='red').encode(
                        x=alt.X('anchor_age:Q', title="Edad del Paciente"),
                        y=alt.Y('charlson_index:Q', title="Índice de Charlson"),
                        tooltip=['anchor_age', 'charlson_index', 'los_icu']
                    ).properties(height=350).interactive()
                    
                    st.altair_chart(scatter, use_container_width=True)
                    st.caption("Cada punto representa un paciente. Arriba a la derecha: pacientes de alta complejidad.")
                else:
                    st.info("No hay datos suficientes para el análisis de complejidad.")

            with col_b:
                st.write("**Mortalidad vs. Media**")
            
                mort_media_global = 15.0  # valor función global
                mort_actual = resumen['mortalidad_pct']
                diff = mort_actual - mort_media_global
                
                st.metric("Mortalidad Diagnóstico", f"{mort_actual}%", delta=f"{diff:.1f}% vs Global", delta_color="inverse")
                
                st.write("---")
                st.write("**Predicción de Estancia (LOS)**")
                
                st.info(f"Estancia esperada: **{edad_estancia['estancia_media_uci']} días**")
                st.progress(min(float(edad_estancia['estancia_media_uci']) / 15, 1.0)) # Barra visual hasta 15 días

        with t2:
            st.write("### Comparativa con otro diagnóstico")
            diag_comp = st.selectbox("Comparar con:", lista_diagnosticos, key="comp_medico")
            resumen_comp = obtener_resumen_diagnostico(diag_comp)
            
            if resumen_comp:
                # Tabla comparativa visual
                data_comp = {
                    "Métrica": ["Ingresos", "Mortalidad (%)", "Charlson Medio"],
                    diagnostico_sel: [resumen["n_ingresos"], resumen["mortalidad_pct"], resumen["charlson_medio"]],
                    diag_comp: [resumen_comp["n_ingresos"], resumen_comp["mortalidad_pct"], resumen_comp["charlson_medio"]]
                }
                
                # Convertimos a DataFrame
                df_comp = pd.DataFrame(data_comp)
                
                
                df_formateado = df_comp.style.format({
                    diagnostico_sel: lambda x: f"{x:,.0f}" if isinstance(x, (int, float)) and x == int(x) and x > 100 else f"{x:.2f}" if isinstance(x, (int, float)) else x,
                    diag_comp: lambda x: f"{x:,.0f}" if isinstance(x, (int, float)) and x == int(x) and x > 100 else f"{x:.2f}" if isinstance(x, (int, float)) else x
                })
                
                # Renderizamos la tabla estilizada
                st.table(df_formateado)

        with t3:
            # "Diagnóstico con más ingresos por periodo"
            st.write(f"### Análisis de Riesgo:{diagnostico_sel}")
            st.caption("Probabilidad de fallecimiento hospitalario según grupo de edad para esta patología.")

            df_mort_edad = obtener_mortalidad_por_edad(diagnostico_sel)
        
            if not df_mort_edad.empty:
                col_chart, col_info = st.columns([2, 1])
                
                with col_chart:
                    # Gráfico de barras para visualizar el riesgo
                    chart_mort = alt.Chart(df_mort_edad).mark_bar().encode(
                        x=alt.X('Rango de Edad:N', sort=None),
                        y=alt.Y('% Mortalidad:Q', scale=alt.Scale(domain=[0, 100])),
                        color=alt.condition(
                            alt.datum['% Mortalidad'] > 20, # Si es > 20% resaltar en rojo
                            alt.value('#ff4b4b'), 
                            alt.value('#31333F')
                        ),
                        tooltip=['Rango de Edad', '% Mortalidad']
                    ).properties(height=300)
                    
                    st.altair_chart(chart_mort, use_container_width=True)

                with col_info:
                    st.write("**Resumen de Riesgo**")
                    # Encontrar el grupo de mayor riesgo
                    max_riesgo = df_mort_edad.loc[df_mort_edad['% Mortalidad'].idxmax()]
                    st.error(f"Mayor riesgo: **{max_riesgo['Rango de Edad']}** ({max_riesgo['% Mortalidad']}%)")
                    
                    st.info("""
                    **Nota clínica:** Estos porcentajes se basan en el histórico de la unidad para pacientes con este diagnóstico principal.
                    """)
            else:
                st.warning("No hay datos suficientes para calcular la mortalidad por edad.")
    

    if st.session_state.perfil == "Investigador":
        st.markdown("### Panel de Investigación y Gestión")
        
        t_reingreso, t_unidad, t_evol = st.tabs([
            "Correlación Crítica", 
            "Distribución Unidades",  
            "Evolutivo"
        ])

        with t_reingreso:
            st.write("**Análisis: Mortalidad vs Estancia**")
            st.caption("Identifica si la patología es un evento único o si los pacientes tienden a reingresar múltiples veces.")
        
            df_reingresos = obtener_analisis_reingresos(diagnostico_sel)
            
            if not df_reingresos.empty:
                col_chart, col_stats = st.columns([2, 1])
                
                with col_chart:
                    # Gráfico de barras: X = Veces que han ingresado, Y = Cuántos pacientes
                    bar_reingreso = alt.Chart(df_reingresos).mark_bar(color='#4c78a8').encode(
                        x=alt.X('Nº de Ingresos:O', title="Número de veces que el paciente ingresó"),
                        y=alt.Y('Cantidad de Pacientes:Q', title="Total de Pacientes"),
                        tooltip=['Nº de Ingresos', 'Cantidad de Pacientes']
                    ).properties(height=350)
                    
                    st.altair_chart(bar_reingreso, use_container_width=True)
                
                with col_stats:
                    total_pacientes = df_reingresos["Cantidad de Pacientes"].sum()
                    reincidentes = df_reingresos[df_reingresos["Nº de Ingresos"] > 1]["Cantidad de Pacientes"].sum()
                    porcentaje_fragilidad = (reincidentes / total_pacientes * 100)
                    
                    st.metric("Total Pacientes Únicos", total_pacientes)
                    st.metric("Tasa de Reincidencia", f"{porcentaje_fragilidad:.1f}%")
                    
                    if porcentaje_fragilidad > 20:
                        st.warning(" Alta cronicidad detectada para este diagnóstico.")
                    else:
                        st.success("Predominio de evento agudo único.")
            else:
                st.info("No hay datos de reingresos para este diagnóstico.")

            
        with t_unidad:
            st.write(f"**Distribución por Unidad de Cuidados para: {diagnostico_sel}**")
            df_unidades = obtener_distribucion_unidades(diagnostico_sel)
            
            if not df_unidades.empty:
                df_unidades.columns = ["Unidad", "Pacientes"]
                bar_unidades = alt.Chart(df_unidades).mark_bar().encode(
                    x=alt.X('Pacientes:Q'),
                    y=alt.Y('Unidad:N', sort='-x'),
                    color=alt.value("#4c78a8")
                ).properties(height=300)
                st.altair_chart(bar_unidades, use_container_width=True)
            else:
                st.info("No hay datos de unidades para este diagnóstico.")

      

        with t_evol:
            st.write("### Tendencias del Periodo")
            st.subheader("Diagnóstico con más ingresos en cada periodo")


            df_top_periodo = cargar_top_diagnostico_por_periodo()


            if not df_top_periodo.empty:
                periodos = df_top_periodo["Periodo"].tolist()


                periodo_sel = st.select_slider(
                    "Selecciona un periodo",
                    options=periodos,
                    value=periodos[0]
                )


                fila = df_top_periodo[df_top_periodo["Periodo"] == periodo_sel]


                if not fila.empty:
                    diagnostico_top = fila.iloc[0]["Diagnóstico"]
                    ingresos_top = fila.iloc[0]["Ingresos"]


                    c1, c2 = st.columns(2)
                    c1.metric("Periodo", periodo_sel)
                    c2.metric("Ingresos del diagnóstico top", int(ingresos_top))


                    st.info(f"Diagnóstico top en {periodo_sel}: {diagnostico_top}")


                st.bar_chart(df_top_periodo.set_index("Periodo")["Ingresos"])





# MÓDULO UCI / ESTANCIAS
from ocupacionuci import (
    obtener_unidades_uci,
    ingresos_por_unidad,
    estancia_media_por_unidad,
    ingresos_por_periodo,
    ocupacion_unidad_periodo,
    distribucion_tipo_ingreso,
    distribucion_sexo,
    distribucion_estancia_por_grupos,
    distribucion_edad_por_grupos,
    carga_asistencial_por_unidad,
    carga_y_charlson_por_unidad,
    benchmark_unidades,
    crecimiento_por_unidad
)

def mostrar_modulo_ocupacion():
    st.title("Ocupación UCI")

    st.sidebar.header("Filtros de ocupación")
    unidades = obtener_unidades_uci()
    unidad_sel = st.sidebar.selectbox("Unidad UCI", unidades, key="unidad_ocupacion")


    df_ingresos = ingresos_por_unidad(unidad_sel)
    df_estancia = estancia_media_por_unidad(unidad_sel)
    df_periodo = ingresos_por_periodo(unidad_sel)
    df_heat = ocupacion_unidad_periodo(unidad_sel)

    if df_ingresos.empty:
        st.warning("No hay datos para ese filtro.")
        return

    total_ingresos = int(df_ingresos["Ingresos"].sum())
    total_unidades = int(df_ingresos["Unidad UCI"].nunique()) if unidad_sel == "(Todas)" else 1
    estancia_media_global = round(df_estancia["Estancia media UCI"].mean(), 2) if not df_estancia.empty else 0

    k1, k2, k3 = st.columns(3)
    k1.metric("Ingresos UCI", total_ingresos)
    k2.metric("Unidades analizadas", total_unidades if unidad_sel == "(Todas)" else 1)
    k3.metric("Estancia media global", estancia_media_global)


     # TODAS LAS UNIDADES 
    if unidad_sel == "(Todas)":
        tab1, tab2, tab3, tab4 = st.tabs([
            "Ingresos por unidad",
            "Estancia media",
            "Evolución temporal",
            "Unidad × periodo"
        ])

        with tab1:
            st.subheader("Distribución de ingresos por unidad UCI")

            chart_donut = alt.Chart(df_ingresos).mark_arc(innerRadius=60).encode(
                theta=alt.Theta(field="Ingresos", type="quantitative"),
                color=alt.Color(field="Unidad UCI", type="nominal"),
                tooltip=[
                    alt.Tooltip("Unidad UCI:N", title="Unidad UCI"),
                    alt.Tooltip("Ingresos:Q", title="Ingresos")
                ]
            )

            st.altair_chart(chart_donut, use_container_width=True)

            if st.session_state.perfil == "Médico":
                st.divider()
                st.subheader("Carga asistencial y complejidad por unidad")

                df_carga_charlson = carga_y_charlson_por_unidad()

                if not df_carga_charlson.empty:
                    col_a, col_b = st.columns(2)

                    with col_a:
                        st.markdown("Carga asistencial estimada")

                        chart_carga = alt.Chart(df_carga_charlson).mark_bar().encode(
                            x=alt.X(
                                "Carga asistencial:Q",
                                title="Carga asistencial estimada"
                            ),
                            y=alt.Y(
                                "Unidad UCI:N",
                                sort="-x",
                                title="Unidad UCI"
                            ),
                            tooltip=[
                                alt.Tooltip("Unidad UCI:N", title="Unidad UCI"),
                                alt.Tooltip("Ingresos:Q", title="Ingresos"),
                                alt.Tooltip("Estancia media UCI:Q", title="Estancia media UCI"),
                                alt.Tooltip("Carga asistencial:Q", title="Carga asistencial")
                            ]
                        )

                        st.altair_chart(chart_carga, use_container_width=True)

                    with col_b:
                        st.markdown(" Balanace de Complejidad vs. Ocupación ")
                        chart_charlson = alt.Chart(df_carga_charlson).mark_circle(size=200).encode(
                            x=alt.X(
                                "Ingresos:Q",
                                title="Número de ingresos"
                            ),
                            y=alt.Y(
                                "Charlson medio:Q",
                                title="Charlson medio"
                            ),
                            size=alt.Size(
                                "Carga asistencial:Q",
                                title="Carga asistencial"
                            ),
                            color=alt.Color("Unidad UCI:N", legend=None),
                            tooltip=[
                                alt.Tooltip("Unidad UCI:N", title="Unidad UCI"),
                                alt.Tooltip("Ingresos:Q", title="Ingresos"),
                                alt.Tooltip("Charlson medio:Q", title="Charlson medio"),
                                alt.Tooltip("Carga asistencial:Q", title="Carga asistencial")
                            ]
                        )

                        st.altair_chart(chart_charlson, use_container_width=True)

                    unidad_carga = df_carga_charlson.iloc[0]["Unidad UCI"]
                    unidad_charlson = df_carga_charlson.sort_values(
                        "Charlson medio", ascending=False
                    ).iloc[0]["Unidad UCI"]

                    st.info(
                        f"La unidad con mayor carga asistencial estimada es **{unidad_carga}**. "
                        f"La unidad con mayor complejidad clínica según Charlson medio es **{unidad_charlson}**."
                    )

            if st.session_state.perfil == "Investigador":
                st.divider()
                st.subheader("Benchmark y tendencia entre unidades")

                unidades_sin_todas = [u for u in obtener_unidades_uci() if u != "(Todas)"]

                c1, c2 = st.columns(2)
                with c1:
                    unidad_a = st.selectbox("Unidad A", unidades_sin_todas, key="bench_a")
                with c2:
                    unidad_b = st.selectbox("Unidad B", unidades_sin_todas, index=1, key="bench_b")

                if unidad_a == unidad_b:
                    st.warning("Selecciona dos unidades diferentes para comparar.")
                else:
                    df_bench = benchmark_unidades(unidad_a, unidad_b)

                    if not df_bench.empty:
                        st.markdown("#### Comparación detallada de métricas")
                        st.dataframe(df_bench, use_container_width=True)

                        df_long = df_bench.melt(
                            id_vars="Unidad UCI",
                            value_vars=["Ingresos", "Estancia media UCI", "Carga asistencial", "Charlson medio"],
                            var_name="Métrica",
                            value_name="Valor"
                        )

                        # Creamos el gráfico 
                        chart_bench = alt.Chart(df_long).mark_bar().encode(
                            
                            x=alt.X("Unidad UCI:N", title=None, axis=alt.Axis(labels=False)), 
                            y=alt.Y("Valor:Q", title=None),
                            color=alt.Color("Unidad UCI:N", title="Unidad UCI"),
                            tooltip=[
                                alt.Tooltip("Unidad UCI:N"),
                                alt.Tooltip("Métrica:N"),
                                alt.Tooltip("Valor:Q", format=".2f")
                            ]
                        ).properties(
                            width=150, # Ancho de cada mini-gráfico
                            height=200
                        ).facet(
                            column=alt.Column("Métrica:N", title="Indicadores Comparativos"),
                            columns=4 # Alinea los 4 gráficos en una fila
                        ).resolve_scale(
                            y='independent' # eje y se ajusta a dato
                        )

                        st.altair_chart(chart_bench, use_container_width=True)

                st.divider()
                st.markdown("#### Tendencia de crecimiento por unidad")

                df_heat = ocupacion_unidad_periodo("(Todas)")

                unidades_disponibles = sorted(df_heat["Unidad UCI"].unique())

                unidades_sel = st.multiselect(
                    "Selecciona unidades para comparar",
                    unidades_disponibles,
                    default=unidades_disponibles[:3]
                )

                df_comp = df_heat[df_heat["Unidad UCI"].isin(unidades_sel)]

                chart_comp = alt.Chart(df_comp).mark_line(point=True).encode(
                    x=alt.X("Periodo:N", title="Periodo"),
                    y=alt.Y("Ingresos:Q", title="Número de ingresos"),
                    color=alt.Color("Unidad UCI:N", title="Unidad UCI"),
                    tooltip=[
                        alt.Tooltip("Periodo:N", title="Periodo"),
                        alt.Tooltip("Unidad UCI:N", title="Unidad UCI"),
                        alt.Tooltip("Ingresos:Q", title="Ingresos")
                    ]
                )

                st.altair_chart(chart_comp, use_container_width=True)


        with tab2:
            st.subheader("Estancia media en UCI por unidad")

            chart_scatter = alt.Chart(df_estancia).mark_circle(size=180).encode(
                x=alt.X("Unidad UCI:N", title="Unidad UCI"),
                y=alt.Y("Estancia media UCI:Q", title="Estancia media en UCI (días)"),
                tooltip=[
                    alt.Tooltip("Unidad UCI:N", title="Unidad UCI"),
                    alt.Tooltip("Estancia media UCI:Q", title="Estancia media (días)")
                ]
            )

            st.altair_chart(chart_scatter, use_container_width=True)

        with tab3:
            st.subheader("Evolución temporal de ingresos en UCI")

            chart_line = alt.Chart(df_periodo).mark_line(point=True).encode(
                x=alt.X("Periodo:N", title="Periodo"),
                y=alt.Y("Ingresos:Q", title="Número de ingresos"),
                tooltip=[
                    alt.Tooltip("Periodo:N", title="Periodo"),
                    alt.Tooltip("Ingresos:Q", title="Ingresos")
                ]
            )

            st.altair_chart(chart_line, use_container_width=True)

        with tab4:
            st.subheader("Ingresos por unidad y periodo")

            chart_heat = alt.Chart(df_heat).mark_rect().encode(
                x=alt.X("Periodo:N", title="Periodo"),
                y=alt.Y("Unidad UCI:N", title="Unidad UCI"),
                color=alt.Color("Ingresos:Q", title="Ingresos"),
                tooltip=[
                    alt.Tooltip("Periodo:N", title="Periodo"),
                    alt.Tooltip("Unidad UCI:N", title="Unidad UCI"),
                    alt.Tooltip("Ingresos:Q", title="Ingresos")
                ]
            )

            st.altair_chart(chart_heat, use_container_width=True)

    #  UNIDAD CONCRETA 
    else:
        st.subheader(f"Análisis específico de la unidad: {unidad_sel}")

        df_tipo = distribucion_tipo_ingreso(unidad_sel)
        df_sexo = distribucion_sexo(unidad_sel)
        df_estancia_grupos = distribucion_estancia_por_grupos(unidad_sel)
        df_edad_grupos = distribucion_edad_por_grupos(unidad_sel)

        tab1, tab2, tab3 = st.tabs(["Actividad", "Perfil del paciente", "Estancia"])

        # ACTIVIDAD 
        with tab1:
            st.subheader("Evolución temporal de ingresos en la unidad")

            chart_line = alt.Chart(df_periodo).mark_line(point=True).encode(
                x=alt.X("Periodo:N", title="Periodo"),
                y=alt.Y("Ingresos:Q", title="Número de ingresos"),
                tooltip=[
                    alt.Tooltip("Periodo:N", title="Periodo"),
                    alt.Tooltip("Ingresos:Q", title="Ingresos")
                ]
            )

            st.altair_chart(chart_line, use_container_width=True)

            st.markdown("### Distribución por tipo de ingreso")

            if not df_tipo.empty:
                chart_tipo = alt.Chart(df_tipo).mark_bar().encode(
                    x=alt.X("Tipo de ingreso:N", title="Tipo de ingreso", sort="-y"),
                    y=alt.Y("Ingresos:Q", title="Número de ingresos"),
                    tooltip=[
                        alt.Tooltip("Tipo de ingreso:N", title="Tipo de ingreso"),
                        alt.Tooltip("Ingresos:Q", title="Ingresos")
                    ]
                )

                st.altair_chart(chart_tipo, use_container_width=True)

        # PERFIL DEL PACIENTE 
        with tab2:
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("### Distribución por sexo")

                if not df_sexo.empty:
                    chart_sexo = alt.Chart(df_sexo).mark_arc(innerRadius=50).encode(
                        theta=alt.Theta(field="Ingresos", type="quantitative"),
                        color=alt.Color(field="Sexo", type="nominal"),
                        tooltip=[
                            alt.Tooltip("Sexo:N", title="Sexo"),
                            alt.Tooltip("Ingresos:Q", title="Ingresos")
                        ]
                    )

                    st.altair_chart(chart_sexo, use_container_width=True)

            with col2:
                st.markdown("### Distribución por grupos de edad")

                if not df_edad_grupos.empty:
                    chart_edad = alt.Chart(df_edad_grupos).mark_line(point=True).encode(
                        x=alt.X(
                            "Grupo de edad:N",
                            title="Grupo de edad",
                            sort=["18–29", "30–39", "40–49", "50–59", "60–69", "70–79", "80–89", "90+"]
                        ),
                        y=alt.Y("Ingresos:Q", title="Número de ingresos"),
                        tooltip=[
                            alt.Tooltip("Grupo de edad:N", title="Grupo de edad"),
                            alt.Tooltip("Ingresos:Q", title="Ingresos")
                        ]
                    )

                    st.altair_chart(chart_edad, use_container_width=True)

        # ESTANCIA 
        with tab3:
            st.markdown("### Distribución por grupos de duración de estancia")

            if not df_estancia_grupos.empty:
                base = alt.Chart(df_estancia_grupos).encode(
                    x=alt.X(
                        "Grupo de estancia:N",
                        title="Duración de estancia",
                        sort=["0–1 días", "1–3 días", "3–7 días", "7–14 días", "14+ días"]
                    ),
                    y=alt.Y("Ingresos:Q", title="Número de ingresos")
                )

                lineas = base.mark_rule()
                puntos = base.mark_circle(size=120).encode(
                    tooltip=[
                        alt.Tooltip("Grupo de estancia:N", title="Grupo de estancia"),
                        alt.Tooltip("Ingresos:Q", title="Ingresos")
                    ]
                )

                st.altair_chart(lineas + puntos, use_container_width=True)

            st.info(
                "La distribución por grupos de estancia permite identificar si la actividad "
                "de la unidad se concentra en ingresos cortos, intermedios o prolongados."
            )        

# MÓDULO AKI    
from sepsis_aki import (
    resumen_aki,
    distribucion_aki_stage,
    creatinina_por_stage,
    diuresis_por_stage
)

def mostrar_modulo_aki():
    st.title("Análisis de AKI")

    st.markdown("Exploración clínica de la lesión renal aguda (AKI) a partir de estados, creatinina y diuresis.")

    resumen = resumen_aki()

    if resumen is None:
        st.warning("No hay datos disponibles para el módulo AKI.")
        return

    # KPIs
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Pacientes analizados", f"{resumen['total']:,}")
    k2.metric("% AKI stage 2–3", f"{resumen['pct_aki_23']} %")
    k3.metric("Creatinina media", f"{resumen['creatinina_media']} mg/dL")
    k4.metric("Diuresis media", f"{resumen['diuresis_media']} mL/día")

    st.divider()

    tab1, tab2, tab3 = st.tabs(["Distribución", "Creatinina", "Diuresis"])

    
    with tab1:
        st.subheader("Distribución de estados de AKI")

        df_stage = distribucion_aki_stage()

        if not df_stage.empty:
            chart_stage = alt.Chart(df_stage).mark_arc(innerRadius=55).encode(
                theta=alt.Theta(field="Pacientes", type="quantitative"),
                color=alt.Color(field="AKI stage", type="nominal"),
                tooltip=[
                    alt.Tooltip("AKI stage:N", title="AKI stage"),
                    alt.Tooltip("Pacientes:Q", title="Pacientes")
                ]
            )

            st.altair_chart(chart_stage, use_container_width=True)

            st.markdown("##### ℹInformación")
            st.write("Este gráfico muestra cómo se distribuyen los pacientes entre los distintos estados de lesión renal aguda.")

    
    with tab2:
        st.subheader("Creatinina media según estadio AKI")

        df_creat = creatinina_por_stage()

        if not df_creat.empty:
            chart_creat = alt.Chart(df_creat).mark_line(point=True).encode(
                x=alt.X("AKI stage:N", title="AKI stage"),
                y=alt.Y("Creatinina media:Q", title="Creatinina media (mg/dL)"),
                tooltip=[
                    alt.Tooltip("AKI stage:N", title="AKI stage"),
                    alt.Tooltip("Creatinina media:Q", title="Creatinina media (mg/dL)")
                ]
            ).properties(height=400)

            st.altair_chart(chart_creat, use_container_width=True)

            st.markdown("Permite observar cómo varía el valor medio de creatinina según la gravedad del AKI.")

    
    with tab3:
        st.subheader("Diuresis media según estado AKI")

        df_diur = diuresis_por_stage()

        if not df_diur.empty:
            base = alt.Chart(df_diur).encode(
                x=alt.X("AKI stage:N", title="AKI stage"),
                y=alt.Y("Diuresis media:Q", title="Diuresis media (mL/día)")
            )

            lineas = base.mark_rule()
            puntos = base.mark_circle(size=120, color='#ff7f0e').encode(
                tooltip=[
                    alt.Tooltip("AKI stage:N", title="AKI stage"),
                    alt.Tooltip("Diuresis media:Q", title="Diuresis media (mL/día)",format=".1f")
                ]
            )

            st.altair_chart(lineas + puntos, use_container_width=True)

            st.markdown("La diuresis media permite explorar el comportamiento renal en los distintos estados de AKI.")

# MÓDULO SEPSIS
from sepsis_aki import (
    resumen_sepsis,
    distribucion_sepsis3,
    distribucion_sofa,
    top_antibioticos,
    biomarcadores_sepsis,

)

def mostrar_modulo_sepsis():
    st.title("Análisis de Sepsis")

    st.markdown("Exploración clínica de pacientes con sepsis a partir de gravedad (SOFA), tratamiento antibiótico y biomarcadores del primer día.")

    resumen = resumen_sepsis()

    if resumen is None:
        st.warning("No hay datos disponibles para el módulo Sepsis.")
        return

    # KPIs
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Pacientes analizados", f"{resumen['total']:,}")
    k2.metric("SOFA medio", f"{resumen['sofa_medio']} pts")
    k3.metric("Lactato medio", f"{resumen['lactato_medio']} mmol/L")
    k4.metric("WBC medio", f"{resumen['wbc_medio']} 10³/µL")

    st.divider()

    tab1, tab2, tab3 = st.tabs(["Resumen clínico", "Gravedad", "Biomarcadores"])

    
    with tab1:
        st.subheader("Top antibióticos")
        df_ab = top_antibioticos()

        if not df_ab.empty:
            chart_ab = alt.Chart(df_ab).mark_bar().encode(
                x=alt.X("Pacientes:Q", title="Pacientes"),
                y=alt.Y("Antibiótico:N", sort="-x", title="Antibiótico"),
                tooltip=[
                    alt.Tooltip("Antibiótico:N", title="Antibiótico"),
                    alt.Tooltip("Pacientes:Q", title="Pacientes",format=",")
                ]
            ).properties(height=400)
            st.altair_chart(chart_ab, use_container_width=True)

    
    with tab2:
        st.subheader("Distribución de gravedad según SOFA")
        df_sofa = distribucion_sofa()

        if not df_sofa.empty:
            chart_sofa = alt.Chart(df_sofa).mark_line(point=True, color="red").encode(
                x=alt.X(
                    "Grupo SOFA:N",
                    title="Grupo SOFA",
                    sort=["0–1", "2–3", "4–5", "6–7", "8–9", "10+"]
                ),
                y=alt.Y("Pacientes:Q", title="Pacientes"),
                tooltip=[
                    alt.Tooltip("Grupo SOFA:N", title="Grupo SOFA"),
                    alt.Tooltip("Pacientes:Q", title="Pacientes")
                ]
            )
            st.altair_chart(chart_sofa, use_container_width=True)

            st.markdown("La distribución por grupos de SOFA permite explorar la gravedad clínica dentro de los pacientes con sepsis.")

    
    with tab3:
        st.subheader("Biomarcadores medios")
        df_bio = biomarcadores_sepsis()

        if not df_bio.empty:
            unidades_bio = {
                "Lactato máximo": "mmol/L",
                "WBC máximo": "10³/µL",
                "Bilirrubina total máxima": "mg/dL"
            }
            chart_bio = alt.Chart(df_bio).mark_bar().encode(
                x=alt.X("Biomarcador:N", title="Biomarcador"),
                y=alt.Y("Valor medio:Q", title="Valor medio"),
                tooltip=[
                    alt.Tooltip("Biomarcador:N", title="Biomarcador"),
                    alt.Tooltip("Valor medio:Q", title="Valor medio", format=".2f")
                ]
            ).properties(height=400)
            st.altair_chart(chart_bio, use_container_width=True)

            st.markdown("Se representan biomarcadores relevantes en el contexto de sepsis y disfunción orgánica.")


# MÓDULO SIGNOS VITALES Y LAB
from signosvitales_lab import (obtener_datos_vitals, estadisticas_vitals,obtener_df_para_graficos, UMBRALES_CRITICOS)

def mostrar_modulo_laboratorio():
    st.title("Explorador Clínico Inteligente")
    
    df_raw = obtener_datos_vitals()
    df_plot = obtener_df_para_graficos()
    #df_raw2 = obtener_datos_vitals_2()

    if df_raw.empty:
        st.warning("No hay datos disponibles.")
        return

    

    # PERFIL MÉDICO 
    if st.session_state.perfil == "Médico":
        st.markdown("### Monitorización Clínica Inteligente")

        #
        if 'df_raw' in locals() or 'df_raw' in globals():
            df_sample = df_raw.sample(n=min(1500, len(df_raw)), random_state=42)
            # Filtro  sugerencias: solo pacientes con datos completos en las 4 métricas principales (dropna)
            df_completos = df_raw.dropna(subset=['lactate_max', 'creatinine_max', 'wbc_max', 'temperature_max'])
        else:
            df_sample = pd.DataFrame()
            df_completos = pd.DataFrame()

        # BUSCADOR 
        col_search, col_suggest = st.columns([2, 1])
        with col_search:
            paciente_input = st.text_input("Introduce el Subject ID:", placeholder="Ej: 14210111")
        
        with col_suggest:
            if not df_completos.empty:
                sugerencias_df = df_completos[
                    (df_completos['lactate_max'] > UMBRALES_CRITICOS['lactate_max']['critico_alto']) | 
                    (df_completos['creatinine_max'] > UMBRALES_CRITICOS['creatinine_max']['critico_alto'])
                ].head(10)
                
                paciente_sel = st.selectbox(
                    "Pacientes críticos con datos completos:", 
                    options=["-- Seleccionar --"] + sugerencias_df['subject_id'].astype(str).tolist()
                )
            else:
                paciente_sel = "-- Seleccionar --"

        # Determinar ID seleccionado
        paciente_id = paciente_input if paciente_input else (paciente_sel if paciente_sel != "-- Seleccionar --" else "")
        p_data = df_raw[df_raw['subject_id'].astype(str) == paciente_id] if paciente_id else pd.DataFrame()

        # Funciones de apoyo
        def get_badge_html(val, key):
            u = UMBRALES_CRITICOS.get(key, {})
            if val >= u.get('critico_alto', 999) or val <= u.get('critico_bajo', -999):
                color, texto = "#ff4b4b", "CRÍTICO"
            elif val >= u.get('alerta_alto', 999) or val <= u.get('alerta_bajo', -999):
                color, texto = "#ffa500", "ALERTA"
            else:
                color, texto = "#28a745", "NORMAL"
            return f'<div style="background-color:{color}; color:white; padding:4px; border-radius:5px; text-align:center; font-size:12px; font-weight:bold;">{texto}</div>'

        def format_metric(val):
            return f"{val:.1f}" if pd.notnull(val) else "N/A"

        # Diccionario de unidades para etiquetas de gráficos
        UNIDADES_MAP = {
            'lactate_max': 'mmol/L', 'creatinine_max': 'mg/dL', 'wbc_max': '10³/µL', 
            'temperature_max': '°C', 'heart_rate_max': 'bpm', 'ph_min': 'pH', 'spo2_min': '%'
        }

        # Métricas ( si hay paciente seleccionado)
        if not p_data.empty:
            st.subheader(f" Resumen Clínico: Paciente {paciente_id}")
            c1, c2, c3, c4 = st.columns(4)
            metrica_render = [
                ("Lactato Máx", "lactate_max", c1),
                ("Creatinina Máx", "creatinine_max", c2),
                ("WBC Máx", "wbc_max", c3),
                ("Temp Máx", "temperature_max", c4)
            ]

            for label, key, col in metrica_render:
                val = p_data[key].iloc[0]
                with col:
                    st.metric(label, f"{format_metric(val)} {UNIDADES_MAP.get(key, '')}")
                    st.markdown(get_badge_html(val, key) if pd.notnull(val) else '<div style="background-color:#6c757d; color:white; padding:4px; border-radius:5px; text-align:center; font-size:12px;">SIN DATOS</div>', unsafe_allow_html=True)
            st.divider()
        else:
            st.info("Exploración General: No hay paciente seleccionado. Los gráficos muestran la población crítica de referencia.")

        # 
        tab1, tab2, tab3 = st.tabs(["Riesgo Poblacional", "Inestabilidad", "Correlación"])
            
        with tab1:
            st.subheader("Posicionamiento respecto a la población")
            lista_constantes = list(UMBRALES_CRITICOS.keys())
            sel = st.selectbox("Constante a analizar:", lista_constantes)
                
            base = alt.Chart(df_raw).transform_density(
                sel, as_=[sel, 'density']
            ).mark_area(opacity=0.3, color='gray').encode(
                x=alt.X(f'{sel}:Q', title=f"{sel} ({UNIDADES_MAP.get(sel, '')})"),
                y=alt.Y('density:Q', title="Densidad")
            ).properties(height=300)

            # añadir línea roja si hay paciente y tiene el dato
            if not p_data.empty and pd.notnull(p_data[sel].iloc[0]):
                val_p = p_data[sel].iloc[0]
                indicador = alt.Chart(pd.DataFrame({'x': [val_p]})).mark_rule(color='red', size=3).encode(x='x')
                st.altair_chart((base + indicador).interactive(), use_container_width=True)
            else:
                st.altair_chart(base.interactive(), use_container_width=True)

        with tab2:
            st.subheader("Detección de Inestabilidad (Pacientes Críticos)")
            var_b = st.selectbox("Selecciona constante:", ["lactate", "heart_rate", "creatinine", "temperature"], key="sel_inestab")
            c_min, c_max = f"{var_b}_min", f"{var_b}_max"
                
            # Fondo: Top 1000 más graves de la variable seleccionada
            df_criticos_bg = df_raw.sort_values(by=c_max, ascending=False).head(1000)
                
            chart_base = alt.Chart(df_criticos_bg).mark_circle(size=40, opacity=0.3, color='steelblue').encode(
                x=alt.X(c_min, title=f"Mínimo ({var_b})", scale=alt.Scale(zero=False)),
                y=alt.Y(c_max, title=f"Máximo ({var_b})", scale=alt.Scale(zero=False)),
                tooltip=['subject_id', c_min, c_max]
            )
                
            linea_estabilidad = alt.Chart(pd.DataFrame({'x': [0, 100], 'y': [0, 100]})).mark_line(
                color='gray', strokeDash=[4,4], opacity=0.5
            ).encode(x='x', y='y')
                
            # Añadir marcador de paciente si existe
            if not p_data.empty and pd.notnull(p_data[c_min].iloc[0]):
                marcador = alt.Chart(p_data).mark_point(
                    size=700, shape='star', color='red', fill='yellow', strokeWidth=2
                ).encode(x=c_min, y=c_max, tooltip=['subject_id', c_min, c_max])
                st.altair_chart((chart_base + linea_estabilidad + marcador).interactive(), use_container_width=True)
            else:
                st.altair_chart((chart_base + linea_estabilidad).interactive(), use_container_width=True)

        with tab3:
            st.subheader("Correlación de Órganos (Pacientes Críticos)")
            cx, cy = st.columns(2)
            v1 = cx.selectbox("Variable X (Gravedad):", ["creatinine_max", "lactate_max", "wbc_max"], index=1)
            v2 = cy.selectbox("Variable Y (Fallo):", ["ph_min", "so2_min", "platelets_min"], index=0)
                
            df_criticos_corr = df_raw.sort_values(by=v1, ascending=False).head(1000)
                
            puntos = alt.Chart(df_criticos_corr).mark_circle(opacity=0.3, color='gray').encode(
                x=alt.X(v1, title=v1), 
                y=alt.Y(v2, title=v2),
                tooltip=['subject_id', v1, v2]
            )
                
            # Añadir marcador de paciente si existe
            if not p_data.empty and pd.notnull(p_data[v1].iloc[0]) and pd.notnull(p_data[v2].iloc[0]):
                marcador = alt.Chart(p_data).mark_point(
                    size=600, color='red', fill='yellow', shape='star'
                ).encode(x=v1, y=v2, tooltip=['subject_id', v1, v2])
                st.altair_chart((puntos + marcador).interactive(), use_container_width=True)
            else:
                st.altair_chart(puntos.interactive(), use_container_width=True)

    # PERFIL INVESTIGADOR 
    if st.session_state.perfil == "Investigador":
        st.sidebar.header(" Filtros de Cohorte")
        col_to_filter = st.sidebar.selectbox("Filtrar población por:", ["creatinine_max", "lactate_max", "wbc_max", "ph_min"])
       
        min_val = float(df_raw[col_to_filter].min())
        max_val = float(df_raw[col_to_filter].max())
        rango = st.sidebar.slider(f"Rango de {col_to_filter}:", min_val, max_val, (min_val, max_val))
       
        df_filtered_global = df_raw[(df_raw[col_to_filter] >= rango[0]) & (df_raw[col_to_filter] <= rango[1])].copy()
        st.info(f"**Análisis de Cohorte:** Estás analizando {len(df_filtered_global)} pacientes.")
    
        #CONFIGURACIÓN CLÍNICA
        RANGOS_CLINICOS = {
            'lactate': {'min_normal': 0.5, 'max_normal': 2.0},
            'ph': {'min_normal': 7.35, 'max_normal': 7.45},
            'creatinine': {'min_normal': 0.6, 'max_normal': 1.2},
            'wbc': {'min_normal': 4.5, 'max_normal': 11.0},
            'temperature': {'min_normal': 36.1, 'max_normal': 37.2},
            'so2': {'min_normal': 95.0, 'max_normal': 100.0}
        }

        
        tab4, tab5 = st.tabs(["Desviación de la normalidad","Relevancia y Consecuencias"])

        

        with tab4:
            st.subheader("Análisis de Desviación de la Normalidad")
            
            # Selector de variable
            var_investigada = st.selectbox("Variable a analizar:", list(RANGOS_CLINICOS.keys()), key="var_inv_rango")
            limites = RANGOS_CLINICOS[var_investigada]
            c_min, c_max = f"{var_investigada}_min", f"{var_investigada}_max"

            # CLASIFICACIÓN 
            def clasificar_paciente(row):
                if pd.isna(row[c_min]) or pd.isna(row[c_max]): return "Sin Datos"
                if row[c_min] < limites['min_normal']: return "Bajo (Anómalo)"
                if row[c_max] > limites['max_normal']: return "Alto (Anómalo)"
                return "Normal"

            # Preparación datos
            df_analisis = df_filtered_global.copy()
            df_analisis['Estado_Clinico'] = df_analisis.apply(clasificar_paciente, axis=1)
            df_analisis = df_analisis[df_analisis['Estado_Clinico'] != "Sin Datos"]

            # Métricas
            col1, col2 = st.columns([1, 1])
            with col1:
                st.write(f"**Distribución de Anomalías ({var_investigada.upper()})**")
                stats = df_analisis['Estado_Clinico'].value_counts().reset_index()
                stats.columns = ['Estado', 'Pacientes']
                
                bar_chart = alt.Chart(stats).mark_bar().encode(
                    x='Pacientes:Q',
                    y=alt.Y('Estado:N', sort='-x'),
                    color=alt.Color('Estado:N', scale=alt.Scale(
                        domain=['Normal', 'Alto (Anómalo)', 'Bajo (Anómalo)'],
                        range=['#28a745', '#ff4b4b', '#ffc107']
                    ))
                ).properties(height=200)
                st.altair_chart(bar_chart, use_container_width=True)

            with col2:
                st.write("**Resumen de la Cohorte**")
                n_total = len(df_analisis)
                n_anomalos = len(df_analisis[df_analisis['Estado_Clinico'] != "Normal"])
                st.metric("Total con Datos", n_total)
                st.metric("% Fuera de Rango", f"{(n_anomalos/n_total*100):.1f}%" if n_total > 0 else "0%")
                st.caption(f"Normalidad: {limites['min_normal']} - {limites['max_normal']}")

            st.divider()

            col_para_histograma = c_max if var_investigada != "ph" else c_min
        
            st.write(f"### Explorador de Distribución: {var_investigada.upper()}")
            
            # Slider local para hacer "zoom" en la gráfica
            min_abs = float(df_raw[col_para_histograma].min())
            max_abs = float(df_raw[col_para_histograma].max())
            
            rango_zoom = st.slider(
                f"Ajustar rango visual para {var_investigada}:", 
                min_abs, max_abs, (min_abs, max_abs),
                key="slider_zoom_tab4"
            )

            # Filtrado para la gráfica
            df_grafica = df_analisis[
                (df_analisis[col_para_histograma] >= rango_zoom[0]) & 
                (df_analisis[col_para_histograma] <= rango_zoom[1])
            ].copy()

            st.caption(f"Mostrando {len(df_grafica)} pacientes en el rango seleccionado.")

            hist_clinico = alt.Chart(df_grafica).mark_bar(color='orange').encode(
                x=alt.X(f"{col_para_histograma}:Q", bin=alt.Bin(maxbins=30), title=f"Valor Medido ({var_investigada})"),
                y=alt.Y('count()', title="Número de Pacientes"),
                tooltip=['count()']
            ).properties(height=300).interactive()
            
            st.altair_chart(hist_clinico, use_container_width=True)

                
        

        with tab5:
            st.subheader("Implicaciones Clínicas y Navegación")
            var_consecuencia = st.selectbox("Selecciona variable para ver riesgos:", ["creatinine", "lactate", "ph", "wbc"], key="var_consec")
        
            
            if var_consecuencia == "creatinine":
                # Calculamos cuántos pacientes superan el rango alto
                lim_alto = RANGOS_CLINICOS['creatinine']['max_normal']
                n_riesgo = len(df_filtered_global[df_filtered_global['creatinine_max'] > lim_alto])
                
                st.error(f"### Riesgo Detectado: Fallo Renal (AKI)")
                st.markdown(f"""
                La **Creatinina alta** ({lim_alto} mg/dL) indica una disminución de la filtración glomerular. 
                En esta cohorte filtrada, hay **{n_riesgo} pacientes** con valores por encima de la normalidad.
                
                **Consecuencias:**
                * Retención de toxinas nitrogenadas.
                * Desequilibrio de electrolitos.
                * Posible progresión a fallo multiorgánico.
                """)
                
                # 
                st.info(" ¿Quieres profundizar en estos casos? El módulo AKI analiza la producción de orina y estados de fallo renal.")
                

            elif var_consecuencia == "lactate":
                lim_alto_lact = RANGOS_CLINICOS['lactate']['max_normal']
                n_riesgo = len(df_filtered_global[df_filtered_global['lactate_max'] > lim_alto_lact])
                st.write("El lactato elevado es un marcador de hipoxia tisular y metabolismo anaerobio.")
                st.warning("### Riesgo Detectado: Hiperlactatemia / Sepsis")
                st.markdown(f"""
                El **Lactato elevado** (>{lim_alto_lact} mmol/L) es un marcador de hipoxia tisular y metabolismo anaerobio.
                En esta cohorte, hay **{n_riesgo} pacientes** en situación de posible hipoperfusión.
                
                **Consecuencias:**
                * Acidosis láctica severa.
                * Indicador temprano de Shock Séptico.
                * Mal pronóstico si no se aclara en las primeras 6 horas.
                """)
                st.info("Valores > 4.0 mmol/L requieren intervención hemodinámica inmediata.")
                    
            elif var_consecuencia == "ph":
                lim_bajo_ph = RANGOS_CLINICOS['ph']['min_normal']
                n_riesgo = len(df_filtered_global[df_filtered_global['ph_min'] < lim_bajo_ph])
                #lim_alto = limites['max_normal']
                n_acidosis = len(df_filtered_global[df_filtered_global['ph_min'] < lim_bajo_ph])
                
                st.error("### Riesgo Detectado: Desequilibrio Ácido-Base")
                st.markdown(f"""
                Un **pH bajo** (<{lim_bajo_ph}) indica un estado de acidosis que compromete la función celular.
                En esta cohorte, hay **{n_riesgo} pacientes** con pH por debajo del rango fisiológico.
                
                **Consecuencias:**
                * Disfunción contráctil del corazón.
                * Vasodilatación arterial sistémica.
                * Alteración del nivel de conciencia y coma.
                """)
                #st.info("Cruzar con pCO2 y Bicarbonato para determinar si es respiratoria o metabólica.")

            # WBC (Leucocitosis)
            elif var_consecuencia == "wbc":
                lim_alto_wbc = RANGOS_CLINICOS['wbc']['max_normal']
                n_riesgo = len(df_filtered_global[df_filtered_global['wbc_max'] > lim_alto_wbc])
                
                st.warning("### Riesgo Detectado: Leucocitosis / Inflamación")
                st.markdown(f"""
                Los **Glóbulos Blancos altos** (>{lim_alto_wbc} K/uL) sugieren una respuesta inflamatoria sistémica (SIRS).
                En esta cohorte, hay **{n_riesgo} pacientes** con recuentos elevados.
                
                **Consecuencias:**
                * Infección bacteriana activa o Sepsis.
                * Respuesta inflamatoria sistémica
                * Estrés postquirúrgico o trauma severo.
                * Necesidad de inicio o ajuste de antibioticoterapia.
                """)
                st.info("Revisar si hay desviación a la izquierda (neutrofilia) en los datos de laboratorio.")
            
        

            
# MÓDULO VENTILACIÓN
from ventilacion import (obtener_datos_ventilacion,obtener_datos_escalada, obtener_relacion_estancia, estadisticas_resumen_vent)

def mostrar_modulo_ventilacion():
    st.title("Soporte Respiratorio y Ventilación")
    st.markdown("Análisis de la intensidad, duración y escalada del soporte ventilatorio.")
    
    # Carga de datos
    df_vent = obtener_datos_ventilacion()
    df_res = estadisticas_resumen_vent()
    df_esc = obtener_datos_escalada()
    df_rel = obtener_relacion_estancia()

    if df_vent.empty:
        st.warning("No se encontraron registros en la colección 'icu_ventilation'.")
        return

    # Definición de pestañas
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Distribución de Soporte", 
        "Intensidad de Oxígeno",
        "Tiempo por Estado",
        "Escalada de Soporte",
        "Impacto en Estancia"
    ])

    
    with tab1:
        st.subheader("Jerarquía de los Estados de Ventilación")

        donut = alt.Chart(df_res).mark_arc(innerRadius=60).encode(
        theta=alt.Theta(field="Total_Registros", type="quantitative"),
        color=alt.Color(field="Estado", type="nominal", title="Estado"),
        # Configuramos cada tooltip con su formato de número
        tooltip=[
            alt.Tooltip('Estado:N', title='Estado'),
            alt.Tooltip('Total_Registros:Q', title='Total Registros', format=','), # Formato con separador de miles
            alt.Tooltip('Media_Horas:Q', title='Media Horas', format='.2f')      # Redondeo a 2 decimales
            ]
        ).properties(height=400)
        st.altair_chart(donut, use_container_width=True)
        st.info("Frecuencia de cada tipo de soporte respiratorio registrado.")

    
    with tab2:
        st.subheader("Relación entre Dispositivo y Flujo de O2")
        dispositivos = df_vent['o2_delivery_device_1'].dropna().unique().tolist()
        if dispositivos:
            seleccion = st.multiselect("Filtrar dispositivos:", dispositivos, default=dispositivos[:2])
            df_filt = df_vent[df_vent['o2_delivery_device_1'].isin(seleccion)]
            if not df_filt.empty:
                chart_o2 = alt.Chart(df_filt).mark_boxplot(extent='min-max').encode(
                    x=alt.X('o2_delivery_device_1:N', title="Dispositivo"),
                    y=alt.Y('o2_flow:Q', title="Flujo de O2 (L/min)"),
                    color='o2_delivery_device_1:N'
                ).properties(height=400).interactive()
                st.altair_chart(chart_o2, use_container_width=True)
            else:
                st.info("Selecciona al menos un dispositivo para visualizar.")
        else:
            st.info("No hay información de dispositivos disponible.")

    
    with tab3:
        st.subheader("Permanencia Media por Tipo de Soporte")
        
        chart_duracion = alt.Chart(df_res).mark_bar().encode(
            
            x=alt.X("Media_Horas:Q", title="Horas promedio", axis=alt.Axis(format='.1f')),
            y=alt.Y("Estado:N", sort='-x', title=None),
            color=alt.Color("Media_Horas:Q", scale=alt.Scale(scheme='teals')),
            
            tooltip=[
                alt.Tooltip("Estado:N", title="Tipo de Soporte"),
                alt.Tooltip("Media_Horas:Q", title="Horas Promedio", format=".2f")
            ]
        ).properties(height=300)
        
        st.altair_chart(chart_duracion, use_container_width=True)

    
    with tab4:
        st.subheader("Estado Inicial al Ingreso")
        if not df_esc.empty:
            primer_estado = df_esc.groupby('stay_id').first().reset_index()
            dist_inicio = primer_estado['ventilation_status'].value_counts().reset_index()
            dist_inicio.columns = ['Estado Inicial', 'Pacientes']
            
            chart_inicio = alt.Chart(dist_inicio).mark_bar(cornerRadiusTopRight=10).encode(
                x=alt.X("Pacientes:Q", title="Número de Estancias"),
                y=alt.Y("Estado Inicial:N", sort='-x', title=None),
                color=alt.value("#FF8C00")
            ).properties(height=300)
            st.altair_chart(chart_inicio, use_container_width=True)
            st.caption("Muestra el primer soporte respiratorio documentado para cada estancia.")

    
    with tab5:
        st.subheader("Ventilación Invasiva vs Estancia en UCI")
        if not df_rel.empty:
            scatter = alt.Chart(df_rel).mark_circle(size=60, opacity=0.4).encode(
                x=alt.X("total_vent_horas:Q", title="Horas totales Ventilado (Invasivo)"),
                y=alt.Y("los_icu:Q", title="Días totales en UCI (LOS)"),
                tooltip=[
                    alt.Tooltip("stay_id:N"),
                    alt.Tooltip("total_vent_horas:Q", format=".1f"),
                    alt.Tooltip("los_icu:Q", format=".1f")
                ]
            ).properties(height=400).interactive()
            
            # Línea de tendencia
            line = scatter.transform_regression('total_vent_horas', 'los_icu').mark_line(color='red')
            st.altair_chart(scatter + line, use_container_width=True)
        else:
            st.info("Datos insuficientes para calcular la relación con la estancia (LOS).")

    # (RESUMEN FINAL) 
    st.divider()
    if df_res is not None:
        top_estado = df_res.sort_values(by='Total_Registros', ascending=False).iloc[0]
        c1, c2 = st.columns(2)
        c1.metric("Estado predominante", top_estado['Estado'])
        c2.metric("Duración media sesión", f"{top_estado['Media_Horas']:.1f} horas")
    




# LÓGICA PRINCIPAL (MAIN)
def main():
    # Si no hay perfil seleccionado, pantalla principal inicial
    if st.session_state.perfil is None:
        mostrar_seleccion_perfil()
    else:
        # Si ya hay perfil, configuramos sidebar y se muestra el módulo elegido
        modulo = configurar_sidebar()
        
        # Mostrar el perfil actual como un banner pequeño
        if st.session_state.perfil == "Médico":
            st.sidebar.caption("Modo Clínico Activo")
        else:
            st.sidebar.caption("Modo Investigador Activo")

        # Navegación 
        if modulo == "Inicio":
            mostrar_inicio()

        elif modulo == "Pacientes":
            mostrar_modulo_pacientes()

        elif modulo == "Diagnósticos":
            mostrar_modulo_diagnosticos()

        elif modulo == "UCI / Estancias":
            mostrar_modulo_ocupacion()

        elif modulo == "Laboratorio / Constantes":
            mostrar_modulo_laboratorio()

        elif modulo == "Ventilación":
            mostrar_modulo_ventilacion()

        elif modulo == "AKI":
            mostrar_modulo_aki()

        elif modulo == "Sepsis":
            mostrar_modulo_sepsis()

    
        else:
            st.title(f"Módulo: {modulo}")
            st.info("Este módulo se implementará más adelante.")

if __name__ == "__main__":
    main()
