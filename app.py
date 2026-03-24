import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Control de Metraje Pro", layout="wide", page_icon="🚀")

# ID DE TU HOJA (Fijo y verificado)
SPREADSHEET_ID = "1behqvajjNR4RYULbCGo2-w7IBXeC48fgnxXYiCGoOVU"

# --- FUNCIÓN DE CONEXIÓN ---
@st.cache_resource
def conectar_google():
    try:
        # 1. Cargar credenciales desde st.secrets de Streamlit Cloud
        # Asegúrate de que en el panel de Streamlit se llamen exactamente así
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
        
        # 2. Abrir el archivo por ID (Evita errores de búsqueda por nombre)
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        
        # 3. Intentar abrir la pestaña Metrajes_DB, si no, abrir la primera (index 0)
        try:
            return spreadsheet.worksheet("Metrajes_DB")
        except gspread.exceptions.WorksheetNotFound:
            return spreadsheet.get_worksheet(0)
            
    except Exception as e:
        st.error(f"❌ Error crítico de conexión: {e}")
        st.info("Revisa que tus 'Secrets' en Streamlit tengan: project_id, private_key y client_email.")
        st.stop()

# --- INICIO DE LA APP ---
hoja = conectar_google()

try:
    # Obtener todos los registros de la hoja
    datos = hoja.get_all_records()
    df_existente = pd.DataFrame(datos)
    
    # Si la hoja está vacía, forzamos las columnas para evitar errores en la tabla
    if df_existente.empty:
        df_existente = pd.DataFrame(columns=['fecha', 'operador', 'metraje'])
        
    st.sidebar.success(f"✅ Conectado a: {hoja.title}")
except Exception as e:
    st.error(f"❌ Error al leer los datos de la hoja: {e}")
    st.info("Asegúrate de que la primera fila de tu Excel tenga estos nombres: fecha, operador, metraje")
    st.stop()

# --- INTERFAZ DE USUARIO ---
st.title("📊 Control de Metraje Pro")
st.markdown("---")

menu = st.sidebar.radio("Menú de Navegación:", ["📝 Registrar Metraje", "📈 Reportes y Gráficos", "🗑️ Administrar Datos"])

# --- OPCIÓN 1: REGISTRAR ---
if menu == "📝 Registrar Metraje":
    st.subheader("Nuevo Registro de Producción")
    with st.form("form_registro", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            operador = st.selectbox("Seleccione Operador", ["Gabriel", "Adrian", "Freddy"])
            fecha = st.date_input("Fecha de trabajo", datetime.now())
        with col2:
            valor = st.number_input("Metraje alcanzado (m)", min_value=0.0, step=0.1, format="%.2f")
        
        btn_enviar = st.form_submit_button("💾 Guardar en Google Sheets", use_container_width=True)
    
    if btn_enviar:
        fecha_str = str(fecha)
        # Verificar si ya existe registro para ese operador en esa fecha
        existe = not df_existente.empty and ((df_existente['fecha'].astype(str) == fecha_str) & (df_existente['operador'] == operador)).any()
        
        if existe:
            st.warning(f"⚠️ El operador **{operador}** ya tiene un registro para el día **{fecha_str}**.")
        else:
            try:
                hoja.append_row([fecha_str, operador, round(valor, 2)])
                st.success(f"✅ ¡Registro guardado exitosamente!")
                st.balloons()
                st.rerun()
            except Exception as e:
                st.error(f"Error al guardar: {e}")

# --- OPCIÓN 2: REPORTES ---
elif menu == "📈 Reportes y Gráficos":
    st.subheader("Visualización de Resultados")
    if not df_existente.empty:
        df_existente['metraje'] = pd.to_numeric(df_existente['metraje'], errors='coerce')
        
        st.write("### Tabla General de Datos")
        st.dataframe(df_existente.sort_values(by="fecha", ascending=False), use_container_width=True)
        
        st.write("### Producción Acumulada por Operador")
        resumen = df_existente.groupby("operador")["metraje"].sum().reset_index()
        st.bar_chart(data=resumen, x="operador", y="metraje")
    else:
        st.info("Aún no hay datos registrados en la nube.")

# --- OPCIÓN 3: ADMINISTRAR ---
elif menu == "🗑️ Administrar Datos":
    st.subheader("Gestión de Historial")
    if not df_existente.empty:
        st.write("Seleccione la fila que desea eliminar:")
        st.dataframe(df_existente, use_container_width=True)
        
        fila_idx = st.number_input("Escriba el índice de la fila a borrar (columna izquierda)", min_value=0, max_value=len(df_existente)-1)
        
        if st.button("❌ Eliminar Fila Seleccionada"):
            # En gspread las filas empiezan en 1. Fila 1 = Encabezados. Fila 2 = Índice 0 del DataFrame.
            hoja.delete_rows(int(fila_idx) + 2)
            st.success("Registro eliminado de la nube.")
            st.rerun()
