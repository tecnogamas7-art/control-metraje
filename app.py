import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from fpdf import FPDF

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Control de Metraje Pro", layout="wide", page_icon="📊")

OPERADORES = ["Gabriel", "Adrian", "Freddy"]
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
        creds = Credentials.from_service_account_info(info, scopes=[
            "https://www.googleapis.com/auth/spreadsheets", 
            "https://www.googleapis.com/auth/drive"
        ])
        return gspread.authorize(creds).open_by_key(SPREADSHEET_ID).get_worksheet(0)
    except Exception as e:
        st.error(f"⚠️ Error de Conexión: {e}"); st.stop()

hoja = conectar_google()

@st.cache_data(ttl=60) # Reducido a 1 min para ver cambios rápido
def cargar_datos():
    try:
        registros = hoja.get_all_records()
        if not registros:
            return pd.DataFrame(columns=['fecha', 'operador', 'metraje', 'mes_nombre'])
        
        df = pd.DataFrame(registros)
        # CRÍTICO: Asegurar que metraje sea float6orze para no perder decimales
        df['metraje'] = pd.to_numeric(df['metraje'], errors='coerce').fillna(0).astype(float)
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
        df = df.dropna(subset=['fecha'])
        df['mes_nombre'] = df['fecha'].dt.strftime('%Y-%m')
        df['fecha'] = df['fecha'].dt.date
        return df
    except:
        return pd.DataFrame(columns=['fecha', 'operador', 'metraje', 'mes_nombre'])

df_raw = cargar_datos()

# --- 2. FUNCIÓN GENERAR PDF ---
def generar_pdf(df_pivot, mes_sel):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 10, f"REPORTE - {mes_sel}", ln=True, align="C")
    pdf.ln(10)
    cols = ["Fecha"] + df_pivot.columns.tolist()
    w = 190 / len(cols)
    pdf.set_font("Arial", "B", 10)
    for col in cols: pdf.cell(w, 8, str(col), 1)
    pdf.ln()
    pdf.set_font("Arial", "", 9)
    for fecha, row in df_pivot.iterrows():
        pdf.cell(w, 7, str(fecha), 1)
        for val in row:
            # Formato :g con round asegura mostrar decimales si existen
            pdf.cell(w, 7, f"{round(float(val), 2):g}", 1)
        pdf.ln()
    return pdf.output(dest="S").encode("latin-1", "replace")

# --- 3. CONTROL DE ACCESO ---
def tiene_acceso():
    if st.session_state.get("authenticated"): return True
    with st.sidebar.expander("🔑 ACCESO"):
        pwd = st.text_input("Contraseña:", type="password")
        if st.button("Validar"):
            if pwd == st.secrets["password"]:
                st.session_state.authenticated = True; st.rerun()
    return False

# --- 4. INTERFAZ ---
st.title("📊 Control de Metraje")

meses_list = sorted(df_raw['mes_nombre'].unique().tolist(), reverse=True) if not df_raw.empty else [datetime.now().strftime('%Y-%m')]
mes_sel = st.sidebar.selectbox("📅 Mes:", meses_list)
opcion = st.sidebar.radio("Menú:", ["📊 Reporte", "📝 Registrar", "🗑️ Eliminar"])

if opcion == "📊 Reporte":
    df_mes = df_raw[df_raw['mes_nombre'] == mes_sel].copy() if not df_raw.empty else df_raw
    if not df_mes.empty:
        # PIVOT TABLE: Aseguramos que no trunque decimales
        df_pivot = df_mes.pivot_table(
            index='fecha', 
            columns='operador', 
            values='metraje', 
            aggfunc='sum'
        ).fillna(0)
        
        st.subheader(f"📅 Historial: {mes_sel}")
        
        # FORMATEO DE TABLA: 
        # lambda x: f"{x:g}" muestra decimales solo si son necesarios (ej: 10.5)
        # Para forzar siempre 2 si quieres ver .50, usa f"{x:.2f}"
        st.dataframe(
            df_pivot.sort_index(ascending=False).style.format(lambda x: f"{round(float(x), 2):g}"), 
            use_container_width=True
        )

        pdf_data = generar_pdf(df_pivot, mes_sel)
        st.download_button(f"📄 PDF {mes_sel}", pdf_data, f"reporte_{mes_sel}.pdf")
    else:
        st.info("Sin datos.")

elif opcion == "📝 Registrar":
    if tiene_acceso():
        with st.form("f"):
            c1, c2 = st.columns(2)
            op = c1.selectbox("Operador", OPERADORES)
            fec = c1.date_input("Fecha", datetime.now())
            val = c2.number_input("Metraje (admite decimales)", min_value=0.0, step=0.01, format="%g")
            if st.form_submit_button("Guardar"):
                # Guardamos como float explícito
                hoja.append_row([str(fec), op, float(round(val, 2))])
                st.cache_data.clear()
                st.success("Guardado"); st.rerun()

elif opcion == "🗑️ Eliminar":
    if tiene_acceso():
        if not df_raw.empty:
            df_del = df_raw.copy()
            df_del['id'] = df_del.index + 2
            df_del['lbl'] = df_del.apply(lambda r: f"{r['fecha']} | {r['operador']} | {r['metraje']:g}", axis=1)
            reg = st.selectbox("Registro:", options=df_del['id'].tolist(), format_func=lambda x: df_del[df_del['id']==x]['lbl'].values[0])
            if st.button("Eliminar"):
                hoja.delete_rows(int(reg)); st.cache_data.clear(); st.rerun()
