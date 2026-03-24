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
            df['metraje'] = pd.to_numeric(df['metraje'], errors='coerce').fillna(0.0)
            df['fecha'] = pd.to_datetime(df['fecha']).dt.date
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
opcion = st.sidebar.radio("Menú Principal:", ["📊 Reporte Mensual", "📝 Registrar Producción", "🗑️ Eliminar Registro"])

# --- VISTA 1: REPORTE MENSUAL (CON TABLA EDITABLE) ---
if opcion == "📊 Reporte Mensual":
    # Filtramos por mes
    df_mes = df_raw[df_raw['mes_nombre'] == mes_sel].copy() if not df_raw.empty else df_raw
    
    if not df_mes.empty:
        # Pivot para la vista horizontal
        df_pivot = df_mes.pivot_table(index='fecha', columns='operador', values='metraje', aggfunc='sum').fillna(0.0).sort_index(ascending=False)
        
        st.subheader(f"📅 Historial Detallado: {mes_sel}")
        
        # SI TIENE ACCESO -> MODO EDITOR
        if tiene_acceso():
            st.info("💡 Puedes editar los números directamente en la tabla. No olvides presionar 'Guardar Cambios'.")
            
            # Editor de datos
            df_editado = st.data_editor(
                df_pivot, 
                use_container_width=True, 
                column_config={col: st.column_config.NumberColumn(format="%.2f") for col in df_pivot.columns}
            )
            
            # Botón para procesar cambios
            if st.button("💾 Guardar Cambios en la Nube"):
                with st.spinner("Actualizando Google Sheets..."):
                    # Comparamos la tabla editada con la original para encontrar qué cambió
                    for fecha, row in df_editado.iterrows():
                        for operador in df_editado.columns:
                            nuevo_val = row[operador]
                            original_val = df_pivot.loc[fecha, operador]
                            
                            if nuevo_val != original_val:
                                # Buscar la fila exacta en la hoja original (df_raw)
                                idx_busqueda = df_raw[(df_raw['fecha'] == fecha) & (df_raw['operador'] == operador)].index
                                if not idx_busqueda.empty:
                                    fila_google = idx_busqueda[0] + 2 # +2 por encabezado e índice 0
                                    hoja.update_cell(fila_google, 3, float(nuevo_val))
                    
                    st.success("✅ ¡Base de datos actualizada!")
                    st.cache_resource.clear() # Limpiar cache para forzar recarga
                    st.rerun()
        
        # SI NO TIENE ACCESO -> VISTA NORMAL (LECTURA)
        else:
            st.dataframe(df_pivot.style.format("{:.2f}"), use_container_width=True)
            st.warning("🔒 Para editar valores, ingresa la contraseña en el menú lateral.")

        # --- RANKING Y GRÁFICAS (Restauradas) ---
        st.markdown("---")
        stats = df_mes.groupby('operador')['metraje'].agg(['sum', 'mean', 'count']).reset_index()
        stats.columns = ['Operador', 'Suma Total (m)', 'Promedio Individual (m)', 'Días Registrados']
        stats = stats.sort_values(by='Promedio Individual (m)', ascending=False)
        
        st.subheader("🏆 Ranking de Eficiencia")
        st.table(stats.style.format({'Suma Total (m)': '{:.2f}', 'Promedio Individual (m)': '{:.2f}'}))
        
        col1, col2 = st.columns(2)
        with col1: st.write("**Metraje Total**"); st.bar_chart(data=stats, x="Operador", y="Suma Total (m)", color="#1E88E5")
        with col2: st.write("**Promedio Diario**"); st.bar_chart(data=stats, x="Operador", y="Promedio Individual (m)", color="#FFC107")
    else:
        st.info("Sin datos.")

# --- VISTA 2: REGISTRAR ---
elif opcion == "📝 Registrar Producción":
    if tiene_acceso():
        st.subheader("📝 Nuevo Registro Diario")
        with st.form("f_reg", clear_on_submit=True):
            c1, c2 = st.columns(2)
            op = c1.selectbox("Operador:", ["Gabriel", "Adrian", "Freddy"])
            fec = c1.date_input("Fecha:", datetime.now())
            val = c2.number_input("Metraje:", min_value=0.0, step=0.01, format="%.2f")
            if st.form_submit_button("💾 Guardar"):
                if not df_raw[(df_raw['fecha'] == fec) & (df_raw['operador'] == op)].empty:
                    st.error("❌ Registro duplicado.")
                else:
                    hoja.append_row([str(fec), op, round(val, 2)])
                    st.success("Guardado"); st.rerun()
    else: st.warning("🔒 Ingrese contraseña para registrar.")

# --- VISTA 3: ELIMINAR ---
elif opcion == "🗑️ Eliminar Registro":
    if tiene_acceso():
        st.subheader("🗑️ Eliminar Registro")
        if not df_raw.empty:
            df_del = df_raw.copy()
            df_del['id'] = df_del.index + 2
            df_del['lbl'] = df_del['fecha'].astype(str) + " | " + df_del['operador'] + " | " + df_del['metraje'].map("{:.2f}".format)
            reg_id = st.selectbox("Seleccione:", options=df_del['id'].tolist(), format_func=lambda x: df_del[df_del['id'] == x]['lbl'].values[0])
            if st.button("🗑️ Borrar"):
                hoja.delete_rows(int(reg_id)); st.success("Eliminado"); st.rerun()
