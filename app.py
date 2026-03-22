import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import os

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Control de Metraje Pro", layout="wide")
st.title("🚀 Sistema de Control de Metraje (Nube)")

# ID único de tu hoja de Google Sheets
SPREADSHEET_ID = "1behqvajjNR4RYULbCGo2-w7IBXeC48fgnxXYiCGoOVU"

# --- FUNCIÓN DE CONEXIÓN ROBUSTA ---
def obtener_conexion():
    # 1. Intentar extraer credenciales de las variables de entorno (GitHub Actions)
    p_id = os.getenv("PROJECT_ID")
    p_key = os.getenv("PRIVATE_KEY")
    c_email = os.getenv("CLIENT_EMAIL")

    # 2. Si existen en el entorno, configuramos la conexión manual corregida
    if p_id and p_key and c_email:
        # Limpieza profunda de la llave privada
        p_key = p_key.replace('\\n', '\n').strip()
        if "-----BEGIN PRIVATE KEY-----" not in p_key:
            p_key = f"-----BEGIN PRIVATE KEY-----\n{p_key}\n-----END PRIVATE KEY-----"
        
        # Diccionario con el formato exacto que pide el SDK de Google
        creds = {
            "project_id": p_id,
            "private_key": p_key,
            "client_email": c_email,
            "token_uri": "https://oauth2.googleapis.com",
            "type": "service_account"
        }
        # Retornamos la conexión inyectando las credenciales
        return st.connection("gsheets", type=GSheetsConnection, **creds)
    
    # 3. Si no hay variables de entorno, usamos la conexión estándar (Streamlit Cloud Secrets)
    return st.connection("gsheets", type=GSheetsConnection)

# --- INICIO DE PROCESO ---
try:
    conn = obtener_conexion()
    
    # Leer datos actuales (ttl=0 para evitar caché y ver datos frescos)
    df_existente = conn.read(spreadsheet=SPREADSHEET_ID, ttl=0).dropna(how="all")
    st.sidebar.success("✅ Conexión con Google Sheets Exitosa")
    
except Exception as e:
    st.error(f"❌ Error de acceso: {e}")
    st.info("Copia este correo y dale permiso de EDITOR en tu Google Sheet:")
    st.code("mi-servidor@mi-servidor-490914.iam.gserviceaccount.com")
    st.stop()

# --- INTERFAZ DE USUARIO ---
menu = st.sidebar.radio("Menú Principal:", ["📝 Registrar Metraje", "📊 Ver Reportes Generales"])

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
        
        # Subir el DataFrame completo actualizado a la hoja de Google
        conn.update(spreadsheet=SPREADSHEET_ID, data=df_actualizado)
        st.success(f"✅ ¡Registro guardado para {operador} ({valor}m)!")
        st.balloons()
        st.rerun()

# --- OPCIÓN: REPORTES ---
elif menu == "📊 Ver Reportes Generales":
    st.subheader("Historial de Metrajes Registrados")
    if not df_existente.empty:
        st.dataframe(df_existente.sort_values(by="fecha", ascending=False), use_container_width=True)
        
        st.write("### Total Acumulado por Operador")
        st.bar_chart(df_existente.groupby("operador")["metraje"].sum())
    else:
        st.warning("No hay datos registrados aún.")
