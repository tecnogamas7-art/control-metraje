import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Control de Metraje Pro", layout="wide", page_icon="📊")

# ID de tu nueva hoja (la que termina en H10E)
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
        return client.open_by_key(SPREADSHEET_ID).sheet1
    except Exception as e:
        st.error(f"❌ Error de Conexión: {e}")
        st.stop()

# --- 2. CONEXIÓN Y CARGA DE DATOS ---
hoja = conectar_google()

try:
    records = hoja.get_all_records()
    df = pd.DataFrame(records)
    # Convertir metraje a número por si acaso hay errores de formato
    if not df.empty:
        df['metraje'] = pd.to_numeric(df['metraje'], errors='coerce').fillna(0)
except:
    df = pd.DataFrame(columns=['fecha', 'operador', 'metraje'])

# --- 3. INTERFAZ Y ALGORITMO DE CÁLCULO ---
st.title("🚀 Sistema de Control de Metraje")

# --- BLOQUE DE ESTADÍSTICAS (TU ALGORITMO) ---
if not df.empty:
    st.markdown("### 📈 Resumen General")
    c1, c2, c3 = st.columns(3)
    
    metraje_total = df['metraje'].sum()
    promedio_diario = df['metraje'].mean()
    total_registros = len(df)

    c1.metric("Metraje General", f"{metraje_total:,.2f} m")
    c2.metric("Promedio por Registro", f"{promedio_diario:,.2f} m")
    c3.metric("Total Registros", total_registros)
    
    st.markdown("---")

# --- MENÚ LATERAL ---
menu = st.sidebar.radio("Menú", ["Registrar Datos", "Ver Reportes y Gráficas"])

if menu == "Registrar Datos":
    st.subheader("📝 Nuevo Registro")
    with st.form("form_reg", clear_on_submit=True):
        col1, col2 = st.columns(2)
        op = col1.selectbox("Operador", ["Gabriel", "Adrian", "Freddy"])
        fec = col1.date_input("Fecha", datetime.now())
        met = col2.number_input("Metraje (m)", min_value=0.0, step=0.1)
        
        if st.form_submit_button("Guardar en la Nube"):
            try:
                hoja.append_row([str(fec), op, round(met, 2)])
                st.success("✅ Registro guardado")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

elif menu == "Ver Reportes y Gráficas":
    if not df.empty:
        st.subheader("📊 Análisis de Producción")
        
        # Gráfica de barras por Operador
        st.write("#### Metraje Total por Operador")
        chart_data = df.groupby("operador")["metraje"].sum().reset_index()
        st.bar_chart(data=chart_data, x="operador", y="metraje", color="#FF4B4B")

        # Historial Detallado
        st.write("#### Historial Reciente")
        st.dataframe(df.sort_values(by="fecha", ascending=False), use_container_width=True)
        
        # Opción para descargar
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Descargar Reporte CSV", csv, "reporte_metraje.csv", "text/csv")
    else:
        st.info("No hay datos suficientes para mostrar gráficas.")
