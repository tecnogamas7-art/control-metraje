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

# --- 2. CARGA DE DATOS ---
hoja = conectar_google()
def cargar_datos():
    try:
        df = pd.DataFrame(hoja.get_all_records())
        if not df.empty:
            df['metraje'] = pd.to_numeric(df['metraje'], errors='coerce').fillna(0)
            df['fecha'] = pd.to_datetime(df['fecha']).dt.date
        return df
    except:
        return pd.DataFrame(columns=['fecha', 'operador', 'metraje'])

df_raw = cargar_datos()

# --- 3. FUNCIÓN PDF ---
def generar_pdf_pro(df_pivot, df_stats):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 10, "REPORTE DE METRAJE PROFESIONAL", ln=True, align="C")
    pdf.ln(10)
    # Tabla Historial
    pdf.set_font("Arial", "B", 10); pdf.cell(190, 10, "HISTORIAL POR FECHA", ln=True)
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

# --- 4. SISTEMA DE LOGIN ---
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    if st.session_state.authenticated:
        return True

    with st.sidebar.expander("🔑 Acceso Administrativo"):
        pwd = st.text_input("Contraseña", type="password")
        if st.button("Ingresar"):
            if pwd == st.secrets["password"]:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Contraseña incorrecta")
    return False

# --- 5. INTERFAZ ---
st.title("📊 Panel de Control de Metraje")
opcion = st.sidebar.radio("Menú Principal:", ["📊 Historial y Reportes", "📝 Registrar Producción", "🗑️ Eliminar Registro"])

# --- VISTA 1: PÚBLICA (Reportes) ---
if opcion == "📊 Historial y Reportes":
    if not df_raw.empty:
        stats = df_raw.groupby('operador')['metraje'].agg(['sum', 'mean', 'count']).reset_index()
        stats.columns = ['Operador', 'Suma Total (m)', 'Promedio Individual (m)', 'Días Registrados']
        stats = stats.sort_values(by='Promedio Individual (m)', ascending=False)
        df_pivot = df_raw.pivot_table(index='fecha', columns='operador', values='metraje', aggfunc='sum').fillna(0).sort_index(ascending=False)
        
        pdf_data = generar_pdf_pro(df_pivot, stats)
        st.download_button("📄 Descargar Reporte PDF", data=pdf_data, file_name="reporte.pdf")
        
        st.markdown("---")
        st.subheader("📅 Historial por Fecha")
        st.dataframe(df_pivot, use_container_width=True)
        
        st.markdown("---")
        st.subheader("🏆 Ranking de Eficiencia")
        st.table(stats.style.format({'Suma Total (m)': '{:,.2f}', 'Promedio Individual (m)': '{:,.2f}'}))
        
        col_g1, col_g2 = st.columns(2)
        with col_g1: st.bar_chart(data=stats, x="Operador", y="Suma Total (m)", color="#1E88E5")
        with col_g2: st.bar_chart(data=stats, x="Operador", y="Promedio Individual (m)", color="#FFC107")
    else:
        st.info("Sin datos.")

# --- VISTA 2 Y 3: PROTEGIDAS ---
elif opcion in ["📝 Registrar Producción", "🗑️ Eliminar Registro"]:
    if check_password():
        if st.sidebar.button("Cerrar Sesión"):
            st.session_state.authenticated = False
            st.rerun()

        if opcion == "📝 Registrar Producción":
            st.subheader("📝 Nuevo Registro")
            with st.form("reg", clear_on_submit=True):
                c1, c2 = st.columns(2)
                op = c1.selectbox("Operador:", ["Gabriel", "Adrian", "Freddy"])
                fec = c1.date_input("Fecha:", datetime.now())
                val = c2.number_input("Metraje:", min_value=0.0)
                if st.form_submit_button("💾 Guardar"):
                    ya_existe = not df_raw[(df_raw['fecha'] == fec) & (df_raw['operador'] == op)].empty
                    if ya_existe: st.error("❌ Ya existe un registro.")
                    else:
                        hoja.append_row([str(fec), op, round(val, 2)])
                        st.success("Guardado")
                        st.rerun()

        elif opcion == "🗑️ Eliminar Registro":
            st.subheader("🗑️ Eliminar")
            if not df_raw.empty:
                df_desc = df_raw.copy()
                df_desc['id'] = df_desc.index + 2
                df_desc['lbl'] = df_desc['fecha'].astype(str) + " | " + df_desc['operador']
                reg = st.selectbox("Seleccione:", options=df_desc['id'].tolist(), format_func=lambda x: df_desc[df_desc['id'] == x]['lbl'].values[0])
                if st.button("BORRAR DEFINITIVAMENTE", type="primary"):
                    hoja.delete_rows(int(reg))
                    st.success("Eliminado")
                    st.rerun()
    else:
        st.warning("🔒 Esta sección requiere acceso administrativo. Ingrese la contraseña en el menú lateral.")
