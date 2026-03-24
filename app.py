import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Control de Metraje Pro", layout="wide")

# ID DE TU HOJA (Verifícalo en la URL de tu navegador)
SPREADSHEET_ID = "1behqvajjNR4RYULbCGo2-w7IBXeC48fgnxXYiCGoOVU"

@st.cache_resource
def conectar_google():
    try:
        # 1. Limpieza manual de Secrets
        # Esto previene que caracteres invisibles rompan la URL de Google
        info = {
            "type": "service_account",
            "project_id": st.secrets["project_id"].strip(),
            "private_key": st.secrets["private_key"].replace('\\n', '\n').strip(),
            "client_email": st.secrets["client_email"].strip(),
            "token_uri": "https://oauth2.googleapis.com",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{st.secrets['client_email'].strip()}"
        }

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]

        # 2. Autenticación con parámetros explícitos
        creds = Credentials.from_service_account_info(info, scopes=scopes)
        client = gspread.authorize(creds)
        
        # 3. Abrir la hoja
        # Si aquí sale 404, es el ID o el botón COMPARTIR
        return client.open_by_key(SPREADSHEET_ID).sheet1
            
    except Exception as e:
        st.error(f"❌ ERROR DE GOOGLE: {e}")
        st.stop()

# --- CARGA DE DATOS ---
hoja = conectar_google()

try:
    data = hoja.get_all_records()
    df = pd.DataFrame(data)
    if df.empty:
        df = pd.DataFrame(columns=['fecha', 'operador', 'metraje'])
    st.sidebar.success("✅ ¡CONECTADO!")
except:
    df = pd.DataFrame(columns=['fecha', 'operador', 'metraje'])

# --- INTERFAZ ---
st.title("📊 Registro de Metraje")

with st.form("registro", clear_on_submit=True):
    col1, col2 = st.columns(2)
    op = col1.selectbox("Operador", ["Gabriel", "Adrian", "Freddy"])
    fec = col1.date_input("Fecha", datetime.now())
    met = col2.number_input("Metraje (m)", min_value=0.0)
    
    if st.form_submit_button("Guardar Datos"):
        try:
            hoja.append_row([str(fec), op, round(met, 2)])
            st.success("✅ Guardado.")
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

st.dataframe(df.tail(10), use_container_width=True)
