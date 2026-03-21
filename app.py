import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Control de Metraje Pro", layout="wide")
st.title("🚀 Sistema de Control de Metraje (Nube)")

# --- CONEXIÓN A GOOGLE SHEETS ---
# Reemplaza sqlite3 por conexión directa a la nube
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Leemos los datos actuales. Si la hoja está vacía, creamos un DataFrame base
    df_existente = conn.read(ttl=0) 
except Exception as e:
    st.error("⚠️ Error de conexión: Revisa tus credenciales en Secrets.")
    st.info("Asegúrate de que la private_key en Secrets use triple comilla (''' )")
    st.stop()

# --- INTERFAZ STREAMLIT ---
menu = st.sidebar.radio("Ir a:", ["📝 Registrar Metraje", "📊 Ver Reportes Generales", "🗑️ Administrar Historial"])

# --- OPCIÓN 1: REGISTRAR ---
if menu == "📝 Registrar Metraje":
    st.subheader("Nuevo Registro Diario")
    
    with st.form("formulario_registro"):
        col1, col2 = st.columns(2)
        with col1:
            operador = st.selectbox("Seleccione Operador", ["Gabriel", "Adrian", "Freddy"])
            fecha = st.date_input("Fecha de trabajo", datetime.now())
        with col2:
            valor = st.number_input("Metraje alcanzado (m)", min_value=0.0, step=0.01, format="%.2f")
        
        submit = st.form_submit_button("💾 Guardar Registro", use_container_width=True)

    if submit:
        # Verificar si ya existe registro para esa fecha y operador
        if not df_existente.empty and ((df_existente['fecha'].astype(str) == str(fecha)) & (df_existente['operador'] == operador)).any():
            st.error(f"❌ Ya existe un registro para {operador} en la fecha {fecha}.")
        else:
            nuevo_dato = pd.DataFrame([{
                "fecha": str(fecha),
                "operador": operador,
                "metraje": round(valor, 2)
            }])
            
            # Actualizar Google Sheets
            df_actualizado = pd.concat([df_existente, nuevo_dato], ignore_index=True)
            conn.update(data=df_actualizado)
            st.success(f"✅ Registro guardado en la nube: {operador} - {valor:.2f}m")
            st.balloons()
            st.rerun()

# --- OPCIÓN 2: REPORTES ---
elif menu == "📊 Ver Reportes Generales":
    st.subheader("📅 Reporte Mensual Detallado")
    
    if not df_existente.empty:
        # Filtro de mes
        mes_actual = datetime.now().strftime("%Y-%m")
        mes_sel = st.text_input("Filtrar por Mes (YYYY-MM):", mes_actual)
        
        df_filtrado = df_existente[df_existente['fecha'].str.contains(mes_sel)].copy()
        
        if not df_filtrado.empty:
            # 1. TABLA PRINCIPAL
            tabla_pivot = df_filtrado.pivot(index='fecha', columns='operador', values='metraje')
            for col in ["Gabriel", "Adrian", "Freddy"]:
                if col not in tabla_pivot.columns: tabla_pivot[col] = None
            
            st.write("### Detalle Diario")
            st.dataframe(tabla_pivot.style.format("{:.2f}", na_rep="-"), use_container_width=True)
            
            # 2. GRÁFICA Y CONSOLIDADO
            st.write("---")
            resumen = df_filtrado.groupby("operador")["metraje"].agg(['mean', 'sum', 'count'])
            resumen.columns = ['Promedio Diario', 'Total Metraje Mes', 'Días Trabajados']
            
            col_graf, col_tab = st.columns([1, 1])
            with col_graf:
                st.write("### 📈 Producción Total")
                st.bar_chart(resumen['Total Metraje Mes'])
            with col_tab:
                st.write("### 📊 Estadísticas")
                st.table(resumen.style.format("{:.2f}"))

            # 3. EXPORTAR HTML (Para PDF)
            html_pro = f"<h2>Reporte {mes_sel}</h2>" + df_filtrado.to_html()
            st.download_button("⬇️ Descargar Reporte HTML", data=html_pro, file_name=f"reporte_{mes_sel}.html")
        else:
            st.warning("No hay datos para este mes.")
    else:
        st.info("La base de datos en la nube está vacía.")

# --- OPCIÓN 3: ADMINISTRAR ---
elif menu == "🗑️ Administrar Historial":
    st.subheader("Eliminar Registros")
    if not df_existente.empty:
        df_ver = df_existente.copy()
        df_ver['ID'] = df_ver.index
        st.dataframe(df_ver[['ID', 'fecha', 'operador', 'metraje']].tail(10), use_container_width=True)
        
        id_eliminar = st.number_input("Ingrese el ID a eliminar", min_value=0, max_value=len(df_existente)-1, step=1)
        if st.button("❌ Eliminar Permanentemente", type="primary"):
            df_final = df_existente.drop(id_eliminar)
            conn.update(data=df_final)
            st.success("Registro eliminado correctamente.")
            st.rerun()
