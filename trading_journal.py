import streamlit as st
import pandas as pd
import sqlite3
import os
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

st.set_page_config(page_title="📊 Journal de Trading - Mr. Chairman", layout="wide")

# Función para inicializar la base de datos
def inicializar_db(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS operaciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT,
        hora TEXT,
        simbolo TEXT,
        tipo TEXT,
        comentario TEXT,
        riesgo_personal REAL,
        entry REAL,
        tp REAL,
        sl REAL,
        pips_win REAL,
        pips_loss REAL,
        ganancia_usd REAL,
        perdida_usd REAL,
        lotaje REAL,
        balance REAL,
        sesion TEXT,
        close REAL,
        resultado REAL,
        archivo TEXT,
        link TEXT,
        hora_cierre TEXT
    )''')
    conn.commit()
    return conn

# Sidebar: gestión de base de datos
st.sidebar.header("📂 Gestión de Journals")
db_files = [f for f in os.listdir() if f.endswith(".db")]
db_file = st.sidebar.selectbox("Selecciona tu Journal", db_files + ["📁 Crear nuevo Journal"])

if db_file == "📁 Crear nuevo Journal":
    nuevo_nombre = st.sidebar.text_input("Nombre del nuevo Journal (sin .db)")
    if nuevo_nombre and st.sidebar.button("Crear Journal"):
        db_file = f"{nuevo_nombre}.db"
        conn = inicializar_db(db_file)
        conn.close()
        st.experimental_rerun()

conn = sqlite3.connect(db_file)
c = conn.cursor()
df = pd.read_sql("SELECT * FROM operaciones", conn)

# Menú de navegación
menu = st.sidebar.radio("Menú", ["Nueva Operación", "Historial", "Dashboard"])

# ------------------- PESTAÑA: NUEVA OPERACIÓN -------------------
if menu == "Nueva Operación":
    st.title("📝 Registrar Nueva Operación")

    if df.empty:
        balance_actual = st.number_input("Balance inicial ($):", value=0.0, format="%.2f")
    else:
        balance_actual = df["balance"].iloc[-1]

    simbolo = st.text_input("Símbolo")
    tipo = st.selectbox("Tipo", ["Long", "Short"])
    fecha = st.date_input("Fecha", value=datetime.today())
    hora = st.time_input("Hora")
    comentario = st.text_area("Comentario")
    riesgo_personal = st.number_input("% Riesgo Personal", min_value=0.0, max_value=100.0, step=0.1)
    entry = st.number_input("Entry Price", format="%.5f")
    tp = st.number_input("Take Profit", format="%.5f")
    sl = st.number_input("Stop Loss", format="%.5f")
    archivo = st.file_uploader("Subir archivo")
    link = st.text_input("Link")

    pips_win = abs(tp - entry) * 10000
    pips_loss = abs(entry - sl) * 10000
    riesgo_usd = (riesgo_personal / 100) * balance_actual
    ganancia_usd = pips_win * (riesgo_usd / pips_loss) if pips_loss != 0 else 0
    perdida_usd = riesgo_usd
    lotaje = riesgo_usd / (pips_loss * 10) if pips_loss != 0 else 0

    st.markdown(f"**Pips Ganancia:** {pips_win:.1f}")
    st.markdown(f"**Pips Pérdida:** {pips_loss:.1f}")
    st.markdown(f"**Ganancia Estimada ($):** {ganancia_usd:.2f}")
    st.markdown(f"**Pérdida Estimada ($):** {perdida_usd:.2f}")
    st.markdown(f"**Lote Recomendado:** {lotaje:.2f}")

    if st.button("Guardar Operación"):
        c.execute('''INSERT INTO operaciones (
            fecha, hora, simbolo, tipo, comentario, riesgo_personal, entry, tp, sl,
            pips_win, pips_loss, ganancia_usd, perdida_usd, lotaje, balance,
            sesion, close, resultado, archivo, link, hora_cierre
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, ?, ?, NULL)''',
        (fecha.strftime("%Y-%m-%d"), hora.strftime("%H:%M:%S"), simbolo, tipo, comentario, riesgo_personal,
         entry, tp, sl, pips_win, pips_loss, ganancia_usd, perdida_usd, lotaje, balance_actual,
         archivo.name if archivo else "", link))
        conn.commit()
        st.success("✅ Operación guardada exitosamente.")

# ------------------- PESTAÑA: HISTORIAL -------------------
elif menu == "Historial":
    st.title("📜 Historial de Operaciones")
    if df.empty:
        st.warning("No hay operaciones registradas todavía.")
    else:
        df['fecha'] = pd.to_datetime(df['fecha'])
        fecha_inicio = st.date_input("Desde", value=df['fecha'].min())
        fecha_fin = st.date_input("Hasta", value=df['fecha'].max())
        df_filtrado = df[(df['fecha'] >= pd.to_datetime(fecha_inicio)) & (df['fecha'] <= pd.to_datetime(fecha_fin))]
        st.dataframe(df_filtrado, use_container_width=True)

        st.download_button("📥 Exportar historial", df_filtrado.to_csv(index=False).encode('utf-8'), "historial_operaciones.csv")

        st.subheader("✏️ Actualizar Operación")
        seleccion_id = st.selectbox("Seleccionar ID de operación:", df_filtrado["id"].tolist())

        if seleccion_id:
            operacion = df[df["id"] == seleccion_id].iloc[0]
            nuevo_entry = st.number_input("Nuevo Entry", value=float(operacion["entry"]), format="%.5f")
            nuevo_close = st.number_input("Nuevo Close", value=float(operacion["close"]) if not pd.isnull(operacion["close"]) else 0.0, format="%.5f")
            nuevo_hora_cierre = st.text_input("Hora de Cierre", value=operacion["hora_cierre"] if "hora_cierre" in operacion else "")
            nuevo_comentario = st.text_area("Comentario actualizado", value=operacion["comentario"])
            nuevo_archivo = st.file_uploader("Actualizar archivo")
            nuevo_link = st.text_input("Actualizar link", value=operacion["link"] if "link" in operacion else "")

            tipo = operacion["tipo"]
            sl = operacion["sl"]
            balance = operacion["balance"]
            riesgo_personal = operacion["riesgo_personal"]

            pips = (nuevo_close - nuevo_entry) * 10000 if tipo == "Long" else (nuevo_entry - nuevo_close) * 10000
            riesgo_usd = (riesgo_personal / 100) * balance
            resultado = pips * (riesgo_usd / (abs(nuevo_entry - sl) * 10000)) if (nuevo_entry - sl) != 0 else 0

            if st.button("Actualizar Operación"):
                nuevo_balance = balance + resultado
                c.execute('''UPDATE operaciones SET entry=?, close=?, resultado=?, balance=?, comentario=?, archivo=?, link=?, hora_cierre=? WHERE id=?''',
                          (nuevo_entry, nuevo_close, resultado, nuevo_balance, nuevo_comentario,
                           nuevo_archivo.name if nuevo_archivo else operacion["archivo"], nuevo_link, nuevo_hora_cierre, seleccion_id))
                conn.commit()
                st.success("✅ Operación actualizada correctamente.")

# ------------------- PESTAÑA: DASHBOARD -------------------
elif menu == "Dashboard":
    st.title("📊 Dashboard General")
    if df.empty:
        st.warning("No hay datos disponibles.")
    else:
        df['fecha'] = pd.to_datetime(df['fecha'])
        df['mes'] = df['fecha'].dt.to_period("M")
        df['dia'] = df['fecha'].dt.day_name()

        st.header(f"💰 Balance General: ${df['balance'].iloc[-1]:,.2f}")

        # Panel de métricas principales
        col1, col2, col3, col4 = st.columns(4)
        total_pnl = df['resultado'].sum()
        pf = df[df['resultado'] > 0]['resultado'].sum() / abs(df[df['resultado'] < 0]['resultado'].sum()) if not df[df['resultado'] < 0].empty else 0
        avg_win = df[df['resultado'] > 0]['resultado'].mean()
        avg_loss = df[df['resultado'] < 0]['resultado'].mean()
        col1.metric("💵 Total P&L", f"${total_pnl:.2f}")
        col2.metric("📈 Profit Factor", f"{pf:.2f}")
        col3.metric("🟢 Promedio Trade Ganador", f"${avg_win:.2f}")
        col4.metric("🔴 Promedio Trade Perdedor", f"${avg_loss:.2f}")

        # Gráfico evolución balance USD
        fig_balance = go.Figure()
        fig_balance.add_trace(go.Scatter(
            x=df['fecha'], y=df['balance'], mode='lines+markers', name="Balance USD"
        ))
        fig_balance.update_layout(title="📈 Evolución del Balance (USD)", template="plotly_dark", height=450)
        st.plotly_chart(fig_balance, use_container_width=True)

        # Gráfico Ganancia mensual en porcentaje
        df_month = df.groupby('mes')['resultado'].sum().reset_index()
        df_month['resultado_pct'] = (df_month['resultado'] / df['balance'].iloc[0]) * 100

        fig_month = go.Figure()
        fig_month.add_trace(go.Bar(
            x=df_month['mes'].astype(str),
            y=df_month['resultado_pct'].astype(int),
            marker_color=['green' if x >= 0 else 'red' for x in df_month['resultado_pct']]
        ))
        fig_month.update_layout(title="📅 Ganancia Mensual (%)", template="plotly_dark", height=350)
        st.plotly_chart(fig_month, use_container_width=True)

        # Gráficos secundarios
        col5, col6 = st.columns(2)
        win_trades = len(df[df['resultado'] > 0])
        loss_trades = len(df[df['resultado'] < 0])

        fig_winrate = make_subplots(rows=1, cols=2, specs=[[{"type": "domain"}, {"type": "domain"}]])
        fig_winrate.add_trace(go.Pie(values=[win_trades, loss_trades], labels=['Ganadoras', 'Perdedoras'], hole=.7, marker_colors=['green', 'red']), 1, 1)
        fig_winrate.add_trace(go.Pie(values=[win_trades, loss_trades], labels=['Ganadoras', 'Perdedoras'], hole=.7, marker_colors=['green', 'red']), 1, 2)
        fig_winrate.update_layout(title="🎯 Winrate General", template="plotly_dark")
        col5.plotly_chart(fig_winrate, use_container_width=True)

        popular_symbols = df['simbolo'].value_counts().head(5)
        fig_popular = go.Figure(go.Pie(labels=popular_symbols.index, values=popular_symbols.values, hole=.6))
        fig_popular.update_layout(title="🥧 Popularidad por Par", template="plotly_dark")
        col6.plotly_chart(fig_popular, use_container_width=True)

        # Métricas avanzadas
        st.subheader("📋 Métricas Avanzadas")
        total_lotes = df['lotaje'].sum()
        best_trade = df['resultado'].max()
        worst_trade = df['resultado'].min()
        st.metric("🔢 Total de Trades", str(len(df)))
        st.metric("📦 Lotes Totales", f"{total_lotes:.2f}")
        st.metric("🏆 Mejor Trade", f"${best_trade:.2f}")

        st.dataframe({
            'Métrica': ["Mejor Trade", "Peor Trade", "Avg Win", "Avg Loss"],
            'Valor ($)': [best_trade, worst_trade, avg_win, avg_loss]
        })

