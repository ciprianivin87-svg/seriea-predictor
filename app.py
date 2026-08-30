import streamlit as st
import requests
import numpy as np
from datetime import datetime
from scipy.stats import poisson

st.set_page_config(page_title="Serie A Hub & Predictor", page_icon="⚽", layout="centered")

# Visual Styling CSS
st.markdown("""
<style>
    .main { background-color: #0f172a; }
    .match-card {
        background-color: #1e293b;
        border-radius: 10px;
        padding: 14px 20px;
        margin-bottom: 10px;
        border-left: 5px solid #38bdf8;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .pred-card {
        background-color: #1e293b;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 15px;
        border: 1px solid #334155;
    }
    .team-name { font-weight: bold; color: #f8fafc; font-size: 15px; width: 40%; }
    .vs-badge { 
        color: #38bdf8; 
        font-weight: bold; 
        font-size: 13px; 
        background: #0f172a; 
        padding: 4px 10px; 
        border-radius: 6px; 
    }
    .match-date { color: #94a3b8; font-size: 11px; margin-top: 4px; }
    .prob-box {
        background-color: #0f172a;
        padding: 8px;
        border-radius: 6px;
        text-align: center;
        color: #cbd5e1;
        font-size: 13px;
    }
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
    """Recupera la classifica e calcola la media gol fatti/subiti per squadra."""
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
                goals_for = row["goalsFor"] / played
                goals_against = row["goalsAgainst"] / played
                
                stats[team_name] = {
                    "gf": goals_for,
                    "ga": goals_against
                }
    except Exception:
        pass
    return stats

def calcola_pronostico(gf_casa, ga_casa, gf_trasferta, ga_trasferta):
    """Calcola le probabilità 1X2 e il risultato esatto usando la distribuzione di Poisson."""
    lambda_casa = max(0.5, (gf_casa + ga_trasferta) / 2)
    lambda_trasferta = max(0.5, (gf_trasferta + ga_casa) / 2)

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

# --- LAYOUT APPLICAZIONE ---

st.title("⚽ Serie A Hub & Predictor")

giornata, partite, successo = fetch_serie_a_matches()
stats_squadre = fetch_team_stats()

if successo and giornata:
    st.markdown(f"### 📅 Giornata Attuale: **{giornata}ª Giornata**")
    st.caption(f"Data di oggi: **{datetime.now().strftime('%d/%m/%Y')}**")
    st.markdown("---")
    
    # SEZIONE 1: CALENDARIO PARTITE GIORNATA
    for match in partite:
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
            badge_text = f"{score_h} - {score_a}"
        else:
            badge_text = "VS"

        st.markdown(
            f"""
            <div class="match-card">
                <div class="team-name" style="text-align: right;">{casa}</div>
                <div style="text-align: center;">
                    <span class="vs-badge">{badge_text}</span>
                    <div class="match-date">{data_ora_str}</div>
                </div>
                <div class="team-name" style="text-align: left;">{trasferta}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # SEZIONE 2: PRONOSTICI AUTOMATICI
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("---")
    st.subheader("🔮 Pronostici della Giornata")
    st.caption("Analisi quantitativa basata sulle metriche offensive/difensive stagionali delle squadre.")

    for match in partite:
        casa = match["homeTeam"]["name"]
        trasferta = match["awayTeam"]["name"]
        
        # Recupera metriche o valori standard se l'inizio stagione ha pochi dati
        st_c = stats_squadre.get(casa, {"gf": 1.3, "ga": 1.1})
        st_t = stats_squadre.get(trasferta, {"gf": 1.1, "ga": 1.3})
        
        prob_1, prob_x, prob_2, g_c, g_t, prob_exact = calcola_pronostico(
            st_c["gf"], st_c["ga"], st_t["gf"], st_t["ga"]
        )
        
        st.markdown(
            f"""
            <div class="pred-card">
                <div style="font-weight: bold; color: #f8fafc; font-size: 16px; margin-bottom: 10px;">
                    ⚽ {casa} vs {trasferta}
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; margin-bottom: 10px;">
                    <div class="prob-box">1: <b>{prob_1:.1f}%</b></div>
                    <div class="prob-box">X: <b>{prob_x:.1f}%</b></div>
                    <div class="prob-box">2: <b>{prob_2:.1f}%</b></div>
                </div>
                <div style="color: #38bdf8; font-size: 14px; font-weight: bold;">
                    🎯 Risultato previsto: {casa} {g_c} - {g_t} {trasferta} <span style="font-weight: normal; color: #94a3b8; font-size: 12px;">({prob_exact:.1f}% probabilità)</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
else:
    st.error("Impossibile caricare le informazioni live. Verificare la connessione API.")
