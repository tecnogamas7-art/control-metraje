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
    
    if st.button("💾 Guardar Registro", use_container_width=True):
        try:
            valor_redondeado = round(valor, 2)
            with sqlite3.connect(DB_NAME) as conn:
                conn.execute("INSERT INTO metrajes VALUES (?, ?, ?)", (str(fecha), operador, valor_redondeado))
                conn.commit()
            st.success(f"✅ Registro guardado: {operador} - {valor_redondeado:.2f}m")
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
            # 1. TABLA PRINCIPAL (VISTA REGISTROS)
            tabla_pivot = df_filtrado.pivot(index='fecha', columns='operador', values='metraje')
            for col in ["Gabriel", "Adrian", "Freddy"]:
                if col not in tabla_pivot.columns: tabla_pivot[col] = None
            tabla_final = tabla_pivot[["Gabriel", "Adrian", "Freddy"]]
            
            st.write("### Detalle Diario")
            st.dataframe(tabla_final.style.format("{:.2f}", na_rep="-"), use_container_width=True)
            
            # 2. GRÁFICA DE BARRAS (RESTAURADA)
            st.write("---")
            st.write("### 📈 Producción Total del Mes")
            resumen = df_filtrado.groupby("operador")["metraje"].agg(['mean', 'sum', 'count']).sort_values(by='mean', ascending=False)
            resumen.columns = ['Promedio Diario', 'Total Metraje Mes', 'Días Trabajados']
            
            st.bar_chart(resumen['Total Metraje Mes'])

            # 3. TABLA DE PROMEDIOS / CONSOLIDADO (RESTAURADA)
            st.write("### 📊 Consolidado Mensual")
            st.table(resumen.style.format({
                'Promedio Diario': '{:.2f}', 
                'Total Metraje Mes': '{:.2f}', 
                'Días Trabajados': '{:.0f}'
            }))

            # 4. EXPORTACIÓN PDF PROFESIONAL
            st.write("---")
            st.write("### ⬇️ Exportar Reporte Profesional")
            
            estilo_pdf = """
            <style>
                body { font-family: Arial, sans-serif; color: #333; padding: 30px; }
                .header { text-align: center; border-bottom: 2px solid #444; padding-bottom: 10px; margin-bottom: 20px; }
                h3 { color: #2c3e50; margin-top: 25px; border-left: 5px solid #2c3e50; padding-left: 10px; }
                table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 11px; }
                th { background-color: #f2f2f2; color: #333; padding: 8px; border: 1px solid #ccc; text-align: left; }
                td { padding: 6px; border: 1px solid #ccc; }
                .resumen-th { background-color: #2c3e50; color: white; }
            </style>
            """
            
            html_pro = f"""
            {estilo_pdf}
            <div class="header">
                <h2>REPORTE MENSUAL DE METRAJES</h2>
                <p>Período: {mes_sel} | Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
            </div>
            <h3>1. Detalle Diario de Metraje</h3>
            {tabla_final.style.format("{:.2f}", na_rep="-").to_html()}
            
            <h3>2. Resumen Estadístico por Operador</h3>
            <table>
                <thead>
                    <tr>
                        <th class="resumen-th">Operador</th>
                        <th class="resumen-th">Promedio Diario (m)</th>
                        <th class="resumen-th">Total Mensual (m)</th>
                        <th class="resumen-th">Días Trabajados</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join([f"<tr><td>{idx}</td><td>{row['Promedio Diario']:.2f}</td><td>{row['Total Metraje Mes']:.2f}</td><td>{row['Días Trabajados']:.0f}</td></tr>" for idx, row in resumen.iterrows()])}
                </tbody>
            </table>
            <p style="margin-top:40px; font-size:10px; color:gray;">* Para guardar como PDF: Abra el archivo descargado y presione Ctrl+P.</p>
            """

            st.download_button(
                label="📄 Descargar Reporte para PDF",
                data=html_pro.encode('utf-8'),
                file_name=f"Reporte_Metraje_{mes_sel}.html",
                mime="text/html"
            )
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
        st.dataframe(df_borrar.style.format({"metraje": "{:.2f}"}), hide_index=True, use_container_width=True)
        id_a_borrar = st.number_input("ID para eliminar", min_value=0, step=1)
        if st.button("❌ Eliminar Registro", type="primary"):
            with sqlite3.connect(DB_NAME) as conn:
                conn.execute("DELETE FROM metrajes WHERE rowid = ?", (id_a_borrar,))
                conn.commit()
            st.success("Registro eliminado.")
            st.rerun()
