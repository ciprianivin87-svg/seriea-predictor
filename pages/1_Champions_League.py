import streamlit as st
import pandas as pd
import numpy as np

# Importazione delle funzioni condivise da utils.py
from utils import (
    calcola_pronostico,
    calcola_probabilita_scommesse,
    genera_plotly_heatmap,
    render_form_badges,
    get_team_key_players,
    estrai_formazioni_match,
    genera_report_gemini
)

# Configurazione della pagina
st.set_page_config(
    page_title="Champions League Predictor",
    page_icon="🇪🇺",
    layout="wide"
)

st.title("🇪🇺 UEFA Champions League - Predictor & Analisi Tattica")
st.markdown("Analisi predittiva basata sulla distribuzione di Poisson integrata con reportistica tattica generata da intelligenza artificiale.")

# --- DATI E STATISTICHE SQUADRE CHAMPIONS LEAGUE ---
stats_squadre_cl = {
    "Real Madrid": {"pos": 1, "punti": 15, "gf": 2.40, "ga": 0.80, "form_list": ['W', 'W', 'D', 'W', 'W']},
    "Manchester City": {"pos": 2, "punti": 13, "gf": 2.60, "ga": 1.00, "form_list": ['W', 'D', 'W', 'W', 'L']},
    "Bayern Monaco": {"pos": 3, "punti": 12, "gf": 2.20, "ga": 0.90, "form_list": ['W', 'W', 'L', 'W', 'W']},
    "Inter": {"pos": 4, "punti": 12, "gf": 1.80, "ga": 0.60, "form_list": ['W', 'W', 'W', 'D', 'W']},
    "PSG": {"pos": 5, "punti": 10, "gf": 2.00, "ga": 1.10, "form_list": ['D', 'W', 'W', 'L', 'W']},
    "Barcelona": {"pos": 6, "punti": 10, "gf": 2.30, "ga": 1.20, "form_list": ['W', 'L', 'W', 'W', 'D']},
    "Arsenal": {"pos": 7, "punti": 10, "gf": 1.90, "ga": 0.70, "form_list": ['W', 'W', 'D', 'W', 'L']},
    "Bayer Leverkusen": {"pos": 8, "punti": 9, "gf": 2.10, "ga": 1.30, "form_list": ['D', 'W', 'W', 'D', 'W']},
    "Juventus": {"pos": 9, "punti": 8, "gf": 1.50, "ga": 0.80, "form_list": ['D', 'D', 'W', 'D', 'W']},
    "Atalanta": {"pos": 10, "punti": 8, "gf": 2.00, "ga": 1.20, "form_list": ['W', 'W', 'L', 'W', 'D']}
}

squadre = sorted(list(stats_squadre_cl.keys()))

# --- SELEZIONE PARTITA ---
st.subheader("⚽ Seleziona la Sfida")
col_sel1, col_sel2 = st.columns(2)

with col_sel1:
    casa = st.selectbox("Squadra in Casa (1)", squadre, index=0)

with col_sel2:
    squadre_trasferta = [s for s in squadre if s != casa]
    trasferta = st.selectbox("Squadra in Trasferta (2)", squadre_trasferta, index=0)

st.divider()

# Recupero dati e statistiche delle squadre
st_casa = stats_squadre_cl[casa]
st_trasf = stats_squadre_cl[trasferta]

# --- CALCOLO PRONOSTICO POISSON ---
prob_1, prob_x, prob_2, g_c, g_t, prob_exact, exp_c, exp_t, matrice_p = calcola_pronostico(
    gf_c=st_casa['gf'],
    ga_c=st_casa['ga'],
    form_c=st_casa['form_list'],
    gf_t=st_trasf['gf'],
    ga_t=st_trasf['ga'],
    form_t=st_trasf['form_list']
)

# --- HEADER RISULTATO E METRICHE ---
col_h1, col_hx, col_h2 = st.columns([2, 1, 2])

with col_h1:
    st.subheader(f"🏠 {casa}")
    st.markdown(f"**Forma recente:** {render_form_badges(st_casa['form_list'])}", unsafe_allow_html=True)
    st.metric("Probabilità Vittoria", f"{prob_1:.1f}%")

with col_hx:
    st.markdown("<h3 style='text-align: center; margin-top: 20px;'>VS</h3>", unsafe_allow_html=True)
    st.metric("Pareggio (X)", f"{prob_x:.1f}%")
    st.markdown(f"<h4 style='text-align: center; color: #00FF66;'>{g_c} - {g_t}</h4>", unsafe_allow_html=True)
    st.caption(f"Probabilità risultato esatto: {prob_exact:.1f}%")

with col_h2:
    st.subheader(f"🚀 {trasferta}")
    st.markdown(f"**Forma recente:** {render_form_badges(st_trasf['form_list'])}", unsafe_allow_html=True)
    st.metric("Probabilità Vittoria", f"{prob_2:.1f}%")

st.divider()

# --- GRAFICO HEATMAP E QUOTE SCOMMESSE ---
col_tab1, col_tab2 = st.columns([1, 1])

with col_tab1:
    st.markdown("### 📊 Mercati & Quote Eque")
    df_scommesse = calcola_probabilita_scommesse(matrice_p, prob_1, prob_x, prob_2)
    st.dataframe(df_scommesse, use_container_width=True, hide_index=True)

with col_tab2:
    st.markdown("### 🎯 Matrice Risultati Esatti")
    fig_heatmap = genera_plotly_heatmap(matrice_p, casa, trasferta)
    st.plotly_chart(fig_heatmap, use_container_width=True)

st.divider()

# --- SEZIONE APPROFONDIMENTI IA (GEMINI) ---
st.markdown("### 🧠 Approfondimenti IA (Analisi Tattica)")

with st.spinner("Generazione dell'analisi tattica in corso con Gemini..."):
    report_ia = genera_report_gemini(
        casa,
        trasferta,
        st_casa,
        st_trasf,
        prob_1,
        prob_x,
        prob_2,
        g_c,
        g_t
    )

st.markdown(report_ia)
