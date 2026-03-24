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
        st.error(f"Error de Conexión: {e}")
        st.stop()

# --- 2. CARGA DE DATOS ---
hoja = conectar_google()

def cargar_datos():
    try:
        registros = hoja.get_all_records()
        df = pd.DataFrame(registros)
        for col in ['fecha', 'operador', 'metraje']:
            if col not in df.columns: df[col] = None
        if not df.empty:
            df['metraje'] = pd.to_numeric(df['metraje'], errors='coerce').fillna(0)
            df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce').dt.date
            df = df.dropna(subset=['fecha'])
            df['mes_nombre'] = pd.to_datetime(df['fecha']).dt.strftime('%Y-%m')
            return df
        return pd.DataFrame(columns=['fecha', 'operador', 'metraje', 'mes_nombre'])
    except:
        return pd.DataFrame(columns=['fecha', 'operador', 'metraje', 'mes_nombre'])

df_raw = cargar_datos()

# --- 3. FUNCIÓN PDF ---
def generar_pdf_pro(df_pivot, df_stats, mes_sel):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 10, f"REPORTE DE METRAJE - {mes_sel}", ln=True, align="C")
    pdf.ln(10)
    # Tabla Historial
    pdf.set_font("Arial", "B", 10); pdf.cell(190, 10, "HISTORIAL", ln=True)
    cols = df_pivot.columns.tolist(); w = 190 / (len(cols) + 1)
    pdf.set_font("Arial", "B", 9); pdf.cell(w, 8, "Fecha", 1)
    for col in cols: pdf.cell(w, 8, str(col), 1)
    pdf.ln()
    pdf.set_font("Arial", "", 8)
    for fecha, row in df_pivot.iterrows():
        pdf.cell(w, 7, str(fecha), 1)
        for col in cols: pdf.cell(w, 7, f"{row[col]:,.2f}", 1)
        pdf.ln()
    return pdf.output(dest="S").encode("latin-1", "replace")

# --- 4. FUNCIÓN DE CONTROL DE ACCESO (PASSWORD) ---
def tiene_acceso():
    """Verifica si el usuario ha ingresado la contraseña correcta."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    if st.session_state.authenticated:
        return True

    with st.sidebar.expander("🔑 ACCESO ADMINISTRATIVO"):
        pwd = st.text_input("Ingrese Contraseña:", type="password")
        if st.button("Validar Acceso"):
            if pwd == st.secrets["password"]:
                st.session_state.authenticated = True
                st.success("Acceso concedido")
                st.rerun()
            else:
                st.error("Contraseña incorrecta")
    return False

# --- 5. INTERFAZ ---
st.title("📊 Panel de Control de Metraje")

# Filtro de Mes
meses_list = sorted(df_raw['mes_nombre'].unique().tolist(), reverse=True) if not df_raw.empty else [datetime.now().strftime('%Y-%m')]
mes_sel = st.sidebar.selectbox("📅 Seleccionar Mes:", meses_list)

opcion = st.sidebar.radio("Menú Principal:", ["📊 Reporte Mensual", "📝 Registrar Producción", "🗑️ Eliminar Registro"])

# --- OPCIÓN 1: REPORTE (PÚBLICO) ---
if opcion == "📊 Reporte Mensual":
    df_mes = df_raw[df_raw['mes_nombre'] == mes_sel] if not df_raw.empty else df_raw
    if not df_mes.empty:
        stats = df_mes.groupby('operador')['metraje'].agg(['sum', 'mean', 'count']).reset_index()
        stats.columns = ['Operador', 'Suma Total (m)', 'Promedio Individual (m)', 'Días Registrados']
        stats = stats.sort_values(by='Promedio Individual (m)', ascending=False)
        df_pivot = df_mes.pivot_table(index='fecha', columns='operador', values='metraje', aggfunc='sum').fillna(0).sort_index(ascending=False)
        
        st.download_button(f"📄 Descargar PDF {mes_sel}", data=generar_pdf_pro(df_pivot, stats, mes_sel), file_name=f"reporte_{mes_sel}.pdf")
        st.subheader("📅 Historial del Mes")
        st.dataframe(df_pivot, use_container_width=True)
        st.subheader("🏆 Ranking de Eficiencia")
        st.table(stats.style.format({'Suma Total (m)': '{:,.2f}', 'Promedio Individual (m)': '{:,.2f}'}))
        st.bar_chart(data=stats, x="Operador", y="Promedio Individual (m)", color="#FFC107")
    else:
        st.info(f"No hay datos para {mes_sel}.")

# --- OPCIÓN 2: REGISTRAR (PROTEGIDO) ---
elif opcion == "📝 Registrar Producción":
    if tiene_acceso():
        st.subheader("📝 Nuevo Registro")
        if st.sidebar.button("🔓 Cerrar Sesión"):
            st.session_state.authenticated = False
            st.rerun()

        with st.form("f_reg", clear_on_submit=True):
            c1, c2 = st.columns(2)
            op = c1.selectbox("Operador:", ["Gabriel", "Adrian", "Freddy"])
            fec = c1.date_input("Fecha:", datetime.now())
            val = c2.number_input("Metraje:", min_value=0.0)
            if st.form_submit_button("💾 Guardar"):
                if not df_raw[(df_raw['fecha'] == fec) & (df_raw['operador'] == op)].empty:
                    st.error("❌ Registro duplicado para este día.")
                else:
                    hoja.append_row([str(fec), op, round(val, 2)])
                    st.success("Guardado")
                    st.rerun()
    else:
        st.warning("🔒 Esta sección está bloqueada. Ingrese la contraseña en el menú lateral.")

# --- OPCIÓN 3: ELIMINAR (PROTEGIDO) ---
elif opcion == "🗑️ Eliminar Registro":
    if tiene_acceso():
        st.subheader("🗑️ Zona de Eliminación")
        if st.sidebar.button("🔓 Cerrar Sesión"):
            st.session_state.authenticated = False
            st.rerun()

        if not df_raw.empty:
            df_desc = df_raw.copy()
            df_desc['id'] = df_desc.index + 2
            df_desc['lbl'] = df_desc['fecha'].astype(str) + " | " + df_desc['operador'] + " | " + df_desc['metraje'].astype(str) + "m"
            reg_id = st.selectbox("Seleccione registro:", options=df_desc['id'].tolist(), format_func=lambda x: df_desc[df_desc['id'] == x]['lbl'].values[0])
            
            # Lógica de confirmación
            if "confirmar_borrar" not in st.session_state: st.session_state.confirmar_borrar = False
            
            if not st.session_state.confirmar_borrar:
                if st.button("🗑️ Eliminar registro"):
                    st.session_state.confirmar_borrar = True
                    st.rerun()
            else:
                st.error("⚠️ ¿Estás seguro de que quieres eliminarlo definitivamente?")
                c1, c2 = st.columns(2)
                if c1.button("✅ SÍ, borrar", type="primary"):
                    hoja.delete_rows(int(reg_id))
                    st.session_state.confirmar_borrar = False
                    st.success("Eliminado")
                    st.rerun()
                if c2.button("❌ NO, cancelar"):
                    st.session_state.confirmar_borrar = False
                    st.rerun()
    else:
        # AQUÍ ESTÁ EL BLOQUEO: Si no hay login, no se muestra nada de arriba
        st.warning("🔒 Acceso Denegado. Se requiere contraseña de administrador para eliminar registros.")
