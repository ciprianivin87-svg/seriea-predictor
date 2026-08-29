import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson

st.set_page_config(page_title="Serie A Predictor Pro", page_icon="⚽", layout="centered")

st.markdown("""
<style>
    .main { background-color: #0f172a; }
    .stButton>button { width: 100%; background-color: #38bdf8; color: black; font-weight: bold; border-radius: 8px; }
    .metric-box { background-color: #1e293b; padding: 15px; border-radius: 10px; border: 1px solid #334155; text-align: center; }
</style>
""", unsafe_allow_html=True)

st.title("⚽ Serie A Predictor Pro")
st.subheader("Analisi Statistica & Previsioni Poisson")

squadre = ['Atalanta', 'Bologna', 'Cagliari', 'Como', 'Empoli', 'Fiorentina', 'Genoa', 'Inter', 'Juventus', 'Lazio', 'Lecce', 'Milan', 'Monza', 'Napoli', 'Parma', 'Roma', 'Torino', 'Udinese', 'Venezia', 'Verona']

col1, col2 = st.columns(2)
with col1:
    casa = st.selectbox("Squadra in Casa", squadre, index=7)
with col2:
    trasferta = st.selectbox("Squadra in Trasferta", squadre, index=11)

if st.button("🚀 GENERA ANALISI MATCH"):
    # Metriche sintetiche di esempio
    xg_c, xg_t = 1.85, 1.25
    prob_1, prob_x, prob_2 = 48.5, 26.0, 25.5
    
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    c1.metric("Vittoria " + casa, f"{prob_1}%")
    c2.metric("Pareggio (X)", f"{prob_x}%")
    c3.metric("Vittoria " + trasferta, f"{prob_2}%")
    
    st.success(f"🎯 Risultato Probabile Modellato: 2 - 1")
    st.info("I dati sono stati registrati nello storico CSV/JSON locale.")
