import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import os

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Control de Metraje Pro", layout="wide", page_icon="🚀")
st.title("🚀 Sistema de Control de Metraje (Nube)")

# ID de tu hoja de Google
SPREADSHEET_ID = "1behqvajjNR4RYULbCGo2-w7IBXeC48fgnxXYiCGoOVU"

# --- FUNCIÓN DE CONEXIÓN (La que ya funciona) ---
def obtener_conexion():
    p_id = os.getenv("PROJECT_ID")
    p_key = os.getenv("PRIVATE_KEY")
    c_email = os.getenv("CLIENT_EMAIL")

    if p_id and p_key and c_email:
        p_key = p_key.replace('\\n', '\n').strip()
        if "-----BEGIN PRIVATE KEY-----" not in p_key:
            p_key = f"-----BEGIN PRIVATE KEY-----\n{p_key}\n-----END PRIVATE KEY-----"
        
        creds = {
            "project_id": p_id,
            "private_key": p_key,
            "client_email": c_email,
            "token_uri": "https://oauth2.googleapis.com",
            "type": "service_account"
        }
        return st.connection("gsheets", type=GSheetsConnection, **creds)
    
    return st.connection("gsheets", type=GSheetsConnection)

# --- INICIO DE PROCESO ---
try:
    conn = obtener_conexion()
    df_existente = conn.read(spreadsheet=SPREADSHEET_ID, ttl=0).dropna(how="all")
    st.sidebar.success("✅ Conexión Exitosa")
except Exception as e:
    st.error(f"❌ Error de acceso: {e}")
    st.stop()

# --- MENÚ LATERAL ---
menu = st.sidebar.radio("Ir a:", ["📝 Registrar Metraje", "📊 Ver Reportes Generales", "🗑️ Administrar Historial"])

# --- 📝 OPCIÓN 1: REGISTRAR (Con lógica de duplicados) ---
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
        # Lógica de duplicados: No permitir mismo operador en misma fecha
        es_duplicado = not df_existente.empty and (
            (df_existente['fecha'].astype(str) == fecha_str) & 
            (df_existente['operador'] == operador)
        ).any()
        
        if es_duplicado:
            st.error(f"❌ Ya existe un registro para **{operador}** en la fecha **{fecha_str}**.")
        else:
            nueva_fila = pd.DataFrame([{"fecha": fecha_str, "operador": operador, "metraje": round(valor, 2)}])
            df_actualizado = pd.concat([df_existente, nueva_fila], ignore_index=True)
            conn.update(spreadsheet=SPREADSHEET_ID, data=df_actualizado)
            st.success(f"✅ ¡Registro guardado: {operador} ({valor}m)!")
            st.balloons()
            st.rerun()

# --- 📊 OPCIÓN 2: REPORTES (Con lógica de filtrado por mes y pivot) ---
elif menu == "📊 Ver Reportes Generales":
    st.subheader("📅 Reporte Mensual Detallado")
    if not df_existente.empty:
        df_existente['fecha'] = df_existente['fecha'].astype(str)
        mes_actual = datetime.now().strftime("%Y-%m")
        mes_sel = st.text_input("Filtrar por Mes (Formato YYYY-MM):", mes_actual)
        
        df_filtrado = df_existente[df_existente['fecha'].str.contains(mes_sel)].copy()
        
        if not df_filtrado.empty:
            # Tabla pivote para ver los 3 operadores lado a lado
            tabla_pivot = df_filtrado.pivot_table(index='fecha', columns='operador', values='metraje', aggfunc='sum')
            # Asegurar que las columnas existan aunque no tengan datos
            for op in ["Gabriel", "Adrian", "Freddy"]:
                if op not in tabla_pivot.columns: tabla_pivot[op] = 0.0
            
            st.write(f"### Detalle del mes: {mes_sel}")
            st.dataframe(tabla_pivot.style.format("{:.2f}"), use_container_width=True)
            
            st.write("### Producción Acumulada")
            st.bar_chart(df_filtrado.groupby("operador")["metraje"].sum())
        else:
            st.warning(f"No hay datos registrados para el mes {mes_sel}.")
    else:
        st.info("La base de datos está vacía.")

# --- 🗑️ OPCIÓN 3: ADMINISTRAR (Con lógica de eliminación por ID) ---
elif menu == "🗑️ Administrar Historial":
    st.subheader("Gestión de Datos")
    if not df_existente.empty:
        df_ver = df_existente.copy()
        st.write("Últimos 10 registros ingresados:")
        st.dataframe(df_ver.tail(10), use_container_width=True)
        
        id_borrar = st.number_input("Seleccione el Índice (ID) de la fila a eliminar", 
                                    min_value=0, max_value=len(df_existente)-1, step=1)
        
        if st.button("❌ Eliminar Registro Permanentemente", type="primary"):
            df_final = df_existente.drop(index=id_borrar)
            conn.update(spreadsheet=SPREADSHEET_ID, data=df_final)
            st.success("Registro eliminado correctamente de la nube.")
            st.rerun()
    else:
        st.info("Nada que administrar por ahora.")
