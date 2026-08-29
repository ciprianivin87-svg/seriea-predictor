import streamlit as st
import pandas as pd
import numpy as np
import requests
from scipy.stats import poisson

st.set_page_config(page_title="Serie A Predictor Pro Live", page_icon="⚽", layout="centered")

# Visual Styling
st.markdown("""
<style>
    .main { background-color: #0f172a; }
    .stButton>button { width: 100%; background-color: #38bdf8; color: black; font-weight: bold; border-radius: 8px; padding: 10px; }
    .stSelectbox label { color: #f8fafc !important; font-weight: bold; }
    .player-card {
        background-color: #1e293b;
        border-left: 4px solid #38bdf8;
        padding: 10px 12px;
        margin-bottom: 8px;
        border-radius: 6px;
    }
    .player-name { font-weight: bold; color: #f8fafc; font-size: 14px; }
    .player-stat { color: #94a3b8; font-size: 12px; }
</style>
""", unsafe_allow_html=True)

# --- GESTIONE DATI LIVE E FETCHING DAL WEB ---
API_KEY = "INSERISCI_LA_TUA_API_KEY_QUI" # Inserisci la tua chiave di football-data.org
SERIE_A_ID = "SA"

@st.cache_data(ttl=3600)  # Aggiorna la cache del web ogni ora per non saturare le chiamate API
def fetch_live_standings():
    headers = {'X-Auth-Token': API_KEY}
    url = f"https://api.football-data.org/v4/competitions/{SERIE_A_ID}/standings"
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            table = data['standings'][0]['table']
            
            # Formattazione dati dinamici per le 20 squadre
            squadre_dict = {}
            for row in table:
                nome = row['team']['name']
                partite = max(1, row['playedGames'])
                gol_fatti = row['goalsFor'] / partite
                gol_subiti = row['goalsAgainst'] / partite
                
                squadre_dict[nome] = {
                    'xG_fatti': round(gol_fatti, 2),
                    'xGA_subiti': round(gol_subiti, 2),
                    'punti': row['points'],
                    'forma': row.get('form', 'N/A')
                }
            return squadre_dict, True
    except Exception:
        pass
    
    # Dati di riserva (Fallback) in caso di assenza API Key o timeout rete
    fallback_data = {
        'Inter': {'xG_fatti': 2.10, 'xGA_subiti': 0.80, 'punti': 45},
        'Juventus': {'xG_fatti': 1.70, 'xGA_subiti': 0.85, 'punti': 40},
        'Milan': {'xG_fatti': 1.85, 'xGA_subiti': 1.10, 'punti': 38},
        'Napoli': {'xG_fatti': 1.75, 'xGA_subiti': 0.95, 'punti': 37},
        'Atalanta': {'xG_fatti': 1.90, 'xGA_subiti': 1.15, 'punti': 35},
        'Roma': {'xG_fatti': 1.60, 'xGA_subiti': 1.00, 'punti': 33},
        'Lazio': {'xG_fatti': 1.50, 'xGA_subiti': 1.15, 'punti': 31},
        'Fiorentina': {'xG_fatti': 1.45, 'xGA_subiti': 1.20, 'punti': 30},
        'Bologna': {'xG_fatti': 1.35, 'xGA_subiti': 1.10, 'punti': 28},
        'Torino': {'xG_fatti': 1.15, 'xGA_subiti': 1.10, 'punti': 25},
        'Genoa': {'xG_fatti': 1.10, 'xGA_subiti': 1.25, 'punti': 24},
        'Como': {'xG_fatti': 1.45, 'xGA_subiti': 1.25, 'punti': 22},
        'Udinese': {'xG_fatti': 1.15, 'xGA_subiti': 1.30, 'punti': 21},
        'Monza': {'xG_fatti': 1.10, 'xGA_subiti': 1.35, 'punti': 20},
        'Parma': {'xG_fatti': 1.25, 'xGA_subiti': 1.45, 'punti': 19},
        'Cagliari': {'xG_fatti': 1.00, 'xGA_subiti': 1.40, 'punti': 18},
        'Lecce': {'xG_fatti': 0.95, 'xGA_subiti': 1.40, 'punti': 17},
        'Sassuolo': {'xG_fatti': 1.20, 'xGA_subiti': 1.45, 'punti': 16},
        'Frosinone': {'xG_fatti': 1.05, 'xGA_subiti': 1.50, 'punti': 15},
        'Venezia': {'xG_fatti': 0.95, 'xGA_subiti': 1.70, 'punti': 14}
    }
    return fallback_data, False

# --- UI & LOGICA APPLICAZIONE ---
st.title("⚽ Serie A Predictor Engine")
st.caption("Algoritmo di Poisson collegato a statistiche web in tempo reale")

dati_squadre, is_live = fetch_live_standings()

if is_live:
    st.sidebar.success("🟢 Dati Web aggiornati in tempo reale")
else:
    st.sidebar.info("🟡 Modalità offline / Dati memorizzati locali")

squadre = sorted(list(dati_squadre.keys()))

col1, col2 = st.columns(2)
with col1:
    casa = st.selectbox("Squadra CASA", squadre, index=0)
with col2:
    trasferta = st.selectbox("Squadra TRASFERTA", squadre, index=min(1, len(squadre)-1))

if casa == trasferta:
    st.warning("⚠️ Seleziona due squadre diverse per l'analisi.")
else:
    if st.button("🚀 ELABORA PRONOSTICO DINAMICO"):
        d_c = dati_squadre[casa]
        d_t = dati_squadre[trasferta]

        # Calcolo Expected Goals (xG attesi per lo scontro)
        lambda_casa = (d_c['xG_fatti'] + d_t['xGA_subiti']) / 2
        lambda_trasferta = (d_t['xG_fatti'] + d_c['xGA_subiti']) / 2

        # Calcolo Poisson 6x6
        matrice_p = np.zeros((6, 6))
        for i in range(6):
            for j in range(6):
                matrice_p[i, j] = poisson.pmf(i, lambda_casa) * poisson.pmf(j, lambda_trasferta) * 100

        prob_1 = np.sum(np.tril(matrice_p, -1))
        prob_x = np.sum(np.diag(matrice_p))
        prob_2 = np.sum(np.triu(matrice_p, 1))

        g_c, g_t = np.unravel_index(np.argmax(matrice_p), matrice_p.shape)
        prob_top = matrice_p[g_c, g_t]

        # UI Risultati
        st.markdown("---")
        st.subheader("📊 Probabilità Calcolate sui Dati Web")
        c1, c2, c3 = st.columns(3)
        c1.metric(f"Vittoria {casa}", f"{prob_1:.1f}%")
        c2.metric("Pareggio (X)", f"{prob_x:.1f}%")
        c3.metric(f"Vittoria {trasferta}", f"{prob_2:.1f}%")

        st.success(f"🎯 Risultato Probabile Modellato: **{casa} {g_c} - {g_t} {trasferta}** ({prob_top:.1f}% di probabilità)")

        st.markdown("---")
        st.subheader("📈 Metriche di Formato Web Utilizzate")
        ca, cb = st.columns(2)
        ca.write(f"• **Media Gol Fatti ({casa}):** {d_c['xG_fatti']:.2f}")
        ca.write(f"• **Media Gol Subiti ({casa}):** {d_c['xGA_subiti']:.2f}")
        cb.write(f"• **Media Gol Fatti ({trasferta}):** {d_t['xG_fatti']:.2f}")
        cb.write(f"• **Media Gol Subiti ({trasferta}):** {d_t['xGA_subiti']:.2f}")
