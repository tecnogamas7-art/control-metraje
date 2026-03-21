import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Control de Metraje Pro", layout="wide")
st.title("🚀 Sistema de Control de Metraje (Nube)")

# --- CONEXIÓN A GOOGLE SHEETS ---
try:
    # Creamos la conexión usando el nuevo estándar de Streamlit
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Leemos la hoja de cálculo (ttl=0 para datos siempre frescos)
    df_existente = conn.read(ttl=0).dropna(how="all")
except Exception as e:
    st.error("⚠️ Error de conexión: Revisa tus credenciales en Secrets.")
    st.info("Asegúrate de que la 'private_key' en Secrets use comillas triples: \"\"\" ")
    st.stop()

# --- INTERFAZ ---
menu = st.sidebar.radio("Ir a:", ["📝 Registrar", "📊 Reportes", "🗑️ Administrar"])

# --- OPCIÓN 1: REGISTRAR ---
if menu == "📝 Registrar":
    st.subheader("Nuevo Registro Diario")
    with st.form("form_registro"):
        col1, col2 = st.columns(2)
        operador = col1.selectbox("Operador", ["Gabriel", "Adrian", "Freddy"])
        fecha = col1.date_input("Fecha", datetime.now())
        valor = col2.number_input("Metraje (m)", min_value=0.0, step=0.1)
        submit = st.form_submit_button("💾 Guardar en la Nube")

    if submit:
        # Verificar duplicados
        fecha_str = str(fecha)
        es_duplicado = not df_existente.empty and ((df_existente['fecha'].astype(str) == fecha_str) & (df_existente['operador'] == operador)).any()
        
        if es_duplicado:
            st.error(f"❌ Ya existe registro para {operador} el {fecha_str}")
        else:
            nueva_fila = pd.DataFrame([{"fecha": fecha_str, "operador": operador, "metraje": valor}])
            df_actualizado = pd.concat([df_existente, nueva_fila], ignore_index=True)
            conn.update(data=df_actualizado)
            st.success("✅ ¡Guardado con éxito!")
            st.rerun()

# --- OPCIÓN 2: REPORTES ---
elif menu == "📊 Reportes":
    if not df_existente.empty:
        st.write("### Vista General")
        st.dataframe(df_existente, use_container_width=True)
        st.bar_chart(df_existente.groupby("operador")["metraje"].sum())
    else:
        st.info("No hay datos en la nube.")

# --- OPCIÓN 3: ADMINISTRAR ---
elif menu == "🗑️ Administrar":
    if not df_existente.empty:
        st.write("### Eliminar Registros")
        df_con_id = df_existente.copy()
        df_con_id['ID'] = df_con_id.index
        st.table(df_con_id.tail(5))
        
        id_eliminar = st.number_input("ID a borrar", min_value=0, max_value=len(df_existente)-1, step=1)
        if st.button("❌ Eliminar Permanentemente"):
            df_final = df_existente.drop(index=id_eliminar)
            conn.update(data=df_final)
            st.success("Registro eliminado.")
            st.rerun()
