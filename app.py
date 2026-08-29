import streamlit as st
import pandas as pd
import numpy as np
import requests
import json
import re
from bs4 import BeautifulSoup
from scipy.stats import poisson

st.set_page_config(page_title="Serie A Predictor Pro", page_icon="⚽", layout="centered")

# Visual Styling CSS (Sintetico)
st.markdown("""
<style>
    .main { background-color: #0f172a; }
    .stButton>button { width: 100%; background-color: #38bdf8; color: black; font-weight: bold; border-radius: 8px; padding: 10px; }
    .stSelectbox label { color: #f8fafc !important; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# METRICHE xG DI RISERVA (Per garantire il funzionamento offline)
DATI_LOCALI = {
    'Atalanta': {'xG_fatti': 1.90, 'xGA_subiti': 1.15},
    'Bologna': {'xG_fatti': 1.35, 'xGA_subiti': 1.10},
    'Cagliari': {'xG_fatti': 1.00, 'xGA_subiti': 1.40},
    'Como': {'xG_fatti': 1.45, 'xGA_subiti': 1.25},
    'Fiorentina': {'xG_fatti': 1.45, 'xGA_subiti': 1.20},
    'Frosinone': {'xG_fatti': 1.05, 'xGA_subiti': 1.50},
    'Genoa': {'xG_fatti': 1.10, 'xGA_subiti': 1.25},
    'Inter': {'xG_fatti': 2.10, 'xGA_subiti': 0.80},
    'Juventus': {'xG_fatti': 1.70, 'xGA_subiti': 0.85},
    'Lazio': {'xG_fatti': 1.50, 'xGA_subiti': 1.15},
    'Lecce': {'xG_fatti': 0.95, 'xGA_subiti': 1.40},
    'Milan': {'xG_fatti': 1.85, 'xGA_subiti': 1.10},
    'Monza': {'xG_fatti': 1.10, 'xGA_subiti': 1.35},
    'Napoli': {'xG_fatti': 1.75, 'xGA_subiti': 0.95},
    'Parma': {'xG_fatti': 1.25, 'xGA_subiti': 1.45},
    'Roma': {'xG_fatti': 1.60, 'xGA_subiti': 1.00},
    'Sassuolo': {'xG_fatti': 1.20, 'xGA_subiti': 1.45},
    'Torino': {'xG_fatti': 1.15, 'xGA_subiti': 1.10},
    'Udinese': {'xG_fatti': 1.15, 'xGA_subiti': 1.30},
    'Venezia': {'xG_fatti': 0.95, 'xGA_subiti': 1.70}
}

# FETCHING xG DA UNDERSTAT CON FALLBACK
@st.cache_data(ttl=3600)
def fetch_understat_live():
    url = "https://understat.com/league/Serie_A"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept-Language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7'
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            soup = BeautifulSoup(res.content, 'html.parser')
            scripts = soup.find_all('script')
            
            teams_data = {}
            for script in scripts:
                if script.string and 'teamsData' in script.string:
                    match = re.search(r"JSON\.parse\('([^']+)'\)", script.string)
                    if match:
                        raw = match.group(1).encode('utf-8').decode('unicode-escape')
                        teams_raw = json.loads(raw)
                        
                        for _, t_info in teams_raw.items():
                            t_name = t_info['title']
                            history = t_info['history']
                            games = max(1, len(history))
                            tot_xg = sum(float(x['xG']) for x in history)
                            tot_xga = sum(float(x['xGA']) for x in history)
                            
                            teams_data[t_name] = {
                                'xG_fatti': round(tot_xg / games, 2),
                                'xGA_subiti': round(tot_xga / games, 2)
                            }
            if teams_data:
                return teams_data, True
    except Exception:
        pass
    
    return DATI_LOCALI, False

# INTERFACCIA E LOGICA PRONOSTICO
st.title("⚽ Serie A Analytics Engine")
st.caption("Modello Statistici di Poisson basato su Expected Goals (xG)")

dati_squadre, is_live = fetch_understat_live()

if is_live:
    st.sidebar.success("🟢 xG aggiornati in tempo reale (Understat)")
else:
    st.sidebar.info("🔵 xG da database locale attivo")

squadre = sorted(list(dati_squadre.keys()))

col1, col2 = st.columns(2)
with col1:
    casa = st.selectbox("Squadra CASA", squadre, index=squadre.index('Inter') if 'Inter' in squadre else 0)
with col2:
    trasferta = st.selectbox("Squadra TRASFERTA", squadre, index=squadre.index('Milan') if 'Milan' in squadre else min(1, len(squadre)-1))

if casa == trasferta:
    st.warning("⚠️ Seleziona due squadre diverse per analizzare il match.")
else:
    if st.button("🚀 CALCOLA PRONOSTICO"):
        d_c = dati_squadre[casa]
        d_t = dati_squadre[trasferta]

        # Calcolo Poisson
        lambda_casa = (d_c['xG_fatti'] + d_t['xGA_subiti']) / 2
        lambda_trasferta = (d_t['xG_fatti'] + d_c['xGA_subiti']) / 2

        matrice_p = np.zeros((6, 6))
        for i in range(6):
            for j in range(6):
                matrice_p[i, j] = poisson.pmf(i, lambda_casa) * poisson.pmf(j, lambda_trasferta) * 100

        prob_1 = np.sum(np.tril(matrice_p, -1))
        prob_x = np.sum(np.diag(matrice_p))
        prob_2 = np.sum(np.triu(matrice_p, 1))

        g_c, g_t = np.unravel_index(np.argmax(matrice_p), matrice_p.shape)
        prob_risultato_top = matrice_p[g_c, g_t]

        # Output Risultati
        st.markdown("---")
        st.subheader("📊 Probabilità Esito 1X2")
        c1, c2, c3 = st.columns(3)
        c1.metric(f"Vittoria {casa}", f"{prob_1:.1f}%")
        c2.metric("Pareggio (X)", f"{prob_x:.1f}%")
        c3.metric(f"Vittoria {trasferta}", f"{prob_2:.1f}%")

        st.success(f"🎯 Risultato Esatto Modellato: **{casa} {g_c} - {g_t} {trasferta}** ({prob_risultato_top:.1f}% di probabilità)")
