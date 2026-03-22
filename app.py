import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import os

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Control de Metraje Pro", layout="wide")
st.title("🚀 Sistema de Control de Metraje (Nube)")

# URL exacta de tu hoja de cálculo (ID: 1behqvajjNR4RYULbCGo2-w7IBXeC48fgnxXYiCGoOVU)
url_hoja = "https://docs.google.com"

# --- CONEXIÓN A GOOGLE SHEETS ---
# IMPORTANTE: Eliminamos el argumento 'credentials' manual para evitar el error de la librería.
# Ahora la conexión busca automáticamente en st.secrets o variables de entorno (PROJECT_ID, etc.)
try:
    # Conexión simplificada (La librería autodetecta las credenciales)
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Leer datos actuales (ttl=0 para datos frescos sin caché)
    df_existente = conn.read(spreadsheet=url_hoja, ttl=0).dropna(how="all")
    st.sidebar.success("✅ Conexión con Google Sheets Establecida")
    
except Exception as e:
    st.error(f"❌ Error de acceso a la hoja: {e}")
    st.info("Asegúrate de que 'mi-servidor@mi-servidor-490914.iam.gserviceaccount.com' sea EDITOR en tu Excel.")
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
        
        # Lógica de guardado: añadir nueva fila al final
        nueva_fila = pd.DataFrame([{"fecha": fecha_str, "operador": operador, "metraje": valor}])
        df_actualizado = pd.concat([df_existente, nueva_fila], ignore_index=True)
        
        # Subir actualización a la nube
        conn.update(spreadsheet=url_hoja, data=df_actualizado)
        st.success(f"✅ ¡Registro guardado para {operador} ({valor}m)!")
        st.balloons()
        st.rerun()

# --- OPCIÓN: REPORTES ---
elif menu == "📊 Ver Reportes Generales":
    st.subheader("Historial de Metrajes Registrados")
    if not df_existente.empty:
        st.dataframe(df_existente.sort_values(by="fecha", ascending=False), use_container_width=True)
        
        # Gráfico de producción acumulada
        st.write("### Total por Operador")
        st.bar_chart(df_existente.groupby("operador")["metraje"].sum())
    else:
        st.info("Aún no hay datos registrados en la base de datos.")

# --- OPCIÓN: ADMINISTRAR ---
elif menu == "🗑️ Administrar Historial":
    st.subheader("Zona de Administración")
    if not df_existente.empty:
        st.write("Selecciona el registro que deseas eliminar:")
        st.dataframe(df_existente.tail(10))
        
        id_borrar = st.number_input("Índice de fila", min_value=0, max_value=len(df_existente)-1, step=1)
        
        if st.button("❌ Eliminar Registro Permanentemente", type="primary"):
            df_final = df_existente.drop(index=id_borrar)
            conn.update(spreadsheet=url_hoja, data=df_final)
            st.success("Registro eliminado correctamente.")
            st.rerun()
