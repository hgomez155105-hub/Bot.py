import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
import numpy as np
import ccxt

# --- ⚙️ CONFIGURACIÓN MAESTRA (LOGIN INTACTO - NO TOCAR) ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1nYyINRPF-cIiAMsKInTxaO6wdptsitVfZnFq-o1Wo1Y/export?format=csv"

def verificar_acceso(u_ingresado, p_ingresado):
    try:
        df = pd.read_csv(SHEET_URL)
        df.columns = df.columns.str.strip().str.lower()
        u_test = str(u_ingresado).strip()
        p_test = str(p_ingresado).strip()
        match = df[(df['usuario'].astype(str).str.strip() == u_test) & 
                   (df['clave'].astype(str).str.strip() == p_test)]
        
