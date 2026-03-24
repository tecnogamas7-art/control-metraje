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
        for col in ['fecha', 'operador', 'metraje']:
            if col not in df.columns: df[col] = None
        if not df.empty:
            # Convertimos a numérico y redondeamos a entero
            df['metraje'] = pd.to_numeric(df['metraje'], errors='coerce').fillna(0).round(0).astype(int)
            df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce').dt.date
            df = df.dropna(subset=['fecha'])
            df['mes_nombre'] = pd.to_datetime(df['fecha']).dt.strftime('%Y-%m')
            return df
        return pd.DataFrame(columns=['fecha', 'operador', 'metraje', 'mes_nombre'])
    except:
        return pd.DataFrame(columns=['fecha', 'operador', 'metraje', 'mes_nombre'])

df_raw = cargar_datos()

# --- 2. FUNCIÓN PDF (Valores Enteros) ---
def generar_pdf_pro(df_pivot, df_stats, mes_sel):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 10, f"REPORTE DE METRAJE - {mes_sel}", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", "B", 10); pdf.cell(190, 10, "HISTORIAL DEL MES", ln=True)
    cols = df_pivot.columns.tolist(); w = 190 / (len(cols) + 1)
    pdf.set_font("Arial", "B", 9); pdf.cell(w, 8, "Fecha", 1)
    for col in cols: pdf.cell(w, 8, str(col), 1)
    pdf.ln()
    pdf.set_font("Arial", "", 8)
    for fecha, row in df_pivot.iterrows():
        pdf.cell(w, 7, str(fecha), 1)
        for col in cols: pdf.cell(w, 7, str(int(row[col])), 1) # <--- ENTERO EN PDF
        pdf.ln()
    return pdf.output(dest="S").encode("latin-1", "replace")

# --- 3. CONTROL DE ACCESO ---
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

# --- 4. INTERFAZ ---
st.title("📊 Panel de Control de Metraje")

meses_list = sorted(df_raw['mes_nombre'].unique().tolist(), reverse=True) if not df_raw.empty else [datetime.now().strftime('%Y-%m')]
mes_sel = st.sidebar.selectbox("📅 Seleccionar Mes:", meses_list)
opcion = st.sidebar.radio("Menú Principal:", ["📊 Reporte Mensual", "📝 Registrar Nuevo", "🗑️ Eliminar Registro"])

# --- VISTA 1: REPORTE ---
if opcion == "📊 Reporte Mensual":
    df_mes = df_raw[df_raw['mes_nombre'] == mes_sel] if not df_raw.empty else df_raw
    if not df_mes.empty:
        stats = df_mes.groupby('operador')['metraje'].agg(['sum', 'mean', 'count']).reset_index()
        stats.columns = ['Operador', 'Total (m)', 'Promedio Diario (m)', 'Días']
        
        # Redondear estadísticas para visualización limpia
        stats['Total (m)'] = stats['Total (m)'].astype(int)
        stats['Promedio Diario (m)'] = stats['Promedio Diario (m)'].round(0).astype(int)
        
        df_pivot = df_mes.pivot_table(index='fecha', columns='operador', values='metraje', aggfunc='sum').fillna(0).astype(int).sort_index(ascending=False)
        
        st.download_button(f"📄 Descargar PDF {mes_sel}", data=generar_pdf_pro(df_pivot, stats, mes_sel), file_name=f"reporte_{mes_sel}.pdf")
        
        st.subheader(f"📅 Historial Detallado: {mes_sel}")
        st.dataframe(df_pivot, use_container_width=True) # Sin formato decimal
        
        st.markdown("---")
        st.subheader("🏆 Ranking de Eficiencia")
        st.table(stats) # Tabla limpia sin decimales
        
        col1, col2 = st.columns(2)
        with col1: st.write("**Metraje Total**"); st.bar_chart(data=stats, x="Operador", y="Total (m)", color="#1E88E5")
        with col2: st.write("**Promedio Diario**"); st.bar_chart(data=stats, x="Operador", y="Promedio Diario (m)", color="#FFC107")
    else:
        st.info(f"No hay registros para {mes_sel}.")

# --- VISTA 2: REGISTRAR ---
elif opcion == "📝 Registrar Nuevo":
    if tiene_acceso():
        if st.sidebar.button("🔓 Cerrar Sesión"):
            st.session_state.authenticated = False; st.rerun()
        st.subheader("📝 Nuevo Registro Diario")
        with st.form("f_reg", clear_on_submit=True):
            c1, c2 = st.columns(2)
            op = c1.selectbox("Operador:", ["Gabriel", "Adrian", "Freddy"])
            fec = c1.date_input("Fecha:", datetime.now())
            val = c2.number_input("Metraje:", min_value=0, step=1) # <--- SOLO ENTEROS
            if st.form_submit_button("💾 Guardar"):
                if not df_raw[(df_raw['fecha'] == fec) & (df_raw['operador'] == op)].empty:
                    st.error("❌ Ya existe un registro para esta fecha.")
                else:
                    hoja.append_row([str(fec), op, int(val)])
                    st.success("Guardado correctamente"); st.rerun()
    else: st.warning("🔒 Ingrese contraseña en el menú lateral.")

# --- VISTA 3: ELIMINAR ---
elif opcion == "🗑️ Eliminar Registro":
    if tiene_acceso():
        if st.sidebar.button("🔓 Cerrar Sesión"):
            st.session_state.authenticated = False; st.rerun()
        st.subheader("🗑️ Zona de Eliminación")
        if not df_raw.empty:
            df_del = df_raw.copy()
            df_del['id'] = df_del.index + 2
            df_del['lbl'] = df_del['fecha'].astype(str) + " | " + df_del['operador'] + " | " + df_del['metraje'].astype(str) + "m"
            reg_id = st.selectbox("Seleccione registro:", options=df_del['id'].tolist(), format_func=lambda x: df_del[df_del['id'] == x]['lbl'].values[0])
            
            if "del_confirm" not in st.session_state: st.session_state.del_confirm = False
            if not st.session_state.del_confirm:
                if st.button("🗑️ Eliminar"): st.session_state.del_confirm = True; st.rerun()
            else:
                st.error("⚠️ ¿Confirmar eliminación?")
                c1, c2 = st.columns(2)
                if c1.button("✅ SÍ", type="primary"):
                    hoja.delete_rows(int(reg_id)); st.session_state.del_confirm = False; st.rerun()
                if c2.button("❌ NO"): st.session_state.del_confirm = False; st.rerun()
    else: st.warning("🔒 Ingrese contraseña para eliminar.")
