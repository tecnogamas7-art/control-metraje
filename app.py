import pandas as pd
import sqlite3
import os
from datetime import datetime

DB_NAME = "registro_metrajes.db"

def inicializar_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS metrajes 
                        (fecha TEXT, operador TEXT, metraje REAL, UNIQUE(fecha, operador))''')

def limpiar_pantalla():
    os.system('cls' if os.name == 'nt' else 'clear')

def exportar_excel():
    with sqlite3.connect(DB_NAME) as conn:
        df = pd.read_sql_query("SELECT * FROM metrajes ORDER BY fecha DESC", conn)
    if not df.empty:
        # Formateamos la fecha para que el Excel sea más legible
        df.to_excel("Reporte_Metrajes.xlsx", index=False)
        print(f"\n✅ Reporte generado: Reporte_Metrajes.xlsx ({len(df)} registros)")
    else:
        print("\n⚠️ No hay datos para exportar.")

inicializar_db()

while True:
    print("\n" + "🚀 SISTEMA DE REGISTRO DE METRAJE ".center(60, "="))
    print(" 1: Gabriel | 2: Adrian | 3: Freddy | B: Borrar | E: Excel | 0: Salir")
    print("-" * 60)
    
    op = input("\nSeleccione una opción: ").upper()
    nombres = {"1": "Gabriel", "2": "Adrian", "3": "Freddy"}
    
    if op == "0": 
        print("Saliendo del sistema...")
        break
    
    conn = sqlite3.connect(DB_NAME)

    if op == "E":
        exportar_excel()
        input("\nPresiona Enter para continuar...")
        limpiar_pantalla()
        continue

    if op == "B":
        ultimos = pd.read_sql_query("SELECT rowid, * FROM metrajes ORDER BY rowid DESC LIMIT 5", conn)
        if not ultimos.empty:
            print("\n🗑️ ÚLTIMOS 5 REGISTROS:")
            for i, fila in ultimos.iterrows():
                print(f"{i+1}. {fila['operador']} | {fila['metraje']}m | {fila['fecha']}")
            
            try:
                sel = int(input("\nNúmero de registro a eliminar (0 cancelar): "))
                if 0 < sel <= len(ultimos):
                    id_borrar = ultimos.iloc[sel-1]['rowid']
                    conn.execute("DELETE FROM metrajes WHERE rowid = ?", (int(id_borrar),))
                    conn.commit()
                    print("✅ Eliminado correctamente.")
            except ValueError: print("⚠️ Entrada no válida.")
        else: print("No hay datos para borrar.")

    elif op in nombres:
        try:
            print(f"\n--- Registrando a {nombres[op]} ---")
            fecha_input = input(f"Fecha (YYYY-MM-DD o Enter para hoy {datetime.now().date()}): ")
            fecha_sel = fecha_input if fecha_input else str(datetime.now().date())
            
            valor = float(input(f"Metraje alcanzado: "))
            conn.execute("INSERT INTO metrajes VALUES (?, ?, ?)", (fecha_sel, nombres[op], valor))
            conn.commit()
            print("✅ Guardado con éxito.")
        except sqlite3.IntegrityError:
            print(f"❌ Error: {nombres[op]} ya tiene un registro en la fecha {fecha_sel}.")
        except ValueError: print("⚠️ Error: El metraje debe ser un número (ej: 150.5).")

    # --- VISUALIZACIÓN DE DATOS ACTUALIZADOS ---
    df = pd.read_sql_query("SELECT * FROM metrajes ORDER BY fecha DESC", conn)
    conn.close()
    
    if not df.empty:
        print("\n" + "📋 RESUMEN DE ACTIVIDAD ".center(40, "-"))
        # Tabla resumen (Pivoteada para comparar operadores)
        df_pivot = df.pivot(index='fecha', columns='operador', values='metraje').fillna(0)
        print(df_pivot.tail(10)) # Muestra los últimos 10 días registrados
        
        print("\n" + "📈 PROMEDIOS Y RENDIMIENTO ".center(40, "-"))
        promedios = df.groupby("operador")["metraje"].mean()
        for nombre, valor in promedios.items():
            barra = "█" * int(valor / 10) # Crea una barra visual simple
            print(f"{nombre.ljust(8)} | {valor:6.2f}m | {barra}")
            
    input("\nPresiona Enter para refrescar el menú...")
    limpiar_pantalla()
