import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import os

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Control de Metraje Pro", layout="wide")
st.title("🚀 Sistema de Control de Metraje (Nube)")

# --- 1. EXTRACCIÓN ROBUSTA DE CREDENCIALES ---
def obtener_credenciales():
    # Intentar sacar de GitHub Actions/Environment o de Streamlit Cloud Secrets
    p_id = os.getenv("PROJECT_ID") or st.secrets.get("project_id")
    p_key = os.getenv("PRIVATE_KEY") or st.secrets.get("private_key")
    c_email = os.getenv("CLIENT_EMAIL") or st.secrets.get("client_email")
    
    # Validar que existan antes de seguir
    faltantes = []
    if not p_id: faltantes.append("PROJECT_ID")
    if not p_key: faltantes.append("PRIVATE_KEY")
    if not c_email: faltantes.append("CLIENT_EMAIL")
    
    if faltantes:
        st.error(f"❌ Faltan secretos en GitHub/Streamlit: {', '.join(faltantes)}")
        st.stop()
        
    # Limpieza absoluta de la llave (esto quita el error de conexión vacío)
    p_key = p_key.replace('\\n', '\n').strip()
    if not p_key.startswith("-----BEGIN PRIVATE KEY-----"):
        p_key = f"-----BEGIN PRIVATE KEY-----\n{p_key}\n-----END PRIVATE KEY-----"
        
    return p_id, p_key, c_email

project_id, private_key, client_email = obtener_credenciales()

# --- 2. CONEXIÓN A GOOGLE SHEETS ---
try:
    url_hoja = "https://docs.google.com"
    
    # Formato de diccionario exigido por gspread/gsheets
    creds = {
        "type": "service_account",
        "project_id": project_id,
        "private_key": private_key,
        "client_email": client_email,
        "token_uri": "https://oauth2.googleapis.com",
    }
    
    # Conectar
    conn = st.connection("gsheets", type=GSheetsConnection, credentials=creds)
    # Leer datos
    df_existente = conn.read(spreadsheet=url_hoja, ttl=0).dropna(how="all")
    
except Exception as e:
    st.error(f"❌ Error de acceso: {str(e)}")
    st.info("Asegúrate de que 'mi-servidor@mi-servidor-490914.iam.gserviceaccount.com' sea EDITOR en la hoja.")
    st.stop()

# --- 3. INTERFAZ Y LÓGICA ---
menu = st.sidebar.radio("Ir a:", ["📝 Registrar", "📊 Reportes", "🗑️ Administrar"])

if menu == "📝 Registrar":
    st.subheader("Nuevo Registro")
    with st.form("registro"):
        op = st.selectbox("Operador", ["Gabriel", "Adrian", "Freddy"])
        fe = st.date_input("Fecha", datetime.now())
        val = st.number_input("Metraje (m)", min_value=0.0)
        btn = st.form_submit_button("Guardar")
        
    if btn:
        # Evitar duplicados
        fecha_s = str(fe)
        existe = not df_existente.empty and ((df_existente['fecha'].astype(str) == fecha_s) & (df_existente['operador'] == op)).any()
        
        if existe:
            st.warning("Ya existe un registro para este operador hoy.")
        else:
            nueva = pd.DataFrame([{"fecha": fecha_s, "operador": op, "metraje": val}])
            df_final = pd.concat([df_existente, nueva], ignore_index=True)
            conn.update(spreadsheet=url_hoja, data=df_final)
            st.success("✅ ¡Guardado!")
            st.rerun()

elif menu == "📊 Reportes":
    st.dataframe(df_existente, use_container_width=True)

elif menu == "🗑️ Administrar":
    st.write("Registros actuales:")
    st.table(df_existente.tail(5))
    if st.button("Limpiar toda la tabla"):
        # Crear DF solo con cabeceras
        df_vacio = pd.DataFrame(columns=["fecha", "operador", "metraje"])
        conn.update(spreadsheet=url_hoja, data=df_vacio)
        st.rerun()
