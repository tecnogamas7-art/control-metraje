import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Control de Metraje Pro", layout="wide", page_icon="🚀")

# ID DE TU HOJA
SPREADSHEET_ID = "1behqvajjNR4RYULbCGo2-w7IBXeC48fgnxXYiCGoOVU"

@st.cache_resource
def conectar_google():
    try:
        # Construcción directa de credenciales
        info = {
            "type": "service_account",
            "project_id": st.secrets["project_id"],
            "private_key": st.secrets["private_key"].replace('\\n', '\n'),
            "client_email": st.secrets["client_email"],
            "token_uri": "https://oauth2.googleapis.com",
        }

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]

        creds = Credentials.from_service_account_info(info, scopes=scopes)
        client = gspread.authorize(creds)
        
        # Abrir hoja
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        return spreadsheet.get_worksheet(0)
            
    except Exception as e:
        # Si esto falla con 404, es la configuración de Google Cloud o los Secrets
        st.error(f"❌ Error de conexión: {e}")
        st.stop()

# --- FLUJO PRINCIPAL ---
hoja = conectar_google()

try:
    datos = hoja.get_all_records()
    df_existente = pd.DataFrame(datos)
    if df_existente.empty:
        df_existente = pd.DataFrame(columns=['fecha', 'operador', 'metraje'])
    st.sidebar.success("✅ Conectado")
except Exception as e:
    st.error(f"❌ Error al leer datos: {e}")
    st.stop()

st.title("🚀 Control de Metraje")

menu = st.sidebar.radio("Menú:", ["Registrar", "Reportes"])

if menu == "Registrar":
    with st.form("form_registro", clear_on_submit=True):
        col1, col2 = st.columns(2)
        op = col1.selectbox("Operador", ["Gabriel", "Adrian", "Freddy"])
        fec = col1.date_input("Fecha", datetime.now())
        val = col2.number_input("Metraje (m)", min_value=0.0)
        enviar = st.form_submit_button("Guardar")

    if enviar:
        try:
            hoja.append_row([str(fec), op, round(val, 2)])
            st.success("✅ Guardado correctamente")
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

elif menu == "Reportes":
    st.dataframe(df_existente, use_container_width=True)
    if not df_existente.empty:
        st.bar_chart(df_existente.groupby("operador")["metraje"].sum())
