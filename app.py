import streamlit as st
import requests
import numpy as np
import pandas as pd
import os
import google.generativeai as genai
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

# 🔑 API TOKENS
API_TOKEN = "2e52e41c56bc4d85b2cc3df2d03c00af"
HEADERS = {"X-Auth-Token": API_TOKEN}
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "AQ.Ab8RN6Ih6njBiYeWxtRQqtNF6xsdXPs1xXvNjOogrCCbfE5d1w")

# Gestione stato della sessione per i menu
if "show_standings" not in st.session_state:
    st.session_state.show_standings = False
if "show_analytics" not in st.session_state:
    st.session_state.show_analytics = False

def toggle_standings():
    st.session_state.show_standings = not st.session_state.show_standings
    if st.session_state.show_standings:
        st.session_state.show_analytics = False

def toggle_analytics():
    st.session_state.show_analytics = not st.session_state.show_analytics
    if st.session_state.show_analytics:
        st.session_state.show_standings = False

# --- FUNZIONI GEMINI & ANALISI CSV ---

def genera_sintesi_df(df):
    """Genera la sintesi strutturata del DataFrame da passare al prompt."""
    sintesi = []
    sintesi.append("INFORMAZIONI GENERALI:")
    sintesi.append(f"- Righe totali: {df.shape[0]}")
    sintesi.append(f"- Colonne totali: {df.shape[1]}")
    sintesi.append(f"- Colonne e Tipi: {dict(zip(df.columns, df.dtypes.astype(str)))}")
    sintesi.append(f"- Duplicati totali: {df.duplicated().sum()}")
    sintesi.append(f"- Valori mancanti: {df.isnull().sum().to_dict()}\n")

    sintesi.append("ANTEPRIMA DATI (PRIME 5 RIGHE):")
    sintesi.append(df.head().to_string())
    sintesi.append("\n")

    num_cols = df.select_dtypes(include=[np.number]).columns
    if len(num_cols) > 0:
        sintesi.append("STATISTICHE COLONNE NUMERICHE:")
        desc = df[num_cols].describe().T[['mean', 'std', 'min', '50%', 'max']].rename(columns={'50%': 'median'})
        sintesi.append(desc.to_string())
        sintesi.append("\n")

    cat_cols = df.select_dtypes(include=['object', 'category']).columns
    if len(cat_cols) > 0:
        sintesi.append("INFORMAZIONI COLONNE TESTUALI:")
        for col in cat_cols:
            val_counts = df[col].value_counts().head(3).to_dict()
            sintesi.append(f"- Colonna '{col}': {df[col].nunique()} valori unici. Più frequenti: {val_counts}")
        sintesi.append("\n")

    return "\n".join(sintesi)

def interroga_gemini(sintesi_dati, obiettivo_pronostico):
    """Invia il prompt a Gemini per l'analisi predittiva."""
    try:
        genai.configure(api_key=GEMINI_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')

        prompt = f"""
Sei un Data Analyst e un esperto di analisi predittiva.
Di seguito trovi il riassunto strutturato di una base dati estratta da un file CSV:

--- INIZIO DATI CSV ---
{sintesi_dati}
--- FINE DATI CSV ---

OBIETTIVO RICHIESTO:
{obiettivo_pronostico}

In base a questi dati:
1. Identifica i pattern o i trend principali.
2. Fornisci un PRONOSTICO / PREVISIONE motivato e dettagliato sull'obiettivo.
3. Evidenzia eventuali limiti dei dati o elementi d'incertezza.
"""
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"❌ Errore durante la chiamata API a Gemini: {e}"

# --- FUNZIONI API FOOTBALL ---

@st.cache_data(ttl=1800)
def fetch_serie_a_matches():
    url = "https://api.football-data.org/v4/competitions/SA/matches"
    try:
        response = requests.get(url, headers=HEADERS, timeout=8)
        if response.status_code == 200:
            data = response.json()
            matches = data.get("matches", [])
            
            current_matchday = None
            for match in matches:
                if match.get("status") in ["IN_PLAY", "PAUSED", "TIMED"]:
                    current_matchday = match.get("matchday")
                    break
            
            if not current_matchday and matches:
                current_matchday = matches[-1].get("matchday")

            giornata_partite = [m for m in matches if m.get("matchday") == current_matchday]
            return current_matchday, giornata_partite, True
    except Exception:
        pass
    return None, [], False

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
    try:
        response = requests.get(url, headers=HEADERS, timeout=8)
        if response.status_code == 200:
            data = response.json()
            for item in data.get("scorers", []):
                team = item["team"]["name"]
                player_data = {
                    "name": item["player"]["name"],
                    "position": item["player"].get("position", "Attaccante"),
                    "goals": item.get("goals", 0),
                    "assists": item.get("assists", 0),
                    "penalties": item.get("penalties", 0)
                }
                if team not in scorers_by_team:
                    scorers_by_team[team] = []
                scorers_by_team[team].append(player_data)
    except Exception:
        pass
    return scorers_by_team

def calcola_moltiplicatore_forma(form_list):
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
    if not form_list:
        return '<span style="color: #94a3b8; font-size: 12px;">Dati non disponibili</span>'
    
    html = ""
    for r in form_list:
        badge_class = r if r in ["W", "D", "L"] else "D"
        html += f'<span class="form-badge form-{badge_class}">{r}</span>'
    return html

# --- LAYOUT APPLICAZIONE ---

st.title("⚽ Serie A Hub")

# Pulsanti della barra superiore
col_btn1, col_btn2 = st.columns(2)

with col_btn1:
    lbl_standings = "❌ Chiudi Classifica" if st.session_state.show_standings else "📊 Classifica"
    st.button(lbl_standings, on_click=toggle_standings, use_container_width=True)

with col_btn2:
    lbl_analytics = "❌ Chiudi Analisi" if st.session_state.show_analytics else "📈 Analisi e Statistiche"
    st.button(lbl_analytics, on_click=toggle_analytics, use_container_width=True)

giornata, partite, successo = fetch_serie_a_matches()
stats_squadre, classifica_completa = fetch_team_stats_and_form()
classifica_marcatori = fetch_top_scorers()

# SEZIONE CLASSIFICA
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

# SEZIONE ANALISI E STATISTICHE (GEMINI + CSV)
if st.session_state.show_analytics:
    st.markdown("---")
    st.subheader("📈 Analisi Predittiva Dati con Gemini AI")
    st.caption("Carica un file CSV per elaborare statistiche e pronostici avanzati tramite IA.")

    file_caricato = st.file_uploader("Carica un file CSV (es. classifica.csv)", type=["csv"])
    
    if file_caricato is not None:
        try:
            df_uploaded = pd.read_csv(file_caricato)
            st.success(f"File caricato correttamente: **{df_uploaded.shape[0]}** righe x **{df_uploaded.shape[1]}** colonne.")
            
            with st.expander("👁️ Anteprima File CSV"):
                st.dataframe(df_uploaded.head())

            domanda_utente = st.text_input(
                "🎯 Domanda o obiettivo per Gemini:",
                value="Sulla base di questi dati, qual è il pronostico sulle vendite o sui risultati futuri?"
            )

            if st.button("🤖 Genera Pronostico con Gemini", use_container_width=True):
                with st.spinner("Elaborazione della sintesi e interrogazione di Gemini in corso..."):
                    sintesi_txt = genera_sintesi_df(df_uploaded)
                    risposta_ai = interroga_gemini(sintesi_txt, domanda_utente)
                    
                    st.markdown("### 🔮 Risultato dell'Analisi AI")
                    st.markdown(risposta_ai)

        except Exception as e:
            st.error(f"Errore durante la lettura del file CSV: {e}")
    st.markdown("---")

# SEZIONE PRINCIPALE: MATCH ANALYZER
if successo and giornata:
    st.markdown(f"### 📅 **{giornata}ª Giornata di Serie A**")
    
    opzioni_match = {
        f"{m['homeTeam']['name']} vs {m['awayTeam']['name']}": m 
        for m in partite
    }
    
    partita_selezionata = st.selectbox(
        "🔍 Seleziona o cerca la partita da analizzare:",
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
    if status in ["FINISHED", "IN_PLAY", "PAUSED"]:
        score_h = match["score"]["fullTime"]["home"]
        score_a = match["score"]["fullTime"]["away"]
        risultato_str = f"Punteggio Live/Finale: **{score_h} - {score_a}**"
    else:
        risultato_str = f"Programmata per il: **{data_ora_str}**"

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
            <div class="vs-header">🎯 Risultato Probabile: {casa} {g_c} - {g_t} {trasferta}</div>
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
    st.caption("I principali marcatori delle due squadre ed il loro apporto atteso nel match.")

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
    st.error("Impossibile caricare le informazioni live dalla Serie A.")
