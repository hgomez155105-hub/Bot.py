import streamlit as st
import pandas as pd
import requests
import time
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="AI Scalper Pro Mac", layout="wide")

# CSS: Letras blancas, fondo verde militar, sin azul
st.markdown("""
    <style>
    .stApp { background-color: #4B5320 !important; }
    h1, h2, h3, p, span, label { color: #FFFFFF !important; font-weight: 800 !important; }
    
    /* Métricas Blancas */
    [data-testid="stMetricValue"] { color: #FFFFFF !important; font-size: 2.2rem !important; font-weight: 800; }
    [data-testid="stMetricLabel"] { color: #FFFFFF !important; font-size: 1.1rem !important; }
    
    /* Cajas de métricas */
    div[data-testid="metric-container"] { 
        background-color: rgba(0,0,0,0.3); 
        border: 2px solid #FFFFFF; 
        border-radius: 12px; 
        padding: 15px;
    }

    /* Estilo de alertas (reemplaza el azul) */
    .stAlert { background-color: #353b16 !important; border: 1px solid #FFF !important; }
    .stAlert p { color: #FFF !important; }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACIÓN ---
if 'saldo' not in st.session_state:
    st.session_state.update({
        'saldo':
