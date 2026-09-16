import streamlit as st
import pandas as pd
import numpy as np

# Importiamo le funzioni condivise da utils.py
from utils import (
    calcola_pronostico,
    calcola_probabilita_scommesse,
    genera_plotly_heatmap,
    render_form_badges,
    genera_report_gemini
)

# Configurazione della pagina
st.set_page_config(
    page_title="Predictor Champions League",
    page_icon="🇪🇺",
    layout="wide"
)

st.title("🇪🇺 UEFA Champions League - Predictor & Analisi Tattica")
st.markdown("Analisi predittiva basata sulla distribuzione di Poisson integrata con reportistica tattica generata da intelligenza artificiale.")

# --- DATI E STATISTICHE SQUADRE (Esempio/Mockup o caricati da dati reali) ---
# Assicurati che i dizionari contengano le chiavi pos, punti, gf, ga e form_list
stats_squadre_cl = {
    "Real Madrid": {"pos": 1, "punti": 15, "gf": 2.4, "ga": 0.8, "form_list": ['W', 'W', 'D', 'W', 'W']},
    "Manchester City": {"pos": 2, "punti": 13, "gf": 2.6, "ga": 1.0, "form_list": ['W', 'D', 'W', 'W', 'L']},
    "Bayern Monaco": {"pos": 3, "punti": 12, "gf": 2.2, "ga": 0.9, "form_list": ['W', 'W', 'L', 'W', 'W']},
    "Inter": {"pos": 4, "punti": 12, "gf": 1.8, "ga": 0.6, "form_list": ['W', 'W', 'W', 'D', 'W']},
    "PSG": {"pos": 5, "punti": 10, "gf": 2.0, "ga": 1.1, "form_list": ['D', 'W', 'W', 'L', 'W']},
    "Barcelona": {"pos": 6, "punti": 10, "gf": 2.3, "ga": 1.2, "form_list": ['W', 'L', 'W', 'W', 'D']},
}

squadre = sorted(list(stats_squadre_cl.keys()))

# --- SELEZIONE PARTITA ---
col_sel1, col_sel2 = st.columns(2)

with col_sel1:
    squadra_casa = st.selectbox("Squadra in Casa (1)", squadre, index=0)

with col_sel2:
    squadre_trasferta = [s for s in squadre if s != squadra_casa]
    squadra_trasferta = st.selectbox("Squadra in Trasferta (2)", squadre_trasferta, index=0)

st.divider()

# Recupero dati squadre selezionate
st_c = stats_squadre_cl[squadra_casa]
st_t = stats_squadre_cl[squadra_trasferta]

# --- CALCOLO PRONOSTICO POISSON ---
prob_1, prob_x, prob_2, g_c_pred, g_t_pred, prob_exact, exp_c, exp_t, matrice = calcola_pronostico(
    gf_c=st_c['gf'],
    ga_c=st_c['ga'],
    form_c=st_c['form_list'],
    gf_t=st_t['gf'],
    ga_t=st_t['ga'],
    form_t=st_t['form_list']
)

# --- HEADER SQUADRE E METRICHE CHIAVE ---
col_h1, col_hx, col_h2 = st.columns([2, 1, 2])

with col_h1:
    st.subheader(f"🏠 {squadra_casa}")
    st.markdown(f"**Forma recente:** {render_form_badges(st_c['form_list'])}", unsafe_allow_html=True)
    st.metric("Probabilità Vittoria", f"{prob_1:.1f}%")

with col_hx:
    st.markdown("<h3 style='text-align: center; margin-top: 25px;'>VS</h3>", unsafe_allow_html=True)
    st.metric("Pareggio (X)", f"{prob_x:.1f}%")
    st.markdown(f"<p style='text-align: center; font-weight: bold;'>Risultato Atteso: {g_c_pred} - {g_t_pred}</p>", unsafe_allow_html=True)

with col_h2:
    st.subheader(f"🚀 {squadra_trasferta}")
    st.markdown(f"**Forma recente:** {render_form_badges(st_t['form_list'])}", unsafe_allow_html=True)
    st.metric("Probabilità Vittoria", f"{prob_2:.1f}%")

st.divider()

# --- TABELLA QUOTE ED HEATMAP ---
col_tab1, col_tab2 = st.columns([1, 1])

with col_tab1:
    st.markdown("### 📊 Mercati & Quote Eque")
    df_scommesse = calcola_probabilita_scommesse(matrice, prob_1, prob_x, prob_2)
    st.dataframe(df_scommesse, use_container_width=True, hide_index=True)

with col_tab2:
    st.markdown("### 🎯 Matrice Risultati Esatti")
    fig_heatmap = genera_plotly_heatmap(matrice, squadra_casa, squadra_trasferta)
    st.plotly_chart(fig_heatmap, use_container_width=True)

st.divider()

# --- SEZIONE APPROFONDIMENTI IA (GEMINI) ---
st.markdown("### 🧠 Approfondimenti IA (Analisi Tattica)")

with st.spinner("Generazione del report tattico con Gemini AI..."):
    report_ia = genera_report_gemini(
        squadra_casa=squadra_casa,
        squadra_trasferta=squadra_trasferta,
        st_c=st_c,
        st_t=st_t,
        prob_1=prob_1,
        prob_x=prob_x,
        prob_2=prob_2,
        g_c=g_c_pred,
        g_t=g_t_pred
    )

st.info(report_ia)
