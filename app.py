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
            # TABLA DE 4 COLUMNAS
            tabla_pivot = df_filtrado.pivot(index='fecha', columns='operador', values='metraje')
            for col in ["Gabriel", "Adrian", "Freddy"]:
                if col not in tabla_pivot.columns: tabla_pivot[col] = None
            
            st.dataframe(tabla_pivot[["Gabriel", "Adrian", "Freddy"]].style.format("{:.2f}", na_rep="-"), use_container_width=True)
            
            st.write("---")
            resumen = df_filtrado.groupby("operador")["metraje"].agg(['mean', 'sum', 'count']).sort_values(by='mean', ascending=False)
            resumen.columns = ['Promedio Diario', 'Total Metraje Mes', 'Días Trabajados']
            st.bar_chart(resumen['Total Metraje Mes'])
            
            # --- GENERACIÓN DE HTML PROFESIONAL ---
            st.write("### ⬇️ Descargas Profesionales")
            
            # Estilo CSS para el HTML
            estilo_html = """
            <style>
                body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #333; margin: 40px; }
                h2 { color: #1f4e78; border-bottom: 2px solid #1f4e78; padding-bottom: 10px; }
                table { border-collapse: collapse; width: 100%; margin-top: 20px; box-shadow: 0 2px 15px rgba(0,0,0,0.1); }
                th { background-color: #1f4e78; color: white; padding: 12px; text-align: left; text-transform: uppercase; font-size: 13px; }
                td { padding: 10px; border-bottom: 1px solid #ddd; font-size: 14px; }
                tr:nth-child(even) { background-color: #f9f9f9; }
                tr:hover { background-color: #f1f1f1; }
                .footer { margin-top: 30px; font-size: 12px; color: #777; font-style: italic; }
            </style>
            """
            
            # Construcción del documento HTML
            header_html = f"<h2>Reporte de Metrajes - {mes_sel}</h2>"
            footer_html = f"<div class='footer'>Reporte generado automáticamente el {datetime.now().strftime('%d/%m/%Y %H:%M')}</div>"
            
            # Convertir tabla a HTML
            tabla_html = tabla_pivot[["Gabriel", "Adrian", "Freddy"]].style.format("{:.2f}", na_rep="-").to_html()
            reporte_completo = f"<html>{estilo_html}<body>{header_html}{tabla_html}{footer_html}</body></html>"
            
            # Botones
            c1, c2 = st.columns(2)
            with c1:
                st.download_button("📥 Descargar CSV Estándar", data=df_filtrado.to_csv(index=True).encode('utf-8'), file_name=f"reporte_{mes_sel}.csv", mime="text/csv")
            with c2:
                st.download_button("🌐 Descargar Reporte Profesional (HTML)", data=reporte_completo.encode('utf-8'), file_name=f"reporte_pro_{mes_sel}.html", mime="text/html")
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
