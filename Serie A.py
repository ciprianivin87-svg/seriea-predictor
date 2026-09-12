import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from utils import (
    calcola_moltiplicatore_forma, calcola_pronostico,
    calcola_probabilita_scommesse, genera_plotly_heatmap,
    render_form_badges, get_team_key_players
)

st.set_page_config(page_title="Serie A Predictor", page_icon="⚽", layout="centered")

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

if "show_standings" not in st.session_state:
    st.session_state.show_standings = False

def toggle_standings():
    st.session_state.show_standings = not st.session_state.show_standings

@st.cache_data(ttl=1800)
def fetch_all_serie_a_matches():
    url = "https://api.football-data.org/v4/competitions/SA/matches"
    try:
        response = requests.get(url, headers=HEADERS, timeout=8)
        if response.status_code == 200:
            data = response.json()
            matches = data.get("matches", [])
            current_matchday = 1
            for match in matches:
                if match.get("status") in ["IN_PLAY", "PAUSED", "TIMED"]:
                    current_matchday = match.get("matchday", 1)
                    break
            else:
                finished = [m.get("matchday") for m in matches if m.get("status") == "FINISHED"]
                if finished:
                    current_matchday = max(finished)
            return matches, current_matchday, True
    except Exception:
        pass
    return [], 1, False

@st.cache_data(ttl=1800)
def fetch_team_stats_and_form():
    url_standings = "https://api.football-data.org/v4/competitions/SA/standings"
    url_matches = "https://api.football-data.org/v4/competitions/SA/matches"
    stats = {}
    standings_table = []
    try:
        resp_s = requests.get(url_standings, headers=HEADERS, timeout=8)
        if resp_s.status_code == 200:
            standings = resp_s.json()["standings"][0]["table"]
            for row in standings:
                t_name = row["team"]["name"]
                played = max(1, row["playedGames"])
                standings_table.append({
                    "Pos": row["position"],
                    "Squadra": t_name,
                    "PT": row["points"],
                    "G": row["playedGames"],
                    "V": row["won"],
                    "N": row["draw"],
                    "P": row["lost"],
                    "GF": row["goalsFor"],
                    "GS": row["goalsAgainst"],
                    "DR": row["goalDifference"]
                })
                stats[t_name] = {
                    "pos": row["position"],
                    "punti": row["points"],
                    "gf": row["goalsFor"] / played,
                    "ga": row["goalsAgainst"] / played,
                    "tot_gf": row["goalsFor"],
                    "tot_ga": row["goalsAgainst"],
                    "form_list": []
                }
        
        resp_m = requests.get(url_matches, headers=HEADERS, timeout=8)
        if resp_m.status_code == 200:
            all_matches = resp_m.json().get("matches", [])
            finished_matches = [m for m in all_matches if m.get("status") == "FINISHED"]
            for team in stats.keys():
                team_results = []
                for m in reversed(finished_matches):
                    home = m["homeTeam"]["name"]
                    away = m["awayTeam"]["name"]
                    score_h = m["score"]["fullTime"]["home"]
                    score_a = m["score"]["fullTime"]["away"]

                    if home == team:
                        if score_h > score_a: team_results.append("W")
                        elif score_h == score_a: team_results.append("D")
                        else: team_results.append("L")
                    elif away == team:
                        if score_a > score_h: team_results.append("W")
                        elif score_a == score_h: team_results.append("D")
                        else: team_results.append("L")
                    
                    if len(team_results) == 5:
                        break
                stats[team]["form_list"] = list(reversed(team_results))
    except Exception:
        pass
    return stats, standings_table

@st.cache_data(ttl=3600)
def fetch_top_scorers():
    url = "https://api.football-data.org/v4/competitions/SA/scorers"
    scorers_by_team = {}
    all_scorers_list = []
    try:
        response = requests.get(url, headers=HEADERS, timeout=8)
        if response.status_code == 200:
            data = response.json()
            for idx, item in enumerate(data.get("scorers", []), start=1):
                team = item["team"]["name"]
                player_name = item["player"]["name"]
                position = item["player"].get("position", "Attaccante")
                goals = item.get("goals", 0)
                assists = item.get("assists") or 0
                penalties = item.get("penalties") or 0
                played_matches = item.get("playedMatches") or 0

                player_data = {
                    "name": player_name,
                    "position": position,
                    "goals": goals,
                    "assists": assists,
                    "penalties": penalties,
                    "playedMatches": played_matches,
                    "is_fallback": False
                }
                if team not in scorers_by_team:
                    scorers_by_team[team] = []
                scorers_by_team[team].append(player_data)

                all_scorers_list.append({
                    "Pos": idx,
                    "Giocatore": player_name,
                    "Squadra": team,
                    "Ruolo": position,
                    "Gol": goals,
                    "Rigori": penalties,
                    "Assist": assists,
                    "Presenze": played_matches
                })
    except Exception:
        pass
    return scorers_by_team, all_scorers_list

def mostra_verifica_pronostici(partite_giornata, stats_squadre):
    partite_concluse = [m for m in partite_giornata if m.get("status") == "FINISHED"]
    if not partite_concluse:
        st.info("ℹ️ Nessuna partita conclusa presente in questa giornata per effettuare il confronto.")
        return

    report_data = []
    tot_1x2_correct = 0
    tot_exact_correct = 0

    for m in partite_concluse:
        casa = m["homeTeam"]["name"]
        trasferta = m["awayTeam"]["name"]
        score_h_real = m["score"]["fullTime"]["home"]
        score_a_real = m["score"]["fullTime"]["away"]

        segno_reale = "1" if score_h_real > score_a_real else ("2" if score_h_real < score_a_real else "X")

        st_c = stats_squadre.get(casa, {"gf": 1.2, "ga": 1.1, "form_list": []})
        st_t = stats_squadre.get(trasferta, {"gf": 1.1, "ga": 1.2, "form_list": []})

        prob_1, prob_x, prob_2, g_c_pred, g_t_pred, _, _, _, _ = calcola_pronostico(
            st_c["gf"], st_c["ga"], st_c.get("form_list", []),
            st_t["gf"], st_t["ga"], st_t.get("form_list", [])
        )

        probs = {"1": prob_1, "X": prob_x, "2": prob_2}
        segno_pred = max(probs, key=probs.get)

        is_1x2_correct = (segno_reale == segno_pred)
        is_exact_correct = (score_h_real == g_c_pred and score_a_real == g_t_pred)

        if is_1x2_correct: tot_1x2_correct += 1
        if is_exact_correct: tot_exact_correct += 1

        report_data.append({
            "Partita": f"{casa} - {trasferta}",
            "Reale": f"{score_h_real} - {score_a_real} ({segno_reale})",
            "Stimato": f"{g_c_pred} - {g_t_pred} ({segno_pred})",
            "Esito 1X2": "✅ Preso" if is_1x2_correct else "❌ Sbagliato",
            "Risultato Esatto": "🎯 Preso" if is_exact_correct else "❌ Mancato"
        })

    total_matches = len(partite_concluse)
    perc_1x2 = (tot_1x2_correct / total_matches) * 100
    perc_exact = (tot_exact_correct / total_matches) * 100

    st.subheader("📋 Resoconto Accuracy Giornata")
    col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
    col_kpi1.metric("Partite Concluse", total_matches)
    col_kpi2.metric("Esiti 1X2 Indovinati", f"{tot_1x2_correct}/{total_matches}", f"{perc_1x2:.1f}%")
    col_kpi3.metric("Risultati Esatti Presi", f"{tot_exact_correct}/{total_matches}", f"{perc_exact:.1f}%")

    st.markdown("---")
    df_report = pd.DataFrame(report_data)
    st.dataframe(df_report, hide_index=True, use_container_width=True)

# LAYOUT
col_title, col_btn = st.columns([3, 1])
with col_title:
    st.title("⚽ Serie A Hub")
with col_btn:
    st.write("")
    lbl_btn = "❌ Chiudi Classifiche" if st.session_state.show_standings else "📊 Classifiche"
    st.button(lbl_btn, on_click=toggle_standings, use_container_width=True)

tutte_le_partite, giornata_corrente, successo = fetch_all_serie_a_matches()
stats_squadre, classifica_completa = fetch_team_stats_and_form()
classifica_marcatori, marcatori_completi_list = fetch_top_scorers()

if st.session_state.show_standings:
    st.markdown("---")
    tipo_classifica = st.radio(
        "Scegli quale classifica visualizzare:",
        options=["🏆 Classifica Serie A Aggiornata", "⚽ Classifica Marcatori Completa"],
        horizontal=True
    )
    if tipo_classifica == "🏆 Classifica Serie A Aggiornata":
        st.subheader("🏆 Classifica Serie A")
        if classifica_completa:
            st.dataframe(pd.DataFrame(classifica_completa), hide_index=True, use_container_width=True)
    elif tipo_classifica == "⚽ Classifica Marcatori Completa":
        st.subheader("🥇 Classifica Marcatori Serie A")
        if marcatori_completi_list:
            df_m = pd.DataFrame(marcatori_completi_list)
            st.dataframe(df_m, hide_index=True, use_container_width=True)
    st.markdown("---")

if successo and tutte_le_partite:
    col_giornata, col_info = st.columns([2, 2])
    with col_giornata:
        giornata_selezionata = st.selectbox(
            "🗓️ **Seleziona la Giornata:**",
            options=list(range(1, 39)),
            index=int(giornata_corrente - 1)
        )
    with col_info:
        st.write("")
        st.write("")
        if giornata_selezionata == giornata_corrente:
            st.caption("🔴 **Giornata Corrente**")

    partite_giornata = [m for m in tutte_le_partite if m.get("matchday") == giornata_selezionata]

    if partite_giornata:
        tab_analisi, tab_verifica = st.tabs(["🔍 Analisi Singola Partita", "📜 Verifica Accuracy Giornata"])

        with tab_analisi:
            opzioni_match = {f"{m['homeTeam']['name']} vs {m['awayTeam']['name']}": m for m in partite_giornata}
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
                risultato_str = f"✅ **Risultato Finale Reale: {score_h} - {score_a}** (Giocata il {data_ora_str})"
            else:
                risultato_str = f"📅 Programmata per il: **{data_ora_str}**"

            st.info(risultato_str)

            st.subheader("📊 Dettagli e Stato di Forma")
            st_c = stats_squadre.get(casa, {"pos": "-", "punti": 0, "gf": 1.2, "ga": 1.1, "tot_gf": 15, "form_list": []})
            st_t = stats_squadre.get(trasferta, {"pos": "-", "punti": 0, "gf": 1.1, "ga": 1.2, "tot_gf": 12, "form_list": []})

            mult_c, list_c = calcola_moltiplicatore_forma(st_c.get("form_list", []))
            mult_t, list_t = calcola_moltiplicatore_forma(st_t.get("form_list", []))

            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"#### 🏠 {casa}")
                st.write(f"• **Posizione in classifica:** {st_c['pos']}° ({st_c['punti']} pt)")
                st.write(f"• **Media Gol:** {st_c['gf']:.2f} / {st_c['ga']:.2f}")
                st.markdown(f"• **Ultime 5:** {render_form_badges(list_c)}", unsafe_allow_html=True)

            with col2:
                st.markdown(f"#### ✈️ {trasferta}")
                st.write(f"• **Posizione in classifica:** {st_t['pos']}° ({st_t['punti']} pt)")
                st.write(f"• **Media Gol:** {st_t['gf']:.2f} / {st_t['ga']:.2f}")
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
                players_c = get_team_key_players(casa, classifica_marcatori, stats_squadre)
                for p in players_c[:2]:
                    st.markdown(f'<div class="player-card"><b>🏃 {p["name"]}</b><br>Gol: {p["goals"]}</div>', unsafe_allow_html=True)

            with p_col2:
                st.markdown(f"**Top Player {trasferta}**")
                players_t = get_team_key_players(trasferta, classifica_marcatori, stats_squadre)
                for p in players_t[:2]:
                    st.markdown(f'<div class="player-card"><b>🏃 {p["name"]}</b><br>Gol: {p["goals"]}</div>', unsafe_allow_html=True)

        with tab_verifica:
            mostra_verifica_pronostici(partite_giornata, stats_squadre)
