import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from fpdf import FPDF

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Control de Metraje Pro", layout="wide", page_icon="📊")
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
        creds = Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
        return gspread.authorize(creds).open_by_key(SPREADSHEET_ID).get_worksheet(0)
    except Exception as e:
        st.error(f"Error de Conexión: {e}"); st.stop()

hoja = conectar_google()

def cargar_datos():
    try:
        registros = hoja.get_all_records()
        df = pd.DataFrame(registros)
        if not df.empty:
            df['metraje'] = pd.to_numeric(df['metraje'], errors='coerce').fillna(0).astype(float)
            df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce').dt.date
            df = df.dropna(subset=['fecha'])
            df['mes_nombre'] = pd.to_datetime(df['fecha']).dt.strftime('%Y-%m')
            return df
        return pd.DataFrame(columns=['fecha', 'operador', 'metraje', 'mes_nombre'])
    except:
        return pd.DataFrame(columns=['fecha', 'operador', 'metraje', 'mes_nombre'])

df_raw = cargar_datos()

# --- 2. CONTROL DE ACCESO ---
def tiene_acceso():
    if "authenticated" not in st.session_state: st.session_state.authenticated = False
    if st.session_state.authenticated: return True
    with st.sidebar.expander("🔑 ACCESO ADMINISTRATIVO"):
        pwd = st.text_input("Contraseña:", type="password")
        if st.button("Validar Acceso"):
            if pwd == st.secrets["password"]:
                st.session_state.authenticated = True; st.rerun()
            else: st.error("Incorrecta")
    return False

# --- 3. INTERFAZ ---
st.title("📊 Panel de Control de Metraje")
meses_list = sorted(df_raw['mes_nombre'].unique().tolist(), reverse=True) if not df_raw.empty else [datetime.now().strftime('%Y-%m')]
mes_sel = st.sidebar.selectbox("📅 Seleccionar Mes:", meses_list)
opcion = st.sidebar.radio("Menú Principal:", ["📊 Reporte Mensual", "📝 Registrar Nuevo", "🗑️ Eliminar"])

# --- VISTA 1: REPORTE MENSUAL (SOLO LECTURA) ---
if opcion == "📊 Reporte Mensual":
    df_mes = df_raw[df_raw['mes_nombre'] == mes_sel].copy() if not df_raw.empty else df_raw
    
    if not df_mes.empty:
        # --- TABLA DE HISTORIAL ---
        df_pivot = df_mes.pivot_table(index='fecha', columns='operador', values='metraje', aggfunc='sum').fillna(0).sort_index(ascending=False)
        st.subheader(f"📅 Historial Detallado: {mes_sel}")
        # Formato inteligente {:g} oculta .00 pero muestra decimales si existen
        st.dataframe(df_pivot.style.format("{:g}"), use_container_width=True)

        # --- TABLA DE RANKING ---
        st.markdown("---")
        st.subheader("🏆 Ranking Mensual")
        stats = df_mes.groupby('operador')['metraje'].agg(['sum', 'mean']).reset_index()
        stats.columns = ['Operador', 'Total (m)', 'Promedio (m)']
        
        # Formato inteligente para Ranking
        st.table(stats.style.format({
            'Total (m)': '{:g}', 
            'Promedio (m)': lambda x: f"{x:g}" if x % 1 == 0 else f"{x:.2f}"
        }))
        
        # Gráficas
        col1, col2 = st.columns(2)
        with col1: st.write("**Metraje Total**"); st.bar_chart(data=stats, x="Operador", y="Total (m)", color="#1E88E5")
        with col2: st.write("**Promedio Diario**"); st.bar_chart(data=stats, x="Operador", y="Promedio (m)", color="#FFC107")
    else:
        st.info("Sin datos para este mes.")

# --- VISTA 2: REGISTRAR ---
elif opcion == "📝 Registrar Nuevo":
    if tiene_acceso():
        st.subheader("📝 Nuevo Registro")
        with st.form("f_reg", clear_on_submit=True):
            c1, c2 = st.columns(2)
            op = c1.selectbox("Operador:", ["Gabriel", "Adrian", "Freddy"])
            fec = c1.date_input("Fecha:", datetime.now())
            # Permite decimales en el ingreso, pero el visor los ocultará si es .0
            val = c2.number_input("Metraje:", min_value=0.0, step=0.1, format="%g")
            if st.form_submit_button("💾 Guardar"):
                hoja.append_row([str(fec), op, float(val)])
                st.success("Guardado correctamente"); st.rerun()
    else: st.warning("🔒 Ingrese contraseña en el lateral para registrar.")

# --- VISTA 3: ELIMINAR ---
elif opcion == "🗑️ Eliminar":
    if tiene_acceso():
        st.subheader("🗑️ Eliminar Registro")
        df_del = df_raw.copy()
        df_del['id'] = df_del.index + 2
        # Etiqueta de eliminación también con formato inteligente
        df_del['lbl'] = df_del['fecha'].astype(str) + " | " + df_del['operador'] + " | " + df_del['metraje'].map(lambda x: f"{x:g}")
        reg_id = st.selectbox("Seleccione registro:", options=df_del['id'].tolist(), format_func=lambda x: df_del[df_del['id'] == x]['lbl'].values[0])
        if st.button("🗑️ Confirmar Borrado"):
            hoja.delete_rows(int(reg_id)); st.success("Eliminado"); st.rerun()
    else: st.warning("🔒 Ingrese contraseña en el lateral para eliminar.")
