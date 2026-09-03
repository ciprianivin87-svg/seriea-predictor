import streamlit as st
import requests
import numpy as np
import pandas as pd
from datetime import datetime
from scipy.stats import poisson

st.set_page_config(page_title="Serie A Predictor", page_icon="⚽", layout="centered")

# Styling CSS
st.markdown("""
<style>
    .main { background-color: #0f172a; }
    .stat-card {
        background-color: #1e293b;
        border-radius: 10px;
        padding: 16px;
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
        margin-bottom: 15px;
    }
    .metric-container {
        display: flex;
        justify-content: space-around;
        background-color: #0f172a;
        padding: 12px;
        border-radius: 8px;
        margin-top: 10px;
    }
    .metric-box { text-align: center; }
    .metric-title { font-size: 12px; color: #94a3b8; margin-bottom: 2px; }
    .metric-value { font-size: 16px; font-weight: bold; color: #38bdf8; }
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

# 🔑 API TOKEN PERSONALE
API_TOKEN = "2e52e41c56bc4d85b2cc3df2d03c00af"
HEADERS = {"X-Auth-Token": API_TOKEN}

# Stato della sessione per la classifica
if "show_standings" not in st.session_state:
    st.session_state.show_standings = False

def toggle_standings():
    st.session_state.show_standings = not st.session_state.show_standings

@st.cache_data(ttl=1800)
def fetch_all_serie_a_matches():
    """Recupera tutte le partite della stagione e individua la giornata corrente."""
    url = "https://api.football-data.org/v4/competitions/SA/matches"
    try:
        response = requests.get(url, headers=HEADERS, timeout=8)
        if response.status_code == 200:
            data = response.json()
            matches = data.get("matches", [])
            
            # Individua la giornata corrente/più recente
            current_matchday = 1
            for match in matches:
                if match.get("status") in ["IN_PLAY", "PAUSED", "TIMED"]:
                    current_matchday = match.get("matchday", 1)
                    break
            else:
                # Se non ci sono partite programmate o in corso, individua l'ultima giocata
                finished = [m.get("matchday") for m in matches if m.get("status") == "FINISHED"]
                if finished:
                    current_matchday = max(finished)

            return matches, current_matchday, True
    except Exception:
        pass
    return [], 1, False

@st.cache_data(ttl=1800)
def fetch_team_stats_and_form():
    """Recupera la classifica dettagliata e calcola la forma reale."""
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
    """Recupera la classifica marcatori generale della Serie A."""
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
                    "playedMatches": played_matches
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

def calcola_moltiplicatore_forma(form_list):
    """Calcola il moltiplicatore di forma basato sulla lista dei risultati (W/D/L)."""
    if not form_list:
        return 1.0, []
    
    modificatore = 0.0
    for r in form_list:
        if r == "W":
            modificatore += 0.05
        elif r == "L":
            modificatore -= 0.05

    moltiplicatore = max(0.7, min(1.3, 1.0 + modificatore))
    return moltiplicatore, form_list

def calcola_pronostico(gf_casa, ga_casa, form_casa, gf_trasferta, ga_trasferta, form_trasferta):
    """Calcola le probabilità 1X2 e il risultato esatto pesando la forma recente."""
    mult_c, _ = calcola_moltiplicatore_forma(form_casa)
    mult_t, _ = calcola_moltiplicatore_forma(form_trasferta)

    gf_c_adj = gf_casa * mult_c
    ga_c_adj = ga_casa / mult_c
    gf_t_adj = gf_trasferta * mult_t
    ga_t_adj = ga_trasferta / mult_t

    lambda_casa = max(0.5, (gf_c_adj + ga_t_adj) / 2)
    lambda_trasferta = max(0.5, (gf_t_adj + ga_c_adj) / 2)

    matrice_p = np.zeros((6, 6))
    for i in range(6):
        for j in range(6):
            matrice_p[i, j] = poisson.pmf(i, lambda_casa) * poisson.pmf(j, lambda_trasferta) * 100

    prob_1 = np.sum(np.tril(matrice_p, -1))
    prob_x = np.sum(np.diag(matrice_p))
    prob_2 = np.sum(np.triu(matrice_p, 1))

    g_c, g_t = np.unravel_index(np.argmax(matrice_p), matrice_p.shape)
    prob_exact = matrice_p[g_c, g_t]

    return prob_1, prob_x, prob_2, g_c, g_t, prob_exact, lambda_casa, lambda_trasferta

def render_form_badges(form_list):
    """Genera l'HTML per mostrare i badge visuali della forma (W/D/L)."""
    if not form_list:
        return '<span style="color: #94a3b8; font-size: 12px;">Dati non disponibili</span>'
    
    html = ""
    for r in form_list:
        badge_class = r if r in ["W", "D", "L"] else "D"
        html += f'<span class="form-badge form-{badge_class}">{r}</span>'
    return html

# --- LAYOUT APPLICAZIONE ---

col_title, col_btn = st.columns([3, 1])

with col_title:
    st.title("⚽ Serie A Hub")

with col_btn:
    st.write("")
    lbl_btn = "❌ Chiudi Classifica" if st.session_state.show_standings else "📊 Classifica"
    st.button(lbl_btn, on_click=toggle_standings, use_container_width=True)

tutte_le_partite, giornata_corrente, successo = fetch_all_serie_a_matches()
stats_squadre, classifica_completa = fetch_team_stats_and_form()
classifica_marcatori, marcatori_completi_list = fetch_top_scorers()

# SEZIONE CLASSIFICA COMPLETA
if st.session_state.show_standings:
    st.markdown("---")
    st.subheader("🏆 Classifica Serie A Aggiornata")
    if classifica_completa:
        df_standings = pd.DataFrame(classifica_completa)
        st.dataframe(
            df_standings,
            column_config={
                "Pos": st.column_config.NumberColumn("Pos", format="%d°"),
                "Squadra": "Squadra",
                "PT": st.column_config.NumberColumn("Punti", format="%d"),
                "G": "G", "V": "V", "N": "N", "P": "P",
                "GF": "GF", "GS": "GS", "DR": "DR"
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.warning("Classifica temporaneamente non disponibile.")
    st.markdown("---")

if successo and tutte_le_partite:
    # 🗓️ SELETTORE DELLA GIORNATA
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
        elif giornata_selezionata < giornata_corrente:
            st.caption("📜 **Giornata Passata** (Scontri già conclusi)")
        else:
            st.caption("🔮 **Giornata Futura** (Prossimi incontri)")

    # Filtra partite per la giornata selezionata
    partite_giornata = [m for m in tutte_le_partite if m.get("matchday") == giornata_selezionata]

    # STRUTTURA A TAB
    tab_match, tab_scorers = st.tabs(["🔮 Analisi Partita", "⚽ Classifica Marcatori Completa"])

    # TAB 1: ANALISI E PRONOSTICI PARTITA
    with tab_match:
        if partite_giornata:
            opzioni_match = {
                f"{m['homeTeam']['name']} vs {m['awayTeam']['name']}": m 
                for m in partite_giornata
            }
            
            partita_selezionata = st.selectbox(
                "🔍 Seleziona la partita da analizzare:",
                options=list(opzioni_match.keys())
            )

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
            elif status in ["IN_PLAY", "PAUSED"]:
                score_h = match["score"]["fullTime"]["home"]
                score_a = match["score"]["fullTime"]["away"]
                risultato_str = f"🔴 **Risultato Live: {score_h} - {score_a}**"
            else:
                risultato_str = f"📅 Programmata per il: **{data_ora_str}**"

            st.info(risultato_str)

            # 1. SCHEDA CONFRONTO STATISTICO E FORMA
            st.subheader("📊 Dettagli e Stato di Forma")
            
            st_c = stats_squadre.get(casa, {"pos": "-", "punti": 0, "gf": 1.2, "ga": 1.1, "tot_gf": 15, "form_list": []})
            st_t = stats_squadre.get(trasferta, {"pos": "-", "punti": 0, "gf": 1.1, "ga": 1.2, "tot_gf": 12, "form_list": []})

            mult_c, list_c = calcola_moltiplicatore_forma(st_c.get("form_list", []))
            mult_t, list_t = calcola_moltiplicatore_forma(st_t.get("form_list", []))

            col1, col2 = st.columns(2)

            with col1:
                st.markdown(f"#### 🏠 {casa}")
                st.write(f"• **Posizione in classifica:** {st_c['pos']}° ({st_c['punti']} pt)")
                st.write(f"• **Media Gol (Segnati/Subiti):** {st_c['gf']:.2f} / {st_c['ga']:.2f}")
                st.markdown(f"• **Ultime 5:** {render_form_badges(list_c)}", unsafe_allow_html=True)
                st.caption(f"Fattore Ponderazione Forma: **x{mult_c:.2f}**")

            with col2:
                st.markdown(f"#### ✈️ {trasferta}")
                st.write(f"• **Posizione in classifica:** {st_t['pos']}° ({st_t['punti']} pt)")
                st.write(f"• **Media Gol (Segnati/Subiti):** {st_t['gf']:.2f} / {st_t['ga']:.2f}")
                st.markdown(f"• **Ultime 5:** {render_form_badges(list_t)}", unsafe_allow_html=True)
                st.caption(f"Fattore Ponderazione Forma: **x{mult_t:.2f}**")

            # 2. PRONOSTICO E PROBABILITÀ
            st.markdown("---")
            st.subheader("🔮 Pronostico Algoritmetico Pesato")

            prob_1, prob_x, prob_2, g_c, g_t, prob_exact, exp_c, exp_t = calcola_pronostico(
                st_c["gf"], st_c["ga"], list_c,
                st_t["gf"], st_t["ga"], list_t
            )

            st.markdown(
                f"""
                <div class="stat-card">
                    <div class="vs-header">🎯 Risultato Stimato: {casa} {g_c} - {g_t} {trasferta}</div>
                    <div style="text-align: center; color: #94a3b8; font-size: 13px; margin-bottom: 15px;">
                        Probabilità del punteggio esatto: <b>{prob_exact:.1f}%</b>
                    </div>
                    <div class="metric-container">
                        <div class="metric-box">
                            <div class="metric-title">Vittoria {casa} (1)</div>
                            <div class="metric-value">{prob_1:.1f}%</div>
                        </div>
                        <div class="metric-box">
                            <div class="metric-title">Pareggio (X)</div>
                            <div class="metric-value">{prob_x:.1f}%</div>
                        </div>
                        <div class="metric-box">
                            <div class="metric-title">Vittoria {trasferta} (2)</div>
                            <div class="metric-value">{prob_2:.1f}%</div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            st.progress(int(prob_1), text=f"Distribuzione pronostico (1: {prob_1:.0f}% | X: {prob_x:.0f}% | 2: {prob_2:.0f}%)")

            # 3. GIOCATORI CHIAVE DA MONITORARE
            st.markdown("---")
            st.subheader("⭐ Giocatori Chiave da Monitorare")

            p_col1, p_col2 = st.columns(2)

            with p_col1:
                st.markdown(f"**Top Player {casa}**")
                players_c = classifica_marcatori.get(casa, [])
                if players_c:
                    for p in players_c[:2]:
                        tot_goals = p['goals']
                        tot_team_gf = max(1, st_c['tot_gf'])
                        quota_gol = (tot_goals / tot_team_gf) if tot_team_gf > 0 else 0.2
                        prob_marcatore = (1 - poisson.pmf(0, exp_c * quota_gol)) * 100
                        
                        st.markdown(
                            f"""
                            <div class="player-card">
                                <div style="font-weight: bold; color: #f8fafc;">🏃 {p['name']}</div>
                                <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">
                                    • Gol stagionali: <b>{tot_goals}</b> (rigori: {p['penalties']})<br>
                                    • Probabilità di segnare oggi: <b style="color: #38bdf8;">{prob_marcatore:.1f}%</b>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                else:
                    st.caption("Dati marcatori non disponibili per questo club.")

            with p_col2:
                st.markdown(f"**Top Player {trasferta}**")
                players_t = classifica_marcatori.get(trasferta, [])
                if players_t:
                    for p in players_t[:2]:
                        tot_goals = p['goals']
                        tot_team_gf = max(1, st_t['tot_gf'])
                        quota_gol = (tot_goals / tot_team_gf) if tot_team_gf > 0 else 0.2
                        prob_marcatore = (1 - poisson.pmf(0, exp_t * quota_gol)) * 100
                        
                        st.markdown(
                            f"""
                            <div class="player-card">
                                <div style="font-weight: bold; color: #f8fafc;">🏃 {p['name']}</div>
                                <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">
                                    • Gol stagionali: <b>{tot_goals}</b> (rigori: {p['penalties']})<br>
                                    • Probabilità di segnare oggi: <b style="color: #38bdf8;">{prob_marcatore:.1f}%</b>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                else:
                    st.caption("Dati marcatori non disponibili per questo club.")
        else:
            st.warning(f"Nessuna partita trovata per la {giornata_selezionata}ª giornata.")

    # TAB 2: CLASSIFICA MARCATORI COMPLETA
    with tab_scorers:
        st.subheader("🥇 Classifica Marcatori Serie A")
        
        if marcatori_completi_list:
            df_marcatori = pd.DataFrame(marcatori_completi_list)

            col_f1, col_f2 = st.columns([2, 1])
            with col_f1:
                search_player = st.text_input("🔍 Cerca giocatore:", placeholder="Es. Lautaro, Vlahovic...")
            with col_f2:
                squadre_disponibili = ["Tutte le squadre"] + sorted(list(set(df_marcatori["Squadra"])))
                selected_team = st.selectbox("Filtrati per squadra:", squadre_disponibili)

            df_filtrato = df_marcatori.copy()
            if selected_team != "Tutte le squadre":
                df_filtrato = df_filtrato[df_filtrato["Squadra"] == selected_team]
            if search_player:
                df_filtrato = df_filtrato[df_filtrato["Giocatore"].str.contains(search_player, case=False, na=False)]

            st.dataframe(
                df_filtrato,
                column_config={
                    "Pos": st.column_config.NumberColumn("Pos", format="%d°"),
                    "Giocatore": "Giocatore",
                    "Squadra": "Squadra",
                    "Ruolo": "Ruolo",
                    "Gol": st.column_config.NumberColumn("⚽ Gol", format="%d"),
                    "Rigori": st.column_config.NumberColumn("🎯 Rigori", format="%d"),
                    "Assist": st.column_config.NumberColumn("🅰️ Assist", format="%d"),
                    "Presenze": st.column_config.NumberColumn("👕 Presenze", format="%d")
                },
                hide_index=True,
                use_container_width=True
            )
        else:
            st.warning("Dati dei marcatori al momento non disponibili tramite API.")

else:
    st.error("Impossibile caricare le informazioni dalla Serie A.")
