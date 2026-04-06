import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from fpdf import FPDF

# --- 1. CONFIGURACIÓN Y ESTILOS ---
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

@st.cache_data(ttl=15)
def cargar_datos():
    try:
        data = hoja.get_all_values()
        if len(data) < 2: return pd.DataFrame(columns=['fecha', 'operador', 'metraje', 'mes_nombre'])
        df = pd.DataFrame(data[1:], columns=data[0])
        # Limpieza de datos
        df['metraje'] = df['metraje'].astype(str).str.replace(',', '.').str.strip()
        df['metraje'] = pd.to_numeric(df['metraje'], errors='coerce').fillna(0.0)
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
        df = df.dropna(subset=['fecha'])
        df['mes_nombre'] = df['fecha'].dt.strftime('%Y-%m')
        # Mantenemos 'fecha' como objeto date para el pivot
        df['fecha_dt'] = df['fecha'].dt.date
        return df
    except: 
        return pd.DataFrame(columns=['fecha', 'operador', 'metraje', 'mes_nombre', 'fecha_dt'])

# --- 2. LÓGICA DE SEMÁFORO (CORREGIDA) ---
def aplicar_semaforo(val):
    try:
        num = float(val)
        if num >= 150:
            color, texto = '#2ecc71', 'white'
        elif 100 <= num < 150:
            color, texto = '#f1c40f', 'black'
        elif 0 < num < 100:
            color, texto = '#e74c3c', 'white'
        else:
            color, texto = 'transparent', '#888888'
        return f'background-color: {color}; color: {texto}; font-weight: bold; border: 1px solid #f0f2f6;'
    except:
        return ''

# --- 3. GENERAR PDF ---
def generar_pdf(df_pivot, mes_sel):
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(190, 10, f"REPORTE DE METRAJE - {mes_sel}", ln=True, align="C")
        pdf.ln(10)
        cols = ["Fecha"] + df_pivot.columns.tolist()
        w = 190 / len(cols)
        pdf.set_font("Arial", "B", 10)
        for col in cols: pdf.cell(w, 8, str(col), 1, 0, "C")
        pdf.ln()
        pdf.set_font("Arial", "", 9)
        for fecha, row in df_pivot.iterrows():
            pdf.cell(w, 7, str(fecha), 1)
            for val in row: pdf.cell(w, 7, f"{float(val):g}", 1, 0, "R")
            pdf.ln()
        return pdf.output(dest="S").encode("latin-1", "replace")
    except Exception as e:
        return None

# --- 4. INTERFAZ PRINCIPAL ---
df_raw = cargar_datos()
st.title("📊 Panel de Control de Metraje")

# Sistema de Acceso
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if not st.session_state.authenticated:
    with st.sidebar.expander("🔑 ACCESO ADMINISTRATIVO", expanded=True):
        pwd = st.text_input("Contraseña:", type="password")
        if st.button("Validar Acceso", use_container_width=True):
            if pwd == st.secrets["password"]: 
                st.session_state.authenticated = True
                st.rerun()
            else: st.error("Incorrecta")
else:
    if st.sidebar.button("🔓 Cerrar Sesión"): 
        st.session_state.authenticated = False
        st.rerun()

# Menú Lateral
meses_disponibles = sorted(df_raw['mes_nombre'].unique().tolist(), reverse=True) if not df_raw.empty else [datetime.now().strftime('%Y-%m')]
mes_sel = st.sidebar.selectbox("📅 Seleccionar Mes:", meses_disponibles)
opcion = st.sidebar.radio("Navegación:", ["📊 Reporte Mensual", "📝 Registrar Nuevo", "🗑️ Eliminar"])

# --- VISTA 1: REPORTE ---
if opcion == "📊 Reporte Mensual":
    df_mes = df_raw[df_raw['mes_nombre'] == mes_sel].copy()
    
    if not df_mes.empty:
        st.subheader(f"Resumen General - {mes_sel}")
        c1, c2, c3 = st.columns(3)
        c1.metric("Metraje Total", f"{df_mes['metraje'].sum():g} m")
        c2.metric("Promedio Diario", f"{df_mes['metraje'].mean():.2f} m")
        c3.metric("Días con Registro", len(df_mes['fecha_dt'].unique()))

        st.divider()

        st.subheader("📅 Historial Detallado (Semáforo de Producción)")
        
        # Creación robusta del pivot
        df_pivot = df_mes.pivot_table(index='fecha_dt', columns='operador', values='metraje', aggfunc='sum').fillna(0.0)
        
        if not df_pivot.empty:
            # APLICACIÓN DE ESTILO CON VALIDACIÓN
            st.dataframe(
                df_pivot.sort_index(ascending=False).style.applymap(aplicar_semaforo).format("{:g}"), 
                use_container_width=True,
                height=400
            )

            # Botón PDF
            pdf_bytes = generar_pdf(df_pivot, mes_sel)
            if pdf_bytes:
                st.download_button(f"📄 Descargar Reporte PDF", pdf_bytes, f"reporte_{mes_sel}.pdf", use_container_width=True)
        
        st.divider()
        
        # Desempeño Individual
        st.subheader("📈 Desempeño por Operador")
        stats = df_mes.groupby('operador')['metraje'].agg(['sum', 'mean', 'count']).reset_index()
        stats.columns = ['Operador', 'Total Metraje (m)', 'Promedio Diario (m)', 'Registros']
        st.table(stats.style.format({'Total Metraje (m)': '{:g}', 'Promedio Diario (m)': '{:.2f}'}))
        st.bar_chart(stats, x="Operador", y="Total Metraje (m)", color="Operador")
    else:
        st.info(f"No hay registros todavía para {mes_sel}.")

# --- VISTA 2: REGISTRAR ---
elif opcion == "📝 Registrar Nuevo":
    st.subheader("📝 Registrar Producción Diaria")
    with st.form("form_registro", clear_on_submit=True):
        col1, col2 = st.columns(2)
        op_f = col1.selectbox("Seleccione Operador:", OPERADORES)
        fec_f = col1.date_input("Fecha de Trabajo:", datetime.now())
        val_f = col2.number_input("Metraje Alcanzado:", min_value=0.0, step=0.01, format="%.2f")
        
        if st.form_submit_button("💾 Guardar en Base de Datos", use_container_width=True):
            # Verificación de duplicados usando fecha_dt
            existe = df_raw[(df_raw['fecha_dt'] == fec_f) & (df_raw['operador'] == op_f)]
            if not existe.empty:
                st.error(f"Ya existe un registro para {op_f} en la fecha {fec_f}")
            else:
                v_str = str(round(float(val_f), 2))
                hoja.append_row([str(fec_f), op_f, v_str])
                st.cache_data.clear()
                st.success(f"✅ Registro exitoso: {v_str} metros para {op_f}")
                st.rerun()

# --- VISTA 3: ELIMINAR ---
elif opcion == "🗑️ Eliminar":
    if st.session_state.authenticated:
        st.subheader("🗑️ Eliminar Registro Existente")
        if not df_raw.empty:
            df_del = df_raw.copy().sort_values('fecha', ascending=False)
            df_del['id'] = range(2, len(df_del) + 2) # Ajuste dinámico de fila de Google Sheets
            df_del['desc'] = df_del.apply(lambda r: f"{r['fecha_dt']} | {r['operador']} | {float(r['metraje']):g}m", axis=1)
            
            sel_desc = st.selectbox("Seleccione el registro a borrar:", options=df_del['desc'].tolist())
            fila_id = df_del[df_del['desc'] == sel_desc]['id'].values[0]
            
            if st.checkbox("Confirmar que deseo borrar este dato permanentemente"):
                if st.button("🔥 ELIMINAR REGISTRO", type="primary", use_container_width=True):
                    hoja.delete_rows(int(fila_id))
                    st.cache_data.clear()
                    st.success("Registro eliminado correctamente.")
                    st.rerun()
        else: st.info("No hay datos para eliminar.")
    else: st.warning("🔒 Ingrese contraseña en el menú lateral para habilitar esta opción.")
