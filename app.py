import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import os

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Control de Metraje Pro", layout="wide")
st.title("🚀 Sistema de Control de Metraje (Nube)")

# --- ID ÚNICO DE TU HOJA (Extraído de tu URL) ---
# Usamos el ID directo para evitar errores de ruta (404)
SPREADSHEET_ID = "1behqvajjNR4RYULbCGo2-w7IBXeC48fgnxXYiCGoOVU"

# --- CONEXIÓN A GOOGLE SHEETS ---
# La librería buscará PROJECT_ID, PRIVATE_KEY y CLIENT_EMAIL en tus Secrets/Entorno
try:
    # Conexión automática (sin pasar el argumento 'credentials' que causaba error)
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Leer datos (usando el SPREADSHEET_ID para máxima precisión)
    # ttl=0 asegura que siempre leas los datos más recientes de la nube
    df_existente = conn.read(spreadsheet=SPREADSHEET_ID, ttl=0).dropna(how="all")
    st.sidebar.success("✅ Conexión con Google Sheets Exitosa")
    
except Exception as e:
    st.error(f"❌ Error de acceso: {e}")
    st.info("Verifica que este correo sea EDITOR en tu hoja de Google:")
    st.code("mi-servidor@mi-servidor-490914.iam.gserviceaccount.com")
    st.stop()

# --- INTERFAZ DE USUARIO ---
menu = st.sidebar.radio("Menú Principal:", ["📝 Registrar Metraje", "📊 Ver Reportes Generales", "🗑️ Administrar Historial"])

# --- OPCIÓN: REGISTRAR ---
if menu == "📝 Registrar Metraje":
    st.subheader("Nuevo Registro Diario")
    with st.form("form_registro"):
        col1, col2 = st.columns(2)
        with col1:
            operador = st.selectbox("Seleccione Operador", ["Gabriel", "Adrian", "Freddy"])
            fecha = st.date_input("Fecha de trabajo", datetime.now())
        with col2:
            valor = st.number_input("Metraje alcanzado (m)", min_value=0.0, step=0.1, format="%.2f")
        
        enviar = st.form_submit_button("💾 Guardar Registro", use_container_width=True)
    
    if enviar:
        fecha_str = str(fecha)
        
        # Lógica de guardado: añadir nueva fila al final del DataFrame
        nueva_fila = pd.DataFrame([{"fecha": fecha_str, "operador": operador, "metraje": valor}])
        df_actualizado = pd.concat([df_existente, nueva_fila], ignore_index=True)
        
        # Subir el DataFrame actualizado a la hoja de Google
        conn.update(spreadsheet=SPREADSHEET_ID, data=df_actualizado)
        st.success(f"✅ ¡Registro guardado para {operador} ({valor}m)!")
        st.balloons()
        st.rerun()

# --- OPCIÓN: REPORTES ---
elif menu == "📊 Ver Reportes Generales":
    st.subheader("Historial de Datos")
    if not df_existente.empty:
        # Mostrar tabla ordenada por fecha (más reciente arriba)
        st.dataframe(df_existente.sort_values(by="fecha", ascending=False), use_container_width=True)
        
        # Gráfico de producción total por operador
        st.write("### Total Acumulado por Operador")
        st.bar_chart(df_existente.groupby("operador")["metraje"].sum())
    else:
        st.warning("No hay datos registrados en la base de datos.")

# --- OPCIÓN: ADMINISTRAR ---
elif menu == "🗑️ Administrar Historial":
    st.subheader("Gestión de Datos")
    if not df_existente.empty:
        st.write("Selecciona el índice de la fila que deseas borrar:")
        st.dataframe(df_existente.tail(10))
        
        id_borrar = st.number_input("Índice de fila a eliminar", min_value=0, max_value=len(df_existente)-1, step=1)
        
        if st.button("❌ Confirmar Eliminación Permanentemente", type="primary"):
            df_final = df_existente.drop(index=id_borrar)
            conn.update(spreadsheet=SPREADSHEET_ID, data=df_final)
            st.success("Registro eliminado de la base de datos.")
            st.rerun()
