def generar_html_reporte(df):
    df['fecha_dt'] = pd.to_datetime(df['fecha'])
    u_mes = df['fecha_dt'].iloc[0].strftime('%B')
    u_anio = df['fecha_dt'].iloc[0].year
    mes_titulo = f"{MESES_ES.get(u_mes, u_mes)} {u_anio}"
    
    # 1. Tabla Historial
    tabla_hist = df.pivot(index='fecha', columns='operador', values='metraje').sort_index(ascending=False).fillna("X").reset_index()
    
    # 2. Ranking de Promedios (CORREGIDO: Sin columna 'operador' repetida si prefieres solo los valores)
    mes_filtro = df['fecha_dt'].iloc[0].strftime('%m-%Y')
    df['m_a'] = df['fecha_dt'].dt.strftime('%m-%Y')
    proms = df[df['m_a'] == mes_filtro].groupby('operador')['metraje'].mean().round(2).sort_values(ascending=False).reset_index()

    html = f"""
    <html><head><meta charset='UTF-8'><style>
    body {{ font-family: sans-serif; text-align: center; padding: 20px; color: #333; }}
    table {{ border-collapse: collapse; width: 90%; margin: 20px auto; }}
    th, td {{ border: 1px solid #333; padding: 10px; text-align: center; }}
    th {{ background-color: #f2f2f2; text-transform: uppercase; }}
    h2, h3 {{ color: #2c3e50; }}
    .firma {{ margin-top: 80px; border-top: 2px solid #000; width: 250px; margin-left: auto; margin-right: auto; padding-top: 10px; font-weight: bold; }}
    </style></head><body>
    <h2>REPORTE MENSUAL DE METRAJES</h2>
    <h4>CORRESPONDIENTE A: {mes_titulo}</h4>
    <br>
    <h3>1. HISTORIAL DE DÍAS</h3>
    {tabla_hist.to_html(index=False)}
    <br>
    <h3>2. RANKING DE PROMEDIOS</h3>
    <table>
        <thead><tr><th>NOMBRE</th><th>PROMEDIO DIARIO (m)</th></tr></thead>
        <tbody>
            {''.join([f"<tr><td>{r['operador']}</td><td>{r['metraje']} m</td></tr>" for _, r in proms.iterrows()])}
        </tbody>
    </table>
    <div class='firma'>FIRMA AUTORIZADA</div>
    </body></html>
    """
    return base64.b64encode(html.encode('utf-8')).decode('utf-8')
