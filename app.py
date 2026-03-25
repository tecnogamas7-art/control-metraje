import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from fpdf import FPDF

# --- 1. CONFIGURACIÓN Y ESTILOS ---
st.set_page_config(page_title="Control de Metraje Pro", layout="wide", page_icon="📊")

# Inyectar un poco de CSS para mejorar la estética de las tablas
st.markdown("""
    <style>
    .stTable { width: 100%; }
    .main { background-color: #f8f9fa; }
    </style>
    """, unsafe_allow_html=True)

SPREADSHEET_ID = "1BJG1sm8lRUK8TPcw9dNr5oQMIo3fJ93IhWdue5Hh10E"
OPERADORES = ["Gabriel", "Adrian", "Freddy"] # Centralizado para fácil edición

@st.cache_resource
def conectar_google():
    try:
        # Mejora: Validación de secretos antes de intentar la conexión
        required_secrets = ["project_id", "private_key", "client_email"]
        if not all(k in st.secrets for k in required_secrets):
            st.error("Faltan credenciales en st.secrets")
            st.stop()
            
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
        st.error(f"⚠️ Error Crítico de Conexión: {e}")
        st.stop()

hoja = conectar_google()

@st.cache_data(ttl=600) # Cache de datos por 10 min para no saturar la API
def cargar_datos():
    try:
        registros = hoja.get_all_records()
        if not registros:
            return pd.DataFrame(columns=['fecha', 'operador', 'metraje', 'mes_nombre'])
        
        df = pd.DataFrame(registros)
        # Limpieza robusta
        df['metraje'] = pd.to_numeric(df['metraje'], errors='coerce').fillna(0)
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
        df = df.dropna(subset=['fecha'])
        df['mes_nombre'] = df['fecha'].dt.strftime('%Y-%m')
        # Convertir fecha a date al final para visualización
        df['fecha'] = df['fecha'].dt.date
        return df
    except Exception as e:
        st.warning(f"Error al leer datos: {e}")
        return pd.DataFrame(columns=['fecha', 'operador', 'metraje', 'mes_nombre'])

df_raw = cargar_datos()

# --- 2. FUNCIÓN PARA GENERAR PDF (Mejorada) ---
def generar_pdf(df_pivot, mes_sel):
    pdf = FPDF()
    pdf.add_page()
    # Encabezado
    pdf.set_fill_color(30, 136, 229) # Azul Pro
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 12, f"REPORTE DE METRAJE - {mes_sel}", ln=True, align="C", fill=True)
    
    pdf.set_text_color(0, 0, 0)
    pdf.ln(10)
    
    # Tabla
    cols = ["Fecha"] + df_pivot.columns.tolist()
    w = 190 / len(cols)
    
    # Headers de tabla
    pdf.set_font("Arial", "B", 10)
    pdf.set_fill_color(240, 240, 240)
    for col in cols:
        pdf.cell(w, 8, str(col), 1, 0, "C", fill=True)
    pdf.ln()
    
    # Datos
    pdf.set_font("Arial", "", 9)
    for fecha, row in df_pivot.iterrows():
        pdf.cell(w, 7, str(fecha), 1, 0, "C")
        for val in row:
            pdf.cell(w, 7, f"{val:g}", 1, 0, "R")
        pdf.ln()
    
    # El encoding 'latin-1' es propenso a errores con símbolos, 'replace' ayuda
    return pdf.output(dest="S").encode("latin-1", "replace")

# --- 3. CONTROL DE ACCESO (Refactorizado) ---
def tiene_acceso():
    if st.session_state.get("authenticated"):
        return True
    
    with st.sidebar.expander("🔑 ACCESO ADMINISTRATIVO", expanded=True):
        pwd = st.text_input("Contraseña:", type="password")
        if st.button("Validar Acceso", use_container_width=True):
            if pwd == st.secrets.get("password"):
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Contraseña Incorrecta")
    return False

# --- 4. INTERFAZ ---
st.title("📊 Panel de Control de Metraje")

# Sidebar
if st.session_state.get("authenticated"):
    st.sidebar.success("✅ Autenticado")
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.authenticated = False
        st.rerun()

meses_list = sorted(df_raw['mes_nombre'].unique().tolist(), reverse=True) if not df_raw.empty else [datetime.now().strftime('%Y-%m')]
mes_sel = st.sidebar.selectbox("📅 Seleccionar Mes:", meses_list)
opcion = st.sidebar.segmented_control("Menú Principal:", ["📊 Reporte", "📝 Registrar", "🗑️ Borrar"]) # Nuevo componente UI

# --- VISTA 1: REPORTE ---
if opcion == "📊 Reporte":
    df_mes = df_raw[df_raw['mes_nombre'] == mes_sel].copy() if not df_raw.empty else df_raw
    
    if not df_mes.empty:
        # Métricas rápidas
        c1, c2, c3 = st.columns(3)
        total_m = df_mes['metraje'].sum()
        mejor_op = df_mes.groupby('operador')['metraje'].sum().idxmax()
        c1.metric("Metraje Total", f"{total_m:g} m")
        c2.metric("Mejor Rendimiento", mejor_op)
        c3.metric("Registros", len(df_mes))
        
        # Historial
        df_pivot = df_mes.pivot_table(index='fecha', columns='operador', values='metraje', aggfunc='sum').fillna(0).sort_index(ascending=False)
        
        st.subheader(f"📅 Historial: {mes_sel}")
        st.dataframe(df_pivot.style.format("{:g}").background_gradient(cmap="Blues"), use_container_width=True)

        # Botón PDF con estilo
        pdf_data = generar_pdf(df_pivot, mes_sel)
        st.download_button(f"📥 Descargar PDF {mes_sel}", data=pdf_data, file_name=f"reporte_{mes_sel}.pdf", mime="application/pdf")
        
        st.divider()
        
        # Visualización
        st.subheader("📈 Análisis de Desempeño")
        stats = df_mes.groupby('operador')['metraje'].agg(['sum', 'mean']).reset_index()
        stats.columns = ['Operador', 'Total (m)', 'Promedio (m)']
        
        col_chart1, col_chart2 = st.columns(2)
        with col_chart1:
            st.bar_chart(stats, x="Operador", y="Total (m)", color="Operador")
        with col_chart2:
            st.table(stats.set_index('Operador'))
    else:
        st.info("No hay datos para este mes.")

# --- VISTA 2: REGISTRAR ---
elif opcion == "📝 Registrar":
    if tiene_acceso():
        st.subheader("📝 Nuevo Registro de Metraje")
        with st.form("f_reg", clear_on_submit=True):
            col1, col2 = st.columns(2)
            op = col1.selectbox("Seleccione Operador:", OPERADORES)
            fec = col1.date_input("Fecha de Trabajo:", datetime.now())
            val = col2.number_input("Metraje Total (m):", min_value=0.0, max_value=2000.0, step=0.1) # Max value por seguridad
            
            if st.form_submit_button("💾 Guardar en Google Sheets", use_container_width=True):
                # Validación de duplicados mejorada (por fecha y operador)
                existe = df_raw[(df_raw['fecha'] == fec) & (df_raw['operador'] == op)]
                if not existe.empty:
                    st.warning(f"⚠️ Ya existe un registro para {op} el {fec}. Si deseas corregirlo, elimínalo primero.")
                elif val <= 0:
                    st.error("El metraje debe ser mayor a 0.")
                else:
                    with st.spinner("Subiendo datos..."):
                        hoja.append_row([str(fec), op, float(val)])
                        st.cache_data.clear() # Limpiar cache para ver cambios
                        st.success("✅ ¡Datos guardados correctamente!")
                        st.rerun()
    else:
        st.warning("🔒 Esta sección requiere acceso administrativo.")

# --- VISTA 3: ELIMINAR ---
elif opcion == "🗑️ Borrar":
    if tiene_acceso():
        st.subheader("🗑️ Eliminar Registros")
        if not df_raw.empty:
            df_del = df_raw.copy().sort_values('fecha', ascending=False)
            df_del['id'] = df_del.index + 2
            df_del['label'] = df_del.apply(lambda r: f"{r['fecha']} - {r['operador']} ({r['metraje']:g}m)", axis=1)
            
            seleccion = st.selectbox("Busque el registro a eliminar:", options=df_del['id'].tolist(), format_func=lambda x: df_del.loc[df_del['id']==x, 'label'].values[0])
            
            if st.button("❌ Eliminar Permanentemente", use_container_width=True, type="primary"):
                hoja.delete_rows(int(seleccion))
                st.cache_data.clear()
                st.success("Registro eliminado.")
                st.rerun()
    else:
        st.warning("🔒 Ingrese la contraseña en el panel lateral.")
