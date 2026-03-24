import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Control de Metraje - Nuevo", layout="wide")

# NUEVO ID ACTUALIZADO
SPREADSHEET_ID = "1BJG1sm8lRUK8TPcw9dNr5oQMIo3fJ93IhWdue5Hh10E"

@st.cache_resource
def conectar_google():
    try:
        # Limpieza de secretos
        info = {
            "type": "service_account",
            "project_id": st.secrets["project_id"].strip(),
            "private_key": st.secrets["private_key"].replace('\\n', '\n').strip(),
            "client_email": st.secrets["client_email"].strip(),
            "token_uri": "https://oauth2.googleapis.com",
        }

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]

        creds = Credentials.from_service_account_info(info, scopes=scopes)
        client = gspread.authorize(creds)
        
        # Abrir la nueva hoja
        return client.open_by_key(SPREADSHEET_ID).sheet1
            
    except Exception as e:
        st.error(f"❌ Error de Conexión: {e}")
        st.info(f"Asegúrate de haber compartido esta NUEVA hoja con: {st.secrets['client_email']}")
        st.stop()

# --- LÓGICA DE LA APP ---
hoja = conectar_google()

try:
    data = hoja.get_all_records()
    df = pd.DataFrame(data)
    if df.empty:
        df = pd.DataFrame(columns=['fecha', 'operador', 'metraje'])
    st.sidebar.success("✅ Conectado a la Hoja Nueva")
except:
    df = pd.DataFrame(columns=['fecha', 'operador', 'metraje'])

st.title("🚀 Registro de Metraje (Hoja Nueva)")

with st.form("registro_metraje", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        op = st.selectbox("Operador", ["Gabriel", "Adrian", "Freddy"])
        fec = st.date_input("Fecha", datetime.now())
    with col2:
        met = st.number_input("Metraje (m)", min_value=0.0, step=0.1)
    
    btn = st.form_submit_button("💾 Guardar Registro")

if btn:
    try:
        # Guardar en Google Sheets
        hoja.append_row([str(fec), op, round(met, 2)])
        st.success("✅ ¡Datos guardados correctamente!")
        st.rerun()
    except Exception as e:
        st.error(f"Error al guardar: {e}")

st.write("### Historial de la nueva hoja")
st.dataframe(df.tail(10), use_container_width=True)
