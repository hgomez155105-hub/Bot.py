import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
import ccxt

# ============================
# INICIALIZACIÓN DE SESSION_STATE
# ============================
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

if 'user_name' not in st.session_state:
    st.session_state.user_name = "Invitado"

for key in ["precios_hist", "ordenes_malla", "posiciones", "eventos", "historial_pnl"]:
    if key not in st.session_state:
        st.session_state[key] = []

# ============================
# FUNCIÓN DE CONEXIÓN A PIONEX (CORREGIDA)
# ============================
def conectar_pionex(api_key, secret_key):
    try:
        exchange = ccxt.pionex({
            'apiKey': api_key,
            'secret': secret_key,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot'
            }
        })
        markets = exchange.load_markets()
        if not markets:
            raise Exception("No se pudieron cargar los mercados de Pionex.")
        return exchange
    except Exception as e:
        st.error(f"Error conectando a Pionex: {e}")
        return None

# ============================
# TOP 20 PARES
# ============================
def obtener_top_20_pionex():
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr"
        res = requests.get(url).json()
        df_vol = pd.DataFrame(res)
        df_vol = df_vol[df_vol['symbol'].str.endswith('USDT')]
        df_vol['quoteVolume'] = df_vol['quoteVolume'].astype(float)
        top_20 = df_vol.sort_values(by='quoteVolume', ascending=False).head(20)
        return [f"{s[:-4]}/USDT" for s in top_20['symbol']]
    except:
        return ["BTC/USDT", "ETH/USDT", "SOL/USDT", "FET/USDT"]

# ============================
# CONFIGURACIÓN DE ACCESO (GOOGLE SHEETS)
# ============================
SHEET_URL = "https://docs.google.com/spreadsheets/d/1nYyINRPF-cIiAMsKInTxaO6wdptsitVfZnFq-o1Wo1Y/export?format=csv"

def verificar_acceso(u, p):
    try:
        df = pd.read_csv(SHEET_URL)
        df.columns = df.columns.str.strip().str.lower()
        match = df[
            (df['usuario'].astype(str).str.strip() == str(u).strip()) &
            (df['clave'].astype(str).str.strip() == str(p).strip())
        ]
        return not match.empty
    except:
        return False

# ============================
# CONFIGURACIÓN GENERAL
# ============================
LOGO_URL = "https://raw.githubusercontent.com/hgomez155105-hub/Bot.py/main/1000266017.png"

st.set_page_config(
    page_title="Bot T800",
    page_icon="🤖",
    layout="wide"
)

# ============================
# LOOP (corregido)
# ============================
try:
    delay = 5  # segundos
    time.sleep(delay)
    st.rerun()
except Exception as e:
    st.error(f"Error: {e}")
    time.sleep(3)
    st.rerun()
else:
    st.info("Bot T800 apagado. Activá el algoritmo para iniciar el escaneo táctico.")

# ============================
# FUNCIÓN RSI
# ============================
def calcular_rsi(series, period=14):
    if len(series) < period:
        return np.nan
    deltas = np.diff(series)
    seed = deltas[:period]
    up = seed[seed >= 0].sum() / period
    down = -seed[seed < 0].sum() / period
    rs = up / down if down != 0 else 0
    return 100 - (100 / (1 + rs))

# ============================
# GRÁFICO TÁCTICO T800
# ============================
st.markdown("### 📈 Gráfico Táctico T800 (Precio, RSI, Niveles, TP, Ejecuciones)")

precios = st.session_state.precios_hist
ordenes = st.session_state.ordenes_malla
posiciones = st.session_state.posiciones
eventos = st.session_state.eventos

if len(precios) > 1:
    fig = go.Figure()

    # Línea de precio
    fig.add_trace(go.Scatter(
        x=list(range(len(precios))),
        y=precios,
        name="Precio",
        mode="lines",
        line=dict(color="#F0B90B", width=3)
    ))

    # Precio actual
    fig.add_hline(
        y=precios[-1],
        line=dict(color="white", width=1.5, dash="solid"),
        annotation_text="Precio actual",
        annotation_position="top right"
    )

    # RSI
    rsi_series = [calcular_rsi(precios[:i]) for i in range(2, len(precios) + 1)]
    fig.add_trace(go.Scatter(
        x=list(range(2, len(precios) + 1)),
        y=rsi_series,
        name="RSI",
        mode="lines",
        yaxis="y2",
        line=dict(color="purple", width=1, dash="dot")
    ))

    # Niveles de malla
    for o in ordenes:
        fig.add_hline(
            y=o["precio"],
            line=dict(color="cyan", width=1, dash="dash"),
            annotation_text=f"Nivel {o['id']} ({o['dir']})",
            annotation_position="top left"
        )

    # TP de posiciones abiertas
    for pos in posiciones:
        fig.add_hline(
            y=pos["tp_precio"],
            line=dict(color="green", width=1, dash="dot"),
            annotation_text=f"TP {pos['id_orden']}",
            annotation_position="bottom left"
        )

    # Eventos
    for ev in eventos:
        color_ev = "lime" if ev["tipo"].startswith("APERTURA") else "red"
        fig.add_trace(go.Scatter(
            x=[len(precios) - 1],
            y=[ev["precio"]],
            mode="markers+text",
            marker=dict(size=10, color=color_ev, symbol="x"),
            text=[f"{ev['tipo']} {ev['id_orden']}"],
            textposition="top center",
            name=f"{ev['tipo']} {ev['id_orden']}"
        ))

    fig.update_layout(
        height=450,
        template="plotly_dark",
        margin=dict(l=0, r=0, b=0, t=0),
        showlegend=True,
        yaxis=dict(title="Precio", side="left", color="#3E4F1F"),
        yaxis2=dict(title="RSI", overlaying="y", side="right", range=[0, 100], color="#3E4F1F")
    )

    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("Esperando datos de precio para dibujar el gráfico...")

# ============================
# TABLAS
# ============================
st.subheader("📋 Malla de Operación (Órdenes abiertas)")
if st.session_state.ordenes_malla:
    st.dataframe(pd.DataFrame(st.session_state.ordenes_malla), use_container_width=True)
else:
    st.write("Sin órdenes en malla por el momento.")

st.subheader("📌 Posiciones abiertas")
if st.session_state.posiciones:
    st.dataframe(pd.DataFrame(st.session_state.posiciones), use_container_width=True)
else:
    st.write("Sin posiciones abiertas.")

st.subheader("📜 Historial de PnL")
if st.session_state.historial_pnl:
    df_hist = pd.DataFrame(st.session_state.historial_pnl)
    st.dataframe(df_hist.tail(50), use_container_width=True)
else:
    st.write("Sin operaciones cerradas aún.")
