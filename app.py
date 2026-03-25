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

@st.cache_data(ttl=10) # TTL bajo para ver cambios en tiempo real
def cargar_datos():
    try:
        registros = hoja.get_all_records()
        if not registros:
            return pd.DataFrame(columns=['fecha', 'operador', 'metraje', 'mes_nombre'])
        
        df = pd.DataFrame(registros)
        
        # --- LIMPIEZA AGRESIVA DE DECIMALES ---
        # 1. Convertimos a string y quitamos espacios
        df['metraje'] = df['metraje'].astype(str).str.strip()
        # 2. Reemplazamos coma por punto (Crucial para Sheets en español)
        df['metraje'] = df['metraje'].str.replace(',', '.')
        # 3. Convertimos a numérico, lo que no sea número será 0
        df['metraje'] = pd.to_numeric(df['metraje'], errors='coerce').fillna(0).astype(float)
        
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
        df = df.dropna(subset=['fecha'])
        df['mes_nombre'] = df['fecha'].dt.strftime('%Y-%m')
        df['fecha'] = df['fecha'].dt.date
        return df
    except Exception as e:
        st.error(f"Error al procesar datos: {e}")
        return pd.DataFrame(columns=['fecha', 'operador', 'metraje', 'mes_nombre'])

df_raw = cargar_datos()

# --- 2. FUNCIÓN GENERAR PDF ---
def generar_pdf(df_pivot, mes_sel):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_fill_color(30, 136, 229); pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 12, f"REPORTE DE METRAJE - {mes_sel}", ln=True, align="C", fill=True)
    pdf.set_text_color(0, 0, 0); pdf.ln(10)
    
    cols = ["Fecha"] + df_pivot.columns.tolist()
    w = 190 / len(cols)
    pdf.set_font("Arial", "B", 10); pdf.set_fill_color(240, 240, 240)
    for col in cols: pdf.cell(w, 8, str(col), 1, 0, "C", fill=True)
    pdf.ln()
    
    pdf.set_font("Arial", "", 9)
    for fecha, row in df_pivot.iterrows():
        pdf.cell(w, 7, str(fecha), 1, 0, "C")
        for val in row:
            # Formato :g para PDF
            pdf.cell(w, 7, f"{float(val):g}", 1, 0, "R")
        pdf.ln()
    return pdf.output(dest="S").encode("latin-1", "replace")

# --- 3. CONTROL DE ACCESO ---
def tiene_acceso():
    if st.session_state.get("authenticated"): return True
    with st.sidebar.expander("🔑 ACCESO ADMINISTRATIVO", expanded=True):
        pwd = st.text_input("Contraseña:", type="password")
        if st.button("Validar Acceso", use_container_width=True):
            if pwd == st.secrets["password"]:
                st.session_state.authenticated = True; st.rerun()
            else: st.error("Incorrecta")
    return False

# --- 4. INTERFAZ ---
st.title("📊 Panel de Control de Metraje")

if st.session_state.get("authenticated"):
    if st.sidebar.button("🔓 Cerrar Sesión"):
        st.session_state.authenticated = False; st.rerun()

meses_list = sorted(df_raw['mes_nombre'].unique().tolist(), reverse=True) if not df_raw.empty else [datetime.now().strftime('%Y-%m')]
mes_sel = st.sidebar.selectbox("📅 Seleccionar Mes:", meses_list)
opcion = st.sidebar.radio("Menú Principal:", ["📊 Reporte Mensual", "📝 Registrar Nuevo", "🗑️ Eliminar"])

if opcion == "📊 Reporte Mensual":
    df_mes = df_raw[df_raw['mes_nombre'] == mes_sel].copy() if not df_raw.empty else df_raw
    if not df_mes.empty:
        # MÉTRICAS
        c1, c2 = st.columns(2)
        total_m = df_mes['metraje'].sum()
        c1.metric("Metraje Total", f"{total_m:g} m")
        c2.metric("Promedio Diario", f"{df_mes['metraje'].mean():.2f} m")

        # TABLA HISTORIAL (PIVOT)
        df_pivot = df_mes.pivot_table(index='fecha', columns='operador', values='metraje', aggfunc='sum').fillna(0).astype(float)
        
        st.subheader(f"📅 Historial Detallado: {mes_sel}")
        
        # FORZAR VISUALIZACIÓN DE DECIMALES EN LA TABLA
        # Usamos format("{:g}") para que oculte .00 pero muestre .5
        st.dataframe(
            df_pivot.sort_index(ascending=False).style.format("{:g}").background_gradient(cmap="Blues"), 
            use_container_width=True
        )

        pdf_data = generar_pdf(df_pivot, mes_sel)
        st.download_button(f"📄 Descargar PDF", pdf_data, f"reporte_{mes_sel}.pdf")
        
        st.divider()
        st.subheader("📈 Gráficos de Desempeño")
        stats = df_mes.groupby('operador')['metraje'].sum().reset_index()
        st.bar_chart(stats, x="operador", y="metraje", color="operador")
    else:
        st.info("Sin datos.")

elif opcion == "📝 Registrar Nuevo":
    if tiene_acceso():
        st.subheader("📝 Nuevo Registro")
        with st.form("f_reg", clear_on_submit=True):
            c1, c2 = st.columns(2)
            op = c1.selectbox("Operador:", OPERADORES)
            fec = c1.date_input("Fecha:", datetime.now())
            # step=0.01 y format="%f" asegura que el widget maneje decimales correctamente
            val = c2.number_input("Metraje:", min_value=0.0, step=0.01, format="%f")
            
            if st.form_submit_button("💾 Guardar Registro", use_container_width=True):
                existe = df_raw[(df_raw['fecha'] == fec) & (df_raw['operador'] == op)]
                if not existe.empty:
                    st.error(f"❌ Ya existe un registro para {op} el {fec}.")
                else:
                    hoja.append_row([str(fec), op, float(val)])
                    st.cache_data.clear()
                    st.success(f"✅ Guardado: {val:g} m"); st.rerun()

elif opcion == "🗑️ Eliminar":
    if tiene_acceso():
        st.subheader("🗑️ Eliminar Registro")
        if not df_raw.empty:
            df_del = df_raw.copy().sort_values('fecha', ascending=False)
            df_del['id'] = df_del.index + 2
            df_del['lbl'] = df_del.apply(lambda r: f"{r['fecha']} | {r['operador']} | {r['metraje']:g}m", axis=1)
            reg_id = st.selectbox("Seleccione:", options=df_del['id'].tolist(), format_func=lambda x: df_del[df_del['id']==x]['lbl'].values[0])
            
            st.warning(f"⚠️ ¿Borrar `{df_del[df_del['id']==reg_id]['lbl'].values[0]}`?")
            if st.checkbox("Confirmo que deseo eliminar este registro definitivamente."):
                if st.button("🔥 Eliminar Ahora", type="primary", use_container_width=True):
                    hoja.delete_rows(int(reg_id)); st.cache_data.clear(); st.success("Eliminado"); st.rerun()
        else: st.info("No hay datos.")
