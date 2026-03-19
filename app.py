import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- CONFIGURACIÓN ---
DB_NAME = "registro_metrajes.db"
META_DIARIA = 150.0

def inicializar_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS metrajes 
                        (fecha TEXT, operador TEXT, metraje REAL, UNIQUE(fecha, operador))''')

inicializar_db()

# --- INTERFAZ STREAMLIT ---
st.set_page_config(page_title="Control de Metraje", layout="wide")
st.title("🚀 Control de Metraje Operadores")

st.sidebar.header("Menú de Navegación")
menu = st.sidebar.radio("Ir a:", ["Registrar Metraje", "Ver Reportes y Análisis", "Borrar Registros"])

# --- OPCIÓN 1: REGISTRAR ---
if menu == "Registrar Metraje":
    st.subheader("📝 Nuevo Registro Diario")
    
    col1, col2 = st.columns(2)
    with col1:
        operador = st.selectbox("Seleccione Operador", ["Gabriel", "Adrian", "Freddy"])
        fecha = st.date_input("Fecha de trabajo", datetime.now())
    with col2:
        valor = st.number_input("Metraje alcanzado (m)", min_value=0.0, step=0.01, format="%.2f")
        st.info(f"Meta diaria: {META_DIARIA}m")

    if st.button("Guardar en Base de Datos"):
        try:
            valor_redondeado = round(valor, 2)
            with sqlite3.connect(DB_NAME) as conn:
                conn.execute("INSERT INTO metrajes VALUES (?, ?, ?)", (str(fecha), operador, valor_redondeado))
                conn.commit()
            
            if valor_redondeado >= META_DIARIA:
                st.success(f"🎉 ¡Excelente! {operador} cumplió la meta con {valor_redondeado:.2f}m.")
            else:
                faltante = round(META_DIARIA - valor_redondeado, 2)
                st.warning(f"📉 A {operador} le faltaron {faltante:.2f}m para la meta.")
        except sqlite3.IntegrityError:
            st.error("❌ Error: Ya existe un registro para este operador en la fecha seleccionada.")

# --- OPCIÓN 2: REPORTES ---
elif menu == "Ver Reportes y Análisis":
    st.subheader("📊 Reporte de Rendimiento")
    
    with sqlite3.connect(DB_NAME) as conn:
        df = pd.read_sql_query("SELECT * FROM metrajes ORDER BY fecha DESC", conn)

    if not df.empty:
        # Filtro de búsqueda
        mes_actual = datetime.now().strftime("%Y-%m")
        mes_sel = st.text_input("Filtrar por Mes (Formato: YYYY-MM)", mes_actual)
        
        df_filtrado = df[df['fecha'].str.contains(mes_sel)].copy()
        
        if not df_filtrado.empty:
            st.write(f"### Datos de {mes_sel}")
            # Tabla de registros individuales con 2 decimales
            st.dataframe(df_filtrado.style.format({"metraje": "{:.2f}"}), use_container_width=True)

            # --- RESUMEN MENSUAL CON 2 DECIMALES ---
            st.subheader(f"📈 Resumen Estadístico: {mes_sel}")
            resumen = df_filtrado.groupby("operador")["metraje"].agg(['mean', 'sum', 'count'])
            resumen.columns = ['Promedio Diario', 'Total Metraje Mes', 'Días Trabajados']
            
            # Formateo estricto a 2 decimales para el resumen
            st.table(resumen.style.format({
                'Promedio Diario': '{:.2f}',
                'Total Metraje Mes': '{:.2f}',
                'Días Trabajados': '{:.0f}'
            }))
        else:
            st.warning(f"No hay datos para el mes {mes_sel}")

        if st.sidebar.button("Preparar Excel"):
            df.to_excel("Reporte_Metrajes.xlsx", index=False)
            st.sidebar.success("Archivo generado en el servidor.")
    else:
        st.info("La base de datos está vacía.")

# --- OPCIÓN 3: BORRAR ---
elif menu == "Borrar Registros":
    st.subheader("🗑️ Administrar Historial")
    with sqlite3.connect(DB_NAME) as conn:
        df_borrar = pd.read_sql_query("SELECT rowid as ID, fecha, operador, metraje FROM metrajes ORDER BY fecha DESC LIMIT 15", conn)
    
    if not df_borrar.empty:
        st.write("Últimos 15 registros:")
        st.table(df_borrar.style.format({"metraje": "{:.2f}"}))
        
        id_a_borrar = st.number_input("Ingrese el ID para eliminar", min_value=0, step=1)
        if st.button("Confirmar Eliminación"):
            with sqlite3.connect(DB_NAME) as conn:
                conn.execute("DELETE FROM metrajes WHERE rowid = ?", (id_a_borrar,))
                conn.commit()
            st.rerun()
    else:
        st.info("No hay registros para eliminar.")
