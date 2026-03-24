import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Control de Metraje Pro", layout="wide", page_icon="🚀")

# ID de tu hoja (Extreído de tu URL de Google Sheets)
SPREADSHEET_ID = "1behqvajjNR4RYULbCGo2-w7IBXeC48fgnxXYiCGoOVU"

# --- 2. CONEXIÓN SEGURA A GOOGLE ---
@st.cache_resource
def conectar_google():
    try:
        # Extraemos los datos de st.secrets (asegúrate de que los nombres coincidan)
        # Limpiamos espacios y arreglamos los saltos de línea de la clave privada
        p_key = st.secrets["private_key"].replace('\\n', '\n').strip()
        c_email = st.secrets["client_email"].strip()
        p_id = st.secrets["project_id"].strip()

        # Diccionario de credenciales estándar de Google
        info = {
            "type": "service_account",
            "project_id": p_id,
            "private_key": p_key,
            "client_email": c_email,
            "token_uri": "https://oauth2.googleapis.com",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        }

        # Scopes: El de Drive es obligatorio para que no dé error 404
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]

        creds = Credentials.from_service_account_info(info, scopes=scopes)
        client = gspread.authorize(creds)
        
        # Abrir la hoja de cálculo por su ID
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        
        # Intentar abrir la primera pestaña disponible
        return spreadsheet.get_worksheet(0)
            
    except Exception as e:
        # Si el robot 404 aparece aquí, es un tema de permisos en Google Cloud
        st.error(f"❌ Error crítico de conexión: {e}")
        st.info("💡 REVISA: ¿Compartiste la hoja con el correo de la cuenta de servicio como EDITOR?")
        st.stop()

# --- 3. LÓGICA DE LA APLICACIÓN ---
hoja = conectar_google()

# Intentar leer los datos para la tabla
try:
    datos = hoja.get_all_records()
    df_existente = pd.DataFrame(datos)
    if df_existente.empty:
        df_existente = pd.DataFrame(columns=['fecha', 'operador', 'metraje'])
    st.sidebar.success("✅ Conectado a la nube")
except Exception:
    df_existente = pd.DataFrame(columns=['fecha', 'operador', 'metraje'])

st.title("📊 Control de Metraje Diarios")
st.markdown("---")

# Formulario de entrada
with st.form("form_registro", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        operador = st.selectbox("Seleccione Operador:", ["Gabriel", "Adrian", "Freddy"])
        fecha = st.date_input("Fecha de trabajo:", datetime.now())
    with col2:
        valor = st.number_input("Metraje alcanzado (m):", min_value=0.0, step=0.01, format="%.2f")
    
    btn_guardar = st.form_submit_button("💾 Guardar en Google Sheets", use_container_width=True)

if btn_guardar:
    fecha_str = str(fecha)
    # Evitar duplicados simples (mismo operador, misma fecha)
    es_duplicado = not df_existente.empty and (
        (df_existente['fecha'].astype(str) == fecha_str) & 
        (df_existente['operador'] == operador)
    ).any()

    if es_duplicado:
        st.warning(f"⚠️ Ya existe un registro para {operador} el día {fecha_str}.")
    else:
        try:
            # Añadir fila al final del Excel
            hoja.append_row([fecha_str, operador, round(valor, 2)])
            st.success("✅ ¡Registro guardado exitosamente!")
            st.balloons()
            st.rerun() # Recarga la app para ver el nuevo dato en la tabla
        except Exception as e:
            st.error(f"Error al guardar datos: {e}")

# --- 4. VISUALIZACIÓN DE DATOS ---
st.markdown("### Historial de Registros")
if not df_existente.empty:
    st.dataframe(df_existente.sort_values(by="fecha", ascending=False), use_container_width=True)
    
    # Gráfico rápido de barras
    st.markdown("#### Producción Total por Operador")
    df_existente['metraje'] = pd.to_numeric(df_existente['metraje'], errors='coerce')
    resumen = df_existente.groupby("operador")["metraje"].sum().reset_index()
    st.bar_
