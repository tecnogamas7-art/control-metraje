import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import json
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Control de Metraje Pro", layout="wide")
st.title("🚀 Sistema de Control de Metraje (Google Sheets)")

# --- CONEXIÓN ROBUSTA A GOOGLE SHEETS ---
@st.cache_resource
def conectar_gsheets():
    try:
        # Extraemos el JSON desde los secrets y lo convertimos en diccionario
        json_info = st.secrets["connections"]["gsheets"]["json_key"]
        credentials_dict = json.loads(json_info)
        
        # Creamos la conexión pasando las credenciales directamente
        return st.connection(
            "gsheets", 
            type=GSheetsConnection, 
            service_account_info=credentials_dict
        )
    except Exception as e:
        st.error(f"❌ Error de configuración: {e}")
        st.stop()

conn = conectar_gsheets()

# Leer datos actuales
try:
    df_existente = conn.read(ttl=0).dropna(how="all")
except Exception as e:
    st.error(f"⚠️ No se pudo leer la hoja: {e}")
    st.info("Revisa que el correo de la cuenta de servicio tenga permisos de EDITOR en el Google Sheet.")
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
            st.success(f"✅ Registro guardado: {operador} - {valor:.2f}m")
            st.balloons()
            st.rerun()

# --- OPCIÓN 2: REPORTES ---
elif menu == "📊 Ver Reportes Generales":
    st.subheader("📅 Reporte Mensual Detallado")
    if not df_existente.empty:
        mes_actual = datetime.now().strftime("%Y-%m")
        mes_sel = st.text_input("Filtrar por Mes (YYYY-MM):", mes_actual)
        df_filtrado = df_existente[df_existente['fecha'].str.contains(mes_sel)].copy()
        
        if not df_filtrado.empty:
            tabla_pivot = df_filtrado.pivot(index='fecha', columns='operador', values='metraje')
            for col in ["Gabriel", "Adrian", "Freddy"]:
                if col not in tabla_pivot.columns: tabla_pivot[col] = None
            tabla_final = tabla_pivot[["Gabriel", "Adrian", "Freddy"]]
            
            st.write("### Detalle Diario")
            st.dataframe(tabla_final.style.format("{:.2f}", na_rep="-"), use_container_width=True)
            
            resumen = df_filtrado.groupby("operador")["metraje"].agg(['mean', 'sum', 'count']).sort_values(by='mean', ascending=False)
            resumen.columns = ['Promedio Diario', 'Total Metraje Mes', 'Días Trabajados']
            
            col_graf, col_tab = st.columns(2)
            with col_graf:
                st.bar_chart(resumen['Total Metraje Mes'])
            with col_tab:
                st.table(resumen.style.format("{:.2f}"))
        else:
            st.warning("No hay registros para este mes.")
    else:
        st.info("La hoja de cálculo está vacía.")

# --- OPCIÓN 3: BORRAR ---
elif menu == "🗑️ Administrar Historial":
    st.subheader("Gestión de Datos")
    if not df_existente.empty:
        df_con_id = df_existente.copy()
        df_con_id['ID'] = df_con_id.index
        st.dataframe(df_con_id[['ID', 'fecha', 'operador', 'metraje']].tail(15), use_container_width=True)
        
        id_borrar = st.number_input("ID del registro a eliminar", min_value=0, max_value=len(df_existente)-1, step=1)
        if st.button("❌ Eliminar Registro Permanentemente", type="primary"):
            df_final = df_existente.drop(index=id_borrar)
            conn.update(data=df_final)
            st.success("Registro eliminado.")
            st.rerun()
