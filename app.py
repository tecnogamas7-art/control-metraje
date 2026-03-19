import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- CONFIGURACIÓN DE SEGURIDAD ---
USUARIO_ADMIN = "admin"
CLAVE_ADMIN = "1234"

# --- CONFIGURACIÓN BASE DE DATOS ---
DB_NAME = "registro_metrajes.db"
META_DIARIA = 150.0

def inicializar_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS metrajes 
                        (fecha TEXT, operador TEXT, metraje REAL, UNIQUE(fecha, operador))''')

inicializar_db()

# --- GESTIÓN DE SESIÓN ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

def login_form():
    st.info("🔐 Inicie sesión para realizar cambios o registros.")
    with st.form("login_form"):
        user = st.text_input("Usuario")
        pw = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Entrar"):
            if user == USUARIO_ADMIN and pw == CLAVE_ADMIN:
                st.session_state.autenticado = True
                st.rerun()
            else:
                st.error("❌ Credenciales incorrectas")

# --- INTERFAZ PRINCIPAL ---
st.set_page_config(page_title="Control de Metraje Pro", layout="wide")
st.title("🚀 Sistema de Control de Metraje")

# Menú lateral libre
menu = st.sidebar.radio("Navegación:", ["📊 Ver Reportes Generales", "📝 Registrar Metraje", "🗑️ Administrar Historial"])

if st.session_state.autenticado:
    if st.sidebar.button("🔓 Cerrar Sesión"):
        st.session_state.autenticado = False
        st.rerun()

# --- OPCIÓN 1: REPORTES (ACCESO LIBRE) ---
if menu == "📊 Ver Reportes Generales":
    st.subheader("📅 Reporte Mensual Detallado")
    with sqlite3.connect(DB_NAME) as conn:
        df = pd.read_sql_query("SELECT * FROM metrajes ORDER BY fecha ASC", conn)
    
    if not df.empty:
        mes_actual = datetime.now().strftime("%Y-%m")
        mes_sel = st.text_input("Filtrar por Mes (YYYY-MM):", mes_actual)
        df_filtrado = df[df['fecha'].str.contains(mes_sel)].copy()
        
        if not df_filtrado.empty:
            # TABLA PRINCIPAL
            tabla_pivot = df_filtrado.pivot(index='fecha', columns='operador', values='metraje')
            for col in ["Gabriel", "Adrian", "Freddy"]:
                if col not in tabla_pivot.columns: tabla_pivot[col] = None
            tabla_final = tabla_pivot[["Gabriel", "Adrian", "Freddy"]]
            
            st.write("### Detalle Diario")
            st.dataframe(tabla_final.style.format("{:.2f}", na_rep="-"), use_container_width=True)
            
            # GRÁFICA Y RESUMEN
            st.write("---")
            resumen = df_filtrado.groupby("operador")["metraje"].agg(['mean', 'sum', 'count']).sort_values(by='mean', ascending=False)
            resumen.columns = ['Promedio Diario', 'Total Metraje Mes', 'Días Trabajados']
            
            col_graf, col_tab = st.columns([2, 1])
            with col_graf:
                st.write("### 📈 Producción Total")
                st.bar_chart(resumen['Total Metraje Mes'])
            with col_tab:
                st.write("### 📊 Consolidado")
                st.table(resumen.style.format({'Promedio Diario': '{:.2f}', 'Total Metraje Mes': '{:.2f}', 'Días Trabajados': '{:.0f}'}))

            # EXPORTACIÓN
            st.write("---")
            estilo_pdf = "<style>body{font-family:Arial;padding:20px;} table{width:100%;border-collapse:collapse;} th{background-color:#2c3e50;color:white;padding:8px;border:1px solid #ccc;} td{padding:6px;border:1px solid #ccc;}</style>"
            html_pro = f"{estilo_pdf}<h2>REPORTE {mes_sel}</h2><h3>Detalle</h3>{tabla_final.style.format('{:.2f}', na_rep='-').to_html()}<h3>Resumen</h3>" + resumen.to_html()
            st.download_button("📄 Descargar para PDF", data=html_pro.encode('utf-8'), file_name=f"Reporte_{mes_sel}.html", mime="text/html")
        else:
            st.warning("No hay registros para este mes.")
    else:
        st.info("Base de datos vacía.")

# --- OPCIÓN 2: REGISTRAR (REQUIERE LOGIN) ---
elif menu == "📝 Registrar Metraje":
    if not st.session_state.autenticado:
        login_form()
    else:
        st.subheader("📝 Nuevo Registro Diario")
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
                st.success(f"✅ Guardado correctamente.")
            except sqlite3.IntegrityError:
                st.error("❌ Ya existe un registro para esa fecha.")

# --- OPCIÓN 3: BORRAR (REQUIERE LOGIN) ---
elif menu == "🗑️ Administrar Historial":
    if not st.session_state.autenticado:
        login_form()
    else:
        st.subheader("🗑️ Gestión de Historial")
        with sqlite3.connect(DB_NAME) as conn:
            df_borrar = pd.read_sql_query("SELECT rowid as ID, fecha, operador, metraje FROM metrajes ORDER BY rowid DESC LIMIT 15", conn)
        
        if not df_borrar.empty:
            st.dataframe(df_borrar.style.format({"metraje": "{:.2f}"}), hide_index=True, use_container_width=True)
            id_a_borrar = st.number_input("ID para eliminar", min_value=0, step=1)
            if st.button("❌ Eliminar Registro", type="primary"):
                with sqlite3.connect(DB_NAME) as conn:
                    conn.execute("DELETE FROM metrajes WHERE rowid = ?", (id_a_borrar,))
                    conn.commit()
                st.success("Eliminado.")
                st.rerun()
