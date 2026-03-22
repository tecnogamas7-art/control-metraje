import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import os

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Control de Metraje Pro", layout="wide")
st.title("🚀 Sistema de Control de Metraje (Nube)")

# --- 1. EXTRACCIÓN Y LIMPIEZA DE CREDENCIALES ---
def obtener_credenciales():
    # Intentar obtener de variables de entorno (GitHub) o Streamlit Secrets
    p_id = os.getenv("PROJECT_ID") or st.secrets.get("project_id")
    p_key = os.getenv("PRIVATE_KEY") or st.secrets.get("private_key")
    c_email = os.getenv("CLIENT_EMAIL") or st.secrets.get("client_email")
    
    # Verificación de que existan los datos
    if not all([p_id, p_key, c_email]):
        st.error("❌ Faltan secretos de configuración (PROJECT_ID, PRIVATE_KEY o CLIENT_EMAIL)")
        st.stop()
        
    # LIMPIEZA CRÍTICA: Corrige los saltos de línea de la llave privada de Google
    p_key = p_key.replace('\\n', '\n').strip()
    
    # Asegurar que la llave tenga los encabezados correctos si GitHub los quitó
    if "-----BEGIN PRIVATE KEY-----" not in p_key:
        p_key = f"-----BEGIN PRIVATE KEY-----\n{p_key}\n-----END PRIVATE KEY-----"
        
    return p_id, p_key, c_email

# Ejecutar la extracción de datos
project_id, private_key, client_email = obtener_credenciales()

# --- 2. CONEXIÓN A GOOGLE SHEETS ---
# URL de tu hoja de cálculo específica
url_hoja = "https://docs.google.com"

try:
    # Diccionario de credenciales que espera la librería
    creds_dict = {
        "type": "service_account",
        "project_id": project_id,
        "private_key": private_key,
        "client_email": client_email,
        "token_uri": "https://oauth2.googleapis.com",
    }
    
    # Iniciar la conexión
    conn = st.connection("gsheets", type=GSheetsConnection, credentials=creds_dict)
    
    # Leer datos actuales (ttl=0 para obligar a leer datos nuevos de la nube)
    df_existente = conn.read(spreadsheet=url_hoja, ttl=0).dropna(how="all")
    st.sidebar.success("✅ Conexión con Google Sheets Exitosa")
    
except Exception as e:
    st.error(f"❌ Error de acceso a la hoja: {e}")
    st.info("Revisa que 'mi-servidor@mi-servidor-490914.iam.gserviceaccount.com' sea EDITOR en tu Excel.")
    st.stop()

# --- 3. INTERFAZ DE USUARIO ---
menu = st.sidebar.radio("Menú Principal:", ["📝 Registrar Metraje", "📊 Reportes Generales", "🗑️ Administrar Historial"])

# --- OPCIÓN: REGISTRAR ---
if menu == "📝 Registrar Metraje":
    st.subheader("Nuevo Registro Diario")
    with st.form("form_registro"):
        col1, col2 = st.columns(2)
        with col1:
            operador = st.selectbox("Seleccione Operador", ["Gabriel", "Adrian", "Freddy"])
            fecha = st.date_input("Fecha de trabajo", datetime.now())
        with col2:
            valor = st.number_input("Metraje alcanzado (m)", min_value=0.0, step=0.1, format="%.2f")
        
        enviar = st.form_submit_button("💾 Guardar Registro", use_container_width=True)
    
    if enviar:
        fecha_str = str(fecha)
        
        # Lógica para no borrar: añadir nueva fila al final del DataFrame
        nueva_fila = pd.DataFrame([{"fecha": fecha_str, "operador": operador, "metraje": valor}])
        df_actualizado = pd.concat([df_existente, nueva_fila], ignore_index=True)
        
        # Subir el DataFrame completo actualizado a la nube
        conn.update(spreadsheet=url_hoja, data=df_actualizado)
        st.success(f"✅ Registro guardado para {operador} ({valor}m)")
        st.balloons()
        # Reiniciar para refrescar datos
        st.rerun()

# --- OPCIÓN: REPORTES ---
elif menu == "📊 Ver Reportes Generales":
    st.subheader("Historial de Metrajes Registrados")
    if not df_existente.empty:
        st.dataframe(df_existente.sort_values(by="fecha", ascending=False), use_container_width=True)
        
        # Gráfico simple de producción por operador
        st.write("### Total por Operador")
        st.bar_chart(df_existente.groupby("operador")["metraje"].sum())
    else:
        st.info("Aún no hay datos registrados en la base de datos.")

# --- OPCIÓN: ADMINISTRAR ---
elif menu == "🗑️ Administrar Historial":
    st.subheader("Zona de Administración")
    if not df_existente.empty:
        st.write("Selecciona el índice de la fila que deseas eliminar:")
        st.dataframe(df_existente.tail(10))
        
        id_borrar = st.number_input("Índice de fila", min_value=0, max_value=len(df_existente)-1, step=1)
        
        if st.button("❌ Eliminar Permanentemente", type="primary"):
            df_final = df_existente.drop(index=id_borrar)
            conn.update(spreadsheet=url_hoja, data=df_final)
            st.success("Registro eliminado correctamente.")
            st.rerun()
