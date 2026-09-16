import streamlit as st
import pandas as pd
import numpy as np

# Importazione delle funzioni condivise e testate da utils.py
from utils import (
    calcola_pronostico,
    calcola_probabilita_scommesse,
    genera_plotly_heatmap,
    render_form_badges,
    genera_report_gemini
)

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(
    page_title="Champions League Predictor",
    page_icon="🇪🇺",
    layout="wide"
)

st.title("🇪🇺 UEFA Champions League - Predictor & Analisi Tattica")
st.markdown("Analisi predittiva basata sulla distribuzione di Poisson integrata con reportistica tattica generata da intelligenza artificiale.")

# --- DATI STATISTICI SQUADRE CHAMPIONS LEAGUE ---
stats_squadre_cl = {
    "Real Madrid": {"pos": 1, "punti": 3, "gf": 2.00, "ga": 1.00, "form_list": ['W', 'W', 'W', 'D', 'W']},
    "Inter": {"pos": 2, "punti": 0, "gf": 1.00, "ga": 2.00, "form_list": ['L', 'W', 'W', 'D', 'W']},
    "Barcelona": {"pos": 3, "punti": 3, "gf": 5.00, "ga": 1.00, "form_list": ['W', 'W', 'L', 'W', 'W']},
    "Bayern Monaco": {"pos": 4, "punti": 3, "gf": 5.00, "ga": 0.00, "form_list": ['W', 'W', 'W', 'W', 'D']},
    "Manchester City": {"pos": 5, "punti": 3, "gf": 2.00, "ga": 0.00, "form_list": ['W', 'D', 'W', 'W', 'L']},
    "Arsenal": {"pos": 6, "punti": 3, "gf": 1.00, "ga": 0.00, "form_list": ['W', 'W', 'D', 'W', 'D']},
    "PSG": {"pos": 7, "punti": 3, "gf": 6.00, "ga": 1.00, "form_list": ['W', 'D', 'W', 'L', 'W']},
    "Liverpool": {"pos": 8, "punti": 3, "gf": 2.00, "ga": 1.00, "form_list": ['W', 'W', 'W', 'W', 'L']},
    "Napoli": {"pos": 9, "punti": 0, "gf": 0.00, "ga": 1.00, "form_list": ['L', 'W', 'D', 'W', 'W']},
    "Atletico Madrid": {"pos": 10, "punti": 0, "gf": 1.00, "ga": 2.00, "form_list": ['L', 'D', 'W', 'W', 'D']},
    "Borussia Dortmund": {"pos": 11, "punti": 3, "gf": 3.00, "ga": 2.00, "form_list": ['W', 'W', 'L', 'W', 'W']},
    "Bayer Leverkusen": {"pos": 12, "punti": 1, "gf": 0.00, "ga": 0.00, "form_list": ['D', 'W', 'W', 'D', 'W']},
    "Juventus": {"pos": 13, "punti": 1, "gf": 0.00, "ga": 0.00, "form_list": ['D', 'D', 'W', 'D', 'W']},
    "Club Brugge": {"pos": 14, "punti": 0, "gf": 2.00, "ga": 3.00, "form_list": ['L', 'W', 'W', 'D', 'L']},
    "Sporting CP": {"pos": 15, "punti": 3, "gf": 3.00, "ga": 1.00, "form_list": ['W', 'W', 'W', 'W', 'D']},
    "Feyenoord": {"pos": 16, "punti": 0, "gf": 1.00, "ga": 5.00, "form_list": ['L', 'D', 'W', 'D', 'W']},
    "Lens": {"pos": 17, "punti": 3, "gf": 3.00, "ga": 2.00, "form_list": ['W', 'D', 'W', 'W', 'D']},
    "Galatasaray": {"pos": 18, "punti": 0, "gf": 1.00, "ga": 3.00, "form_list": ['L', 'W', 'W', 'D', 'W']},
    "Villarreal": {"pos": 19, "punti": 0, "gf": 2.00, "ga": 3.00, "form_list": ['L', 'W', 'D', 'W', 'L']},
    "RB Leipzig": {"pos": 20, "punti": 0, "gf": 1.00, "ga": 4.00, "form_list": ['L', 'L', 'W', 'W', 'D']},
    "PSV": {"pos": 21, "punti": 1, "gf": 1.00, "ga": 1.00, "form_list": ['D', 'W', 'W', 'W', 'L']},
    "Como": {"pos": 22, "punti": 3, "gf": 4.00, "ga": 1.00, "form_list": ['W', 'W', 'D', 'W', 'D']}
}

# --- CALENDARIO PROGRAMMATO (Partite Reali Fase Unica UCL) ---
calendario_cl = {
    "Giornata 2 (13-14 Ottobre)": [
        ("Inter", "Club Brugge"),
        ("Galatasaray", "Barcelona"),
        ("Arsenal", "Lens"),
        ("Atletico Madrid", "Manchester City"),
        ("Villarreal", "Napoli"),
        ("RB Leipzig", "PSV"),
        ("Feyenoord", "Como")
    ],
    "Giornata 3 (20-21 Ottobre)": [
        ("Real Madrid", "Borussia Dortmund"),
        ("Barcelona", "Bayern Monaco"),
        ("PSG", "Atletico Madrid"),
        ("Liverpool", "Bayer Leverkusen"),
        ("Juventus", "Sporting CP"),
        ("Napoli", "Inter")
    ],
    "Giornata 1 (Risultati recenti)": [
        ("Real Madrid", "Inter"),
        ("Barcelona", "Feyenoord"),
        ("Napoli", "Arsenal"),
        ("Liverpool", "Atletico Madrid"),
        ("Bayern Monaco", "Club Brugge"),
        ("Como", "RB Leipzig")
    ]
}

# --- SELEZIONE GIORNATA E MATCH ---
st.subheader("📅 Calendario & Partite Programmate")
col_giornata, col_partita = st.columns(2)

with col_giornata:
    giornata_sel = st.selectbox("Seleziona la Giornata", list(calendario_cl.keys()), index=0)

partite_giornata = calendario_cl[giornata_sel]
opzioni_partite = [f"{m[0]} vs {m[1]}" for m in partite_giornata]

with col_partita:
    partita_sel = st.selectbox("Seleziona il Match programmato", opzioni_partite, index=0)

# Estrazione delle squadre selezionate
idx_partita = opzioni_partite.index(partita_sel)
casa, trasferta = partite_giornata[idx_partita]

st.divider()

# Recupero dati squadre
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

# --- HEADER RISULTATO E METRICHE CHIAVE ---
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

# --- GRAFICO HEATMAP E TABLE QUOTE ---
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

# --- SEZIONE APPROFONDIMENTI IA (GEMINI 3.6 FLASH) ---
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
