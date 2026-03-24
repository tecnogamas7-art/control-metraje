import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Control de Metraje Pro", layout="wide", page_icon="🚀")

# ID DE TU HOJA (Verificado de tu URL)
SPREADSHEET_ID = "1behqvajjNR4RYULbCGo2-w7IBXeC48fgnxXYiCGoOVU"

# --- FUNCIÓN DE CONEXIÓN ROBUSTA ---
@st.cache_resource
def conectar_google():
    try:
        # 1. Cargar credenciales desde st.secrets
        # IMPORTANTE: Asegúrate de que en Streamlit Cloud pegaste los 3 valores
        info = {
            "type": "service_account",
            "project_id": st.secrets["project_id"],
            "private_key": st.secrets["private_key"].replace('\\n', '\n'),
            "client_email": st.secrets["client_email"],
            "token_uri": "https://oauth2.googleapis.com",
        }

        # 2. Definir los Scopes (Necesarios para Sheets y Drive)
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]

        # 3. Autenticación técnica
        creds = Credentials.from_service_account_info(info, scopes=scopes)
        client = gspread.authorize(creds)
        
        # 4. Abrir el archivo por ID
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        
        # 5. Intentar abrir la pestaña Metrajes_DB. Si falla, abrir la primera pestaña.
        try:
            return spreadsheet.worksheet("Metrajes_DB")
        except:
            return spreadsheet.get_worksheet(0)
            
    except Exception as e:
        st.error(f"❌ Error crítico de conexión: {e}")
        st.info("Revisa que tus 'Secrets' en Streamlit tengan: project_id, private_key y client_email.")
        st.stop()

# --- CARGA DE DATOS ---
hoja = conectar_google()

try:
    datos = hoja.get_all_records()
    df_existente = pd.DataFrame(datos)
    
    # Si la hoja está vacía, inicializamos las columnas necesarias
    if df_existente.empty:
        df_existente = pd.DataFrame(columns=['fecha', 'operador', 'metraje'])
        
    st.sidebar.success(f"✅ Conectado a: {hoja.title}")
except Exception as e:
    st.error(f"❌ Error al leer la hoja: {e}")
    st.info("💡 Asegúrate de que la primera fila de tu Excel tenga estos nombres: fecha, operador, metraje")
    st.stop()

# --- INTERFAZ DE USUARIO ---
st.title("🚀 Sistema de Control de Metraje")
st.markdown("---")

menu = st.sidebar.radio("Navegación:", ["📝 Registrar Metraje", "📊 Ver Reportes", "🗑️ Administrar Datos"])

# --- 1. REGISTRAR METRAJE ---
if menu == "📝 Registrar Metraje":
    st.subheader("Nuevo Registro Diario")
    with st.form("form_registro", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            operador = st.selectbox("Seleccione Operador", ["Gabriel", "Adrian", "Freddy"])
            fecha = st.date_input("Fecha de trabajo", datetime.now())
        with col2:
            valor = st.number_input("Metraje alcanzado (m)", min_value=0.0, step=0.01, format="%.2f")
        
        enviar = st.form_submit_button("💾 Guardar Registro", use_container_width=True)
    
    if enviar:
        fecha_str = str(fecha)
        # Lógica de duplicados: evita registrar al mismo operador el mismo día
        es_duplicado = not df_existente.empty and (
            (df_existente['fecha'].astype(str) == fecha_str) & 
            (df_existente['operador'] == operador)
        ).any()
        
        if es_duplicado:
            st.error(f"❌ Ya existe un registro para **{operador}** en la fecha **{fecha_str}**.")
        else:
            try:
                hoja.append_row([fecha_str, operador, round(valor, 2)])
