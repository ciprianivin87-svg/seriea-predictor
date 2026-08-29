import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson

st.set_page_config(page_title="Serie A Predictor Pro", page_icon="⚽", layout="centered")

# Styling CSS per mobile
st.markdown("""
<style>
    .main { background-color: #0f172a; }
    .stButton>button { width: 100%; background-color: #38bdf8; color: black; font-weight: bold; border-radius: 8px; padding: 10px; }
    .stSelectbox label { color: #f8fafc !important; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# 1. DATABASE METRICHE REALI SQUADRE (xG fatti, xGA subiti e Possesso)
dati_squadre = {
    'Inter': {'xG_fatti': 2.05, 'xGA_subiti': 0.80, 'possesso': 58.4},
    'Juventus': {'xG_fatti': 1.70, 'xGA_subiti': 0.85, 'possesso': 52.8},
    'Milan': {'xG_fatti': 1.85, 'xGA_subiti': 1.10, 'possesso': 54.2},
    'Napoli': {'xG_fatti': 1.75, 'xGA_subiti': 0.95, 'possesso': 56.1},
    'Atalanta': {'xG_fatti': 1.90, 'xGA_subiti': 1.15, 'possesso': 53.5},
    'Roma': {'xG_fatti': 1.55, 'xGA_subiti': 1.05, 'possesso': 51.0},
    'Lazio': {'xG_fatti': 1.50, 'xGA_subiti': 1.15, 'possesso': 50.5},
    'Fiorentina': {'xG_fatti': 1.45, 'xGA_subiti': 1.20, 'possesso': 52.0},
    'Bologna': {'xG_fatti': 1.35, 'xGA_subiti': 1.10, 'possesso': 53.0},
    'Torino': {'xG_fatti': 1.15, 'xGA_subiti': 1.10, 'possesso': 47.5},
    'Genoa': {'xG_fatti': 1.10, 'xGA_subiti': 1.25, 'possesso': 45.0},
    'Monza': {'xG_fatti': 1.10, 'xGA_subiti': 1.35, 'possesso': 46.2},
    'Udinese': {'xG_fatti': 1.15, 'xGA_subiti': 1.30, 'possesso': 44.8},
    'Cagliari': {'xG_fatti': 1.00, 'xGA_subiti': 1.40, 'possesso': 43.5},
    'Parma': {'xG_fatti': 1.25, 'xGA_subiti': 1.45, 'possesso': 47.0},
    'Lecce': {'xG_fatti': 0.95, 'xGA_subiti': 1.40, 'possesso': 42.0},
    'Verona': {'xG_fatti': 1.00, 'xGA_subiti': 1.45, 'possesso': 41.5},
    'Empoli': {'xG_fatti': 0.90, 'xGA_subiti': 1.40, 'possesso': 43.0},
    'Como': {'xG_fatti': 1.10, 'xGA_subiti': 1.50, 'possesso': 48.0},
    'Venezia': {'xG_fatti': 0.95, 'xGA_subiti': 1.75, 'possesso': 41.0}
}

squadre = sorted(list(dati_squadre.keys()))

st.title("⚽ Serie A Analytics Engine")
st.caption("Modello Matematico di Poisson basato su Expected Goals (xG)")

col1, col2 = st.columns(2)
with col1:
    casa = st.selectbox("Squadra CASA", squadre, index=squadre.index('Inter'))
with col2:
    trasferta = st.selectbox("Squadra TRASFERTA", squadre, index=squadre.index('Milan'))

if casa == trasferta:
    st.warning("⚠️ Seleziona due squadre diverse per analizzare il match.")
else:
    if st.button("🚀 CALCOLA PROBABILITÀ REALISTICHE"):
        d_c = dati_squadre[casa]
        d_t = dati_squadre[trasferta]

        # CALCOLO DINAMICO LAMBDA (xG attesi per lo scontro specifico)
        lambda_casa = (d_c['xG_fatti'] + d_t['xGA_subiti']) / 2
        lambda_trasferta = (d_t['xG_fatti'] + d_c['xGA_subiti']) / 2

        # MATRICE PROBABILITÀ POISSON (fino a 5 gol a squadra)
        matrice_p = np.zeros((6, 6))
        for i in range(6):
            for j in range(6):
                matrice_p[i, j] = poisson.pmf(i, lambda_casa) * poisson.pmf(j, lambda_trasferta) * 100

        # Calcolo Esito 1X2 reale
        prob_1 = np.sum(np.tril(matrice_p, -1))
        prob_x = np.sum(np.diag(matrice_p))
        prob_2 = np.sum(np.triu(matrice_p, 1))

        # Risultato Esatto con la percentuale più alta nella matrice
        g_c, g_t = np.unravel_index(np.argmax(matrice_p), matrice_p.shape)
        prob_risultato_top = matrice_p[g_c, g_t]

        st.markdown("---")
        st.subheader("📊 Probabilità Esito 1X2")
        c1, c2, c3 = st.columns(3)
        c1.metric(f"Vittoria {casa}", f"{prob_1:.1f}%")
        c2.metric("Pareggio (X)", f"{prob_x:.1f}%")
        c3.metric(f"Vittoria {trasferta}", f"{prob_2:.1f}%")

        st.markdown("---")
        st.subheader("🎯 Risultato Esatto Modellato")
        st.success(f"**{casa} {g_c} - {g_t} {trasferta}** (Probabilità Statistica: **{prob_risultato_top:.1f}%**)")

        st.markdown("---")
        st.subheader("📈 Dettagli Tecnici")
        col_a, col_b = st.columns(2)
        col_a.write(f"• **xG Attesi {casa}:** {lambda_casa:.2f}")
        col_a.write(f"• **Possesso Palla:** {d_c['possesso']}%")
        col_b.write(f"• **xG Attesi {trasferta}:** {lambda_trasferta:.2f}")
        col_b.write(f"• **Possesso Palla:** {d_t['possesso']}%")
