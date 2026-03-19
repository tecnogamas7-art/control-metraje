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
st.set_page_config(page_title="Control de Metraje Pro", layout="wide")
st.title("🚀 Sistema de Control de Metraje")

# Menú lateral
st.sidebar.title("Navegación")
menu = st.sidebar.radio("Ir a:", ["📝 Registrar Metraje", "📊 Ver Reportes Generales", "🗑️ Administrar Historial"])

# --- OPCIÓN 1: REGISTRAR ---
if menu == "📝 Registrar Metraje":
    st.subheader("Nuevo Registro Diario")
    
    col1, col2 = st.columns(2)
    with col1:
        operador = st.selectbox("Seleccione Operador", ["Gabriel", "Adrian", "Freddy"])
        fecha = st.date_input("Fecha de trabajo", datetime.now())
    with col2:
        valor = st.number_input("Metraje alcanzado (m)", min_value=0.0, step=0.01, format="%.2f")
        st.info(f"Meta diaria: **{META_DIARIA}m**")

    if st.button("💾 Guardar Registro", use_container_width=True):
        try:
            valor_redondeado = round(valor, 2)
            with sqlite3.connect(DB_NAME) as conn:
                conn.execute("INSERT INTO metrajes VALUES (?, ?, ?)", (str(fecha), operador, valor_redondeado))
                conn.commit()
            
            if valor_redondeado >= META_DIARIA:
                st.success(f"✅ ¡Excelente! {operador} cumplió la meta con {valor_redondeado:.2f}m.")
            else:
                faltante = round(META_DIARIA - valor_redondeado, 2)
                st.warning(f"⚠️ A {operador} le faltaron {faltante:.2f}m para la meta.")
        except sqlite3.IntegrityError:
            st.error("❌ Ya existe un registro para este operador en esta fecha.")

# --- OPCIÓN 2: REPORTES ---
elif menu == "📊 Ver Reportes Generales":
    st.subheader("📅 Reporte Mensual Detallado")
    
    with sqlite3.connect(DB_NAME) as conn:
        df = pd.read_sql_query("SELECT * FROM metrajes ORDER BY fecha ASC", conn)

    if not df.empty:
        mes_actual = datetime.now().strftime("%Y-%m")
        mes_sel = st.text_input("Filtrar por Mes (YYYY-MM):", mes_actual)
        df_filtrado = df[df['fecha'].str.contains(mes_sel)].copy()
        
        if not df_filtrado.empty:
            # --- TABLA DE 4 COLUMNAS (FECHA + OPERADORES) ---
            tabla_pivot = df_filtrado.pivot(index='fecha', columns='operador', values='metraje')
            columnas_fijas = ["Gabriel", "Adrian", "Freddy"]
            for col in columnas_fijas:
                if col not in tabla_pivot.columns:
                    tabla_pivot[col] = None
            
            tabla_pivot = tabla_pivot[columnas_fijas]

            st.write(f"### Registros de {mes_sel}")
            st.dataframe(tabla_pivot.style.format("{:.2f}", na_rep="-"), use_container_width=True)

            # --- GRÁFICA DE BARRAS ---
            st.write("---")
            st.write("### 📈 Producción Total del Mes")
            resumen = df_filtrado.groupby("operador")["metraje"].agg(['mean', 'sum', 'count'])
            resumen.columns = ['Promedio Diario', 'Total Metraje Mes', 'Días Trabajados']
            
            # Gráfica comparativa
            st.bar_chart(resumen['Total Metraje Mes'])

            # --- RESUMEN ESTADÍSTICO ---
            st.write("### 📊 Resumen por Operador")
            st.table(resumen.style.format({
                'Promedio Diario': '{:.2f}', 
                'Total Metraje Mes': '{:.2f}', 
                'Días Trabajados': '{:.0f}'
            }))
            
            csv = df_filtrado.to_csv(index=True).encode('utf-8')
            st.download_button("📥 Descargar este reporte (CSV)", data=csv, file_name=f"reporte_{mes_sel}.csv", mime="text/csv")
        else:
            st.warning(f"No hay registros para {mes_sel}")
    else:
        st.info("La base de datos está vacía.")

# --- OPCIÓN 3: BORRAR ---
elif menu == "🗑️ Administrar Historial":
    st.subheader("Gestión de Datos")
    with sqlite3.connect(DB_NAME) as conn:
        df_borrar = pd.read_sql_query("SELECT rowid as ID, fecha, operador, metraje FROM metrajes ORDER BY fecha DESC LIMIT 15", conn)
    
    if not df_borrar.empty:
        st.write("Últimos 15 registros:")
        st.table(df_borrar.style.format({"metraje": "{:.2f}"}))
        
        id_a_borrar = st.number_input("Ingrese el ID para eliminar", min_value=0, step=1)
        if st.button("⚠️ Confirmar Eliminación", type="primary"):
            with sqlite3.connect(DB_NAME) as conn:
                conn.execute("DELETE FROM metrajes WHERE rowid = ?", (id_a_borrar,))
                conn.commit()
            st.success("Registro eliminado.")
            st.rerun()
