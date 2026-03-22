import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import os

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Control de Metraje Pro", layout="wide", page_icon="🚀")
st.title("🚀 Sistema de Control de Metraje (Nube)")

# ID de tu hoja de Google
SPREADSHEET_ID = "1behqvajjNR4RYULbCGo2-w7IBXeC48fgnxXYiCGoOVU"

# --- FUNCIÓN DE CONEXIÓN ROBUSTA (GSPREAD) ---
@st.cache_resource
def conectar_google():
    p_id = os.getenv("PROJECT_ID") or st.secrets.get("project_id")
    p_key = os.getenv("PRIVATE_KEY") or st.secrets.get("private_key")
    c_email = os.getenv("CLIENT_EMAIL") or st.secrets.get("client_email")

    if not all([p_id, p_key, c_email]):
        st.error("❌ Faltan secretos de configuración.")
        st.stop()

    p_key = p_key.replace('\\n', '\n').strip()
    
    scopes = ["https://www.googleapis.com", "https://www.googleapis.com"]
    creds = Credentials.from_service_account_info({
        "type": "service_account",
        "project_id": p_id,
        "private_key": p_key,
        "client_email": c_email,
        "token_uri": "https://oauth2.googleapis.com",
    }, scopes=scopes)
    
    client = gspread.authorize(creds)
    return client.open_by_key(SPREADSHEET_ID).get_worksheet(0)

# --- INICIO DE PROCESO ---
try:
    hoja = conectar_google()
    # Leer datos convirtiendo a DataFrame
    datos = hoja.get_all_records()
    df_existente = pd.DataFrame(datos)
    st.sidebar.success("✅ Conexión Establecida")
except Exception as e:
    st.error(f"❌ Error de acceso: {e}")
    st.stop()

# --- MENÚ LATERAL ---
menu = st.sidebar.radio("Ir a:", ["📝 Registrar Metraje", "📊 Ver Reportes Generales", "🗑️ Administrar Historial"])

# --- 📝 OPCIÓN 1: REGISTRAR ---
if menu == "📝 Registrar Metraje":
    st.subheader("Nuevo Registro Diario")
    with st.form("form_registro"):
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
            # GUARDAR: gspread permite añadir filas directamente sin errores de permisos
            nueva_fila = [fecha_str, operador, round(valor, 2)]
            hoja.append_row(nueva_fila)
            st.success(f"✅ ¡Registro guardado: {operador} ({valor}m)!")
            st.balloons()
            st.rerun()

# --- 📊 OPCIÓN 2: REPORTES ---
elif menu == "📊 Ver Reportes Generales":
    st.subheader("📅 Reporte Mensual Detallado")
    if not df_existente.empty:
        df_existente['fecha'] = df_existente['fecha'].astype(str)
        mes_sel = st.text_input("Filtrar por Mes (YYYY-MM):", datetime.now().strftime("%Y-%m"))
        df_filtrado = df_existente[df_existente['fecha'].str.contains(mes_sel)].copy()
        
        if not df_filtrado.empty:
            tabla_pivot = df_filtrado.pivot_table(index='fecha', columns='operador', values='metraje', aggfunc='sum').fillna(0)
            st.dataframe(tabla_pivot.style.format("{:.2f}"), use_container_width=True)
            st.bar_chart(df_filtrado.groupby("operador")["metraje"].sum())
        else:
            st.warning("No hay datos para este mes.")
    else:
        st.info("La base de datos está vacía.")

# --- 🗑️ OPCIÓN 3: ADMINISTRAR ---
elif menu == "🗑️ Administrar Historial":
    st.subheader("Gestión de Datos")
    if not df_existente.empty:
        st.dataframe(df_existente.tail(10), use_container_width=True)
        # En Google Sheets las filas empiezan en 1 y tienen encabezado, por eso +2
        id_borrar = st.number_input("Seleccione el ID (Fila) a eliminar", min_value=0, max_value=len(df_existente)-1)
        
        if st.button("❌ Eliminar Registro"):
            hoja.delete_rows(int(id_borrar) + 2)
            st.success("Registro eliminado correctamente.")
            st.rerun()
