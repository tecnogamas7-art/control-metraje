import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import os

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Control de Metraje Pro", layout="wide", page_icon="🚀")

# Estilo visual
st.markdown("<h1 style='text-align: center;'>🚀 Sistema de Control de Metraje (Nube)</h1>", unsafe_allow_html=True)
st.markdown("---")

# ID DE TU HOJA (Extraído de tu URL)
SPREADSHEET_ID = "1behqvajjNR4RYULbCGo2-w7IBXeC48fgnxXYiCGoOVU"

# --- FUNCIÓN DE CONEXIÓN ROBUSTA ---
@st.cache_resource
def conectar_google():
    try:
        # Cargamos los secretos de Streamlit Cloud
        # Asegúrate de que en 'Secrets' existan: project_id, private_key y client_email
        info = {
            "type": "service_account",
            "project_id": st.secrets["project_id"],
            "private_key": st.secrets["private_key"].replace('\\n', '\n'),
            "client_email": st.secrets["client_email"],
            "token_uri": "https://oauth2.googleapis.com",
        }

        # SCOPES obligatorios para evitar el Error 404
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]

        creds = Credentials.from_service_account_info(info, scopes=scopes)
        client = gspread.authorize(creds)
        
        # Abrimos la hoja por ID y seleccionamos la primera pestaña (index 0)
        return client.open_by_key(SPREADSHEET_ID).get_worksheet(0)
    
    except Exception as e:
        st.error(f"❌ Error de autenticación: {e}")
        st.info("💡 RECUERDA: Debes compartir tu Google Sheet con el correo de tu cuenta de servicio como 'Editor'.")
        st.stop()

# --- CARGA DE DATOS ---
hoja = conectar_google()

try:
    datos = hoja.get_all_records()
    df_existente = pd.DataFrame(datos)
    
    # Si la hoja está vacía, creamos un DF con las columnas esperadas
    if df_existente.empty:
        df_existente = pd.DataFrame(columns=['fecha', 'operador', 'metraje'])
        
    st.sidebar.success("✅ Conexión con Google Sheets Activa")
except Exception as e:
    st.error(f"❌ Error al leer la hoja: {e}")
    st.stop()

# --- MENÚ LATERAL ---
menu = st.sidebar.radio("Navegación:", ["📝 Registrar Metraje", "📊 Ver Reportes", "🗑️ Administrar Historial"])

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
        # Lógica de duplicados
        es_duplicado = not df_existente.empty and (
            (df_existente['fecha'].astype(str) == fecha_str) & 
            (df_existente['operador'] == operador)
        ).any()
        
        if es_duplicado:
            st.error(f"❌ Ya existe un registro para **{operador}** en la fecha **{fecha_str}**.")
        else:
            try:
                hoja.append_row([fecha_str, operador, round(valor, 2)])
                st.success(f"✅ ¡Registro guardado: {operador} ({valor}m)!")
                st.balloons()
                st.rerun()
            except Exception as e:
                st.error(f"Error al guardar: {e}")

# --- 2. REPORTES ---
elif menu == "📊 Ver Reportes":
    st.subheader("📅 Reporte de Producción")
    if not df_existente.empty:
        df_existente['metraje'] = pd.to_numeric(df_existente['metraje'], errors='coerce')
        
        # Filtro rápido
        st.write("### Últimos registros")
        st.dataframe(df_existente.tail(10), use_container_width=True)
        
        # Gráfico
        st.write("### Metraje Total por Operador")
        resumen = df_existente.groupby("operador")["metraje"].sum().reset_index()
        st.bar_chart(data=resumen, x="operador", y="metraje")
    else:
        st.info("La base de datos está vacía.")

# --- 3. ADMINISTRAR ---
elif menu == "🗑️ Administrar Historial":
    st.subheader("Gestión de Datos")
    if not df_existente.empty:
        st.write("Seleccione la fila que desea eliminar:")
        st.dataframe(df_existente, use_container_width=True)
        
        id_borrar = st.number_input("Índice de fila a eliminar (0 es la primera)", min_value=0, max_value=len(df_existente)-1)
        
        if st.button("❌ Eliminar Registro"):
            # +2 porque gspread es 1-based y la fila 1 es el encabezado
            hoja.delete_rows(int(id_borrar) + 2)
            st.success("Registro eliminado correctamente.")
            st.rerun()
