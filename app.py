import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import os

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Control de Metraje Pro", layout="wide", page_icon="🚀")
st.title("🚀 Sistema de Control de Metraje (Nube)")

# ID de tu hoja de Google (Extraído de tu URL)
SPREADSHEET_ID = "1behqvajjNR4RYULbCGo2-w7IBXeC48fgnxXYiCGoOVU"

# --- FUNCIÓN DE CONEXIÓN ROBUSTA (GSPREAD) ---
@st.cache_resource
def conectar_google():
    # Intentar obtener de secrets (Streamlit Cloud) o variables de entorno
    p_id = st.secrets.get("project_id") or os.getenv("PROJECT_ID")
    p_key = st.secrets.get("private_key") or os.getenv("PRIVATE_KEY")
    c_email = st.secrets.get("client_email") or os.getenv("CLIENT_EMAIL")

    if not all([p_id, p_key, c_email]):
        st.error("❌ Faltan secretos de configuración (project_id, private_key o client_email).")
        st.info("Asegúrate de haber configurado los 'Secrets' en el dashboard de Streamlit Cloud.")
        st.stop()

    # Limpieza crucial de la clave privada
    p_key = p_key.replace('\\n', '\n').strip()
    
    # SCOPES CORRECTOS (Esto soluciona el error 404/403)
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    try:
        creds = Credentials.from_service_account_info({
            "type": "service_account",
            "project_id": p_id,
            "private_key": p_key,
            "client_email": c_email,
            "token_uri": "https://oauth2.googleapis.com",
        }, scopes=scopes)
        
        client = gspread.authorize(creds)
        # Abrir la hoja y seleccionar la primera pestaña
        return client.open_by_key(SPREADSHEET_ID).get_worksheet(0)
    except Exception as e:
        st.error(f"❌ Error al autenticar con Google: {e}")
        st.stop()

# --- INICIO DE PROCESO ---
try:
    hoja = conectar_google()
    # Leer datos convirtiendo a DataFrame
    datos = hoja.get_all_records()
    df_existente = pd.DataFrame(datos)
    # Si la hoja está vacía, asegurar que las columnas existan
    if df_existente.empty:
        df_existente = pd.DataFrame(columns=['fecha', 'operador', 'metraje'])
    st.sidebar.success("✅ Conexión Establecida")
except Exception as e:
    st.error(f"❌ Error de acceso a la hoja: {e}")
    st.info("Paso obligatorio: Ve a tu Google Sheet, clic en 'Compartir' y añade el correo de tu 'client_email' como Editor.")
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
            # Asegurar que 'metraje' sea numérico para el pivot
            df_filtrado['metraje'] = pd.to_numeric(df_filtrado['metraje'], errors='coerce')
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
        st.write("Últimos 10 registros:")
        st.dataframe(df_existente.tail(10), use_container_width=True)
        
        id_borrar = st.number_input("Seleccione el índice a eliminar (0 es el primero de la lista de arriba)", 
                                   min_value=0, max_value=len(df_existente)-1)
        
        if st.button("❌ Eliminar Registro"):
            # En gspread, las filas empiezan en 1. Encabezado es 1, datos empiezan en 2.
            # id_borrar es el índice del dataframe.
            fila_real = int(id_borrar) + 2
            hoja.delete_rows(fila_real)
            st.success(f"Registro en fila {fila_real} eliminado correctamente.")
            st.rerun()
