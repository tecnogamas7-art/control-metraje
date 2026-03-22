import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import os

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Control de Metraje Pro", layout="wide")
st.title("🚀 Sistema de Control de Metraje (Nube)")

# --- PUENTE DE CONEXIÓN (GITHUB ACTIONS -> STREAMLIT SECRETS) ---
# Este bloque permite que la librería GSheetsConnection encuentre los secretos en GitHub
if "PROJECT_ID" in os.environ:
    if "connections" not in st.secrets:
        st.secrets["connections"] = {"gsheets": {
            "project_id": os.getenv("PROJECT_ID"),
            "private_key": os.getenv("PRIVATE_KEY").replace('\\n', '\n'),
            "client_email": os.getenv("CLIENT_EMAIL"),
            "private_key_id": os.getenv("PRIVATE_KEY_ID"),
            "client_id": os.getenv("CLIENT_ID"),
            "type": "service_account",
            "token_uri": "https://oauth2.googleapis.com",
            "auth_uri": "https://accounts.google.com",
        }}

# --- CONEXIÓN A GOOGLE SHEETS ---
try:
    # La librería buscará en st.secrets["connections"]["gsheets"]
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_existente = conn.read(ttl=0).dropna(how="all")
except Exception as e:
    st.error(f"❌ Error de conexión: {e}")
    st.info("Asegúrate de que los Secrets en GitHub coincidan con los nombres en el archivo YAML.")
    st.stop()

# --- INTERFAZ STREAMLIT ---
menu = st.sidebar.radio("Ir a:", ["📝 Registrar Metraje", "📊 Ver Reportes Generales", "🗑️ Administrar Historial"])

# --- OPCIÓN 1: REGISTRAR ---
if menu == "📝 Registrar Metraje":
    st.subheader("Nuevo Registro Diario")
    with st.form("form_registro"):
        col1, col2 = st.columns(2)
        with col1:
            operador = st.selectbox("Seleccione Operador", ["Gabriel", "Adrian", "Freddy"])
            fecha = st.date_input("Fecha de trabajo", datetime.now())
        with col2:
            valor = st.number_input("Metraje alcanzado (m)", min_value=0.0, step=0.01, format="%.2f")
        
        enviar = st.form_submit_button("💾 Guardar Registro", use_container_width=True)
    
    if enviar:
        fecha_str = str(fecha)
        # Verificar duplicados
        es_duplicado = not df_existente.empty and (
            (df_existente['fecha'].astype(str) == fecha_str) & 
            (df_existente['operador'] == operador)
        ).any()
        
        if es_duplicado:
            st.error(f"❌ Ya existe un registro para {operador} en la fecha {fecha_str}.")
        else:
            nueva_fila = pd.DataFrame([{"fecha": fecha_str, "operador": operador, "metraje": round(valor, 2)}])
            df_actualizado = pd.concat([df_existente, nueva_fila], ignore_index=True)
            conn.update(data=df_actualizado)
            st.success("✅ ¡Registro guardado en Google Sheets!")
            st.balloons()
            st.rerun()

# --- OPCIÓN 2: REPORTES ---
elif menu == "📊 Ver Reportes Generales":
    st.subheader("📅 Reporte Mensual Detallado")
    if not df_existente.empty:
        mes_actual = datetime.now().strftime("%Y-%m")
        mes_sel = st.text_input("Filtrar por Mes (YYYY-MM):", mes_actual)
        
        # Asegurar que la columna fecha sea string para el filtro
        df_existente['fecha'] = df_existente['fecha'].astype(str)
        df_filtrado = df_existente[df_existente['fecha'].str.contains(mes_sel)].copy()
        
        if not df_filtrado.empty:
            tabla_pivot = df_filtrado.pivot(index='fecha', columns='operador', values='metraje')
            # Asegurar que todas las columnas de operadores existan
            for col in ["Gabriel", "Adrian", "Freddy"]:
                if col not in tabla_pivot.columns: tabla_pivot[col] = None
            
            st.dataframe(tabla_pivot.style.format("{:.2f}", na_rep="-"), use_container_width=True)
            st.bar_chart(df_filtrado.groupby("operador")["metraje"].sum())
        else:
            st.warning("No hay datos para este mes.")
    else:
        st.info("La hoja de cálculo está vacía.")

# --- OPCIÓN 3: BORRAR ---
elif menu == "🗑️ Administrar Historial":
    st.subheader("Gestión de Datos")
    if not df_existente.empty:
        df_ver = df_existente.copy()
        df_ver['ID'] = df_ver.index
        st.table(df_ver.tail(10))
        
        id_borrar = st.number_input("ID a eliminar", min_value=0, max_value=len(df_existente)-1, step=1)
        if st.button("❌ Eliminar Registro", type="primary"):
            df_final = df_existente.drop(index=id_borrar)
            conn.update(data=df_final)
            st.success("Registro eliminado.")
            st.rerun()
