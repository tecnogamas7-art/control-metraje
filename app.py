import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Control de Metraje Pro", layout="wide", page_icon="🚀")

# ID de tu hoja (extraído de tu URL)
SPREADSHEET_ID = "1behqvajjNR4RYULbCGo2-w7IBXeC48fgnxXYiCGoOVU"

@st.cache_resource
def conectar_google():
    try:
        # Extraemos la llave de los secrets y limpiamos saltos de línea
        p_key = st.secrets["private_key"].replace('\\n', '\n').strip()
        
        info = {
            "type": "service_account",
            "project_id": st.secrets["project_id"],
            "private_key": p_key,
            "client_email": st.secrets["client_email"],
            "token_uri": "https://oauth2.googleapis.com",
        }

        # Permisos necesarios
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]

        creds = Credentials.from_service_account_info(info, scopes=scopes)
        client = gspread.authorize(creds)
        
        # Abrir la primera pestaña de la hoja
        return client.open_by_key(SPREADSHEET_ID).sheet1
            
    except Exception as e:
        st.error(f"❌ Error de conexión: {e}")
        st.stop()

# --- CARGA DE DATOS ---
hoja = conectar_google()

try:
    # Intentar leer datos existentes
    records = hoja.get_all_records()
    df_existente = pd.DataFrame(records)
    if df_existente.empty:
        df_existente = pd.DataFrame(columns=['fecha', 'operador', 'metraje'])
except:
    df_existente = pd.DataFrame(columns=['fecha', 'operador', 'metraje'])

# --- DISEÑO DE LA APLICACIÓN ---
st.title("🚀 Sistema de Control de Metraje")
st.markdown("---")

# Menú lateral
menu = st.sidebar.radio("Ir a:", ["📝 Registrar Metraje", "📊 Ver Reportes"])

if menu == "📝 Registrar Metraje":
    st.subheader("Nuevo Registro Diario")
    
    with st.form("registro_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            operador = st.selectbox("Operador:", ["Gabriel", "Adrian", "Freddy"])
            fecha = st.date_input("Fecha:", datetime.now())
        with col2:
            valor = st.number_input("Metraje alcanzado (m):", min_value=0.0, step=0.01, format="%.2f")
        
        btn_guardar = st.form_submit_button("💾 Guardar en Google Sheets", use_container_width=True)

    if btn_guardar:
        fecha_str = str(fecha)
        # Validar duplicados básicos
        existe = not df_existente.empty and (
            (df_existente['fecha'].astype(str) == fecha_str) & 
            (df_existente['operador'] == operador)
        ).any()

        if existe:
            st.warning(f"⚠️ Ya existe un registro para {operador} en la fecha {fecha_str}.")
        else:
            try:
                # Escribir en la nube
                hoja.append_row([fecha_str, operador, round(valor, 2)])
                st.success(f"✅ ¡Datos de {operador} guardados exitosamente!")
                st.balloons()
                st.rerun()
            except Exception as e:
                st.error(f"Error al guardar: {e}")

elif menu == "📊 Ver Reportes":
    st.subheader("Historial de Producción")
    if not df_existente.empty:
        st.dataframe(df_existente.sort_values(by="fecha", ascending=False), use_container_width=True)
        
        st.markdown("### Total por Operador")
        df_existente['metraje'] = pd.to_numeric(df_existente['metraje'], errors='coerce')
        resumen = df_existente.groupby("operador")["metraje"].sum().reset_index()
        st.bar_chart(data=resumen, x="operador", y="metraje")
    else:
        st.info("Aún no hay datos registrados.")
