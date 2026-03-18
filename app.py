import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import pytz
import base64

# --- CONFIGURACIÓN E INTERFAZ ---
st.set_page_config(page_title="Control Metraje", layout="centered")

ZONA_HORARIA = pytz.timezone('America/Bogota')
DB_NAME = "registro_metrajes.db"

MESES_ES = {
    "January": "ENERO", "February": "FEBRERO", "March": "MARZO", 
    "April": "ABRIL", "May": "MAYO", "June": "JUNIO", 
    "July": "JULIO", "August": "AGOSTO", "September": "SEPTIEMBRE", 
    "October": "OCTUBRE", "November": "NOVIEMBRE", "December": "DICIEMBRE"
}

# --- FUNCIONES DE BASE DE DATOS ---
def inicializar_db():
    conn = sqlite3.connect(DB_NAME)
    conn.execute('''CREATE TABLE IF NOT EXISTS metrajes 
                    (fecha TEXT, operador TEXT, metraje REAL, UNIQUE(fecha, operador))''')
    conn.commit()
    conn.close()

def guardar_registro(fecha, operador, valor):
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.execute("INSERT INTO metrajes VALUES (?, ?, ?)", (str(fecha), operador, valor))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

# --- LÓGICA DE IMPRESIÓN ---
def generar_html_reporte(df):
    df['fecha_dt'] = pd.to_datetime(df['fecha'])
    u_mes = df['fecha_dt'].iloc[0].strftime('%B')
    u_anio = df['fecha_dt'].iloc[0].year
    mes_titulo = f"{MESES_ES.get(u_mes, u_mes)} {u_anio}"
    
    tabla_hist = df.pivot(index='fecha', columns='operador', values='metraje').sort_index(ascending=False).fillna("X").reset_index()
    
    mes_filtro = df['fecha_dt'].iloc[0].strftime('%m-%Y')
    df['m_a'] = df['fecha_dt'].dt.strftime('%m-%Y')
    proms = df[df['m_a'] == mes_filtro].groupby('operador')['metraje'].mean().round(2).sort_values(ascending=False).reset_index()

    html = f"""
    <html><head><meta charset='UTF-8'><style>
    body {{ font-family: sans-serif; text-align: center; padding: 20px; }}
    table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
    th, td {{ border: 1px solid #333; padding: 8px; text-align: center; }}
    th {{ background-color: #f2f2f2; }}
    .firma {{ margin-top: 50px; border-top: 2px solid #000; width: 200px; margin-left: auto; margin-right: auto; }}
    </style></head><body>
    <h2>REPORTE DE METRAJES: {mes_titulo}</h2>
    <h3>Historial</h3>{tabla_hist.to_html(index=False)}
    <h3>Ranking Promedios</h3>{proms.to_html(index=False)}
    <div class='firma'>FIRMA</div></body></html>
    """
    return base64.b64encode(html.encode('utf-8')).decode('utf-8')

# --- APP VISUAL ---
inicializar_db()

st.title("📊 Control de Metraje")

# Pestañas para organizar la App en el móvil
tab1, tab2, tab3 = st.tabs(["📝 Registro", "📋 Historial", "🔍 Buscador"])

with tab1:
    with st.form("registro_form"):
        fecha_sel = st.date_input("Fecha", datetime.now(ZONA_HORARIA))
        operador = st.selectbox("Operador", ["Gabriel", "Adrian", "Freddy"])
        valor = st.number_input("Metraje (m)", min_value=0.0, step=0.1)
        enviar = st.form_submit_button("GUARDAR REGISTRO")
        
        if enviar:
            if guardar_registro(fecha_sel, operador, valor):
                st.success(f"✅ Guardado: {operador} - {valor}m")
            else:
                st.error("❌ Ya existe un registro para este operador en esta fecha.")

with tab2:
    conn = sqlite3.connect(DB_NAME)
    df_v = pd.read_sql_query("SELECT * FROM metrajes ORDER BY fecha DESC", conn)
    conn.close()

    if not df_v.empty:
        # Tabla resumen
        tabla_pivote = df_v.pivot(index='fecha', columns='operador', values='metraje').fillna("-")
        st.dataframe(tabla_pivote, use_container_width=True)
        
        # Ranking
        st.subheader("🏆 Ranking del Mes")
        df_v['fecha_dt'] = pd.to_datetime(df_v['fecha'])
        mes_actual = datetime.now(ZONA_HORARIA).strftime('%m-%Y')
        df_v['m_a'] = df_v['fecha_dt'].dt.strftime('%m-%Y')
        rank = df_v[df_v['m_a'] == mes_actual].groupby("operador")["metraje"].mean().sort_values(ascending=False).round(2)
        st.table(rank)

        # Botón Imprimir
        b64 = generar_html_reporte(df_v)
        href = f'<a href="data:text/html;base64,{b64}" download="reporte.html"><button style="width:100%; height:50px; background-color:#4CAF50; color:white; border:none; border-radius:5px;">🚀 GENERAR ENLACE DE IMPRESIÓN</button></a>'
        st.markdown(href, unsafe_allow_html=True)
    else:
        st.info("Aún no hay datos.")

with tab3:
    st.subheader("🔍 Buscar por fecha")
    f_buscar = st.date_input("Selecciona fecha a consultar")
    if st.button("Buscar"):
        conn = sqlite3.connect(DB_NAME)
        res = pd.read_sql_query("SELECT * FROM metrajes WHERE fecha = ?", conn, params=(str(f_buscar),))
        conn.close()
        if not res.empty:
            st.table(res)
        else:
            st.warning("No hay registros para ese día.")
