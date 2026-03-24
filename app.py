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
            df['fecha'] = pd.to_datetime(df['fecha']).dt.date
        return df
    except:
        return pd.DataFrame(columns=['fecha', 'operador', 'metraje'])

df_raw = cargar_datos()

# --- 3. INTERFAZ ---
st.title("📊 Panel de Control de Metraje")

# --- NAVEGACIÓN LATERAL ---
st.sidebar.markdown("---")
opcion = st.sidebar.radio("Seleccione una acción:", ["📝 Registro Diario", "📊 Historial y Reportes", "🗑️ Eliminar Registro"])

# --- OPCIÓN: REGISTRAR ---
if opcion == "📝 Registro Diario":
    st.subheader("Registrar Nueva Producción")
    with st.form("nuevo_registro", clear_on_submit=True):
        col1, col2 = st.columns(2)
        op = col1.selectbox("Operador:", ["Gabriel", "Adrian", "Freddy"])
        fec = col1.date_input("Fecha:", datetime.now())
        val = col2.number_input("Metraje alcanzado (m):", min_value=0.0, format="%.2f")
        if st.form_submit_button("💾 Guardar Datos"):
            hoja.append_row([str(fec), op, round(val, 2)])
            st.success("¡Datos guardados!")
            st.rerun()

# --- OPCIÓN: REPORTES ---
elif opcion == "📊 Historial y Reportes":
    if not df_raw.empty:
        st.subheader("📈 Resumen General")
        c1, c2, c3 = st.columns(3)
        c1.metric("🏗️ Metraje Total", f"{df_raw['metraje'].sum():,.2f} m")
        c2.metric("📈 Promedio General", f"{df_raw['metraje'].mean():,.2f} m")
        c3.metric("📋 Entradas", len(df_raw))

        st.markdown("---")
        st.subheader("👥 Ranking por Promedio Individual (Mayor a Menor)")
        stats_individual = df_raw.groupby('operador')['metraje'].agg(['sum', 'mean', 'count']).reset_index()
        stats_individual.columns = ['Operador', 'Suma Total (m)', 'Promedio Individual (m)', 'Días Registrados']
        
        # ORDENAR DE MAYOR A MENOR PROMEDIO
        stats_individual = stats_individual.sort_values(by='Promedio Individual (m)', ascending=False)
        
        st.table(stats_individual.style.format({
            'Suma Total (m)': '{:,.2f}',
            'Promedio Individual (m)': '{:,.2f}'
        }))

        st.markdown("---")
        st.subheader("📅 Historial por Fecha")
        df_pivot = df_raw.pivot_table(index='fecha', columns='operador', values='metraje', aggfunc='sum').fillna(0).sort_index(ascending=False)
        st.dataframe(df_pivot, use_container_width=True)
        st.bar_chart(df_raw.groupby("operador")["metraje"].sum())
    else:
        st.info("No hay datos registrados aún.")

# --- OPCIÓN: ELIMINAR (CON DOBLE CONFIRMACIÓN) ---
elif opcion == "🗑️ Eliminar Registro":
    st.subheader("Eliminar un Registro")
    if not df_raw.empty:
        # Preparamos los datos para el selector
        df_desc = df_raw.copy()
        df_desc['id_borrar'] = df_desc.index + 2
        df_desc['etiqueta'] = df_desc['fecha'].astype(str) + " | " + df_desc['operador'] + " | " + df_desc['metraje'].astype(str) + "m"
        
        registro_a_borrar = st.selectbox("Seleccione el registro que desea eliminar:", 
                                         options=df_desc['id_borrar'].tolist(),
                                         format_func=lambda x: df_desc[df_desc['id_borrar'] == x]['etiqueta'].values[0])
        
        # Inicializamos el estado de confirmación si no existe
        if 'confirmar_borrado' not in st.session_state:
            st.session_state.confirmar_borrado = False

        if not st.session_state.confirmar_borrado:
            # Primer botón: Solicita eliminar
            if st.button("🗑️ Eliminar registro seleccionado"):
                st.session_state.confirmar_borrado = True
                st.rerun()
        else:
            # Mensaje de advertencia y botones de decisión final
            st.error("⚠️ **ADVERTENCIA:** ¿Realmente desea eliminar este registro de forma DEFINITIVA? Esta acción no se puede deshacer.")
            col_si, col_no = st.columns(2)
            
            if col_si.button("✅ SÍ, eliminar definitivamente", type="primary"):
                try:
                    hoja.delete_rows(int(registro_a_borrar))
                    st.success("Registro eliminado con éxito.")
                    st.session_state.confirmar_borrado = False
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al eliminar: {e}")
            
            if col_no.button("❌ NO, cancelar"):
                st.session_state.confirmar_borrado = False
                st.rerun()
    else:
        st.info("No hay registros para eliminar.")
