import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Control de Metraje Pro", layout="wide", page_icon="🚀")

# ID DE TU HOJA (No cambia aunque cambies el nombre del archivo)
SPREADSHEET_ID = "1behqvajjNR4RYULbCGo2-w7IBXeC48fgnxXYiCGoOVU"

# --- FUNCIÓN DE CONEXIÓN ---
@st.cache_resource
def conectar_google():
    try:
        # 1. Cargar credenciales desde st.secrets
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
        
        # 2. Abrir el archivo por ID
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        
        # 3. Seleccionar la pestaña específica
        # Si tu pestaña abajo se llama "Metrajes_DB", cámbialo aquí:
        try:
            return spreadsheet.worksheet("Metrajes_DB")
        except:
            # Si falla el nombre, agarra la primera que encuentre
            return spreadsheet.get_worksheet(0)
            
    except Exception as e:
        st.error(f"❌ Error de conexión: {e}")
        st.stop()

# --- INICIO DE LA APP ---
hoja = conectar_google()

try:
    # Obtener datos y limpiar
    datos = hoja.get_all_records()
    df_existente = pd.DataFrame(datos)
    
    if df_existente.empty:
        df_existente = pd.DataFrame(columns=['fecha', 'operador', 'metraje'])
        
    st.sidebar.success(f"✅ Conectado a: {hoja.title}")
except Exception as e:
    st.error(f"❌ Error al leer la pestaña: {e}")
    st.info("Asegúrate de que la hoja tenga encabezados: fecha, operador, metraje")
    st.stop()

# --- INTERFAZ ---
st.title("🚀 Control de Metraje")
menu = st.sidebar.radio("Ir a:", ["Registrar", "Reportes", "Borrar"])

if menu == "Registrar":
    with st.form("form_registro", clear_on_submit=True):
        col1, col2 = st.columns(2)
        op = col1.selectbox("Operador", ["Gabriel", "Adrian", "Freddy"])
        fec = col1.date_input("Fecha", datetime.now())
        met = col2.number_input("Metraje (m)", min_value=0.0)
        btn = st.form_submit_button("Guardar")
        
    if btn:
        if not df_existente.empty and ((df_existente['fecha'].astype(str) == str(fec)) & (df_existente['operador'] == op)).any():
            st.error("Ya existe este registro.")
        else:
            hoja.append_row([str(fec), op, met])
            st.success("Guardado!")
            st.rerun()

elif menu == "Reportes":
    st.dataframe(df_existente, use_container_width=True)
    if not df_existente.empty:
        st.bar_chart(df_existente.groupby("operador")["metraje"].sum())

elif menu == "Borrar":
    st.write("Seleccione índice para borrar:")
    st.dataframe(df_existente)
    idx = st.number_input("Índice", min_value=0, max_value=max(0, len(df_existente)-1))
    if st.button("Eliminar"):
        hoja.delete_rows(int(idx) + 2)
        st.success("Eliminado")
        st.rerun()
