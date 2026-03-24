import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from fpdf import FPDF # Librería para generar el PDF

# --- 1. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Control de Metraje Pro", layout="wide", page_icon="🏗️")

# ID de tu hoja
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
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(info, scopes=scopes)
        client = gspread.authorize(creds)
        return client.open_by_key(SPREADSHEET_ID).get_worksheet(0)
    except Exception as e:
        st.error(f"❌ Error de Conexión: {e}")
        st.stop()

# --- 2. CARGA DE DATOS ---
hoja = conectar_google()

def cargar_datos():
    try:
        registros = hoja.get_all_records()
        df = pd.DataFrame(registros)
        if not df.empty:
            df['metraje'] = pd.to_numeric(df['metraje'], errors='coerce').fillna(0)
            df['fecha'] = pd.to_datetime(df['fecha']).dt.date
        return df
    except:
        return pd.DataFrame(columns=['fecha', 'operador', 'metraje'])

df_raw = cargar_datos()

# --- FUNCIÓN PARA GENERAR PDF ---
def generar_pdf(dataframe, stats):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 10, "REPORTE DE METRAJE DIARIO", ln=True, align="C")
    pdf.set_font("Arial", "", 10)
    pdf.cell(190, 10, f"Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align="C")
    pdf.ln(10)

    # Ranking
    pdf.set_font("Arial", "B", 12)
    pdf.cell(190, 10, "Ranking de Operadores (Promedio)", ln=True)
    pdf.set_font("Arial", "", 10)
    for index, row in stats.iterrows():
        linea = f"- {row['Operador']}: Total {row['Suma Total (m)']}m | Promedio: {row['Promedio Individual (m)']}m"
        pdf.cell(190, 7, linea, ln=True)
    
    pdf.ln(10)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(190, 10, "Historial de Registros", ln=True)
    pdf.set_font("Arial", "", 9)
    # Encabezados tabla
    pdf.cell(40, 7, "Fecha", 1)
    pdf.cell(80, 7, "Operador", 1)
    pdf.cell(40, 7, "Metraje", 1)
    pdf.ln()
    
    # Filas
    for index, row in dataframe.sort_values(by='fecha', ascending=False).iterrows():
        pdf.cell(40, 7, str(row['fecha']), 1)
        pdf.cell(80, 7, str(row['operador']), 1)
        pdf.cell(40, 7, str(row['metraje']), 1)
        pdf.ln()
        
    return pdf.output(dest="S").encode("latin-1")

# --- 3. INTERFAZ ---
st.title("📊 Panel de Control de Metraje")

st.sidebar.markdown("---")
opcion = st.sidebar.radio("Seleccione una acción:", ["📝 Registro Diario", "📊 Historial y Reportes", "🗑️ Eliminar Registro"])

if opcion == "📝 Registro Diario":
    st.subheader("Registrar Nueva Producción")
    with st.form("nuevo_registro", clear_on_submit=True):
        col1, col2 = st.columns(2)
        op = col1.selectbox("Operador:", ["Gabriel", "Adrian", "Freddy"])
        fec = col1.date_input("Fecha:", datetime.now())
        val = col2.number_input("Metraje alcanzado (m):", min_value=0.0, format="%.2f")
        if st.form_submit_button("💾 Guardar Datos"):
            hoja.append_row([str(fec), op, round(val, 2)])
            st.success("¡Datos guardados!")
            st.rerun()

elif opcion == "📊 Historial y Reportes":
    if not df_raw.empty:
        st.subheader("📈 Resumen General")
        
        # Estadísticas para el PDF y la tabla
        stats_individual = df_raw.groupby('operador')['metraje'].agg(['sum', 'mean', 'count']).reset_index()
        stats_individual.columns = ['Operador', 'Suma Total (m)', 'Promedio Individual (m)', 'Días Registrados']
        stats_individual = stats_individual.sort_values(by='Promedio Individual (m)', ascending=False)

        # Botones de exportación arriba
        col_exp1, col_exp2 = st.columns([1, 5])
        with col_exp1:
            pdf_bytes = generar_pdf(df_raw, stats_individual)
            st.download_button(label="📄 Exportar a PDF", data=pdf_bytes, file_name="reporte_metraje.pdf", mime="application/pdf")
        
        st.markdown("---")
        st.table(stats_individual.style.format({'Suma Total (m)': '{:,.2f}', 'Promedio Individual (m)': '{:,.2f}'}))

        st.subheader("📅 Historial por Fecha")
        df_pivot = df_raw.pivot_table(index='fecha', columns='operador', values='metraje', aggfunc='sum').fillna(0).sort_index(ascending=False)
        st.dataframe(df_pivot, use_container_width=True)
        st.bar_chart(df_raw.groupby("operador")["metraje"].sum())
    else:
        st.info("No hay datos.")

elif opcion == "🗑️ Eliminar Registro":
    st.subheader("Eliminar un Registro")
    if not df_raw.empty:
        df_desc = df_raw.copy()
        df_desc['id_borrar'] = df_desc.index + 2
        df_desc['etiqueta'] = df_desc['fecha'].astype(str) + " | " + df_desc['operador'] + " | " + df_desc['metraje'].astype(str) + "m"
        
        registro_a_borrar = st.selectbox("Seleccione el registro:", options=df_desc['id_borrar'].tolist(),
                                         format_func=lambda x: df_desc[df_desc['id_borrar'] == x]['etiqueta'].values[0])
        
        if 'confirmar_borrado' not in st.session_state: st.session_state.confirmar_borrado = False

        if not st.session_state.confirmar_
