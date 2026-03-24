import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from fpdf import FPDF

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Control de Metraje Pro", layout="wide", page_icon="📊")
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
        creds = Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
        return gspread.authorize(creds).open_by_key(SPREADSHEET_ID).get_worksheet(0)
    except Exception as e:
        st.error(f"Error de Conexión: {e}")
        st.stop()

# --- 2. CARGA Y PROCESAMIENTO DE DATOS ---
hoja = conectar_google()

def cargar_datos():
    try:
        df = pd.DataFrame(hoja.get_all_records())
        if not df.empty:
            df['metraje'] = pd.to_numeric(df['metraje'], errors='coerce').fillna(0)
            df['fecha'] = pd.to_datetime(df['fecha']).dt.date
            # Añadir columna de Mes para filtrar
            df['mes_nombre'] = pd.to_datetime(df['fecha']).dt.strftime('%Y-%m')
        return df
    except:
        return pd.DataFrame(columns=['fecha', 'operador', 'metraje', 'mes_nombre'])

df_raw = cargar_datos()

# --- 3. FUNCIÓN PDF (Filtrado) ---
def generar_pdf_pro(df_pivot, df_stats, mes_sel):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 10, f"REPORTE DE METRAJE - PERIODO {mes_sel}", ln=True, align="C")
    pdf.ln(10)
    
    pdf.set_font("Arial", "B", 10); pdf.cell(190, 10, "HISTORIAL MENSUAL", ln=True)
    cols = df_pivot.columns.tolist(); w = 190 / (len(cols) + 1)
    pdf.set_font("Arial", "B", 9); pdf.cell(w, 8, "Fecha", 1)
    for col in cols: pdf.cell(w, 8, str(col), 1)
    pdf.ln()
    pdf.set_font("Arial", "", 8)
    for fecha, row in df_pivot.iterrows():
        pdf.cell(w, 7, str(fecha), 1)
        for col in cols: pdf.cell(w, 7, f"{row[col]:,.2f}", 1)
        pdf.ln()
    return pdf.output(dest="S").encode("latin-1", "replace")

# --- 4. SEGURIDAD ---
def check_password():
    if "authenticated" not in st.session_state: st.session_state.authenticated = False
    if st.session_state.authenticated: return True
    with st.sidebar.expander("🔑 Acceso Administrativo"):
        pwd = st.text_input("Contraseña", type="password")
        if st.button("Ingresar"):
            if pwd == st.secrets["password"]:
                st.session_state.authenticated = True
                st.rerun()
            else: st.error("Contraseña incorrecta")
    return False

# --- 5. INTERFAZ ---
st.sidebar.title("Configuración")
meses_disponibles = sorted(df_raw['mes_nombre'].unique().tolist(), reverse=True) if not df_raw.empty else [datetime.now().strftime('%Y-%m')]
mes_seleccionado = st.sidebar.selectbox("Seleccione Mes de Reporte:", meses_disponibles)

opcion = st.sidebar.radio("Menú Principal:", ["📊 Reporte Mensual", "📝 Registrar Producción", "🗑️ Eliminar Registro"])

# Filtrar el DataFrame según el mes seleccionado
df_mes = df_raw[df_raw['mes_nombre'] == mes_seleccionado] if not df_raw.empty else df_raw

# --- VISTA 1: REPORTE MENSUAL ---
if opcion == "📊 Reporte Mensual":
    st.header(f"📅 Reporte de {mes_seleccionado}")
    if not df_mes.empty:
        # Cálculos del mes
        stats = df_mes.groupby('operador')['metraje'].agg(['sum', 'mean', 'count']).reset_index()
        stats.columns = ['Operador', 'Suma Total (m)', 'Promedio Individual (m)', 'Días Registrados']
        stats = stats.sort_values(by='Promedio Individual (m)', ascending=False)
        df_pivot = df_mes.pivot_table(index='fecha', columns='operador', values='metraje', aggfunc='sum').fillna(0).sort_index(ascending=False)
        
        pdf_data = generar_pdf_pro(df_pivot, stats, mes_seleccionado)
        st.download_button(f"📄 Descargar PDF {mes_seleccionado}", data=pdf_data, file_name=f"reporte_{mes_seleccionado}.pdf")
        
        st.markdown("---")
        st.subheader("📋 Historial del Mes")
        st.dataframe(df_pivot, use_container_width=True)
        
        st.markdown("---")
        st.subheader("🏆 Ranking de Eficiencia (Mes)")
        st.table(stats.style.format({'Suma Total (m)': '{:,.2f}', 'Promedio Individual (m)': '{:,.2f}'}))
        
        col_g1, col_g2 = st.columns(2)
        with col_g1: st.bar_chart(data=stats, x="Operador", y="Suma Total (m)", color="#1E88E5")
        with col_g2: st.bar_chart(data=stats, x="Operador", y="Promedio Individual (m)", color="#FFC107")
    else:
        st.info(f"No hay registros para el mes {mes_seleccionado}.")

# --- VISTA 2: REGISTRO ---
elif opcion == "📝 Registrar Producción":
    if check_password():
        st.subheader("📝 Nuevo Registro")
        with st.form("reg", clear_on_submit=True):
            c1, c2 = st.columns(2)
            op = c1.selectbox("Operador:", ["Gabriel", "Adrian", "Freddy"])
            fec = c1.date_input("Fecha:", datetime.now())
            val = c2.number_input("Metraje:", min_value=0.0)
            if st.form_submit_button("💾 Guardar"):
                ya_existe = not df_raw[(df_raw['fecha'] == fec) & (df_raw['operador'] == op)].empty
                if ya_existe: st.error("❌ Ya existe un registro para esta fecha.")
                else:
                    hoja.append_row([str(fec), op, round(val, 2)])
                    st.success("Guardado correctamente")
                    st.rerun()
    else: st.warning("🔒 Ingrese contraseña en el menú lateral.")

# --- VISTA 3: ELIMINAR ---
elif opcion == "🗑️ Eliminar Registro":
    if check_password():
        st.subheader("🗑️ Eliminar Registro")
        if not df_raw.empty:
            df_desc = df_raw.copy()
            df_desc['id'] = df_desc.index + 2
            df_desc['lbl'] = df_desc['fecha'].astype(str) + " | " + df_desc['operador'] + " | " + df_desc['metraje'].astype(str) + "m"
            reg_id = st.selectbox("Seleccione registro:", options=df_desc['id'].tolist(), format_func=lambda x: df_desc[df_desc['id'] == x]['lbl'].values[0])
            
            if "del_confirm" not in st.session_state: st.session_state.del_confirm = False
            if not st.session_state.del_confirm:
                if st.button("🗑️ Borrar seleccionado"):
                    st.session_state.del_confirm = True
                    st.rerun()
            else:
                st.error("⚠️ ¿Eliminar definitivamente?")
                c_si, c_no = st.columns(2)
                if c_si.button("✅ SÍ", type="primary"):
                    hoja.delete_rows(int(reg_id)); st.session_state.del_confirm = False; st.rerun()
                if c_no.button("❌ NO"): st.session_state.del_confirm = False; st.rerun()
    else: st.warning("🔒 Ingrese contraseña en el menú lateral.")
