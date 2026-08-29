import streamlit as st
import pandas as pd
import numpy as np
import asyncio
from scipy.stats import poisson
from understatapi import UnderstatClient

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

# GESTIONE FETCHING ASINCRONO CON UNDERSTATAPI
async def async_fetch_understat():
    async with UnderstatClient() as client:
        # Recupera dati ultime stagioni Serie A
        leagues_data = await client.league("Serie_A").get_team_data(season=2024)
        players_data_raw = await client.league("Serie_A").get_player_data(season=2024)
        return leagues_data, players_data_raw

@st.cache_data(ttl=3600)
def load_live_data():
    try:
        # Esecuzione del ciclo asincrono richiesto da understatapi
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        teams_raw, players_raw = loop.run_until_complete(async_fetch_understat())
        
        teams_data = {}
        players_data = {}

        # Parsing dati squadre
        for t_id, t_info in teams_raw.items():
            team_name = t_info['title']
            history = t_info['history']
            games = max(1, len(history))
            tot_xg = sum(float(x['xG']) for x in history)
            tot_xga = sum(float(x['xGA']) for x in history)
            
            teams_data[team_name] = {
                'xG_fatti': round(tot_xg / games, 2),
                'xGA_subiti': round(tot_xga / games, 2)
            }

        # Parsing dati giocatori
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

        return teams_data, players_data, True
    except Exception as e:
        return {}, {}, False

# ESSECUZIONE APP
st.title("⚽ Serie A Predictor Engine")
st.caption("Analisi avanzata con metriche ufficiali Understat")

teams_data, players_data, is_live = load_live_data()

if is_live and teams_data:
    st.sidebar.success("🟢 Connesso live a Understat API")
else:
    st.sidebar.error("🔴 Impossibile contattare i server Understat. Verifica la rete o riprova più tardi.")

squadre = sorted(list(teams_data.keys())) if teams_data else []

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
            st.subheader("📊 Probabilità Calcolate da Understat")
            c1, c2, c3 = st.columns(3)
            c1.metric(f"Vittoria {casa}", f"{prob_1:.1f}%")
            c2.metric("Pareggio (X)", f"{prob_x:.1f}%")
            c3.metric(f"Vittoria {trasferta}", f"{prob_2:.1f}%")

            st.success(f"🎯 Risultato Esatto Modellato: **{casa} {g_c} - {g_t} {trasferta}** ({prob_top:.1f}% probabilità)")

            st.markdown("---")
            st.subheader("⭐ Top Giocatori (Understat)")
            
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
