import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- 1. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Control de Metraje Pro", layout="wide", page_icon="🏗️")

# ID de tu hoja
SPREADSHEET_ID = "1BJG1sm8lRUK8TPcw9dNr5oQMIo3fJ93IhWdue5Hh10E"

@st.cache_resource
def conectar_google():
    try:
        info = {
            "type": "service_account",
            "project_id": st.secrets["project_id"].strip(),
            "private_key": st.secrets["private_key"].replace('\\n', '\n').strip(),
            "client_email": st.secrets["client_email"].strip(),
            "token_uri": "https://oauth2.googleapis.com/token",
        }
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(info, scopes=scopes)
        client = gspread.authorize(creds)
        return client.open_by_key(SPREADSHEET_ID).get_worksheet(0)
    except Exception as e:
        st.error(f"❌ Error de Conexión: {e}")
        st.stop()

# --- 2. CARGA DE DATOS ---
hoja = conectar_google()

def cargar_datos():
    try:
        registros = hoja.get_all_records()
        df = pd.DataFrame(registros)
        if not df.empty:
            df['metraje'] = pd.to_numeric(df['metraje'], errors='coerce').fillna(0)
            # Asegurar que la fecha sea reconocida como tal
            df['fecha'] = pd.to_datetime(df['fecha']).dt.date
        return df
    except:
        return pd.DataFrame(columns=['fecha', 'operador', 'metraje'])

df_raw = cargar_datos()

# --- 3. INTERFAZ ---
st.title("📊 Panel de Control de Metraje")

# --- NAVEGACIÓN LATERAL ---
st.sidebar.markdown("---")
opcion = st.sidebar.radio("Seleccione una acción:", ["📝 Registro Diario", "📊 Historial y Gráficas", "🗑️ Eliminar Registro"])

# --- OPCIÓN: REGISTRAR ---
if opcion == "📝 Registro Diario":
    st.subheader("Registrar Nueva Producción")
    with st.form("nuevo_registro", clear_on_submit=True):
        col1, col2 = st.columns(2)
        op = col1.selectbox("Operador:", ["Gabriel", "Adrian", "Freddy"])
        fec = col1.date_input("Fecha:", datetime.now())
        val = col2.number_input("Metraje (m):", min_value=0.0)
        if st.form_submit_button("💾 Guardar"):
            hoja.append_row([str(fec), op, round(val, 2)])
            st.success("¡Guardado!")
            st.rerun()

# --- OPCIÓN: HISTORIAL MODIFICADO (COLUMNAS POR NOMBRE) ---
elif opcion == "📊 Historial y Gráficas":
    if not df_raw.empty:
        st.subheader("📈 Resumen de Producción")
        
        # MÉTRICAS GENERALES
        c1, c2, c3 = st.columns(3)
        c1.metric("🏗️ Metraje Total", f"{df_raw['metraje'].sum():,.2f} m")
        c2.metric("📈 Promedio General", f"{df_raw['metraje'].mean():,.2f} m")
        c3.metric("📋 Registros", len(df_raw))

        st.markdown("---")
        
        # --- ALGORITMO DE TRANSFORMACIÓN (PIVOT TABLE) ---
        # Convertimos la tabla vertical en una donde la fecha es el índice y los operadores son columnas
        df_pivot = df_raw.pivot_table(
            index='fecha', 
            columns='operador', 
            values='metraje', 
            aggfunc='sum'
        ).fillna(0) # Si un operador no trabajó ese día, ponemos 0
        
        # Ordenar por fecha más reciente arriba
        df_pivot = df_pivot.sort_index(ascending=False)

        st.write("#### 📅 Historial por Fecha y Operador")
        st.dataframe(df_pivot, use_container_width=True)

        st.markdown("---")
        st.write("#### 📊 Comparativa Total")
        st.bar_chart(df_raw.groupby("operador")["metraje"].sum())
        
    else:
        st.info("No hay datos suficientes.")

# --- OPCIÓN: ELIMINAR ---
elif opcion == "🗑️ Eliminar Registro":
    st.subheader("Eliminar un Registro")
    if not df_raw.empty:
        df_desc = df_raw.copy()
        df_desc['id_borrar'] = df_desc.index + 2
        df_desc['etiqueta'] = df_desc['fecha'].astype(str) + " | " + df_desc['operador'] + " | " + df_desc['metraje'].astype(str) + "m"
        
        seleccion = st.selectbox("Seleccione el registro:", 
                                 options=df_desc['id_borrar'].tolist(),
                                 format_func=lambda x: df_desc[df_desc['id_borrar'] == x]['etiqueta'].values[0])
        
        if st.button("✅ Confirmar Eliminación", type="primary"):
            hoja.delete_rows(int(seleccion))
            st.success("Eliminado.")
            st.rerun()
