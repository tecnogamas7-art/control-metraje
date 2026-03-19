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
            st.error("❌ Ya existe un registro para ese operador en esta fecha.")

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
            # TABLA DE 4 COLUMNAS (Misma vista que registros)
            tabla_pivot = df_filtrado.pivot(index='fecha', columns='operador', values='metraje')
            for col in ["Gabriel", "Adrian", "Freddy"]:
                if col not in tabla_pivot.columns: tabla_pivot[col] = None
            tabla_final = tabla_pivot[["Gabriel", "Adrian", "Freddy"]]

            st.dataframe(tabla_final.style.format("{:.2f}", na_rep="-"), use_container_width=True)
            
            # RESUMEN PARA EL REPORTE
            resumen = df_filtrado.groupby("operador")["metraje"].agg(['mean', 'sum']).sort_values(by='mean', ascending=False)
            resumen.columns = ['Promedio Diario', 'Total Mensual']

            # --- GENERACIÓN DE REPORTE PDF (VÍA HTML) ---
            st.write("---")
            st.write("### ⬇️ Exportar Reporte Profesional")

            estilo_pdf = """
            <style>
                @media print { .no-print { display: none; } }
                body { font-family: 'Helvetica', sans-serif; color: #2c3e50; padding: 20px; }
                .header { text-align: center; border-bottom: 2px solid #34495e; padding-bottom: 10px; margin-bottom: 20px; }
                table { width: 100%; border-collapse: collapse; margin-bottom: 30px; font-size: 12px; }
                th { background-color: #f8f9fa; color: #34495e; padding: 10px; border: 1px solid #dee2e6; text-align: left; }
                td { padding: 8px; border: 1px solid #dee2e6; }
                .summary-table th { background-color: #34495e; color: white; }
                .title { font-size: 22px; font-weight: bold; }
            </style>
            """
            
            html_content = f"""
            {estilo_pdf}
            <div class="header">
                <div class="title">REPORTE MENSUAL DE METRAJES</div>
                <div>Período: {mes_sel} | Generado: {datetime.now().strftime('%d/%m/%Y')}</div>
            </div>
            
            <h3>Detalle Diario</h3>
            {tabla_final.style.format("{:.2f}", na_rep="-").to_html()}
            
            <h3>Resumen de Promedios</h3>
            <table class="summary-table">
                <thead>
                    <tr><th>Operador</th><th>Promedio Diario (m)</th><th>Total Mensual (m)</th></tr>
                </thead>
                <tbody>
                    {''.join([f"<tr><td>{idx}</td><td>{row['Promedio Diario']:.2f}</td><td>{row['Total Mensual']:.2f}</td></tr>" for idx, row in resumen.iterrows()])}
                </tbody>
            </table>
            """

            # Botón para descargar el HTML (que el usuario puede imprimir como PDF)
            st.download_button(
                label="📄 Generar Reporte PDF (Descargar HTML para imprimir)",
                data=html_content.encode('utf-8'),
                file_name=f"Reporte_Metraje_{mes_sel}.html",
                mime="text/html",
                help="Descarga este archivo, ábrelo en tu navegador y presiona Ctrl+P para guardar como PDF."
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
