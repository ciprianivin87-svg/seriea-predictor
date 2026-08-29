import streamlit as st
import pandas as pd
import numpy as np
import requests
import json
import re
from bs4 import BeautifulSoup
from scipy.stats import poisson

st.set_page_config(page_title="Serie A Predictor Understat", page_icon="⚽", layout="centered")

# Visual Styling
st.markdown("""
<style>
    .main { background-color: #0f172a; }
    .stButton>button { width: 100%; background-color: #38bdf8; color: black; font-weight: bold; border-radius: 8px; padding: 10px; }
    .stSelectbox label { color: #f8fafc !important; font-weight: bold; }
    .player-card {
        background-color: #1e293b;
        border-left: 4px solid #38bdf8;
        padding: 8px 12px;
        margin-bottom: 6px;
        border-radius: 6px;
    }
    .player-name { font-weight: bold; color: #f8fafc; font-size: 13px; }
    .player-stat { color: #94a3b8; font-size: 11px; }
</style>
""", unsafe_allow_html=True)

# --- SCRAPING DIRECT FROM UNDERSTAT ---
@st.cache_data(ttl=7200)  # Aggiorna la cache ogni 2 ore
def get_understat_data():
    url = "https://understat.com/league/Serie_A"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        scripts = soup.find_all('script')
        
        teams_data = {}
        players_data = {}
        
        # Estrazione dati JSON integrati nello script HTML di Understat
        for script in scripts:
            if script.string:
                if 'teamsData' in script.string:
                    match = re.search(r"JSON\.parse\('([^']+)'\)", script.string)
                    if match:
                        raw_data = match.group(1).encode('utf-8').decode('unicode-escape')
                        teams_raw = json.loads(raw_data)
                        
                        for t_id, t_info in teams_raw.items():
                            team_name = t_info['title']
                            history = t_info['history']
                            
                            tot_xg = sum(float(x['xG']) for x in history)
                            tot_xga = sum(float(x['xGA']) for x in history)
                            games = max(1, len(history))
                            
                            teams_data[team_name] = {
                                'xG_fatti': round(tot_xg / games, 2),
                                'xGA_subiti': round(tot_xga / games, 2)
                            }

                if 'playersData' in script.string:
                    match = re.search(r"JSON\.parse\('([^']+)'\)", script.string)
                    if match:
                        raw_data = match.group(1).encode('utf-8').decode('unicode-escape')
                        players_raw = json.loads(raw_data)
                        
                        for p in players_raw:
                            t_name = p['team_title']
                            if t_name not in players_data:
                                players_data[t_name] = []
                            
                            if len(players_data[t_name]) < 3:  # Prendi i primi 3 giocatori chiave
                                time_played = max(1, int(p['time']))
                                xg_90 = (float(p['xG']) / time_played) * 90
                                xa_90 = (float(p['xA']) / time_played) * 90
                                
                                players_data[t_name].append({
                                    'nome': p['player_name'],
                                    'stat': f"xG/90: {xg_90:.2f} | xA/90: {xa_90:.2f} | Gol: {p['goals']}"
                                })
                                
        return teams_data, players_data, True
    except Exception:
        return {}, {}, False

# --- ENGINE PRINCIPALE ---
st.title("⚽ Serie A Understat Engine")
st.caption("Analisi basata su Web Scraping in tempo reale da Understat.com")

teams_data, players_data, is_live = get_understat_data()

if is_live and teams_data:
    st.sidebar.success("🟢 Connesso a Understat (xG Reali)")
    squadre = sorted(list(teams_data.keys()))
else:
    st.sidebar.error("🔴 Errore scraping Understat: verificare la connessione.")
    squadre = []

if squadre:
    col1, col2 = st.columns(2)
    with col1:
        casa = st.selectbox("Squadra CASA", squadre, index=0)
    with col2:
        trasferta = st.selectbox("Squadra TRASFERTA", squadre, index=min(1, len(squadre)-1))

    if casa == trasferta:
        st.warning("⚠️ Seleziona due squadre diverse.")
    else:
        if st.button("🚀 ELABORA PRONOSTICO & GIOCATORI"):
            d_c = teams_data[casa]
            d_t = teams_data[trasferta]

            # Algoritmo Poisson
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
            prob_top = matrice_p[g_c, g_t]

            # Output Esiti
            st.markdown("---")
            st.subheader("📊 Probabilità Calcolate dagli xG di Understat")
            c1, c2, c3 = st.columns(3)
            c1.metric(f"Vittoria {casa}", f"{prob_1:.1f}%")
            c2.metric("Pareggio (X)", f"{prob_x:.1f}%")
            c3.metric(f"Vittoria {trasferta}", f"{prob_2:.1f}%")

            st.success(f"🎯 Risultato Probabile Modellato: **{casa} {g_c} - {g_t} {trasferta}** ({prob_top:.1f}% di probabilità)")

            # Top Scorer / Giocatori da Understat
            st.markdown("---")
            st.subheader("⭐ Top Giocatori & Metriche Avanzate (Understat)")
            
            cg1, cg2 = st.columns(2)
            with cg1:
                st.markdown(f"**🏠 {casa}**")
                for p in players_data.get(casa, []):
                    st.markdown(f"""
                    <div class="player-card">
                        <div class="player-name">👤 {p['nome']}</div>
                        <div class="player-stat">📊 {p['stat']}</div>
                    </div>
                    """, unsafe_allow_html=True)

            with cg2:
                st.markdown(f"**✈️ {trasferta}**")
                for p in players_data.get(trasferta, []):
                    st.markdown(f"""
                    <div class="player-card">
                        <div class="player-name">👤 {p['nome']}</div>
                        <div class="player-stat">📊 {p['stat']}</div>
                    </div>
                    """, unsafe_allow_html=True)
