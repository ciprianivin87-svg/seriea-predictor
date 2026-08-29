import streamlit as st
import pandas as pd
import numpy as np
import requests
import json
import re
from bs4 import BeautifulSoup
from scipy.stats import poisson

st.set_page_config(page_title="Serie A Predictor Pro", page_icon="⚽", layout="centered")

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

# Database di riserva immediato (garantisce il funzionamento anche se Cloudflare blocca le richieste)
FALLBACK_TEAMS = {
    'Atalanta': {'xG_fatti': 1.90, 'xGA_subiti': 1.15},
    'Bologna': {'xG_fatti': 1.35, 'xGA_subiti': 1.10},
    'Cagliari': {'xG_fatti': 1.00, 'xGA_subiti': 1.40},
    'Como': {'xG_fatti': 1.45, 'xGA_subiti': 1.25},
    'Fiorentina': {'xG_fatti': 1.45, 'xGA_subiti': 1.20},
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
    'Torino': {'xG_fatti': 1.15, 'xGA_subiti': 1.10},
    'Udinese': {'xG_fatti': 1.15, 'xGA_subiti': 1.30},
    'Venezia': {'xG_fatti': 0.95, 'xGA_subiti': 1.70}
}

FALLBACK_PLAYERS = {
    'Inter': [{'nome': 'Lautaro Martinez', 'stat': 'xG/90: 0.65 | xA/90: 0.20'}, {'nome': 'H. Calhanoglu', 'stat': 'xG/90: 0.35 | xA/90: 0.30'}],
    'Juventus': [{'nome': 'Dusan Vlahovic', 'stat': 'xG/90: 0.58 | xA/90: 0.12'}, {'nome': 'Kenan Yildiz', 'stat': 'xG/90: 0.30 | xA/90: 0.25'}],
    'Milan': [{'nome': 'Christian Pulisic', 'stat': 'xG/90: 0.45 | xA/90: 0.28'}, {'nome': 'Rafael Leao', 'stat': 'xG/90: 0.40 | xA/90: 0.35'}],
    'Napoli': [{'nome': 'Romelu Lukaku', 'stat': 'xG/90: 0.52 | xA/90: 0.25'}, {'nome': 'K. Kvaratskhelia', 'stat': 'xG/90: 0.42 | xA/90: 0.30'}],
    'Atalanta': [{'nome': 'Mateo Retegui', 'stat': 'xG/90: 0.62 | xA/90: 0.15'}, {'nome': 'Ademola Lookman', 'stat': 'xG/90: 0.48 | xA/90: 0.32'}]
}

@st.cache_data(ttl=3600)
def get_understat_data():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5'
    }
    url = "https://understat.com/league/Serie_A"
    
    try:
        session = requests.Session()
        response = session.get(url, headers=headers, timeout=8)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            scripts = soup.find_all('script')
            
            teams_data = {}
            players_data = {}
            
            for script in scripts:
                if script.string and 'teamsData' in script.string:
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
                
                if script.string and 'playersData' in script.string:
                    match = re.search(r"JSON\.parse\('([^']+)'\)", script.string)
                    if match:
                        raw_data = match.group(1).encode('utf-8').decode('unicode-escape')
                        players_raw = json.loads(raw_data)
                        
                        for p in players_raw:
                            t_name = p['team_title']
                            if t_name not in players_data:
                                players_data[t_name] = []
                            if len(players_data[t_name]) < 2:
                                time_played = max(1, int(p['time']))
                                xg_90 = (float(p['xG']) / time_played) * 90
                                xa_90 = (float(p['xA']) / time_played) * 90
                                players_data[t_name].append({
                                    'nome': p['player_name'],
                                    'stat': f"xG/90: {xg_90:.2f} | xA/90: {xa_90:.2f}"
                                })
            
            if teams_data:
                return teams_data, players_data, True
    except Exception:
        pass
        
    return FALLBACK_TEAMS, FALLBACK_PLAYERS, False

# --- UI & ELABORAZIONE ---
st.title("⚽ Serie A Predictor Engine")
st.caption("Modello di Poisson basato sulle metriche xG")

teams_data, players_data, is_live = get_understat_data()

if is_live:
    st.sidebar.success("🟢 Dati aggiornati live da Understat")
else:
    st.sidebar.warning("🟡 Modalità Protetta: Uso metriche stimate locali")

squadre = sorted(list(teams_data.keys()))

col1, col2 = st.columns(2)
with col1:
    casa = st.selectbox("Squadra CASA", squadre, index=squadre.index('Inter') if 'Inter' in squadre else 0)
with col2:
    trasferta = st.selectbox("Squadra TRASFERTA", squadre, index=squadre.index('Milan') if 'Milan' in squadre else 1)

if casa == trasferta:
    st.warning("⚠️ Seleziona due squadre diverse.")
else:
    if st.button("🚀 ELABORA PRONOSTICO & GIOCATORI"):
        d_c = teams_data[casa]
        d_t = teams_data[trasferta]

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

        st.markdown("---")
        st.subheader("📊 Probabilità Esito 1X2")
        c1, c2, c3 = st.columns(3)
        c1.metric(f"Vittoria {casa}", f"{prob_1:.1f}%")
        c2.metric("Pareggio (X)", f"{prob_x:.1f}%")
        c3.metric(f"Vittoria {trasferta}", f"{prob_2:.1f}%")

        st.success(f"🎯 Risultato Esatto Modellato: **{casa} {g_c} - {g_t} {trasferta}** ({prob_top:.1f}% probabilità)")

        st.markdown("---")
        st.subheader("⭐ Giocatori Chiave & Metriche")
        
        cg1, cg2 = st.columns(2)
        with cg1:
            st.markdown(f"**🏠 {casa}**")
            p_casa = players_data.get(casa, [{'nome': 'Top Scorer', 'stat': 'xG/90: 0.45'}])
            for p in p_casa:
                st.markdown(f"""
                <div class="player-card">
                    <div class="player-name">👤 {p['nome']}</div>
                    <div class="player-stat">📊 {p['stat']}</div>
                </div>
                """, unsafe_allow_html=True)

        with cg2:
            st.markdown(f"**✈️ {trasferta}**")
            p_trasferta = players_data.get(trasferta, [{'nome': 'Top Scorer', 'stat': 'xG/90: 0.40'}])
            for p in p_trasferta:
                st.markdown(f"""
                <div class="player-card">
                    <div class="player-name">👤 {p['nome']}</div>
                    <div class="player-stat">📊 {p['stat']}</div>
                </div>
                """, unsafe_allow_html=True)
