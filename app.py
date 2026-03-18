import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import pytz

# Configuración de la App para Celular
st.set_page_config(
    page_title="Control Metraje",
    page_icon="📏",
    layout="centered"
)

# Estilo personalizado para botones grandes y colores
st.markdown("""
    <style>
    div.stButton > button:first-child {
        width: 100%;
        height: 3em;
        background-color: #007bff;
        color: white;
        font-size: 18px;
        font-weight: bold;
        border-radius: 10px;
    }
    .main {
        background-color: #f8f9fa;
    }
    </style>
    """, unsafe_allow_stdio=True)

ZONA_HORARIA = pytz.timezone('America/Bogota')
DB_NAME = "metrajes_movil.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    conn.execute('''CREATE TABLE IF NOT EXISTS metrajes 
                    (fecha TEXT, operador TEXT, metraje REAL, UNIQUE(fecha, operador))''')
    conn.commit()
    return conn

# --- CABECERA ---
st.title("📏 Control de Metraje")
st.write(f"📅 Hoy es: **{datetime.now(ZONA_HORARIA).strftime('%d/%m/%Y')}**")

# --- FORMULARIO DE REGISTRO (Optimizado para pulgar) ---
with st.container():
    st.subheader("📝 Nuevo Registro")
    fecha_sel = st.date_input("Seleccionar Fecha", datetime.now(ZONA_HORARIA))
    op_sel = st.selectbox("Operador", ["Gabriel", "Adrian", "Freddy"])
    valor_metraje = st.number_input("Metraje ingresado (m)", min_value=0.0, step=0.1, format="%.1f")
    
    if st.button("💾 GUARDAR REGISTRO"):
        try:
            conn = init_db()
            conn.execute("INSERT INTO metrajes VALUES (?, ?, ?)", (str(fecha_sel), op_sel, valor_metraje))
            conn.commit()
            st.success(f"✅ ¡Guardado! {op_sel}: {valor_metraje}m")
        except:
            st.error("❌ Ya existe un registro para esta fecha.")

st.divider()

# --- VISUALIZACIÓN DE DATOS ---
conn = init_db()
df = pd.read_sql_query("SELECT * FROM metrajes ORDER BY fecha DESC", conn)

if not df.empty:
    # Ranking Visual (Barras de mayor a menor)
    st.subheader("🏆 Ranking del Mes")
    ranking = df.groupby("operador")["metraje"].mean().sort_values(ascending=False).round(2)
    st.bar_chart(ranking)

    # Historial Táctil
    st.subheader("📋 Historial Reciente")
    tabla = df.pivot(index='fecha', columns='operador', values='metraje').fillna("-")
    st.dataframe(tabla, use_container_width=True)
    
    # Buscador Rápido
    with st.expander("🔍 Buscar fecha específica"):
        f_busqueda = st.date_input("Ver datos del día:", datetime.now(ZONA_HORARIA))
        res = df[df['fecha'] == str(f_busqueda)]
        if not res.empty:
            st.table(res[['operador', 'metraje']])
        else:
            st.write("No hay datos para este día.")

    # Exportar
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Descargar Reporte (CSV)", csv, "metraje.csv", "text/csv")
else:
    st.info("No hay datos registrados aún. ¡Empieza ahora!")

