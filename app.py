import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import os
import json

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Control de Metraje Pro", layout="wide")
st.title("🚀 Sistema de Control de Metraje (Nube)")

# --- 1. EXTRACCIÓN ROBUSTA DE CREDENCIALES ---
def obtener_credenciales():
    # Intenta obtener de Variables de Entorno (GitHub Actions)
    p_id = os.getenv("PROJECT_ID")
    p_key = os.getenv("PRIVATE_KEY")
    c_email = os.getenv("CLIENT_EMAIL")
    
    # Si no están en el entorno, intenta desde Streamlit Secrets (Cloud)
    if not p_id:
        try:
            p_id = st.secrets.get("project_id")
            p_key = st.secrets.get("private_key")
            c_email = st.secrets.get("client_email")
        except:
            pass

    # Verificación de seguridad
    if not all([p_id, p_key, c_email]):
        st.error("❌ Error: Los secretos no se detectan. Revisa los nombres en GitHub Secrets.")
        st.info("Deben llamarse exactamente: PROJECT_ID, PRIVATE_KEY, CLIENT_EMAIL")
        st.stop()
        
    # Limpieza crítica de la llave privada
    p_key = p_key.replace('\\n', '\n').strip()
    
    # Asegurar que tenga los encabezados correctos
    if "-----BEGIN PRIVATE KEY-----" not in p_key:
        p_key = f"-----BEGIN PRIVATE KEY-----\n{p_key}\n-----END PRIVATE KEY-----"
        
    return p_id, p_key, c_email

# Ejecutar extracción
project_id, private_key, client_email = obtener_credenciales()

# --- 2. CONEXIÓN A GOOGLE SHEETS ---
url_hoja = "https://docs.google.com"

try:
    # Diccionario de configuración para la conexión
    creds_dict = {
        "type": "service_account",
        "project_id": project_id,
        "private_key": private_key,
        "client_email": client_email,
        "token_uri": "https://oauth2.googleapis.com",
    }
    
    # Iniciar conexión
    conn = st.connection("gsheets", type=GSheetsConnection, credentials=creds_dict)
    
    # Leer datos actuales (ttl=0 para datos frescos)
    df_existente = conn.read(spreadsheet=url_hoja, ttl=0).dropna(how="all")
    st.sidebar.success("✅ Conexión Exitosa")
    
except Exception as e:
    st.error(f"❌ Error de acceso a la hoja: {e}")
    st.info("Verifica que el correo de la cuenta de servicio tenga acceso de EDITOR en la hoja.")
    st.stop()

# --- 3. INTERFAZ DE USUARIO ---
menu = st.sidebar.radio("Ir a:", ["📝 Registrar Metraje", "📊 Ver Reportes", "🗑️ Administrar Historial"])

# --- OPCIÓN: REGISTRAR ---
if menu == "📝 Registrar Metraje":
    st.subheader("Nuevo Registro Diario")
    with st.form("form_registro"):
        col1, col2 = st.columns(2)
        with col1:
            operador = st.selectbox("Seleccione Operador", ["Gabriel", "Adrian", "Freddy"])
            fecha = st.date_input("Fecha de trabajo", datetime.now())
        with col2:
            valor = st.number_input("Metraje alcanzado (m)", min_value=0.0, step=0.1)
        
        enviar = st.form_submit_button("💾 Guardar Registro", use_container_width=True)
    
    if enviar:
        fecha_str = str(fecha)
        # Verificar si ya existe registro
        es_duplicado = not df_existente.empty and (
            (df_existente['fecha'].astype(str) == fecha_str) & 
            (df_existente['operador'] == operador)
        ).any()
        
        if es_duplicado:
            st.error(f"❌ {operador} ya tiene un registro para el {fecha_str}.")
        else:
            nueva_fila = pd.DataFrame([{"fecha": fecha_str, "operador": operador, "metraje": valor}])
            df_actualizado = pd.concat([df_existente, nueva_fila], ignore_index=True)
            
            # Subir cambios
            conn.update(spreadsheet=url_hoja, data=df_actualizado)
            st.success("✅ ¡Guardado correctamente!")
            st.balloons()
            st.rerun()

# --- OPCIÓN: REPORTES ---
elif menu == "📊 Ver Reportes":
    st.subheader("Reporte General")
    if not df_existente.empty:
        st.dataframe(df_existente, use_container_width=True)
        st.bar_chart(df_existente.groupby("operador")["metraje"].sum())
    else:
        st.info("No hay datos registrados.")

# --- OPCIÓN: ADMINISTRAR ---
elif menu == "🗑️ Administrar Historial":
    st.subheader("Eliminar Registros")
    if not df_existente.empty:
        df_ver = df_existente.copy()
        st.dataframe(df_ver.tail(10))
        
        id_borrar = st.number_input("Índice de fila a borrar", min_value=0, max_value=len(df_existente)-1)
        if st.button("❌ Confirmar Eliminación", type="primary"):
            df_final = df_existente.drop(index=id_borrar)
            conn.update(spreadsheet=url_hoja, data=df_final)
            st.success("Registro eliminado.")
            st.rerun()
