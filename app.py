import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Control de Metraje Pro", layout="wide", page_icon="🚀")

# ID DE TU HOJA (Verificado)
SPREADSHEET_ID = "1behqvajjNR4RYULbCGo2-w7IBXeC48fgnxXYiCGoOVU"

# --- FUNCIÓN DE CONEXIÓN ---
@st.cache_resource
def conectar_google():
    try:
        # Cargar credenciales desde st.secrets
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
        
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        
        # Intentar abrir pestaña específica o la primera
        try:
            return spreadsheet.worksheet("Metrajes_DB")
        except:
            return spreadsheet.get_worksheet(0)
            
    except Exception as e:
        st.error(f"❌ Error crítico de conexión: {e}")
        st.stop()

# --- CARGA DE DATOS ---
hoja = conectar_google()

try:
    datos = hoja.get_all_records()
    df_existente = pd.DataFrame(datos)
    if df_existente.empty:
        df_existente = pd.DataFrame(columns=['fecha', 'operador', 'metraje'])
    st.sidebar.success(f"✅ Conectado a: {hoja.title}")
except Exception as e:
    st.error(f"❌ Error al leer la hoja: {e}")
    st.stop()

# --- INTERFAZ ---
st.title("🚀 Sistema de Control de Metraje")
st.markdown("---")

menu = st.sidebar.radio("Navegación:", ["📝 Registrar", "📊 Reportes", "🗑️ Administrar"])

# --- 1. REGISTRAR (Aquí estaba el error de sintaxis) ---
if menu == "📝 Registrar":
    st.subheader("Nuevo Registro Diario")
    with st.form("form_registro", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            operador = st.selectbox("Operador", ["Gabriel", "Adrian", "Freddy"])
            fecha = st.date_input("Fecha", datetime.now())
        with col2:
            valor = st.number_input("Metraje (m)", min_value=0.0, step=0.01, format="%.2f")
        
        enviar = st.form_submit_button("💾 Guardar Registro", use_container_width=True)
    
    if enviar:
        fecha_str = str(fecha)
        # Validar duplicados
        existe = not df_existente.empty and (
            (df_existente['fecha'].astype(str) == fecha_str) & 
            (df_existente['operador'] == operador)
        ).any()
        
        if existe:
            st.error(f"❌ Ya existe un registro para {operador} el {fecha_str}")
        else:
            try:
                # Escribir fila
                hoja.append_row([fecha_str, operador, round(valor, 2)])
                st.success("✅ ¡Guardado en la nube!")
                st.balloons()
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error al guardar: {e}")

# --- 2. REPORTES ---
elif menu == "📊 Reportes":
    st.subheader("Análisis de Producción")
    if not df_existente.empty:
        df_existente['metraje'] = pd.to_numeric(df_existente['metraje'], errors='coerce')
        st.dataframe(df_existente.tail(10), use_container_width=True)
        resumen = df_existente.groupby("operador")["metraje"].sum().reset_index()
        st.bar_chart(data=resumen, x="operador", y="metraje")
    else:
        st.info("Sin datos.")

# --- 3. ADMINISTRAR ---
elif menu == "🗑️ Administrar":
    st.subheader("Eliminar Registros")
    if not df_existente.empty:
        st.dataframe(df_existente, use_container_width=True)
        idx = st.number_input("Índice de fila a borrar", min_value=0, max_value=len(df_existente)-1)
        if st.button("❌ Confirmar Eliminación"):
            try:
                hoja.delete_rows(int(idx) + 2)
                st.success("Eliminado.")
                st.rerun()
            except Exception as e:
                st.error(f"Error al borrar: {e}")
