import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from utils import (
    calcola_moltiplicatore_forma, calcola_pronostico,
    calcola_probabilita_scommesse, genera_plotly_heatmap,
    render_form_badges, get_team_key_players
)

st.set_page_config(page_title="Champions League Predictor", page_icon="🇪🇺", layout="centered")

st.markdown("""
<style>
    .main { background-color: #0f172a; }
    .stat-card {
        background-color: #1e293b;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 15px;
        border: 1px solid #334155;
    }
    .player-card {
        background-color: #0f172a;
        border-radius: 8px;
        padding: 12px;
        margin-top: 8px;
        border-left: 4px solid #38bdf8;
    }
    .vs-header {
        font-size: 22px;
        font-weight: bold;
        color: #f8fafc;
        text-align: center;
    }
    .form-badge {
        display: inline-block;
        padding: 2px 6px;
        border-radius: 4px;
        font-weight: bold;
        font-size: 11px;
        margin-right: 2px;
        color: #fff;
    }
    .form-W { background-color: #22c55e; }
    .form-D { background-color: #eab308; }
    .form-L { background-color: #ef4444; }
</style>
""", unsafe_allow_html=True)

API_TOKEN = st.secrets["API_TOKEN"]
HEADERS = {"X-Auth-Token": API_TOKEN}

@st.cache_data(ttl=1800)
def fetch_all_cl_matches():
    """Recupera tutte le partite di Champions League (Codice API: CL)."""
    url = "https://api.football-data.org/v4/competitions/CL/matches"
    try:
        response = requests.get(url, headers=HEADERS, timeout=8)
        if response.status_code == 200:
            data = response.json()
            matches = data.get("matches", [])
            
            # Mappatura delle giornate/fasi
            stages = []
            for m in matches:
                stage = m.get("stage")
                matchday = m.get("matchday")
                label = f"Matchday {matchday}" if matchday else stage.replace("_", " ").title()
                if label not in stages:
                    stages.append(label)
            return matches, stages, True
    except Exception:
        pass
    return [], [], False

@st.cache_data(ttl=1800)
def fetch_cl_team_stats():
    """Calcola le statistiche generali basandosi sulle partite della stagione corrente."""
    url = "https://api.football-data.org/v4/competitions/CL/matches"
    stats = {}
    try:
        response = requests.get(url, headers=HEADERS, timeout=8)
        if response.status_code == 200:
            matches = response.json().get("matches", [])
            finished = [m for m in matches if m.get("status") == "FINISHED"]
            
            # Inizializza squadre
            for m in matches:
                h = m["homeTeam"]["name"]
                a = m["awayTeam"]["name"]
                if h not in stats: stats[h] = {"gf_tot": 0, "ga_tot": 0, "played": 0, "results": []}
                if a not in stats: stats[a] = {"gf_tot": 0, "ga_tot": 0, "played": 0, "results": []}
            
            for m in finished:
                h = m["homeTeam"]["name"]
                a = m["awayTeam"]["name"]
                sh = m["score"]["fullTime"]["home"]
                sa = m["score"]["fullTime"]["away"]
                
                stats[h]["gf_tot"] += sh
                stats[h]["ga_tot"] += sa
                stats[h]["played"] += 1
                
                stats[a]["gf_tot"] += sa
                stats[a]["ga_tot"] += sh
                stats[a]["played"] += 1

                if sh > sa:
                    stats[h]["results"].append("W")
                    stats[a]["results"].append("L")
                elif sh < sa:
                    stats[h]["results"].append("L")
                    stats[a]["results"].append("W")
                else:
                    stats[h]["results"].append("D")
                    stats[a]["results"].append("D")

            # Formatta il dizionario
            formatted_stats = {}
            for t_name, data in stats.items():
                p = max(1, data["played"])
                formatted_stats[t_name] = {
                    "pos": "-",
                    "punti": "-",
                    "gf": data["gf_tot"] / p if p > 0 else 1.2,
                    "ga": data["ga_tot"] / p if p > 0 else 1.1,
                    "tot_gf": data["gf_tot"],
                    "form_list": data["results"][-5:]
                }
            return formatted_stats
    except Exception:
        pass
    return {}

@st.cache_data(ttl=3600)
def fetch_cl_top_scorers():
    url = "https://api.football-data.org/v4/competitions/CL/scorers"
    scorers_by_team = {}
    try:
        response = requests.get(url, headers=HEADERS, timeout=8)
        if response.status_code == 200:
            data = response.json()
            for item in data.get("scorers", []):
                team = item["team"]["name"]
                player_name = item["player"]["name"]
                goals = item.get("goals", 0)
                penalties = item.get("penalties") or 0

                player_data = {
                    "name": player_name,
                    "goals": goals,
                    "penalties": penalties,
                    "is_fallback": False
                }
                if team not in scorers_by_team:
                    scorers_by_team[team] = []
                scorers_by_team[team].append(player_data)
    except Exception:
        pass
    return scorers_by_team

st.title("🇪🇺 Champions League Hub")

matches, stages, success = fetch_all_cl_matches()
stats_squadre = fetch_cl_team_stats()
marcatori = fetch_cl_top_scorers()

if success and matches:
    fase_selezionata = st.selectbox("🏆 **Seleziona la Fase / Giornata:**", options=stages)
    
    # Filtra partite per la fase scelta
    partite_fase = []
    for m in matches:
        label = f"Matchday {m.get('matchday')}" if m.get('matchday') else m.get('stage', '').replace("_", " ").title()
        if label == fase_selezionata:
            partite_fase.append(m)

    if partite_fase:
        opzioni_match = {f"{m['homeTeam']['name']} vs {m['awayTeam']['name']}": m for m in partite_fase}
        partita_selezionata = st.selectbox("🔍 Seleziona la partita da analizzare:", options=list(opzioni_match.keys()))

        match = opzioni_match[partita_selezionata]
        casa = match["homeTeam"]["name"]
        trasferta = match["awayTeam"]["name"]

        try:
            utc_time = datetime.strptime(match["utcDate"], "%Y-%m-%dT%H:%M:%SZ")
            data_ora_str = utc_time.strftime("%d/%m/%Y alle %H:%M")
        except ValueError:
            data_ora_str = match["utcDate"]

        status = match["status"]
        if status == "FINISHED":
            score_h = match["score"]["fullTime"]["home"]
            score_a = match["score"]["fullTime"]["away"]
            st.info(f"✅ **Risultato Finale Reale: {score_h} - {score_a}** ({data_ora_str})")
        else:
            st.info(f"📅 Programmata per il: **{data_ora_str}**")

        st.subheader("📊 Dettagli e Stato di Forma")
        st_c = stats_squadre.get(casa, {"gf": 1.2, "ga": 1.1, "tot_gf": 10, "form_list": []})
        st_t = stats_squadre.get(trasferta, {"gf": 1.1, "ga": 1.2, "tot_gf": 8, "form_list": []})

        mult_c, list_c = calcola_moltiplicatore_forma(st_c.get("form_list", []))
        mult_t, list_t = calcola_moltiplicatore_forma(st_t.get("form_list", []))

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"#### 🏠 {casa}")
            st.write(f"• **Media Gol Segnati/Subiti:** {st_c['gf']:.2f} / {st_c['ga']:.2f}")
            st.markdown(f"• **Ultime 5:** {render_form_badges(list_c)}", unsafe_allow_html=True)

        with col2:
            st.markdown(f"#### ✈️ {trasferta}")
            st.write(f"• **Media Gol Segnati/Subiti:** {st_t['gf']:.2f} / {st_t['ga']:.2f}")
            st.markdown(f"• **Ultime 5:** {render_form_badges(list_t)}", unsafe_allow_html=True)

        st.markdown("---")
        st.subheader("🔮 Pronostico Algoritmetico Pesato")
        prob_1, prob_x, prob_2, g_c, g_t, prob_exact, exp_c, exp_t, matrice_p = calcola_pronostico(
            st_c["gf"], st_c["ga"], list_c, st_t["gf"], st_t["ga"], list_t
        )

        st.markdown(f'<div class="stat-card"><div class="vs-header">🎯 Risultato Stimato: {casa} {g_c} - {g_t} {trasferta}</div></div>', unsafe_allow_html=True)

        st.markdown("---")
        st.subheader("🎲 Quote Equa & Probabilità per Scommesse")
        df_scommesse = calcola_probabilita_scommesse(matrice_p, prob_1, prob_x, prob_2)
        st.dataframe(df_scommesse, hide_index=True, use_container_width=True)

        st.markdown("---")
        fig_heatmap = genera_plotly_heatmap(matrice_p, casa, trasferta)
        st.plotly_chart(fig_heatmap, use_container_width=True)

        st.markdown("---")
        st.subheader("⭐ Giocatori Chiave da Monitorare")
        p_col1, p_col2 = st.columns(2)

        with p_col1:
            st.markdown(f"**Top Player {casa}**")
            players_c = get_team_key_players(casa, marcatori, stats_squadre)
            for p in players_c[:2]:
                st.markdown(f'<div class="player-card"><b>🏃 {p["name"]}</b><br>Gol in CL: {p["goals"]}</div>', unsafe_allow_html=True)

        with p_col2:
            st.markdown(f"**Top Player {trasferta}**")
            players_t = get_team_key_players(trasferta, marcatori, stats_squadre)
            for p in players_t[:2]:
                st.markdown(f'<div class="player-card"><b>🏃 {p["name"]}</b><br>Gol in CL: {p["goals"]}</div>', unsafe_allow_html=True)

else:
    st.error("Impossibile caricare le informazioni della Champions League.")
