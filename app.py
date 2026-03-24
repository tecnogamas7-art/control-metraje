import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Control de Metraje Pro", layout="wide", page_icon="🚀")

# ID de tu hoja (Verificado de tu URL)
SPREADSHEET_ID = "1behqvajjNR4RYULbCGo2-w7IBXeC48fgnxXYiCGoOVU"

@st.cache_resource
def conectar_google():
    try:
        # 1. Limpieza extrema de los Secrets de Streamlit
        # Quitamos espacios en blanco o saltos de línea accidentales al inicio/final
        p_key = st.secrets["private_key"].replace('\\n', '\n').strip()
        c_email = st.secrets["client_email"].strip()
        p_id = st.secrets["project_id"].strip()

        # 2. Configuración técnica de credenciales
        info = {
            "type": "service_account",
            "project_id": p_id,
            "private_key": p_key,
            "client_email": c_email,
            "token_uri": "https://oauth2.googleapis.com",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        }

        # Scopes necesarios para que Google no devuelva error 404
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]

        # 3. Autenticación
        creds = Credentials.from_service_account_info(info, scopes=scopes)
        client = gspread.authorize(creds)
        
        # 4. Abrir la hoja por ID (Es el método más seguro)
        return client.open_by_key(SPREADSHEET_ID).sheet1
            
    except Exception as e:
        st.error(f"❌ Error crítico de conexión: {e}")
        st.info("💡 Asegúrate de haber compartido la hoja con: mi-servidor@mi-servidor-490914.iam.gserviceaccount.com")
        st.stop()

# --- CARGA DE DATOS ---
hoja = conectar_google()

try:
    # Intentar obtener datos existentes
    registros = hoja.get_all_records()
    df_existente = pd.DataFrame(registros)
    if df_existente.empty:
        df_existente = pd.DataFrame(columns=['fecha', 'operador', 'metraje'])
    st.sidebar.success("✅ Conexión establecida con la nube")
except Exception as e:
    # Si la hoja está totalmente vacía (sin encabezados), creamos el DF base
    df_existente = pd.DataFrame(columns=['fecha', 'operador', 'metraje'])
    st.sidebar.warning("⚠️ Hoja lista para recibir datos")

# --- INTERFAZ ---
st.title("📊 Control de Metraje Diarios")
st.markdown("---")

menu = st.sidebar.radio("Navegación:", ["📝 Registrar Metraje", "📈 Ver Historial"])

if menu == "📝 Registrar Metraje":
    st.subheader("Ingresar nueva producción")
    
    with st.form("form_metraje", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            operador = st.selectbox("Operador:", ["Gabriel", "Adrian", "Freddy"])
            fecha = st.date_input("Fecha:", datetime.now())
        with col2:
            metraje = st.number_input("Metraje alcanzado (m):", min_value=0.0, step=0.1, format="%.2f")
        
        btn_guardar = st.form_submit_button("💾 Guardar en Google Sheets", use_container_width=True)

    if btn_guardar:
        fecha_str = str(fecha)
        # Verificar duplicado en la sesión actual
        duplicado = not df_existente.empty and (
            (df_existente['fecha'].astype(str) == fecha_str) & 
            (df_existente['operador'] == operador)
        ).any()

        if duplicado:
            st.warning(f"⚠️ Ya existe un registro para **{operador}** el día **{fecha_str}**.")
        else:
            try:
                # Escribir la nueva fila en Google Sheets
                hoja.append_row([fecha_str, operador, round(metraje, 2)])
                st.success(f"✅ ¡Registro de {operador} guardado!")
                st.balloons()
                st.rerun()
            except Exception as e:
                st.error(f"No se pudo guardar: {e}")

elif menu == "📈 Ver Historial":
    st.subheader("Producción Acumulada")
    if not df_existente.empty:
        # Mostrar tabla
        st.dataframe(df_existente.sort_values(by="fecha", ascending=False), use_container_width=True)
        
        # Gráfico simple
        st.markdown("### Total por Operador")
        df_existente['metraje'] = pd.to_numeric(df_existente['metraje'], errors='coerce')
        resumen = df_existente.groupby("operador")["metraje"].sum().reset_index()
        st.bar_chart(data=resumen, x="operador", y="metraje")
    else:
        st.info("No hay datos registrados aún.")
