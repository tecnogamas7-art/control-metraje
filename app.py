import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from fpdf import FPDF

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Control de Metraje Pro", layout="wide", page_icon="🏗️")
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
    pdf.set_font("Arial", "", 10)
    pdf.cell(190, 10, f"Fecha de impresion: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", "B", 12); pdf.cell(190, 10, "1. RANKING POR PROMEDIO", ln=True)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(50, 8, "Operador", 1); pdf.cell(45, 8, "Suma Total (m)", 1); pdf.cell(50, 8, "Promedio (m)", 1); pdf.cell(45, 8, "Registros", 1); pdf.ln()
    pdf.set_font("Arial", "", 9)
    for _, row in df_stats.iterrows():
        pdf.cell(50, 7, str(row['Operador']), 1); pdf.cell(45, 7, f"{row['Suma Total (m)']:,.2f}", 1); pdf.cell(50, 7, f"{row['Promedio Individual (m)']:,.2f}", 1); pdf.cell(45, 7, str(row['Días Registrados']), 1); pdf.ln()
    pdf.ln(10)
    pdf.set_font("Arial", "B", 12); pdf.cell(190, 10, "2. HISTORIAL DETALLADO", ln=True)
    cols = df_pivot.columns.tolist(); n_cols = len(cols) + 1; w = 190 / n_cols
    pdf.set_font("Arial", "B", 9); pdf.cell(w, 8, "Fecha", 1)
    for col in cols: pdf.cell(w, 8, str(col), 1)
    pdf.ln()
    pdf.set_font("Arial", "", 8)
    for fecha, row in df_pivot.iterrows():
        pdf.cell(w, 7, str(fecha), 1)
        for col in cols: pdf.cell(w, 7, f"{row[col]:,.2f}", 1)
        pdf.ln()
    return pdf.output(dest="S").encode("latin-1", "replace")

# --- 4. INTERFAZ ---
st.title("📊 Panel de Control de Metraje")
opcion = st.sidebar.radio("Menú:", ["📝 Registro Diario", "📊 Historial y Reportes", "🗑️ Eliminar Registro"])

if opcion == "📝 Registro Diario":
    st.subheader("Registrar Nueva Producción")
    with st.form("nuevo_registro", clear_on_submit=True):
        c1, c2 = st.columns(2)
        op = c1.selectbox("Operador:", ["Gabriel", "Adrian", "Freddy"])
        fec = c1.date_input("Fecha:", datetime.now())
        val = c2.number_input("Metraje:", min_value=0.0, format="%.2f")
        
        if st.form_submit_button("💾 Guardar"):
            # --- ALGORITMO DE VALIDACIÓN (DATO ÚNICO POR DÍA) ---
            ya_existe = not df_raw[(df_raw['fecha'] == fec) & (df_raw['operador'] == op)].empty
            
            if ya_existe:
                st.error(f"❌ Error: {op} ya tiene un registro para la fecha {fec}. Si te equivocaste, primero elimina el registro anterior.")
            elif val <= 0:
                st.warning("El metraje debe ser mayor a 0.")
            else:
                try:
                    hoja.append_row([str(fec), op, round(val, 2)])
                    st.success(f"✅ ¡Registro de {op} guardado!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al conectar con la nube: {e}")

elif opcion == "📊 Historial y Reportes":
    if not df_raw.empty:
        stats = df_raw.groupby('operador')['metraje'].agg(['sum', 'mean', 'count']).reset_index()
        stats.columns = ['Operador', 'Suma Total (m)', 'Promedio Individual (m)', 'Días Registrados']
        stats = stats.sort_values(by='Promedio Individual (m)', ascending=False)
        df_pivot = df_raw.pivot_table(index='fecha', columns='operador', values='metraje', aggfunc='sum').fillna(0).sort_index(ascending=False)
        
        pdf_data = generar_pdf_pro(df_pivot, stats)
        st.download_button("📄 Descargar Reporte PDF", data=pdf_data, file_name="reporte_metraje.pdf", mime="application/pdf")
        
        st.markdown("---")
        st.subheader("🏆 Ranking de Eficiencia (Promedio)")
        st.table(stats.style.format({'Suma Total (m)': '{:,.2f}', 'Promedio Individual (m)': '{:,.2f}'}))
        
        st.markdown("---")
        st.subheader("📊 Gráficas Comparativas")
        col_g1, col_g2 = st.columns(2)
        with col_g1: st.write("**Metraje Total**"); st.bar_chart(data=stats, x="Operador", y="Suma Total (m)", color="#1E88E5")
        with col_g2: st.write("**Eficiencia (Promedio)**"); st.bar_chart(data=stats, x="Operador", y="Promedio Individual (m)", color="#FFC107")
        
        st.markdown("---")
        st.subheader("📅 Historial Horizontal")
        st.dataframe(df_pivot, use_container_width=True)
    else:
        st.info("No hay datos.")

elif opcion == "🗑️ Eliminar Registro":
    st.subheader("Eliminar Registro")
    if not df_raw.empty:
        df_desc = df_raw.copy()
        df_desc['id_borrar'] = df_desc.index + 2
        df_desc['label'] = df_desc['fecha'].astype(str) + " | " + df_desc['operador'] + " | " + df_desc['metraje'].astype(str) + "m"
        reg = st.selectbox("Seleccione:", options=df_desc['id_borrar'].tolist(), format_func=lambda x: df_desc[df_desc['id_borrar'] == x]['label'].values[0])
        
        if 'c' not in st.session_state: st.session_state.c = False
        if not st.session_state.c:
            if st.button("🗑️ Preparar Eliminación"): st.session_state.c = True; st.rerun()
        else:
            st.error("⚠️ ¿Desea eliminar definitivamente?")
            c_si, c_no = st.columns(2)
            if c_si.button("SÍ, BORRAR", type="primary"):
                hoja.delete_rows(int(reg)); st.session_state.c = False; st.rerun()
            if c_no.button("CANCELAR"): st.session_state.c = False; st.rerun()
