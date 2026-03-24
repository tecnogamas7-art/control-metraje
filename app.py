import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import os

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Control de Metraje Pro", layout="wide", page_icon="🚀")

# Título visual
st.markdown("<h1 style='text-align: center;'>🚀 Sistema de Control de Metraje</h1>", unsafe_allow_html=True)
st.markdown("---")

# ID de tu hoja de Google (Extraído de tu URL)
SPREADSHEET_ID = "1behqvajjNR4RYULbCGo2-w7IBXeC48fgnxXYiCGoOVU"

# --- FUNCIÓN DE CONEXIÓN ROBUSTA ---
@st.cache_resource
def conectar_google():
    # Intentar obtener de st.secrets (Streamlit Cloud) o variables de entorno (Local)
    try:
        p_id = st.secrets.get("project_id") or os.getenv("PROJECT_ID")
        p_key = st.secrets.get("private_key") or os.getenv("PRIVATE_KEY")
        c_email = st.secrets.get("client_email") or os.getenv("CLIENT_EMAIL")

        if not all([p_id, p_key, c_email]):
            st.error("❌ Error: Faltan credenciales en los Secrets de Streamlit.")
            st.stop()

        # Limpieza de la llave privada (Paso crítico para evitar el Error 404/400)
        p_key = p_key.replace('\\n', '\n').strip()
        if not p_key.startswith("-----BEGIN PRIVATE KEY-----"):
            p_key = f"-----BEGIN PRIVATE KEY-----\n{p_key}\n-----END PRIVATE KEY-----"

        # SCOPES específicos y completos para Google Sheets y Drive
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]

        creds = Credentials.from_service_account_info({
            "type": "service_account",
            "project_id": p_id,
            "private_key": p_key,
            "client_email": c_email,
            "token_uri": "https://oauth2.googleapis.com",
        }, scopes=scopes)

        client = gspread.authorize(creds)
        # Abrimos por ID y seleccionamos la primera hoja (index 0)
        return client.open_by_key(SPREADSHEET_ID).get_worksheet(0)
    
    except Exception as e:
        st.error(f"❌ Error de autenticación: {e}")
        st.stop()

# --- CARGA DE DATOS ---
try:
    hoja = conectar_google()
    datos = hoja.get_all_records()
    df_existente = pd.DataFrame(datos)
    
    # Asegurar que el DataFrame tenga las columnas correctas si la hoja está vacía
    if df_existente.empty:
        df_existente = pd.DataFrame(columns=['fecha', 'operador', 'metraje'])
        
    st.sidebar.success("✅ Conexión con Google Sheets Activa")
except Exception as e:
    st.error(f"❌ No se pudo leer la hoja: {e}")
    st.info("Asegúrate de haber compartido la hoja con el correo de 'client_email' como Editor.")
    st.stop()

# --- MENÚ LATERAL ---
menu = st.sidebar.radio("Navegación:", ["📝 Registrar Metraje", "📊 Reportes", "🗑️ Administrar"])

# --- 📝 REGISTRAR METRAJE ---
if menu == "📝 Registrar Metraje":
    st.subheader("Nuevo Registro de Trabajo")
    with st.form("form_registro", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            operador = st.selectbox("Operador", ["Gabriel", "Adrian", "Freddy"])
            fecha = st.date_input("Fecha", datetime.now())
        with col2:
            valor = st.number_input("Metraje (m)", min_value=0.0, step=0.1, format="%.2f")
        
        btn_guardar = st.form_submit_button("💾 Guardar en la Nube")

    if btn_guardar:
        fecha_str = str(fecha)
        # Verificar duplicados
        es_duplicado = not df_existente.empty and (
            (df_existente['fecha'].astype(str) == fecha_str) & 
            (df_existente['operador'] == operador)
        ).any()

        if es_duplicado:
            st.warning(f"⚠️ Ya existe un registro para {operador} el día {fecha_str}.")
        else:
            try:
                hoja.append_row([fecha_str, operador, valor])
                st.success("✅ ¡Datos guardados correctamente!")
                st.balloons()
                st.rerun()
            except Exception as e:
                st.error(f"Error al guardar: {e}")

# --- 📊 REPORTES ---
elif menu == "📊 Reportes":
    st.subheader("Visualización de Resultados")
    if not df_existente.empty:
        # Convertir metraje a numérico por seguridad
        df_existente['metraje'] = pd.to_numeric(df_existente['metraje'], errors='coerce')
        
        st.write("### Resumen Total por Operador")
        resumen = df_existente.groupby("operador")["metraje"].sum().reset_index()
        st.bar_chart(data=resumen, x="operador", y="metraje")
        
        st.write("### Tabla de Datos Recientes")
        st.dataframe(df_existente.sort_values(by="fecha", ascending=False), use_container_width=True)
    else:
        st.info("Aún no hay datos registrados.")

# --- 🗑️ ADMINISTRAR ---
elif menu == "🗑️ Administrar":
    st.subheader("Eliminar Registros")
    if not df_existente.empty:
        st.warning("Selecciona el índice de la fila que deseas borrar.")
        # Mostramos el índice para que el usuario sepa qué número poner
        st.dataframe(df_existente)
        
        fila_idx = st.number_input("Índice a eliminar", min_value=0, max_value=len(df_existente)-1, step=1)
        
        if st.button("❌ Eliminar Fila Seleccionada"):
            # En gspread las filas son 1-based. 1 es encabezado, 2 es el primer dato (índice 0)
            hoja.delete_rows(int(fila_idx) + 2)
            st.success("Registro eliminado.")
            st.rerun()
