import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import os

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Control de Metraje Pro", layout="wide", page_icon="🚀")

# Estilo de título
st.markdown("<h1 style='text-align: center;'>🚀 Sistema de Control de Metraje (Nube)</h1>", unsafe_allow_html=True)
st.markdown("---")

# ID DE TU HOJA (Verificado de tu URL)
SPREADSHEET_ID = "1behqvajjNR4RYULbCGo2-w7IBXeC48fgnxXYiCGoOVU"

# --- FUNCIÓN DE CONEXIÓN CORREGIDA ---
@st.cache_resource
def conectar_google():
    try:
        # Extraer secretos de Streamlit Cloud
        # Nota: Asegúrate de que en Streamlit Cloud los nombres coincidan exactamente
        info = {
            "type": "service_account",
            "project_id": st.secrets["project_id"],
            "private_key_id": st.secrets.get("private_key_id", ""),
            "private_key": st.secrets["private_key"].replace('\\n', '\n'),
            "client_email": st.secrets["client_email"],
            "client_id": st.secrets.get("client_id", ""),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": st.secrets.get("client_x509_cert_url", "")
        }

        # SCOPES específicos (Esto evita el Error 404 de URL no encontrada)
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]

        creds = Credentials.from_service_account_info(info, scopes=scopes)
        client = gspread.authorize(creds)
        
        # Abrir la hoja por ID y seleccionar la primera pestaña
        sheet = client.open_by_key(SPREADSHEET_ID).sheet1
        return sheet

    except KeyError as e:
        st.error(f"❌ Falta el secreto: {e}. Revisa la configuración en Streamlit Cloud.")
        st.stop()
    except Exception as e:
        st.error(f"❌ Error crítico de conexión: {e}")
        st.stop()

# --- CARGA DE DATOS INICIAL ---
hoja = conectar_google()

try:
    # Obtener todos los registros
    datos = hoja.get_all_records()
    df_existente = pd.DataFrame(datos)
    
    # Si la hoja está nueva, inicializamos columnas
    if df_existente.empty:
        df_existente = pd.DataFrame(columns=['fecha', 'operador', 'metraje'])
        
    st.sidebar.success("✅ Conexión Exitosa")
except Exception as e:
    st.error(f"❌ Error al leer datos: {e}")
    st.info("💡 Consejo: Asegúrate de que la primera fila de tu Excel tenga los encabezados: fecha, operador, metraje")
    st.stop()

# --- MENÚ DE NAVEGACIÓN ---
menu = st.sidebar.radio("Seleccione una opción:", ["📝 Registrar Metraje", "📊 Reportes", "🗑️ Administrar Datos"])

# --- 1. REGISTRAR METRAJE ---
if menu == "📝 Registrar Metraje":
    st.subheader("Añadir nuevo registro diario")
    
    with st.form("registro_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            operador = st.selectbox("Operador:", ["Gabriel", "Adrian", "Freddy"])
            fecha = st.date_input("Fecha:", datetime.now())
        with col2:
            metraje = st.number_input("Metraje alcanzado (m):", min_value=0.0, step=0.01, format="%.2f")
        
        boton_guardar = st.form_submit_button("💾 Guardar en Google Sheets")

    if boton_guardar:
        fecha_str = str(fecha)
        
        # Validar duplicados en el DataFrame actual
        es_duplicado = not df_existente.empty and (
            (df_existente['fecha'].astype(str) == fecha_str) & 
            (df_existente['operador'] == operador)
        ).any()

        if es_duplicado:
            st.warning(f"⚠️ Ya existe un registro para **{operador}** en la fecha **{fecha_str}**.")
        else:
            try:
                # Insertar en la nube
                hoja.append_row([fecha_str, operador, round(metraje, 2)])
                st.success("✅ ¡Datos guardados en la nube!")
                st.balloons()
                st.rerun()
            except Exception as e:
                st.error(f"Error al guardar: {e}")

# --- 2. REPORTES ---
elif menu == "📊 Reportes":
    st.subheader("Análisis de Metraje")
    if not df_existente.empty:
        # Convertir a numérico para evitar errores de cálculo
        df_existente['metraje'] = pd.to_numeric(df_existente['metraje'], errors='coerce')
        
        # Filtro por mes
        mes_filtro = st.text_input("Filtrar por Mes (Ej: 2026-03):
