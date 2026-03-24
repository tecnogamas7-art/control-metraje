import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- 1. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Control de Metraje Pro", layout="wide", page_icon="🏗️")

# ID de tu nueva hoja (Verificado)
SPREADSHEET_ID = "1BJG1sm8lRUK8TPcw9dNr5oQMIo3fJ93IhWdue5Hh10E"

@st.cache_resource
def conectar_google():
    try:
        # Extraemos y limpiamos los secretos
        info = {
            "type": "service_account",
            "project_id": st.secrets["project_id"].strip(),
            "private_key": st.secrets["private_key"].replace('\\n', '\n').strip(),
            "client_email": st.secrets["client_email"].strip(),
            "token_uri": "https://oauth2.googleapis.com/token",
        }
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_info(info, scopes=scopes)
        client = gspread.authorize(creds)
        # Accedemos a la primera pestaña de la hoja
        return client.open_by_key(SPREADSHEET_ID).get_worksheet(0)
    except Exception as e:
        st.error(f"❌ Error Crítico de Conexión: {e}")
        st.stop()

# --- 2. CARGA Y PROCESAMIENTO DE DATOS ---
hoja = conectar_google()

try:
    # Leemos todos los registros de la hoja
    registros = hoja.get_all_records()
    df = pd.DataFrame(registros)
    
    if not df.empty:
        # Aseguramos que el metraje sea numérico para cálculos
        df['metraje'] = pd.to_numeric(df['metraje'], errors='coerce').fillna(0)
        # Aseguramos formato de fecha
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce').dt.date
except Exception as e:
    st.warning("La hoja está vacía o no tiene el formato correcto (fecha, operador, metraje).")
    df = pd.DataFrame(columns=['fecha', 'operador', 'metraje'])

# --- 3. DISEÑO DE LA INTERFAZ ---
st.title("📊 Panel de Control de Metraje")
st.markdown("---")

# --- BLOQUE DE MÉTRICAS GENERALES (TU ALGORITMO) ---
if not df.empty:
    col_a, col_b, col_c = st.columns
