import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from fpdf import FPDF

# --- 1. CONFIGURACIÓN Y CONEXIÓN ---
st.set_page_config(page_title="Control de Metraje Pro", layout="wide", page_icon="📊")

OPERADORES = ["Gabriel", "Adrian", "Freddy"]
SPREADSHEET_ID = "1BJG1sm8lRUK8TPcw9dNr5oQMIo3fJ93IhWdue5Hh10E"

@st.cache_resource
def conectar_google():
    try:
        info = {
            "type": "service_account",
            "project_id": st.secrets["project_id"].strip(),
            "private_key": st.secrets["private_key"].replace('\\n', '\n').strip(),
            "client_email": st.secrets["client_email"].strip(),
            "token_uri": "https://oauth2.googleapis.com/token",
        }
        creds = Credentials.from_service_account_info(info, scopes=[
            "https://www.googleapis.com/auth/spreadsheets", 
            "https://www.googleapis.com/auth/drive"
        ])
        return gspread.authorize(creds).open_by_key(SPREADSHEET_ID).get_worksheet(0)
    except Exception as e:
        st.error(f"⚠️ Error de Conexión: {e}"); st.stop()

hoja = conectar_google()

@st.cache_data(ttl=30)
def cargar_datos():
    try:
        data = hoja.get_all_values()
        if len(data) < 2:
            return pd.DataFrame(columns=['fecha', 'operador', 'metraje', 'mes_nombre'])
        
        df = pd.DataFrame(data[1:], columns=data[0])
        # Limpieza de decimales para asegurar que Python los reconozca
        df['metraje'] = df['metraje'].astype(str).str.replace(',', '.').str.strip()
        df['metraje'] = pd.to_numeric(df['metraje'], errors='coerce').fillna(0.0).astype(float)
        
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
        df = df.dropna(subset=['fecha'])
        df['mes_nombre'] = df['fecha'].dt.strftime('%Y-%m')
        df['fecha'] = df['fecha'].dt.date
        return df
    except:
        return pd.DataFrame(columns=['fecha', 'operador', 'metraje', 'mes_nombre'])

df_raw = cargar_datos()

# --- 2. FUNCIÓN GENERAR PDF ---
def generar_pdf(df_pivot, mes_sel):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_fill_color(30, 136, 229); pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 12, f"REPORTE DE METRAJE - {mes_sel}", ln=True, align="C", fill=True)
    pdf.set_text_color(0, 0, 0); pdf.ln(10)
    
    cols = ["Fecha"] + df_pivot.columns.tolist()
    w = 190 / len(cols)
    pdf.set_font("Arial", "B", 10); pdf.set_fill_color(240, 240, 240)
    for col in cols: pdf.cell(w, 8, str(col), 1, 0, "C", fill=True)
    pdf.ln()
    
    pdf.set_font("Arial", "", 9)
    for fecha, row in df_pivot.iterrows():
        pdf.cell(w, 7, str(fecha), 1, 0, "C")
        for val in row:
            pdf.cell(w, 7, f"{float(val):g}", 1, 0, "R")
        pdf.ln()
    return pdf.output(dest="S").encode("latin-1", "replace")

# --- 3. CONTROL DE ACCESO ---
def tiene_acceso():
    if st.session_state.get("authenticated"): return True
    with st.sidebar.expander("🔑 ACCESO ADMINISTRATIVO", expanded=True):
        pwd = st.text_input("Contraseña:", type="password")
        if st.button("Validar Acceso", use_container_width=True):
            if pwd == st.secrets["password"]:
                st.session_state.authenticated = True; st.rerun()
            else: st.error("Incorrecta")
    return False

# --- 4. INTERFAZ ---
st.title("📊 Panel de Control de Metraje")

if st.session_state.get("authenticated"):
    if st.sidebar.button("🔓 Cerrar Sesión"):
        st.session_state.authenticated = False; st.rerun()

meses_list = sorted(df_raw['mes_nombre'].unique().tolist(), reverse=True) if not df_raw.empty else [datetime.now().strftime('%Y-%m')]
mes_sel = st.sidebar.selectbox("📅 Seleccionar Mes:", meses_list)
opcion = st.sidebar.radio("Menú Principal:", ["📊 Reporte Mensual", "📝 Registrar Nuevo", "🗑️ Eliminar"])

# --- VISTA 1: REPORTE ---
if opcion == "📊 Reporte Mensual":
    df_mes = df_raw[df_raw['mes_nombre'] == mes_sel].copy()
    if not df_mes.empty:
        # MÉTRICAS GENERALES
        c1, c2, c3 = st.columns(3)
        total_m = df_mes['metraje'].sum()
        c1.metric("Metraje Total del Mes", f"{total_m:g} m")
        c2.metric("Promedio Diario General", f"{df_mes['metraje'].mean():.2f} m")
        c3.metric("Días Registrados", len(df_mes['fecha'].unique()))

        # 1. TABLA HISTORIAL DETALLADO
        df_pivot = df_mes.pivot_table(index='fecha', columns='operador', values='metraje', aggfunc='sum').fillna(0.0).astype(float)
        st.subheader(f"📅 Historial Detallado: {mes_sel}")
        st.dataframe(df_pivot.sort_index(ascending=False).style.format("{:g}").background_gradient(cmap="Blues"), use_container_width=True)

        # Botón de PDF
        pdf_data = generar_pdf(df_pivot, mes_sel)
        st.download_button(f"📄 Descargar PDF {mes_sel}", pdf_data, f"reporte_{mes_sel}.pdf")
        
        st.divider()
        
        # 2. TABLA DE DESEMPEÑO POR OPERADOR
        st.subheader("📈 Resumen de Desempeño por Operador")
        stats = df_mes.groupby('operador')['metraje'].agg(['sum', 'mean', 'count']).reset_index()
        stats.columns = ['Operador', 'Total Metraje (m)', 'Promedio Diario (m)', 'Días Trabajados']
        
        # Mostramos la tabla ocupando el ancho
        st.table(stats.style.format({
            'Total Metraje (m)': '{:g}', 
            'Promedio Diario (m)': '{:g}'
        }))
        
        # 3. GRÁFICA DE BARRAS (Debajo de la tabla)
        st.write("**Gráfica Comparativa: Metraje Total**")
        st.bar_chart(stats, x="Operador", y="Total Metraje (m)", color="Operador")

    else:
        st.info("Sin datos para este período.")

# --- VISTA 2: REGISTRAR ---
elif opcion == "📝 Registrar Nuevo":
    if tiene_acceso():
        st.subheader("📝 Nuevo Registro")
        with st.form("f_reg", clear_on_submit=True):
            c1, c2 = st.columns(2)
            op = c1.selectbox("Operador:", OPERADORES)
            fec = c1.date_input("Fecha:", datetime.now())
            # Forzamos formato decimal en el widget
            val = c2.number_input("Metraje:", min_value=0.0, step=0.01, format="%.2f")
            
            if st.form_submit_button("💾 Guardar Registro", use_container_width=True):
                existe = df_raw[(df_raw['fecha'] == fec) & (df_raw['operador'] == op)]
                if not existe.empty:
                    st.error(f"❌ Ya existe un registro para {op} el {fec}.")
                else:
                    valor_str = str(round(float(val), 2))
                    hoja.append_row([str(fec), op, valor_str])
                    st.cache_data.clear()
                    st.success(f"✅ Guardado: {valor_str} m"); st.rerun()
    else:
        st.warning("🔒 Ingrese contraseña en el panel lateral.")

# --- VISTA 3: ELIMINAR ---
elif opcion == "🗑️ Eliminar":
    if tiene_acceso():
        st.subheader("🗑️ Eliminar Registro")
        if not df_raw.empty:
            df_del = df_raw.copy().sort_values('fecha', ascending=False)
            df_del['id'] = df_del.index + 2
            df_del['lbl'] = df_del.apply(lambda r: f"{r['fecha']} | {r['operador']} | {float(r['metraje']):g}m", axis=1)
            reg_id = st.selectbox("Seleccione:", options=df_del['id'].tolist(), format_func=lambda x: df_del[df_del['id']==x]['lbl'].values[0])
            
            st.warning(f"⚠️ ¿Borrar `{df_del[df_del['id']==reg_id]['lbl'].values[0]}`?")
            if st.checkbox("Confirmo eliminación definitiva."):
                if st.button("🔥 ELIMINAR", type="primary", use_container_width=True):
                    hoja.delete_rows(int(reg_id)); st.cache_data.clear(); st.success("Eliminado"); st.rerun()
        else: st.info("No hay datos.")
