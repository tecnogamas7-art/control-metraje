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
                st.warning(f"⚠️ A {operador} le faltaron {round(META_DIARIA - valor_redondeado, 2):.2f}m.")
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
            tabla_pivot = df_filtrado.pivot(index='fecha', columns='operador', values='metraje')
            for col in ["Gabriel", "Adrian", "Freddy"]:
                if col not in tabla_pivot.columns: tabla_pivot[col] = None
            
            st.write(f"### Registros de {mes_sel}")
            st.dataframe(tabla_pivot[["Gabriel", "Adrian", "Freddy"]].style.format("{:.2f}", na_rep="-"), use_container_width=True)
            
            st.write("---")
            st.write("### 📈 Producción Total del Mes")
            resumen = df_filtrado.groupby("operador")["metraje"].agg(['mean', 'sum', 'count']).sort_values(by='mean', ascending=False)
            resumen.columns = ['Promedio Diario', 'Total Metraje Mes', 'Días Trabajados']
            
            st.bar_chart(resumen['Total Metraje Mes'])
            
            st.write("### 📊 Resumen por Operador (Ordenado por mejor promedio)")
            st.table(resumen.style.format({'Promedio Diario': '{:.2f}', 'Total Metraje Mes': '{:.2f}', 'Días Trabajados': '{:.0f}'}))
            
            # --- BOTONES DE DESCARGA ---
            st.write("---")
            st.write("### ⬇️ Descargar Reportes")
            
            # Botón CSV
            csv = df_filtrado.to_csv(index=True).encode('utf-8')
            st.download_button("📥 Descargar reporte (CSV)", data=csv, file_name=f"reporte_{mes_sel}.csv", mime="text/csv")
            
            # Botón HTML
            html = df_filtrado.to_html(index=True, classes='table table-striped').encode('utf-8')
            st.download_button("🌐 Descargar reporte (HTML)", data=html, file_name=f"reporte_{mes_sel}.html", mime="text/html")
            
        else:
            st.warning("No hay registros para este mes.")
    else:
        st.info("Base de datos vacía.")

# --- OPCIÓN 3: BORRAR ---
elif menu == "🗑️ Administrar Historial":
    st.subheader("Gestión de Datos")
    with sqlite3.connect(DB_NAME) as conn:
        df_borrar = pd.read_sql_query("SELECT rowid as ID, fecha, operador, metraje FROM metrajes ORDER BY rowid DESC LIMIT 15", conn)
    
    if not df_borrar.empty:
        st.write("Últimos 15 registros ingresados:")
        st.dataframe(df_borrar.style.format({"metraje": "{:.2f}"}), hide_index=True, use_container_width=True)
        
        st.write("---")
        id_a_borrar = st.number_input("Ingrese el número de la columna ID para eliminar", min_value=0, step=1)
        
        if st.button("❌ Eliminar Registro", type="primary"):
            st.session_state.confirmar_borrado = True

        if "confirmar_borrado" in st.session_state and st.session_state.confirmar_borrado:
            st.warning(f"⚠️ ¿Confirmas la eliminación permanente del ID {id_a_borrar}?")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ SÍ, ELIMINAR", use_container_width=True):
                    with sqlite3.connect(DB_NAME) as conn:
                        conn.execute("DELETE FROM metrajes WHERE rowid = ?", (id_a_borrar,))
                        conn.commit()
                    st.success("Eliminado correctamente.")
                    st.session_state.confirmar_borrado = False
                    st.rerun()
            with c2:
                if st.button("🔙 CANCELAR", use_container_width=True):
                    st.session_state.confirmar_borrado = False
                    st.rerun()
    else:
        st.info("Base de datos vacía. ¡El próximo registro será el ID 1!")
