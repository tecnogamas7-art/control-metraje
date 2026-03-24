import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Control de Metraje", layout="wide")
SPREADSHEET_ID = "1behqvajjNR4RYULbCGo2-w7IBXeC48fgnxXYiCGoOVU"

@st.cache_resource
def conectar_google():
    try:
        # Extraemos y limpiamos la llave
        p_key = st.secrets["private_key"].replace('\\n', '\n').strip()
        
        info = {
            "type": "service_account",
            "project_id": st.secrets["project_id"],
            "private_key": p_key,
            "client_email": st.secrets["client_email"],
            "token_uri": "https://oauth2.googleapis.com",
        }

        creds = Credentials.from_service_account_info(info, scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ])
        
        client = gspread.authorize(creds)
        return client.open_by_key(SPREADSHEET_ID).sheet1
            
    except Exception as e:
        st.error(f"❌ Error al conectar: {e}")
        st.stop()

# --- APP ---
hoja = conectar_google()
st.title("🚀 Registro de Metraje")

try:
    # Intentar leer los datos para mostrar la tabla
    datos = hoja.get_all_records()
    df = pd.DataFrame(datos)
    st.sidebar.success("✅ ¡Conexión Exitosa!")
except:
    df = pd.DataFrame(columns=['fecha', 'operador', 'metraje'])

# Formulario
with st.form("registro", clear_on_submit=True):
    col1, col2 = st.columns(2)
    op = col1.selectbox("Operador", ["Gabriel", "Adrian", "Freddy"])
    fec = col1.date_input("Fecha", datetime.now())
    met = col2.number_input("Metraje (m)", min_value=0.0)
    
    if st.form_submit_button("Guardar Datos"):
        hoja.append_row([str(fec), op, met])
        st.success("✅ Guardado en Google Sheets")
        st.rerun()

st.write("### Últimos Registros")
st.dataframe(df.tail(10), use_container_width=True)
