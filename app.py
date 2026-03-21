import streamlit as st
import pandas as pd
from google.oauth2.service_account import Credentials
import gspread
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Control de Metraje Pro", layout="wide")

# --- CONEXIÓN A GOOGLE SHEETS (NUBE PERMANENTE) ---
def conectar_google_sheets():
    try:
        # Extraer credenciales desde Secrets
        info_llaves = dict(st.secrets["gsheets"])
        # Limpiar saltos de línea en la llave privada
        info_llaves["private_key"] = info_llaves["private_key"].replace("\\n", "\n")
        
        scopes = ["https://www.googleapis.com"]
        creds = Credentials.from_service_account_info(info_llaves, scopes=scopes)
        client = gspread.authorize(creds)
        
        # Abrir la hoja por URL (definida en Secrets)
        sheet = client.open_by_url(st.secrets["gsheets"]["spreadsheet"]).sheet1
        return sheet
    except Exception as e:
        st.error(f"❌ Error de conexión: {e}")
        return None

# Inicializar conexión y cargar datos
sheet = conectar_google_sheets()

if sheet:
    # Leer todos los datos de la hoja
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    
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
            # Validar si ya existe el registro en el DataFrame cargado
            fecha_str = str(fecha)
            existe = not df.empty and ((df['fecha'] == fecha_str) & (df['operador'] == operador)).any()
            
            if existe:
                st.error(f"❌ Ya existe un registro para {operador} en la fecha {fecha_str}.")
            else:
                try:
                    valor_redondeado = round(valor, 2)
                    # Insertar fila en Google Sheets: fecha, operador, metraje
                    sheet.append_row([fecha_str, operador, valor_redondeado])
                    st.success(f"✅ Registro guardado en la nube: {operador} - {valor_redondeado:.2f}m")
                    st.rerun() # Recargar para actualizar el reporte
                except Exception as e:
                    st.error(f"Error al guardar: {e}")

    # --- OPCIÓN 2: REPORTES (Tu lógica original adaptada) ---
    elif menu == "📊 Ver Reportes Generales":
        st.subheader("📅 Reporte Mensual Detallado")
        
        if not df.empty:
            # Asegurar que la columna fecha sea string para el filtro
            df['fecha'] = df['fecha'].astype(str)
            mes_actual = datetime.now().strftime("%Y-%m")
            mes_sel = st.text_input("Filtrar por Mes (YYYY-MM):", mes_actual)
            df_filtrado = df[df['fecha'].str.contains(mes_sel)].copy()
            
            if not df_filtrado.empty:
                # 1. TABLA PRINCIPAL
                tabla_pivot = df_filtrado.pivot(index='fecha', columns='operador', values='metraje')
                for col in ["Gabriel", "Adrian", "Freddy"]:
                    if col not in tabla_pivot.columns: tabla_pivot[col] = None
                tabla_final = tabla_pivot[["Gabriel", "Adrian", "Freddy"]]
                
                st.write("### Detalle Diario")
                st.dataframe(tabla_final.style.format("{:.2f}", na_rep="-"), use_container_width=True)
                
                # 2. GRÁFICA
                st.write("---")
                st.write("### 📈 Producción Total del Mes")
                resumen = df_filtrado.groupby("operador")["metraje"].agg(['mean', 'sum', 'count']).sort_values(by='mean', ascending=False)
                resumen.columns = ['Promedio Diario', 'Total Metraje Mes', 'Días Trabajados']
                st.bar_chart(resumen['Total Metraje Mes'])

                # 3. CONSOLIDADO
                st.write("### 📊 Consolidado Mensual")
                st.table(resumen.style.format({'Promedio Diario': '{:.2f}', 'Total Metraje Mes': '{:.2f}', 'Días Trabajados': '{:.0f}'}))

                # 4. EXPORTACIÓN HTML/PDF
                st.write("---")
                st.write("### ⬇️ Exportar Reporte Profesional")
                # (Aquí se mantiene tu bloque de estilo_pdf y html_pro igual...)
                estilo_pdf = "<style>body { font-family: Arial; } table { width: 100%; border-collapse: collapse; } th, td { border: 1px solid #ccc; padding: 8px; }</style>"
                html_pro = f"{estilo_pdf}<h2>REPORTE {mes_sel}</h2>{tabla_final.to_html()}"
                
                st.download_button("📄 Descargar Reporte HTML", data=html_pro, file_name=f"Reporte_{mes_sel}.html", mime="text/html")
            else:
                st.warning("No hay registros para este mes.")
        else:
            st.info("La base de datos en Google Sheets está vacía.")

    # --- OPCIÓN 3: ADMINISTRAR (BORRAR) ---
    elif menu == "🗑️ Administrar Historial":
        st.subheader("Eliminar Registros Recientes")
        if not df.empty:
            # Mostrar los últimos 15 con su número de fila real (index + 2 porque headers es fila 1)
            df_display = df.copy()
            df_display['Fila'] = df_display.index + 2
            st.dataframe(df_display.tail(15), use_container_width=True)
            
            fila_borrar = st.number_input("Número de fila a eliminar", min_value=2, max_value=len(df)+1, step=1)
            if st.button("❌ Eliminar Registro de la Nube", type="primary"):
                sheet.delete_rows(int(fila_borrar))
                st.success(f"Fila {fila_borrar} eliminada.")
                st.rerun()
        else:
            st.info("No hay datos para administrar.")
else:
    st.warning("⚠️ Esperando conexión con Google Sheets... Revisa tus credenciales en Secrets.")
