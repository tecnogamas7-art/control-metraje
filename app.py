import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
import os
from datetime import datetime

# --- CONFIGURACIÓN DE SEGURIDAD (CONEXIÓN GOOGLE) ---
def conectar_google_sheets():
    try:
        # Definir permisos
        scope = ['https://www.googleapis.com', "https://www.googleapis.com"]
        
        # Cargar credenciales desde los Secrets de Streamlit
        # Asegúrate de haber pegado el JSON con las comillas ''' en Advanced Settings
        service_account_info = json.loads(os.environ.get('GOOGLE_CREDENTIALS'))
        creds = Credentials.from_service_account_info(service_account_info, scopes=scope)
        client = gspread.authorize(creds)
        
        # IMPORTANTE: El nombre del Excel en Drive debe ser EXACTO a este:
        return client.open("Registro Metrajes").sheet1 
    except Exception as e:
        st.error(f"❌ Error de conexión: {e}")
        return None

sheet = conectar_google_sheets()

# --- CONFIGURACIÓN DE INTERFAZ ---
st.set_page_config(page_title="Control de Metraje Pro", layout="wide")
st.title("🚀 Sistema de Control de Metraje (Nube)")

if sheet:
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
                # Guardar fila en Google Sheets: fecha, operador, metraje
                nueva_fila = [str(fecha), operador, round(valor, 2)]
                sheet.append_row(nueva_fila)
                st.success(f"✅ Guardado en Google Sheets: {operador} - {valor:.2f}m")
            except Exception as e:
                st.error(f"❌ Error al guardar: {e}")

    # --- OPCIÓN 2: REPORTES ---
    elif menu == "📊 Ver Reportes Generales":
        st.subheader("📅 Reporte Mensual Detallado")
        
        # Obtener todos los datos de la nube
        registros = sheet.get_all_records()
        df = pd.DataFrame(registros)
        
        if not df.empty:
            # Asegurar que el metraje sea numérico
            df['metraje'] = pd.to_numeric(df['metraje'], errors='coerce')
            
            mes_actual = datetime.now().strftime("%Y-%m")
            mes_sel = st.text_input("Filtrar por Mes (YYYY-MM):", mes_actual)
            df_filtrado = df[df['fecha'].str.contains(mes_sel)].copy()
            
            if not df_filtrado.empty:
                # Tabla Pivot para ver por columnas de operador
                tabla_pivot = df_filtrado.pivot_table(index='fecha', columns='operador', values='metraje', aggfunc='sum')
                st.write("### Detalle Diario")
                st.dataframe(tabla_pivot.style.format("{:.2f}", na_rep="-"), use_container_width=True)
                
                # Gráfica
                st.write("### 📈 Producción Total del Mes")
                resumen = df_filtrado.groupby("operador")["metraje"].agg(['mean', 'sum', 'count'])
                resumen.columns = ['Promedio Diario', 'Total Mes', 'Días']
                st.bar_chart(resumen['Total Mes'])
                
                st.write("### 📊 Consolidado")
                st.table(resumen.style.format({'Promedio Diario': '{:.2f}', 'Total Mes': '{:.2f}'}))
            else:
                st.warning("No hay datos para este mes.")
        else:
            st.info("La hoja de cálculo está vacía.")

    # --- OPCIÓN 3: ADMINISTRAR (BORRAR) ---
    elif menu == "🗑️ Administrar Historial":
        st.subheader("Eliminar Últimos Registros")
        registros = sheet.get_all_records()
        if registros:
            df_admin = pd.DataFrame(registros)
            # Mostramos los últimos 10 (Google Sheets no tiene ID automático como SQLite)
            st.write("Últimos registros detectados:")
            st.dataframe(df_admin.tail(10))
            
            fila_borrar = st.number_input("Número de fila a borrar (La fila 2 es el primer registro)", min_value=2)
            if st.button("❌ Eliminar Fila Seleccionada", type="primary"):
                sheet.delete_rows(int(fila_borrar))
                st.success(f"Fila {fila_borrar} eliminada correctamente.")
                st.rerun()
        else:
            st.info("No hay nada que borrar.")

else:
    st.warning("⚠️ Esperando conexión con Google Sheets... Revisa tus credenciales en Secrets.")
