import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- CONFIGURACIÓN DE SEGURIDAD ---
# Puedes cambiar el usuario y la clave aquí
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

# --- FUNCIÓN DE LOGIN ---
def login():
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False

    if not st.session_state.autenticado:
        st.title("🔐 Acceso al Sistema")
        with st.form("login_form"):
            user = st.text_input("Usuario")
            pw = st.text_input("Contraseña", type="password")
            btn_login = st.form_submit_button("Entrar")
            
            if btn_login:
                if user == USUARIO_ADMIN and pw == CLAVE_ADMIN:
                    st.session_state.autenticado = True
                    st.rerun()
                else:
                    st.error("❌ Usuario o clave incorrectos")
        return False
    return True

# --- INTERFAZ PRINCIPAL ---
if login():
    st.set_page_config(page_title="Control de Metraje Pro", layout="wide")
    
    # Botón para cerrar sesión en la barra lateral
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.autenticado = False
        st.rerun()

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
                # TABLA PRINCIPAL
                tabla_pivot = df_filtrado.pivot(index='fecha', columns='operador', values='metraje')
                for col in ["Gabriel", "Adrian", "Freddy"]:
                    if col not in tabla_pivot.columns: tabla_pivot[col] = None
                tabla_final = tabla_pivot[["Gabriel", "Adrian", "Freddy"]]
                
                st.write("### Detalle Diario")
                st.dataframe(tabla_final.style.format("{:.2f}", na_rep="-"), use_container_width=True)
                
                # GRÁFICA DE BARRAS
                st.write("---")
                st.write("### 📈 Producción Total del Mes")
                resumen = df_filtrado.groupby("operador")["metraje"].agg(['mean', 'sum', 'count']).sort_values(by='mean', ascending=False)
                resumen.columns = ['Promedio Diario', 'Total Metraje Mes', 'Días Trabajados']
                st.bar_chart(resumen['Total Metraje Mes'])

                # TABLA DE PROMEDIOS
                st.write("### 📊 Consolidado Mensual")
                st.table(resumen.style.format({'Promedio Diario': '{:.2f}', 'Total Metraje Mes': '{:.2f}', 'Días Trabajados': '{:.0f}'}))

                # EXPORTACIÓN PROFESIONAL
                st.write("---")
                st.write("### ⬇️ Exportar Reporte")
                estilo_pdf = "<style>body{font-family:Arial;padding:30px;} .header{text-align:center;border-bottom:2px solid #444;} table{width:100%;border-collapse:collapse;margin-top:20px;font-size:11px;} th{background-color:#2c3e50;color:white;padding:8px;border:1px solid #ccc;} td{padding:6px;border:1px solid #ccc;}</style>"
                html_pro = f"{estilo_pdf}<div class='header'><h2>REPORTE MENSUAL</h2><p>{mes_sel}</p></div><h3>Detalle Diario</h3>{tabla_final.style.format('{:.2f}', na_rep='-').to_html()}<h3>Resumen</h3><table><tr><th>Operador</th><th>Promedio</th><th>Total</th><th>Días</th></tr>" + "".join([f"<tr><td>{idx}</td><td>{row['Promedio Diario']:.2f}</td><td>{row['Total Metraje Mes']:.2f}</td><td>{row['Días Trabajados']:.0f}</td></tr>" for idx, row in resumen.iterrows()]) + "</table>"
                
                st.download_button("📄 Descargar para PDF", data=html_pro.encode('utf-8'), file_name=f"Reporte_{mes_sel}.html", mime="text/html")
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
