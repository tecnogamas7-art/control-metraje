import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Control de Metraje Pro", layout="wide")

# ID DE TU HOJA
SPREADSHEET_ID = "1behqvajjNR4RYULbCGo2-w7IBXeC48fgnxXYiCGoOVU"

@st.cache_resource
def conectar_google():
    try:
        # 1. Obtener la llave y limpiarla agresivamente
        raw_key = st.secrets["private_key"]
        
        # Esto elimina comillas accidentales y arregla los saltos de línea \n
        clean_key = raw_key.replace('\\n', '\n').strip()
        
        # 2. Configuración de credenciales
        credentials_info = {
            "type": "service_account",
            "project_id": st.secrets["project_id"],
            "private_key": clean_key,
            "client_email": st.secrets["client_email"],
            "token_uri": "https://oauth2.googleapis.com",
        }

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]

        # 3. Autenticación
        creds = Credentials.from_service_account_info(credentials_info, scopes=scopes)
        client = gspread.authorize(creds)
        
        # 4. Abrir la hoja
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        return spreadsheet.get_worksheet(0)
            
    except Exception as e:
        st.error(f"❌ Error de conexión: {e}")
        st.stop()

# --- FLUJO PRINCIPAL ---
hoja = conectar_google()

try:
    records = hoja.get_all_records()
    df_existente = pd.DataFrame(records)
    if df_existente.empty:
        df_existente = pd.DataFrame(columns=['fecha', 'operador', 'metraje'])
    st.sidebar.success("✅ Conexión Establecida")
except Exception as e:
    st.error(f"Error al leer datos: {e}")
    st.stop()

# --- INTERFAZ ---
st.title("🚀 Sistema de Control de Metraje")

menu = st.sidebar.radio("Menú:", ["Registrar", "Reportes"])

if menu == "Registrar":
    with st.form("registro", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            operador = st.selectbox("Operador", ["Gabriel", "Adrian", "Freddy"])
            fecha = st.date_input("Fecha", datetime.now())
        with col2:
            valor = st.number_input("Metraje (m)", min_value=0.0)
        
        btn = st.form_submit_button("Guardar Registro")

    if btn:
        try:
            hoja.append_row([str(fecha), operador, round(valor, 2)])
            st.success("✅ ¡Guardado!")
            st.rerun()
        except Exception as e:
            st.error(f"Error al guardar: {e}")

elif menu == "Reportes":
    st.subheader("Datos en la Nube")
    st.dataframe(df_existente, use_container_width=True)
