import streamlit as st
import requests
import numpy as np
import pandas as pd
from scipy.stats import poisson
import plotly.express as px

# --- CONFIGURAZIONE E TITOLO ---
st.set_page_config(page_title="Serie A Predictor", layout="wide")
st.title("⚽ Serie A - Predictor & Match Analyst")

# --- RECUPERO SEGRETI ---
FOOTBALL_DATA_API_KEY = st.secrets.get("FOOTBALL_DATA_API_KEY", "")

# --- FUNZIONI DI SUPPORTO ---
@st.cache_data(ttl=3600)
def fetch_matches():
    """Recupera le partite della Serie A da football-data.org"""
    url = "https://api.football-data.org/v4/competitions/SA/matches"
    headers = {"X-Auth-Token": FOOTBALL_DATA_API_KEY} if FOOTBALL_DATA_API_KEY else {}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("matches", [])
    return []

def calcola_parametri_poisson(df_finished):
    """Calcola le medie gol in casa e in trasferta del campionato e delle squadre."""
    avg_home_goals = df_finished['home_score'].mean() if not df_finished.empty else 1.5
    avg_away_goals = df_finished['away_score'].mean() if not df_finished.empty else 1.1
    return avg_home_goals, avg_away_goals

def calcola_probabilita_poisson(lambda_home, lambda_away, max_goals=6):
    """Genera la matrice delle probabilità per i punteggi esatti."""
    prob_matrix = np.zeros((max_goals, max_goals))
    for h in range(max_goals):
        for a in range(max_goals):
            prob_matrix[h, a] = poisson.pmf(h, lambda_home) * poisson.pmf(a, lambda_away)
    
    prob_home = np.sum(np.tril(prob_matrix, -1)) * 100
    prob_draw = np.sum(np.diag(prob_matrix)) * 100
    prob_away = np.sum(np.triu(prob_matrix, 1)) * 100
    
    return prob_matrix, prob_home, prob_draw, prob_away

# --- CARICAMENTO DATI ---
matches = fetch_matches()

if not matches:
    st.warning("Impossibile recuperare i dati. Verifica la configurazione della tua API Key o le quote di accesso a football-data.org.")
else:
    # Preparazione DataFrame
    data = []
    for m in matches:
        data.append({
            'id': m['id'],
            'matchday': m['matchday'],
            'status': m['status'],
            'home_team': m['homeTeam']['name'],
            'away_team': m['awayTeam']['name'],
            'home_score': m['score']['fullTime']['home'],
            'away_score': m['score']['fullTime']['away']
        })
    df_matches = pd.DataFrame(data)

    # Filtra partite concluse per le medie
    df_finished = df_matches[df_matches['status'] == 'FINISHED'].copy()
    
    avg_home_goals, avg_away_goals = calcola_parametri_poisson(df_finished)

    # --- SELEZIONE PARTITA ---
    st.sidebar.header("Filtri Partita")
    squadre = sorted(list(set(df_matches['home_team'].tolist() + df_matches['away_team'].tolist())))
    
    team_home = st.sidebar.selectbox("Squadra in Casa", squadre, index=0)
    squadre_away = [s for s in squadre if s != team_home]
    team_away = st.sidebar.selectbox("Squadra in Trasferta", squadre_away, index=0)

    # --- CALCOLO ATTESA GOL (LAMBDA) ---
    if not df_finished.empty:
        # Attacco e difesa casa
        home_g_scored = df_finished[df_finished['home_team'] == team_home]['home_score'].mean() or avg_home_goals
        home_g_conceded = df_finished[df_finished['home_team'] == team_home]['away_score'].mean() or avg_away_goals
        
        # Attacco e difesa trasferta
        away_g_scored = df_finished[df_finished['away_team'] == team_away]['away_score'].mean() or avg_away_goals
        away_g_conceded = df_finished[df_finished['away_team'] == team_away]['home_score'].mean() or avg_home_goals

        lambda_home = (home_g_scored / avg_home_goals) * (away_g_conceded / avg_home_goals) * avg_home_goals
        lambda_away = (away_g_scored / avg_away_goals) * (home_g_conceded / avg_away_goals) * avg_away_goals
    else:
        lambda_home, lambda_away = 1.4, 1.0

    # Calcolo Matrice e Percentuali
    prob_matrix, p_home, p_draw, p_away = calcola_probabilita_poisson(lambda_home, lambda_away)

    # --- VISUALIZZAZIONE RISULTATI ---
    col1, col2, col3 = st.columns(3)
    col1.metric(f"Vittoria {team_home} (1)", f"{p_home:.1f}%")
    col2.metric("Pareggio (X)", f"{p_draw:.1f}%")
    col3.metric(f"Vittoria {team_away} (2)", f"{p_away:.1f}%")

    st.subheader(f"Matrice Probabilità Punteggio: {team_home} vs {team_away}")
    
    fig = px.imshow(
        prob_matrix * 100,
        labels=dict(x=f"Gol {team_away}", y=f"Gol {team_home}", color="Probabilità %"),
        x=[str(i) for i in range(6)],
        y=[str(i) for i in range(6)],
        text_auto=".1f",
        color_continuous_scale="Blues"
    )
    st.plotly_chart(fig, use_container_width=True)
