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
        if len(data) < 2: 
            return pd.DataFrame(columns=['fecha', 'operador', 'metraje', 'mes_nombre', 'fecha_dt'])
        
        df = pd.DataFrame(data[1:], columns=data[0])
        
        # Limpieza de metraje (soporta comas y puntos)
        df['metraje'] = df['metraje'].astype(str).str.replace(',', '.').str.strip()
        df['metraje'] = pd.to_numeric(df['metraje'], errors='coerce').fillna(0.0)
        
        # Procesamiento de fechas
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
        df = df.dropna(subset=['fecha'])
        
        # Identificadores temporales
        df['mes_nombre'] = df['fecha'].dt.strftime('%Y-%m')
        df['fecha_dt'] = df['fecha'].dt.date
        return df
    except: 
        return pd.DataFrame(columns=['fecha', 'operador', 'metraje', 'mes_nombre', 'fecha_dt'])

# --- 2. LÓGICA DE SEMÁFORO (ADAPTATIVA) ---
def aplicar_semaforo(val):
    try:
        num = float(val)
        if num >= 150:
            return 'background-color: #2ecc71; color: white; font-weight: bold;'
        elif 100 <= num < 150:
            return 'background-color: #f1c40f; color: black; font-weight: bold;'
        elif 0 < num < 100:
            return 'background-color: #e74c3c; color: white; font-weight: bold;'
        return 'color: #888888;'
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
    except: return None

# --- 4. INTERFAZ PRINCIPAL ---
df_raw = cargar_datos()
st.title("📊 Panel de Control de Metraje")

# Autenticación
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

# Menú de Navegación
meses_list = sorted(df_raw['mes_nombre'].unique().tolist(), reverse=True) if not df_raw.empty else [datetime.now().strftime('%Y-%m')]
mes_sel = st.sidebar.selectbox("📅 Seleccionar Mes:", meses_list)
opcion = st.sidebar.radio("Ir a:", ["📊 Reporte Mensual", "📝 Registrar Nuevo", "🗑️ Eliminar"])

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
        
        try:
            df_pivot = df_mes.pivot_table(
                index='fecha_dt', 
                columns='operador', 
                values='metraje', 
                aggfunc='sum'
            ).fillna(0.0)

            if not df_pivot.empty:
                df_visual = df_pivot.sort_index(ascending=False).apply(pd.to_numeric)
                
                # SOPORTE PARA PANDAS NUEVO (.map) Y VIEJO (.applymap)
                try:
                    styled_df = df_visual.style.map(aplicar_semaforo).format("{:g}")
                except AttributeError:
                    styled_df = df_visual.style.applymap(aplicar_semaforo).format("{:g}")
                
                st.dataframe(styled_df, use_container_width=True, height=400)

                # Exportación
                pdf_data = generar_pdf(df_pivot, mes_sel)
                if pdf_data:
                    st.download_button(f"📄 Descargar Reporte PDF", pdf_data, f"reporte_{mes_sel}.pdf", use_container_width=True)
            else:
                st.info("No hay datos cruzados para mostrar en el historial de este mes.")
        except Exception as e:
            st.warning(f"Mostrando tabla básica: {e}")
            st.table(df_mes[['fecha_dt', 'operador', 'metraje']])

        st.divider()
        
        # Desempeño Individual
        st.subheader("📈 Desempeño por Operador")
        stats = df_mes.groupby('operador')['metraje'].agg(['sum', 'mean', 'count']).reset_index()
        stats.columns = ['Operador', 'Total Metraje (m)', 'Promedio Diario (m)', 'Registros']
        st.table(stats.style.format({'Total Metraje (m)': '{:g}', 'Promedio Diario (m)': '{:.2f}'}))
        st.bar_chart(stats, x="Operador", y="Total Metraje (m)", color="Operador")
    else:
        st.info(f"No hay registros registrados para {mes_sel}.")

# --- VISTA 2: REGISTRAR ---
elif opcion == "📝 Registrar Nuevo":
    st.subheader("📝 Registrar Producción Diaria")
    with st.form("form_registro", clear_on_submit=True):
        col1, col2 = st.columns(2)
        op_f = col1.selectbox("Seleccione Operador:", OPERADORES)
        fec_f = col1.date_input("Fecha de Trabajo:", datetime.now())
        val_f = col2.number_input("Metraje Alcanzado:", min_value=0.0, step=0.01, format="%.2f")
        
        if st.form_submit_button("💾 Guardar en Base de Datos", use_container_width=True):
            existe = df_raw[(df_raw['fecha_dt'] == fec_f) & (df_raw['operador'] == op_f)]
            if not existe.empty:
                st.error(f"Ya existe un registro para {op_f} en la fecha {fec_f}")
            else:
                v_str = str(round(float(val_f), 2))
                hoja.append_row([str(fec_f), op_f, v_str])
                st.cache_data.clear()
                st.success(f"✅ Registrado con éxito para {op_f}")
                st.rerun()

# --- VISTA 3: ELIMINAR ---
elif opcion == "🗑️ Eliminar":
    if st.session_state.authenticated:
        st.subheader("🗑️ Eliminar Registro")
        if not df_raw.empty:
            df_del = df_raw.copy().sort_values('fecha', ascending=False)
            # El ID es el índice + 2 (por la fila de encabezado en GS)
            df_del['fila_gs'] = range(2, len(df_del) + 2) 
            df_del['desc'] = df_del.apply(lambda r: f"{r['fecha_dt']} | {r['operador']} | {r['metraje']:g}m", axis=1)
            
            seleccion = st.selectbox("Registro a borrar:", options=df_del['desc'].tolist())
            fila_a_borrar = df_del[df_del['desc'] == seleccion]['fila_gs'].values[0]
            
            if st.checkbox("Confirmar eliminación permanente"):
                if st.button("🔥 ELIMINAR REGISTRO", type="primary", use_container_width=True):
                    hoja.delete_rows(int(fila_a_borrar))
                    st.cache_data.clear()
                    st.success("Registro eliminado correctamente.")
                    st.rerun()
        else:
            st.info("No hay datos para eliminar.")
    else:
        st.warning("🔒 Ingrese su contraseña en el menú lateral.")
