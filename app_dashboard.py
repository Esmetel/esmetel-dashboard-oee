import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from streamlit_option_menu import option_menu
from fpdf import FPDF
import os

# ---------------------------------------------------------
# 1. CONFIGURACIÓN E IDENTIDAD CORPORATIVA ESMETEL
# ---------------------------------------------------------
st.set_page_config(
    page_title="ESMETEL Perú - OEE Dashboard",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

HEX_DARK_TEAL = "#1A4D54"
HEX_YELLOW = "#FFB703"
HEX_STEEL_GRAY = "#2B3A42"
HEX_SUCCESS_TEAL = "#2A9D8F"
HEX_ALERT_RED = "#D90429"
HEX_BG_LIGHT = "#F4F6F8"

# Enlace CSV publicado de Google Sheets
URL_SHEETS_CSV_DEFAULT = ""

st.markdown(f"""
<style>
    .stApp {{ background-color: {HEX_BG_LIGHT}; }}
    .esmetel-banner {{
        background-color: {HEX_DARK_TEAL};
        border-bottom: 5px solid {HEX_YELLOW};
        padding: 20px 25px;
        border-radius: 10px;
        color: #FFFFFF;
        margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        text-align: center;
    }}
    .esmetel-banner h1 {{ color: #FFFFFF !important; margin: 0; font-size: 2.2rem; font-weight: 800; }}
    .esmetel-banner p {{ color: {HEX_YELLOW} !important; margin: 5px 0 0 0; font-size: 1.05rem; }}
    div[data-testid="stMetric"] {{
        background-color: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        border-top: 4px solid {HEX_DARK_TEAL} !important;
        padding: 16px !important;
        border-radius: 10px !important;
        box-shadow: 0 3px 10px rgba(0,0,0,0.04) !important;
    }}
    section[data-testid="stSidebar"] {{
        background-color: #FFFFFF !important;
        border-right: 1px solid #E2E8F0;
    }}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# FUNCIONES DE CARGA DE DATOS Y GENERACIÓN DE PDF
# ---------------------------------------------------------
@st.cache_data(ttl=10) # Refresco automático de Google Sheets cada 10 segundos
def cargar_datos_google_sheets(url_csv):
    if not url_csv:
        return pd.DataFrame(), False
    try:
        df = pd.read_csv(url_csv)
        return df, True
    except Exception:
        return pd.DataFrame(), False

@st.cache_data
def cargar_datos_historicos(filepath='registro_operativo_esmetel.xlsx'):
    if os.path.exists(filepath):
        df_paradas = pd.read_excel(filepath, sheet_name='paradas_soldadoras')
        df_prod = pd.read_excel(filepath, sheet_name='produccion_turnos')
    else:
        np.random.seed(42)
        fechas = pd.date_range(start="2026-01-01", periods=90, freq="D")
        df_prod = pd.DataFrame({
            'fecha': np.repeat(fechas, 3),
            'equipo_id': np.tile(['EQ-01', 'EQ-02', 'EQ-03'], 90),
            'tiempo_planificado_min': 480,
            'tiempo_setup_min': 45
        })
        causas = [
            'Desgaste de componentes (Boquillas/Guías)',
            'Deficiente Lubricación / Rodillos',
            'Ausencia de Mantenimiento Preventivo',
            'Falta de Hilo / Material',
            'Falla eléctrica de fuente'
        ]
        paradas_list = []
        for eq in ['EQ-01', 'EQ-02', 'EQ-03']:
            for _ in range(15):
                paradas_list.append({
                    'equipo_id': eq,
                    'tipo_parada': 'No Programada',
                    'duracion_min': np.random.randint(20, 110),
                    'causa_raiz': np.random.choice(causas)
                })
        df_paradas = pd.DataFrame(paradas_list)

    df_prod['setup_tobe_min'] = df_prod['tiempo_setup_min'] * (22.0 / 45.0)
    causas_lup = ['Desgaste de componentes (Boquillas/Guías)', 'Deficiente Lubricación / Rodillos', 'Ausencia de Mantenimiento Preventivo']
    
    paradas_np = df_paradas[df_paradas['tipo_parada'] == 'No Programada'].copy()
    np.random.seed(42)
    paradas_np['erradicada'] = paradas_np.apply(lambda r: (np.random.rand() < 0.70) if r['causa_raiz'] in causas_lup else False, axis=1)
    
    paradas_tobe = paradas_np[~paradas_np['erradicada']].copy()
    paradas_tobe['duracion_tobe_min'] = paradas_tobe['duracion_min'] * 0.65
    
    return df_paradas, df_prod, paradas_tobe

def generar_reporte_pdf(escenario_txt, equipo_txt, disp, mtbf, mttr, h_parada, ganancia_smed, total_lup):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "ESMETEL PERU S.A.C. - REPORTE GERENCIAL OPERATIVO", ln=1, align="C")
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 8, f"Escenario Evaluado: {escenario_txt} | Equipo: {equipo_txt}", ln=1, align="C")
    pdf.ln(5)
    
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "1. RESUMEN DE METRICAS OPERATIVAS (KPIs)", ln=1)
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 7, f"- Disponibilidad Mecanica: {disp:.2f}%", ln=1)
    pdf.cell(0, 7, f"- Confiabilidad (MTBF): {mtbf:.1f} horas", ln=1)
    pdf.cell(0, 7, f"- Mantenibilidad (MTTR): {mttr:.2f} horas", ln=1)
    pdf.cell(0, 7, f"- Horas Improductivas Acumuladas: {h_parada:.1f} horas", ln=1)
    pdf.cell(0, 7, f"- Capacidad Ganada por SMED: +{ganancia_smed:.1f} horas/ano", ln=1)
    pdf.cell(0, 7, f"- Inspecciones LUP-01 Recibidas (Nube): {total_lup} registros", ln=1)
    pdf.ln(5)
    
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "2. DIAGNOSTICO GERENCIAL", ln=1)
    pdf.set_font("Arial", "", 11)
    if disp >= 95.0:
        pdf.multi_cell(0, 6, "ESTADO OPTIMO: La disponibilidad cumple con la meta institucional (>= 95%). Las inspecciones autonomas LUP-01 registradas desde Google Forms resguardan la continuidad operativa.")
    else:
        pdf.multi_cell(0, 6, "ALERTA REQUERIDA: La disponibilidad esta por debajo de la meta (<95%). Se recomienda auditar las frecuencias de falla capturadas en el formulario de campo.")
        
    out = pdf.output(dest="S")
    return bytes(out) if isinstance(out, (bytes, bytearray)) else out.encode("latin-1")

# ---------------------------------------------------------
# INTERFAZ Y NAVEGACIÓN
# ---------------------------------------------------------
with st.sidebar:
    if os.path.exists("logo_esmetel.png"):
        st.image("logo_esmetel.png", use_container_width=True)
    else:
        st.markdown("### 🏗️ **ESMETEL Perú**")
    
    menu_seleccion = option_menu(
        menu_title="Menú Principal",
        options=["Visión General OEE", "Análisis de Paradas", "Datos Campo (Google Sheets)", "Plan & Reporte PDF"],
        icons=["speedometer2", "bar-chart-steps", "cloud-check", "file-earmark-pdf"],
        menu_icon="layers-half",
        default_index=0,
        styles={
            "container": {"padding": "5px!", "background-color": "#FAFAFA"},
            "icon": {"color": HEX_DARK_TEAL, "font-size": "18px"},
            "nav-link": {"font-size": "13px", "text-align": "left", "margin": "0px", "--hover-color": "#EAEAEA"},
            "nav-link-selected": {"background-color": HEX_DARK_TEAL, "color": "#FFFFFF"},
        }
    )
    
    st.markdown("### Filtros Operativos")
    escenario = st.radio("Escenario:", ["TO-BE (Propuesta TPM + SMED)", "AS-IS (Situación Actual)"])
    equipo_sel = st.selectbox("Unidad MIG:", ["Planta General (EQ-01, EQ-02, EQ-03)", "EQ-01", "EQ-02", "EQ-03"])
    
    st.divider()
    st.markdown("### Conexión Google Sheets")
    url_sheets = st.text_input("URL Enlace CSV Publicado:", value=URL_SHEETS_CSV_DEFAULT, help="Pega aquí la URL publicada (.csv) de tu hoja de Google Sheets.")

st.markdown(f"""
<div class="esmetel-banner">
    <h1>Tablero de Control Operativo - ESMETEL</h1>
    <p>Integración Nube Google Forms/Sheets | Monitoreo de Disponibilidad, Confiabilidad (MTBF) y SMED</p>
</div>
""", unsafe_allow_html=True)

df_paradas_asis, df_prod, df_paradas_tobe = cargar_datos_historicos()
df_gs, gs_conectado = cargar_datos_google_sheets(url_sheets)

df_prod_f = df_prod if equipo_sel.startswith("Planta") else df_prod[df_prod['equipo_id'] == equipo_sel]
paradas_asis_f = df_paradas_asis if equipo_sel.startswith("Planta") else df_paradas_asis[df_paradas_asis['equipo_id'] == equipo_sel]
paradas_tobe_f = df_paradas_tobe if equipo_sel.startswith("Planta") else df_paradas_tobe[df_paradas_tobe['equipo_id'] == equipo_sel]

es_tobe = escenario.startswith("TO-BE")
paradas_f = paradas_tobe_f if es_tobe else paradas_asis_f

t_plan_total = df_prod_f['tiempo_planificado_min'].sum()
t_setup_asis = df_prod_f['tiempo_setup_min'].sum()
t_setup_tobe = df_prod_f['setup_tobe_min'].sum()

duracion_col = 'duracion_tobe_min' if es_tobe else 'duracion_min'
horas_parada = paradas_f[duracion_col].sum() / 60.0
num_fallas = len(paradas_f[paradas_f['tipo_parada'] == 'No Programada'])

disp = ((t_plan_total - (horas_parada * 60)) / t_plan_total) * 100
mtbf = ((t_plan_total - (horas_parada * 60)) / 60.0) / max(num_fallas, 1)
mttr = horas_parada / max(num_fallas, 1)
ahorro_smed_horas = (t_setup_asis - t_setup_tobe) / 60.0 if es_tobe else 0.0
total_lup = len(df_gs) if gs_conectado else 0

if menu_seleccion == "Visión General OEE":
    st.subheader("Indicadores de Desempeño Operativo")
    k1, k2, k3, k4, k5 = st.columns(5)
    
    k1.metric("Disponibilidad Mecánica", f"{disp:.2f}%", f"{'Meta Cumplida (≥95%)' if disp>=95.0 else 'Bajo Meta (<95%)'}", delta_color="normal" if disp>=95.0 else "inverse")
    k2.metric("Confiabilidad (MTBF)", f"{mtbf:.1f} h", f"{'Óptimo (≥120h)' if mtbf>=120.0 else 'Crítico (<120h)'}", delta_color="normal" if mtbf>=120.0 else "inverse")
    k3.metric("Mantenibilidad (MTTR)", f"{mttr:.2f} h", f"{'Óptimo (≤2.0h)' if mttr<=2.0 else 'Alto (>2.0h)'}", delta_color="inverse" if mttr<=2.0 else "normal")
    k4.metric("Paradas Improductivas", f"{horas_parada:.1f} h", f"{'En Meta' if horas_parada<=120.0 else 'Exceso de Parada'}", delta_color="inverse" if horas_parada<=120.0 else "normal")
    k5.metric("Checklists LUP (Nube)", f"{total_lup}", "Respuestas Forms", delta_color="normal")

    st.divider()
    c_tacometro, c_andon = st.columns([1.8, 2.2])
    
    with c_tacometro:
        st.subheader("Disponibilidad Mecánica")
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=disp,
            number={'suffix': "%", 'font': {'size': 36}},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': HEX_DARK_TEAL},
                'steps': [
                    {'range': [0, 85], 'color': '#FFD1D1'},
                    {'range': [85, 95], 'color': '#FFEAA7'},
                    {'range': [95, 100], 'color': '#D4EDDA'}
                ],
                'threshold': {'line': {'color': HEX_ALERT_RED, 'width': 4}, 'thickness': 0.75, 'value': 95.0}
            }
        ))
        fig_gauge.update_layout(height=280, margin=dict(l=20, r=20, t=10, b=10))
        st.plotly_chart(fig_gauge, use_container_width=True)

    with c_andon:
        st.subheader("Matriz de Diagnóstico y Andón")
        if disp >= 95.0:
            st.success("**DISPONIBILIDAD ÓPTIMA**:\n\nInspecciones LUP-01 efectivas. Capacidad productiva resguardada.")
        else:
            st.error("**ALERTA EN DISPONIBILIDAD**:\n\nPérdida de horas por paradas no programadas. Auditar checklists de campo.")
            
        if mtbf >= 120.0:
            st.success("**CONFIABILIDAD OK**:\n\nMantenimiento autónomo operativo. Intervalo entre averías superior a 120 horas.")
        else:
            st.warning("**PRECAUCIÓN EN CONFIABILIDAD**:\n\nFrecuencia de fallas elevada. Verificar alineación de guías y alimentador.")

elif menu_seleccion == "Análisis de Paradas":
    col_g1, col_g2 = st.columns([3.2, 2])
    
    with col_g1:
        st.subheader("Diagrama de Pareto - Causas de Parada")
        pareto_df = paradas_f.groupby('causa_raiz')[duracion_col].sum().reset_index()
        pareto_df['horas'] = pareto_df[duracion_col] / 60.0
        pareto_df = pareto_df.sort_values(by='horas', ascending=False)
        pareto_df['acumulado_horas'] = pareto_df['horas'].cumsum()
        total_h = pareto_df['horas'].sum()
        pareto_df['pct_acumulado'] = (pareto_df['acumulado_horas'] / max(total_h, 0.001)) * 100
        
        fig_pareto = go.Figure()
        fig_pareto.add_trace(go.Bar(x=pareto_df['causa_raiz'], y=pareto_df['horas'], name="Horas Improductivas", marker_color=HEX_DARK_TEAL, text=pareto_df['horas'].round(1), textposition='auto'))
        fig_pareto.add_trace(go.Scatter(x=pareto_df['causa_raiz'], y=pareto_df['pct_acumulado'], name="% Acumulado (Pareto)", yaxis="y2", mode="lines+markers", line=dict(color=HEX_ALERT_RED, width=3), marker=dict(size=8, color=HEX_YELLOW)))
        fig_pareto.update_layout(template="plotly_white", height=420, margin=dict(l=20, r=20, t=30, b=20), yaxis=dict(title="Horas de Parada"), yaxis2=dict(title="% Acumulado", overlaying="y", side="right", range=[0, 110]), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig_pareto, use_container_width=True)

    with col_g2:
        st.subheader("Horas Improductivas por Unidad")
        eq_summary = []
        for eq in ['EQ-01', 'EQ-02', 'EQ-03']:
            p_eq = paradas_tobe_f if es_tobe else paradas_asis_f
            p_eq = p_eq[p_eq['equipo_id'] == eq]
            h_eq = p_eq[duracion_col].sum() / 60.0
            eq_summary.append({'Equipo': eq, 'Horas de Parada': h_eq})
            
        df_eq = pd.DataFrame(eq_summary)
        fig_eq = px.bar(df_eq, x='Equipo', y='Horas de Parada', color='Equipo', text_auto='.1f', color_discrete_map={'EQ-01': HEX_DARK_TEAL, 'EQ-02': HEX_SUCCESS_TEAL, 'EQ-03': HEX_YELLOW})
        fig_eq.update_layout(template="plotly_white", height=420, margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig_eq, use_container_width=True)

elif menu_seleccion == "Datos Campo (Google Sheets)":
    st.subheader("Monitoreo en Vivo de Inspecciones LUP-01")
    st.write("Esta sección lee la hoja de Google Sheets vinculada a tus códigos QR de Google Forms.")
    
    if gs_conectado and not df_gs.empty:
        st.success(f"Conexión exitosa con Google Sheets. Se han recibido **{len(df_gs)} registros** de inspección.")
        st.dataframe(df_gs, use_container_width=True)
    else:
        st.info("💡 **Instrucciones de Vinculación:**\n1. En tu hoja de Google Sheets, ve a **Archivo > Compartir > Publicar en la web**.\n2. Selecciona la hoja de respuestas y elije el formato **Valores separados por comas (.csv)**.\n3. Copia el enlace generado y pégalo en el campo **'URL Enlace CSV Publicado'** en la barra lateral izquierda.")

elif menu_seleccion == "Plan & Reporte PDF":
    st.subheader("Plan de Acción Estratégico TPM / SMED")
    
    matriz_decisiones = pd.DataFrame({
        "Pilares TPM / SMED": ["Mantenimiento Autónomo (LUP-01)", "Estandarización SMED", "Gestión de Repuestos Críticos", "Mantenimiento Planificado"],
        "Diagnóstico AS-IS": [
            "Fallas por falta de lubricación y desgaste prematuro de boquillas/guías.",
            "Tiempos de setup prolongados (45 min promedio) por búsqueda de herramientas.",
            "Demora en reparaciones complejas (MTTR inicial de 2.95 h).",
            "Ausencia de un plan de mantenimiento estructurado por máquina."
        ],
        "Acción Estratégica Implementada (TO-BE)": [
            "Checklist LUP-01 capturado vía Google Forms escaneando el código QR fijo en soldadora.",
            "Matriz modular y separación estandarizada de tareas internas/externas.",
            "SOP estandarizado con Kit de repuestos críticos a pie de máquina.",
            "Rutinas semanales programadas para soldadoras EQ-01, EQ-02 y EQ-03."
        ],
        "Impacto Proyectado": [
            "Erradicación del 70% de fallas mecánicas recurrentes.",
            "Reducción del 51.1% en setup (22 min/cambio) → Capacidad ganada: +309 h/año.",
            "Disminución del MTTR a ≤ 1.97 horas.",
            "Aumento del MTBF a > 150 horas de operabilidad continua."
        ]
    })
    st.dataframe(matriz_decisiones, use_container_width=True, hide_index=True)
    
    st.divider()
    st.subheader("Exportación de Informe Gerencial")
    
    pdf_bytes = generar_reporte_pdf(escenario, equipo_sel, disp, mtbf, mttr, horas_parada, ahorro_smed_horas, total_lup)
    
    st.download_button(
        label="Descargar Reporte Gerencial en PDF",
        data=pdf_bytes,
        file_name=f"Reporte_Gerencial_ESMETEL_{equipo_sel.replace(' ', '_')}.pdf",
        mime="application/pdf"
    )
