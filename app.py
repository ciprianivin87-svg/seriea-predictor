import streamlit as st
import requests
import numpy as np
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

@st.cache_data(ttl=1800)
def fetch_serie_a_matches():
    """Recupera la giornata corrente e le partite della Serie A."""
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

@st.cache_data(ttl=3600)
def fetch_team_stats():
    """Recupera la classifica e le metriche di rendimento dei club."""
    url = "https://api.football-data.org/v4/competitions/SA/standings"
    stats = {}
    try:
        response = requests.get(url, headers=HEADERS, timeout=8)
        if response.status_code == 200:
            data = response.json()
            standings = data["standings"][0]["table"]
            
            for row in standings:
                team_name = row["team"]["name"]
                played = max(1, row["playedGames"])
                stats[team_name] = {
                    "pos": row["position"],
                    "punti": row["points"],
                    "gf": row["goalsFor"] / played,
                    "ga": row["goalsAgainst"] / played,
                    "tot_gf": row["goalsFor"],
                    "tot_ga": row["goalsAgainst"],
                    "form": row.get("form", "W,D,L,W,D")
                }
    except Exception:
        pass
    return stats

def calcola_moltiplicatore_forma(form_str):
    """
    Calcola il moltiplicatore di forma basato sulle ultime partite.
    Vittoria (W) = +5%, Pareggio (D) = 0%, Sconfitta (L) = -5%
    """
    if not form_str or form_str == "N/A":
        return 1.0, []
    
    risultati = [r.strip() for r in form_str.split(",") if r.strip()]
    
    modificatore = 0.0
    for r in risultati[-5:]:
        if r == "W":
            modificatore += 0.05
        elif r == "L":
            modificatore -= 0.05

    moltiplicatore = max(0.7, min(1.3, 1.0 + modificatore))
    return moltiplicatore, risultati[-5:]

def calcola_pronostico(gf_casa, ga_casa, form_casa, gf_trasferta, ga_trasferta, form_trasferta):
    """Calcola le probabilità 1X2 e il risultato esatto pesando la forma recente."""
    mult_c, _ = calcola_moltiplicatore_forma(form_casa)
    mult_t, _ = calcola_moltiplicatore_forma(form_trasferta)

    # Applicazione del fattore forma alle medie gol offensive e difensive
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

    return prob_1, prob_x, prob_2, g_c, g_t, prob_exact

def render_form_badges(form_list):
    """Genera l'HTML per mostrare i badge visuali della forma (W/D/L)."""
    html = ""
    for r in form_list:
        html += f'<span class="form-badge form-{r}">{r}</span>'
    return html

# --- LAYOUT APPLICAZIONE ---

st.title("⚽ Serie A Hub & Predictor")

giornata, partite, successo = fetch_serie_a_matches()
stats_squadre = fetch_team_stats()

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
    
    st_c = stats_squadre.get(casa, {"pos": "-", "punti": 0, "gf": 1.2, "ga": 1.1, "form": "W,D,L,W,D"})
    st_t = stats_squadre.get(trasferta, {"pos": "-", "punti": 0, "gf": 1.1, "ga": 1.2, "form": "D,L,W,D,L"})

    mult_c, list_c = calcola_moltiplicatore_forma(st_c["form"])
    mult_t, list_t = calcola_moltiplicatore_forma(st_t["form"])

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

    prob_1, prob_x, prob_2, g_c, g_t, prob_exact = calcola_pronostico(
        st_c["gf"], st_c["ga"], st_c["form"],
        st_t["gf"], st_t["ga"], st_t["form"]
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

else:
    st.error("Impossibile caricare le informazioni live dalla Serie A.")
