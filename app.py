import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import pytz
import base64

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Control Metraje", layout="centered")
ZONA_HORARIA = pytz.timezone('America/Bogota')
DB_NAME = "registro_metrajes.db"

MESES_ES = {
    "January": "ENERO", "February": "FEBRERO", "March": "MARZO", 
    "April": "ABRIL", "May": "MAYO", "June": "JUNIO", 
    "July": "JULIO", "August": "AGOSTO", "September": "SEPTIEMBRE", 
    "October": "OCTUBRE", "November": "NOVIEMBRE", "December": "DICIEMBRE"
}

def inicializar_db():
    conn = sqlite3.connect(DB_NAME)
    conn.execute('''CREATE TABLE IF NOT EXISTS metrajes 
                    (fecha TEXT, operador TEXT, metraje REAL, UNIQUE(fecha, operador))''')
    conn.commit()
    conn.close()

def generar_html_reporte(df):
    df['fecha_dt'] = pd.to_datetime(df['fecha'])
    try:
        u_mes = df['fecha_dt'].iloc[0].strftime('%B')
        u_anio = df['fecha_dt'].iloc[0].year
        mes_titulo = f"{MESES_ES.get(u_mes, u_mes)} {u_anio}"
    except:
        mes_titulo = "REPORTE"
    
    tabla_hist = df.pivot(index='fecha', columns='operador', values='metraje').sort_index(ascending=False).fillna("X").reset_index()
    mes_filtro = datetime.now(ZONA_HORARIA).strftime('%m-%Y')
    df['m_a'] = df['fecha_dt'].dt.strftime('%m-%Y')
    proms = df[df['m_a'] == mes_filtro].groupby('operador')['metraje'].mean().round(2).sort_values(ascending=False).reset_index()

    html = f"""
    <html><head><meta charset='UTF-8'><style>
    body {{ font-family: sans-serif; text-align: center; padding: 20px; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 10px; }}
    th, td {{ border: 1px solid #333; padding: 8px; text-align: center; }}
    th {{ background-color: #f2f2f2; }}
    .firma {{ margin-top: 60px; border-top: 2px solid #000; width: 200px; margin: 40px auto; }}
    </style></head><body>
    <h2>REPORTE MENSUAL: {mes_titulo}</h2>
    <h3>1. HISTORIAL DE DÍAS</h3>{tabla_hist.to_html(index=False)}
    <h3>2. RANKING DE PROMEDIOS</h3>{proms.to_html(index=False)}
    <div class='firma'>FIRMA</div></body></html>
    """
    return base64.b64encode(html.encode('utf-8')).decode('utf-8')

# --- INTERFAZ ---
inicializar_db()
st.title("📊 Registro de Metraje")

tab1, tab2, tab3 = st.tabs(["📝 Registro", "📋 Historial", "🔍 Buscador"])

with tab1:
    with st.form("reg_form", clear_on_submit=True):
        f = st.date_input("Fecha", datetime.now(ZONA_HORARIA))
        op = st.selectbox("Operador", ["Gabriel", "Adrian", "Freddy"])
        val = st.number_input("Metraje (m)", min_value=0.0, step=0.1)
        if st.form_submit_button("GUARDAR"):
            try:
                conn = sqlite3.connect(DB_NAME)
                conn.execute("INSERT INTO metrajes VALUES (?,?,?)", (str(f), op, val))
                conn.commit()
                conn.close()
                st.success("✅ Guardado correctamente")
            except:
                st.error("❌ Ya existe un registro para este operador en esta fecha")

with tab2:
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT rowid, * FROM metrajes ORDER BY fecha DESC", conn)
    conn.close()
    
    if not df.empty:
        # Tabla Historial Limpia
        tabla_historial = df.pivot(index='fecha', columns='operador', values='metraje').sort_index(ascending=False).fillna("-")
        st.subheader("Historial Reciente")
        st.dataframe(tabla_historial, use_container_width=True)
        
        # --- SECCIÓN DE BORRADO ---
        st.divider()
        with st.expander("🗑️ Zona de Borrado"):
            st.warning("Se borrará el registro más reciente que hiciste.")
            if st.button("CONFIRMAR: BORRAR ÚLTIMO REGISTRO"):
                conn = sqlite3.connect(DB_NAME)
                conn.execute("DELETE FROM metrajes WHERE rowid = (SELECT MAX(rowid) FROM metrajes)")
                conn.commit()
                conn.close()
                st.toast("Registro eliminado")
                st.rerun() # Recarga la app para ver el cambio

        # Botón Impresión
        st.divider()
        b64 = generar_html_reporte(df)
        st.markdown(f'<a href="data:text/html;base64,{b64}" download="reporte.html"><button style="width:100%;background-color:#4CAF50;color:white;padding:12px;border:none;border-radius:5px;cursor:pointer;font-weight:bold;">📥 DESCARGAR REPORTE PARA IMPRIMIR</button></a>', unsafe_allow_html=True)
    else:
        st.info("No hay datos registrados aún.")

with tab3:
    f_buscar = st.date_input("Consultar fecha específica")
    if st.button("Buscar"):
        conn = sqlite3.connect(DB_NAME)
        res = pd.read_sql_query("SELECT * FROM metrajes WHERE fecha = ?", conn, params=(str(f_buscar),))
        conn.close()
        if not res.empty:
            st.table(res.pivot(index='fecha', columns='operador', values='metraje').fillna("-"))
        else:
            st.warning("No hay registros para esta fecha.")
