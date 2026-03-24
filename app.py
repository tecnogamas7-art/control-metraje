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
        return df
    except:
        return pd.DataFrame(columns=['fecha', 'operador', 'metraje'])

df = cargar_datos()

# --- 3. INTERFAZ ---
st.title("📊 Panel de Control de Metraje")

# Métricas rápidas
if not df.empty:
    c1, c2, c3 = st.columns(3)
    c1.metric("🏗️ Metraje Total", f"{df['metraje'].sum():,.2f} m")
    c2.metric("📈 Promedio", f"{df['metraje'].mean():,.2f} m")
    c3.metric("📋 Registros", len(df))

st.sidebar.markdown("---")
opcion = st.sidebar.radio("Seleccione una acción:", ["📝 Registro Diario", "📊 Gráficas y Reportes", "🗑️ Eliminar Registro"])

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

# --- OPCIÓN: REPORTES ---
elif opcion == "📊 Gráficas y Reportes":
    if not df.empty:
        st.subheader("Análisis de Producción")
        st.bar_chart(data=df.groupby("operador")["metraje"].sum().reset_index(), x="operador", y="metraje")
        st.dataframe(df.sort_values(by="fecha", ascending=False), use_container_width=True)
    else:
        st.info("No hay datos.")

# --- OPCIÓN: ELIMINAR (CON CONFIRMACIÓN) ---
elif opcion == "🗑️ Eliminar Registro":
    st.subheader("Eliminar un Registro Existente")
    
    if not df.empty:
        # Creamos una lista de opciones legible para el usuario
        df_desc = df.copy()
        df_desc['id_borrar'] = df_desc.index + 2 # +2 porque gspread empieza en 1 y la fila 1 es encabezado
        df_desc['etiqueta'] = df_desc['fecha'].astype(str) + " | " + df_desc['operador'] + " | " + df_desc['metraje'].astype(str) + "m"
        
        seleccion = st.selectbox("Seleccione el registro que desea eliminar:", 
                                 options=df_desc['id_borrar'].tolist(),
                                 format_func=lambda x: df_desc[df_desc['id_borrar'] == x]['etiqueta'].values[0])
        
        st.warning(f"¿Está seguro de que desea eliminar el registro seleccionado?")
        
        # Botón de confirmación
        col_btn1, col_btn2 = st.columns([1, 4])
        confirmar = col_btn1.button("✅ SÍ, Eliminar", type="primary")
        
        if confirmar:
            try:
                # Eliminamos la fila en Google Sheets
                hoja.delete_rows(int(seleccion))
                st.success("🗑️ Registro eliminado correctamente.")
                st.balloons()
                st.rerun()
            except Exception as e:
                st.error(f"Error al eliminar: {e}")
    else:
        st.info("No hay registros para eliminar.")
