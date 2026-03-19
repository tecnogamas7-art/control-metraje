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

# Menú lateral estilizado
st.sidebar.image("https://cdn-icons-png.flaticon.com", width=100)
st.sidebar.title("Navegación")
menu = st.sidebar.radio("Ir a:", ["📝 Registrar Metraje", "📊 Ver Reportes y Análisis", "🗑️ Administrar Historial"])

# --- OPCIÓN 1: REGISTRAR ---
if menu == "📝 Registrar Metraje":
    st.subheader("Nuevo Registro Diario")
    
    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            operador = st.selectbox("Seleccione Operador", ["Gabriel", "Adrian", "Freddy"])
            fecha = st.date_input("Fecha de trabajo", datetime.now())
        with col2:
            valor = st.number_input("Metraje alcanzado (m)", min_value=0.0, step=0.01, format="%.2f")
            st.info(f"Meta diaria configurada: **{META_DIARIA}m**")

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
                st.error("❌ Ya existe un registro para este operador en la fecha seleccionada.")

# --- OPCIÓN 2: REPORTES ---
elif menu == "📊 Ver Reportes y Análisis":
    st.subheader("Panel de Rendimiento Operativo")
    
    with sqlite3.connect(DB_NAME) as conn:
        df = pd.read_sql_query("SELECT * FROM metrajes ORDER BY fecha DESC", conn)

    if not df.empty:
        # Filtros en la parte superior
        mes_actual = datetime.now().strftime("%Y-%m")
        mes_sel = st.text_input("📅 Filtrar por Mes (Formato: YYYY-MM):", mes_actual)
        df_filtrado = df[df['fecha'].str.contains(mes_sel)].copy()
        
        if not df_filtrado.empty:
            # --- KPIs (Tarjetas de indicadores) ---
            total_mes = df_filtrado['metraje'].sum()
            promedio_gral = df_filtrado['metraje'].mean()
            mejor_dia = df_filtrado['metraje'].max()

            c1, c2, c3 = st.columns(3)
            c1.metric("Total Metraje Mes", f"{total_mes:.2f} m")
            c2.metric("Promedio Diario Gral.", f"{promedio_gral:.2f} m")
            c3.metric("Récord del Mes", f"{mejor_dia:.2f} m")

            # --- GRÁFICO COMPARATIVO ---
            st.write("---")
            st.write("### 📈 Producción Total por Operador")
            resumen = df_filtrado.groupby("operador")["metraje"].agg(['mean', 'sum', 'count'])
            resumen.columns = ['Promedio Diario', 'Total Metraje Mes', 'Días Trabajados']
            
            # Gráfico de barras
            st.bar_chart(resumen['Total Metraje Mes'])

            # --- TABLA DE RESUMEN DETALLADO ---
            st.write("### 📋 Resumen Estadístico")
            st.table(resumen.style.format({
                'Promedio Diario': '{:.2f}',
                'Total Metraje Mes': '{:.2f}',
                'Días Trabajados': '{:.0f}'
            }))

            # --- LISTA DE REGISTROS ---
            with st.expander("🔍 Ver todos los registros individuales de este mes"):
                st.dataframe(df_filtrado.style.format({"metraje": "{:.2f}"}), use_container_width=True)
            
            # Botón de descarga en la barra lateral
            csv = df.to_csv(index=False).encode('utf-8')
            st.sidebar.download_button(
                label="📥 Descargar Reporte CSV",
                data=csv,
                file_name=f'reporte_{mes_sel}.csv',
                mime='text/csv',
            )
        else:
            st.warning(f"No hay datos registrados para el mes: {mes_sel}")
    else:
        st.info("La base de datos aún no tiene registros.")

# --- OPCIÓN 3: BORRAR ---
elif menu == "🗑️ Administrar Historial":
    st.subheader("Gestión de Datos")
    with sqlite3.connect(DB_NAME) as conn:
        df_borrar = pd.read_sql_query("SELECT rowid as ID, fecha, operador, metraje FROM metrajes ORDER BY fecha DESC LIMIT 10", conn)
    
    if not df_borrar.empty:
        st.write("Últimos 10 registros:")
        st.table(df_borrar.style.format({"metraje": "{:.2f}"}))
        
        id_a_borrar = st.number_input("Ingrese el ID (columna ID) para eliminar", min_value=0, step=1)
        if st.button("⚠️ Confirmar Eliminación Permanente", type="primary"):
            with sqlite3.connect(DB_NAME) as conn:
                conn.execute("DELETE FROM metrajes WHERE rowid = ?", (id_a_borrar,))
                conn.commit()
            st.success("Registro eliminado correctamente.")
            st.rerun()
    else:
        st.info("No hay nada que borrar.")
