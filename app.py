import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from fpdf import FPDF

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Control de Metraje Pro", layout="wide", page_icon="📊")

# ID de tu hoja de Google Sheets
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
        client = gspread.authorize(creds)
        return client.open_by_key(SPREADSHEET_ID).get_worksheet(0)
    except Exception as e:
        st.error(f"❌ Error de Conexión: {e}")
        st.stop()

# --- 2. CARGA DE DATOS (CON PROTECCIÓN DE COLUMNAS) ---
hoja = conectar_google()

def cargar_datos():
    try:
        registros = hoja.get_all_records()
        df = pd.DataFrame(registros)
        
        # Validar si las columnas existen, si no, crearlas vacías
        for col in ['fecha', 'operador', 'metraje']:
            if col not in df.columns:
                df[col] = None

        if not df.empty:
            # Limpieza y formato
            df['metraje'] = pd.to_numeric(df['metraje'], errors='coerce').fillna(0)
            df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce').dt.date
            df = df.dropna(subset=['fecha']) # Quitar filas sin fecha válida
            df['mes_nombre'] = pd.to_datetime(df['fecha']).dt.strftime('%Y-%m')
            return df
        else:
            return pd.DataFrame(columns=['fecha', 'operador', 'metraje', 'mes_nombre'])
    except Exception as e:
        st.warning("La hoja parece estar vacía o mal configurada. Asegúrate de tener los encabezados: fecha, operador, metraje.")
        return pd.DataFrame(columns=['fecha', 'operador', 'metraje', 'mes_nombre'])

df_raw = cargar_datos()

# --- 3. FUNCIÓN GENERAR PDF ---
def generar_pdf_pro(df_pivot, df_stats, mes_sel):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 10, f"REPORTE DE METRAJE - PERIODO {mes_sel}", ln=True, align="C")
    pdf.set_font("Arial", "", 10)
    pdf.cell(190, 10, f"Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align="C")
    pdf.ln(10)
    
    # Tabla Historial
    pdf.set_font("Arial", "B", 11); pdf.cell(190, 10, "HISTORIAL DETALLADO", ln=True)
    cols = df_pivot.columns.tolist()
    w = 190 / (len(cols) + 1)
    pdf.set_font("Arial", "B", 9); pdf.cell(w, 8, "Fecha", 1)
    for col in cols: pdf.cell(w, 8, str(col), 1)
    pdf.ln()
    pdf.set_font("Arial", "", 8)
    for fecha, row in df_pivot.iterrows():
        pdf.cell(w, 7, str(fecha), 1)
        for col in cols: pdf.cell(w, 7, f"{row[col]:,.2f}", 1)
        pdf.ln()
    
    pdf.ln(10)
    # Tabla Ranking
    pdf.set_font("Arial", "B", 11); pdf.cell(190, 10, "RANKING DE EFICIENCIA", ln=True)
    pdf.set_font("Arial", "B", 9)
    pdf.cell(50, 8, "Operador", 1); pdf.cell(45, 8, "Total (m)", 1); pdf.cell(50, 8, "Promedio (m)", 1); pdf.cell(45, 8, "Dias", 1); pdf.ln()
    pdf.set_font("Arial", "", 9)
    for _, row in df_stats.iterrows():
        pdf.cell(50, 7, str(row['Operador']), 1)
        pdf.cell(45, 7, f"{row['Suma Total (m)']:,.2f}", 1)
        pdf.cell(50, 7, f"{row['Promedio Individual (m)']:,.2f}", 1)
        pdf.cell(45, 7, str(row['Días Registrados']), 1); pdf.ln()
        
    return pdf.output(dest="S").encode("latin-1", "replace")

# --- 4. SISTEMA DE SEGURIDAD ---
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if st.session_state.authenticated:
        return True
    with st.sidebar.expander("🔑 Acceso Administrativo"):
        pwd = st.text_input("Contraseña", type="password")
        if st.button("Ingresar"):
            if pwd == st.secrets["password"]:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Contraseña incorrecta")
    return False

# --- 5. INTERFAZ Y NAVEGACIÓN ---
st.title("📊 Panel de Control de Metraje")

# Selector de Mes en la barra lateral
meses_list = sorted(df_raw['mes_nombre'].unique().tolist(), reverse=True) if not df_raw.empty else [datetime.now().strftime('%Y-%m')]
mes_sel = st.sidebar.selectbox("📅 Seleccionar Mes:", meses_list)

opcion = st.sidebar.radio("Menú Principal:", ["📊 Reporte Mensual", "📝 Registrar Producción", "🗑️ Eliminar Registro"])

# Filtrar datos por el mes seleccionado
df_mes = df_raw[df_raw['mes_nombre'] == mes_sel] if not df_raw.empty else df_raw

# --- VISTA 1: REPORTE ---
if opcion == "📊 Reporte Mensual":
    st.header(f"Reporte de Metraje: {mes_sel}")
    if not df_mes.empty:
        # Cálculos
        stats = df_mes.groupby('operador')['metraje'].agg(['sum', 'mean', 'count']).reset_index()
        stats.columns = ['Operador', 'Suma Total (m)', 'Promedio Individual (m)', 'Días Registrados']
        stats = stats.sort_values(by='Promedio Individual (m)', ascending=False)
        df_pivot = df_mes.pivot_table(index='fecha', columns='operador', values='metraje', aggfunc='sum').fillna(0).sort_index(ascending=False)
        
        # Botón PDF
        pdf_bytes = generar_pdf_pro(df_pivot, stats, mes_sel)
        st.download_button(f"📄 Descargar PDF {mes_sel}", data=pdf_bytes, file_name=f"reporte_{mes_sel}.pdf")
        
        st.markdown("---")
        st.subheader("📅 Historial Horizontal")
        st.dataframe(df_pivot, use_container_width=True)
        
        st.markdown("---")
        st.subheader("🏆 Ranking de Eficiencia (Promedio)")
        st.table(stats.style.format({'Suma Total (m)': '{:,.2f}', 'Promedio Individual (m)': '{:,.2f}'}))
        
        st.markdown("---")
        col_g1, col_g2 = st.columns(2)
        with col_g1: st.write("**Metraje Total**"); st.bar_chart(data=stats, x="Operador", y="Suma Total (m)", color="#1E88E5")
        with col_g2: st.write("**Promedio de Eficiencia**"); st.bar_chart(data=stats, x="Operador", y="Promedio Individual (m)", color="#FFC107")
    else:
        st.info(f"No hay registros para {mes_sel}.")

# --- VISTA 2: REGISTRO ---
elif opcion == "📝 Registrar Producción":
    if check_password():
        st.subheader("📝 Nuevo Registro Diario")
        if st.sidebar.button("Cerrar Sesión"):
            st.session_state.authenticated = False
            st.rerun()

        with st.form("form_registro", clear_on_submit=True):
            c1, c2 = st.columns(2)
            op = c1.selectbox("Operador:", ["Gabriel", "Adrian", "Freddy"])
            fec = c1.date_input("Fecha:", datetime.now())
            val = c2.number_input("Metraje (m):", min_value=0.0, format="%.2f")
            
            if st.form_submit_button("💾 Guardar Datos"):
                # Validar duplicados
                ya_existe = not df_raw[(df_raw['fecha'] == fec) & (df_raw['operador'] == op)].empty
                if ya_existe:
                    st.error(f"❌ {op} ya tiene un registro para el día {fec}.")
                elif val <= 0:
                    st.warning("El metraje debe ser mayor a 0.")
                else:
                    hoja.append_row([str(fec), op, round(val, 2)])
                    st.success("✅ ¡Datos guardados!")
                    st.rerun()
    else:
        st.warning("🔒 Ingrese la contraseña en el menú lateral para registrar.")

# --- VISTA 3: ELIMINAR ---
elif opcion == "🗑️ Eliminar Registro":
    if check_password():
        st.subheader("🗑️ Eliminar Registro Existente")
        if not df_raw.empty:
            df_desc = df_raw.copy()
            df_desc['id_real'] = df_desc.index + 2
            df_desc['etiqueta'] = df_desc['fecha'].astype(str) + " | " + df_desc['operador'] + " | " + df_desc['metraje'].astype(str) + "m"
            
            reg_a_borrar = st.selectbox("Seleccione registro:", options=df_desc['id_real'].tolist(), 
                                        format_func=lambda x: df_desc[df_desc['id_real'] == x]['etiqueta'].values[0])
            
            if "confirm_delete" not in st.session_state: st.session_state.confirm_delete = False
            
            if not st.session_state.confirm_delete:
                if st.button("🗑️ Eliminar seleccionado"):
                    st.session_state.confirm_delete = True
                    st.rerun()
            else:
                st.error("⚠️ ¿Estás seguro de eliminar esto permanentemente?")
                col1, col2 = st.columns(2)
                if col1.button("✅ SÍ, borrar", type="primary"):
                    hoja.delete_rows(int(reg_a_borrar))
                    st.session_state.confirm_delete = False
                    st.success("Eliminado.")
                    st.rerun()
                if col2.button("❌ NO, cancelar"):
                    st.session_state.confirm_delete = False
                    st.rerun()
    else:
        st.warning("🔒 Ingrese la contraseña en el menú lateral para eliminar.")
