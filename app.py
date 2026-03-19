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
st.title("🚀 Control de Metraje")
st.sidebar.header("Opciones")

menu = st.sidebar.selectbox("Seleccione una acción", ["Registrar", "Ver Reportes", "Borrar Registros"])

# --- OPCIÓN 1: REGISTRAR ---
if menu == "Registrar":
    st.subheader("Nuevo Registro")
    operador = st.selectbox("Operador", ["Gabriel", "Adrian", "Freddy"])
    fecha = st.date_input("Fecha", datetime.now())
    valor = st.number_input("Metraje (m)", min_value=0.0, step=1.0)

    if st.button("Guardar Registro"):
        try:
            with sqlite3.connect(DB_NAME) as conn:
                conn.execute("INSERT INTO metrajes VALUES (?, ?, ?)", (str(fecha), operador, valor))
                conn.commit()
            
            if valor >= META_DIARIA:
                st.success(f"🎉 ¡Excelente! {operador} superó la meta de {META_DIARIA}m.")
            else:
                st.warning(f"📉 Faltaron {(META_DIARIA - valor):.2f}m para la meta.")
        except sqlite3.IntegrityError:
            st.error("❌ Ya existe un registro para este operador en esta fecha.")

# --- OPCIÓN 2: REPORTES ---
elif menu == "Ver Reportes":
    st.subheader("📊 Análisis de Datos")
    
    with sqlite3.connect(DB_NAME) as conn:
        df = pd.read_sql_query("SELECT * FROM metrajes ORDER BY fecha DESC", conn)

    if not df.empty:
        # Filtro por mes
        mes_sel = st.text_input("Filtrar por mes (YYYY-MM)", datetime.now().strftime("%Y-%m"))
        df_filtrado = df[df['fecha'].str.contains(mes_sel)]
        
        st.write(f"Mostrando datos de: {mes_sel}")
        st.dataframe(df_filtrado)

        # Resumen
        st.subheader("Resumen Mensual")
        resumen = df_filtrado.groupby("operador")["metraje"].agg(['mean', 'sum', 'count'])
        resumen.columns = ['Promedio', 'Total Mes', 'Días Trabajados']
        st.table(resumen.round(2))

        # Botón para Excel
        if st.button("Generar reporte para descargar"):
            df.to_excel("Reporte_Metrajes.xlsx", index=False)
            st.success("Reporte listo internamente.")
    else:
        st.info("No hay datos registrados aún.")

# --- OPCIÓN 3: BORRAR ---
elif menu == "Borrar Registros":
    st.subheader("🗑️ Eliminar Entradas")
    with sqlite3.connect(DB_NAME) as conn:
        df_borrar = pd.read_sql_query("SELECT rowid, * FROM metrajes ORDER BY rowid DESC LIMIT 10", conn)
    
    if not df_borrar.empty:
        st.table(df_borrar)
        id_a_borrar = st.number_input("Ingrese el ID (rowid) a eliminar", min_value=0, step=1)
        if st.button("Eliminar"):
            with sqlite3.connect(DB_NAME) as conn:
                conn.execute("DELETE FROM metrajes WHERE rowid = ?", (id_a_borrar,))
                conn.commit()
            st.rerun()
    else:
        st.info("Nada que borrar.")
