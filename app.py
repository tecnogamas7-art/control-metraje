import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import os
import json

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Control de Metraje Pro", layout="wide")
st.title("🚀 Sistema de Control de Metraje (Nube)")

# --- PREPARACIÓN DE CREDENCIALES ---
# Intentamos obtener desde Variables de Entorno (GitHub/Local) o Streamlit Secrets
project_id = os.getenv("PROJECT_ID") or st.secrets.get("project_id")
private_key = os.getenv("PRIVATE_KEY") or st.secrets.get("private_key")
client_email = os.getenv("CLIENT_EMAIL") or st.secrets.get("client_email")

# Limpieza crítica de la llave privada
if private_key:
    private_key = private_key.replace('\\n', '\n').strip()

# --- CONEXIÓN A GOOGLE SHEETS ---
@st.cache_data(ttl=0)  # Evita que se quede pegado el Response 200 anterior
def conectar_y_leer():
    try:
        # Definimos la URL de tu hoja directamente
        url_hoja = "https://docs.google.com"
        
        if project_id and private_key and client_email:
            # Creamos un diccionario con el formato exacto que espera Google
            creds_dict = {
                "type": "service_account",
                "project_id": project_id,
                "private_key": private_key,
                "client_email": client_email,
                "token_uri": "https://oauth2.googleapis.com",
                "auth_uri": "https://accounts.google.com",
                "auth_provider_x509_cert_url": "https://www.googleapis.com",
                "client_x509_cert_url": f"https://www.googleapis.com{client_email.replace('@', '%40')}"
            }
            
            # Conexión usando el diccionario de credenciales
            conn = st.connection("gsheets", type=GSheetsConnection, credentials=creds_dict)
        else:
            # Fallback a secrets.toml estándar si no hay variables de entorno
            conn = st.connection("gsheets", type=GSheetsConnection)
        
        # Leemos los datos (usamos spreadsheet= para asegurar que use tu URL)
        df = conn.read(spreadsheet=url_hoja, ttl=0).dropna(how="all")
        return conn, df
    except Exception as e:
        st.error(f"❌ Error real de conexión: {str(e)}")
        st.stop()

# Ejecutar conexión
conn, df_existente = conectar_y_leer()

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
            # Crear nueva fila
            nueva_fila = pd.DataFrame([{"fecha": fecha_str, "operador": operador, "metraje": round(valor, 2)}])
            # Concatenar y actualizar (GSheetsConnection requiere el DF completo)
            df_actualizado = pd.concat([df_existente, nueva_fila], ignore_index=True)
            conn.update(spreadsheet="https://docs.google.com", data=df_actualizado)
            st.success("✅ ¡Registro guardado permanentemente!")
            st.balloons()
            st.cache_data.clear() # Limpia caché para leer datos frescos
            st.rerun()

# --- OPCIÓN 2: REPORTES ---
elif menu == "📊 Ver Reportes Generales":
    st.subheader("📅 Reporte Mensual Detallado")
    if not df_existente.empty:
        # Asegurar formato de fecha
        df_existente['fecha'] = df_existente['fecha'].astype(str)
        mes_actual = datetime.now().strftime("%Y-%m")
        mes_sel = st.text_input("Filtrar por Mes (YYYY-MM):", mes_actual)
        
        df_filtrado = df_existente[df_existente['fecha'].str.contains(mes_sel)].copy()
        
        if not df_filtrado.empty:
            # Pivotear para ver operadores en columnas
            tabla_pivot = df_filtrado.pivot_table(index='fecha', columns='operador', values='metraje', aggfunc='sum')
            # Asegurar que todas las columnas existan
            for op in ["Gabriel", "Adrian", "Freddy"]:
                if op not in tabla_pivot.columns: tabla_pivot[op] = 0.0
            
            st.dataframe(tabla_pivot.style.format("{:.2f}"), use_container_width=True)
            st.bar_chart(df_filtrado.groupby("operador")["metraje"].sum())
        else:
            st.warning(f"No hay datos para el mes {mes_sel}.")
    else:
        st.info("No hay datos históricos registrados aún.")

# --- OPCIÓN 3: BORRAR ---
elif menu == "🗑️ Administrar Historial":
    st.subheader("Gestión de Datos")
    if not df_existente.empty:
        df_ver = df_existente.copy()
        st.write("Últimos 10 registros:")
        st.dataframe(df_ver.tail(10), use_container_width=True)
        
        id_borrar = st.number_input("ID de fila a eliminar (Índice)", min_value=0, max_value=len(df_existente)-1, step=1)
        if st.button("❌ Eliminar Registro", type="primary"):
            df_final = df_existente.drop(index=id_borrar)
            conn.update(spreadsheet="https://docs.google.com", data=df_final)
            st.success("Registro eliminado de la base de datos.")
            st.cache_data.clear()
            st.rerun()
