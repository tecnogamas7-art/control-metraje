import streamlit as st
import pandas as pd
from datetime import datetime
import pytz

# Configuración de la página para móvil
st.set_page_config(page_title="Control de Metraje", layout="centered")

# --- ESTILO VISUAL (CORREGIDO) ---
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        height: 3em;
        background-color: #007bff;
        color: white;
        font-weight: bold;
        border: none;
    }
    .stDataFrame { background-color: white; border-radius: 10px; }
    h1 { color: #1e3a8a; text-align: center; font-size: 24px; }
    </style>
    """, unsafe_allow_html=True)

st.title("Registrador de Metraje 📏")

# --- LÓGICA DE DATOS ---
# Creamos un archivo temporal para guardar los datos mientras la app esté abierta
if 'datos' not in st.session_state:
    st.session_state.datos = pd.DataFrame(columns=["Fecha/Hora", "Metraje (m)", "Operador"])

# --- FORMULARIO DE ENTRADA ---
with st.container():
    st.subheader("Nuevo Registro")
    metraje = st.number_input("Metraje actual:", min_value=0.0, step=0.1, format="%.1f")
    operador = st.text_input("Nombre del Operador:", placeholder="Ej. Juan Pérez")
    
    if st.button("Guardar Registro 💾"):
        if operador:
            # Obtener hora local (ajusta 'America/Bogota' según tu zona)
            zona_horaria = pytz.timezone('America/Bogota')
            ahora = datetime.now(zona_horaria).strftime("%d/%m/%Y %H:%M")
            
            # Añadir nueva fila
            nueva_fila = pd.DataFrame({"Fecha/Hora": [ahora], "Metraje (m)": [metraje], "Operador": [operador]})
            st.session_state.datos = pd.concat([st.session_state.datos, nueva_fila], ignore_index=True)
            st.success("¡Guardado correctamente!")
        else:
            st.error("Por favor, pon el nombre del operador.")

# --- VISUALIZACIÓN ---
st.divider()
st.subheader("Registros del Turno")

if not st.session_state.datos.empty:
    # Mostrar tabla
    st.dataframe(st.session_state.datos, use_container_width=True)
    
    # Botón para descargar a Excel/CSV
    csv = st.session_state.datos.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Descargar Reporte (CSV) 📥",
        data=csv,
        file_name=f"metraje_{datetime.now().strftime('%d_%m_%Y')}.csv",
        mime="text/csv",
    )
else:
    st.info("Aún no hay datos registrados.")

# Pie de página
st.caption("App optimizada para uso en celular.")
