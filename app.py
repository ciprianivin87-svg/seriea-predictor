import os
import sys

# Aggiunge la directory del file corrente al sys.path di Python
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Ora gli import dei moduli locali funzioneranno senza errori
from api_squad_mapper import get_team_squad_from_api, parse_absentees_with_squad
from lineup_impact import adjust_lambda_for_absences, calculate_team_malus
from scraper_absentees import fetch_live_absentees, get_team_absentees

import numpy as np
import pandas as pd
from scipy.stats import poisson
import streamlit as st

# Importazione dei moduli personalizzati sviluppati negli Step 1, 2 e 3
from api_squad_mapper import get_team_squad_from_api, parse_absentees_with_squad
from lineup_impact import adjust_lambda_for_absences, calculate_team_malus
from scraper_absentees import fetch_live_absentees, get_team_absentees

st.set_page_config(
    page_title="Predictor Serie A - Live Lineup Impact", layout="wide"
)

st.title("⚽ Predictor Serie A con Impatto Formazioni Live")

# --- SIDEBAR: SELEZIONE MATCH ---
st.sidebar.header("Impostazioni Partita")

SERIE_A_TEAMS = [
    "ATALANTA",
    "BOLOGNA",
    "CAGLIARI",
    "COMO",
    "FIORENTINA",
    "FROSINONE",
    "GENOA",
    "INTER",
    "JUVENTUS",
    "LAZIO",
    "LECCE",
    "MILAN",
    "MONZA",
    "NAPOLI",
    "PARMA",
    "ROMA",
    "SASSUOLO",
    "TORINO",
    "UDINESE",
    "VENEZIA",
]

home_team = st.sidebar.selectbox("Squadra Casa", SERIE_A_TEAMS, index=8)  # Juve
away_team = st.sidebar.selectbox(
    "Squadra Ospite", SERIE_A_TEAMS, index=13
)  # Napoli

st.sidebar.markdown("---")
st.sidebar.subheader("Lambda Base (Expected Goals)")
base_lambda_home = st.sidebar.number_input(
    "Lambda Casa Base", min_value=0.2, max_value=5.0, value=1.65, step=0.05
)
base_lambda_away = st.sidebar.number_input(
    "Lambda Ospite Base", min_value=0.2, max_value=5.0, value=1.10, step=0.05
)

# --- CARICAMENTO DATI INDISPONIBILI LIVE ---
st.subheader("📋 Gestione Indisponibili e Formazioni Live")

col_btn1, col_btn2 = st.columns([1, 4])
with col_btn1:
  if st.button("🔄 Aggiorna Indisponibili Live"):
    st.cache_data.clear()
    st.success("Dati aggiornati!")

# Fetch dei dati dallo scraper (Fantacalcio)
raw_absentees_dict = fetch_live_absentees()

# Extraction e mapping per le due squadre selezionate
raw_home_absent = get_team_absentees(home_team, raw_absentees_dict)
raw_away_absent = get_team_absentees(away_team, raw_absentees_dict)

squad_home_api = get_team_squad_from_api(home_team)
squad_away_api = get_team_squad_from_api(away_team)

parsed_home_absent = parse_absentees_with_squad(
    raw_home_absent, squad_home_api
)
parsed_away_absent = parse_absentees_with_squad(
    raw_away_absent, squad_away_api
)

# Interfaccia a colonne per visualizzare gli assenti
col_home, col_away = st.columns(2)

with col_home:
  st.markdown(f"### {home_team}")
  if parsed_home_absent:
    st.warning(f"Assenti rilevati: {len(parsed_home_absent)}")
    home_df = pd.DataFrame(parsed_home_absent)
    st.dataframe(home_df, use_container_width=True)
  else:
    st.success("Nessuna assenza critica segnalata.")

with col_away:
  st.markdown(f"### {away_team}")
  if parsed_away_absent:
    st.warning(f"Assenti rilevati: {len(parsed_away_absent)}")
    away_df = pd.DataFrame(parsed_away_absent)
    st.dataframe(away_df, use_container_width=True)
  else:
    st.success("Nessuna assenza critica segnalata.")

# --- CALCOLO MATEMATICO MALUS E LAMBDA RETTIFICATI ---
adj_lambda_home, adj_lambda_away = adjust_lambda_for_absences(
    base_lambda_home, base_lambda_away, parsed_home_absent, parsed_away_absent
)

home_att_m, home_def_m = calculate_team_malus(parsed_home_absent)
away_att_m, away_def_m = calculate_team_malus(parsed_away_absent)

st.markdown("---")
st.subheader("⚖️ Rettifica Expected Goals (Lambda)")

m_col1, m_col2, m_col3, m_col4 = st.columns(4)
m_col1.metric("Lambda Casa Orig.", f"{base_lambda_home:.2f}")
m_col2.metric(
    "Lambda Casa Rettificato",
    f"{adj_lambda_home:.2f}",
    delta=f"-{home_att_m * 100:.1f}% Att.",
    delta_color="inverse",
)
m_col3.metric("Lambda Ospite Orig.", f"{base_lambda_away:.2f}")
m_col4.metric(
    "Lambda Ospite Rettificato",
    f"{adj_lambda_away:.2f}",
    delta=f"-{away_att_m * 100:.1f}% Att.",
    delta_color="inverse",
)

# --- SIMULAZIONE POISSON / PROBABILITÀ MATCH ---
st.markdown("---")
st.subheader("📊 Matrice di Probabilità & Esiti Match")


def calculate_poisson_matrix(lh, la, max_goals=5):
  matrix = np.zeros((max_goals + 1, max_goals + 1))
  for i in range(max_goals + 1):
    for j in range(max_goals + 1):
      matrix[i, j] = poisson.pmf(i, lh) * poisson.pmf(j, la)
  return matrix


matrix = calculate_poisson_matrix(adj_lambda_home, adj_lambda_away)

p_home = np.sum(np.tril(matrix, -1))
p_draw = np.sum(np.diag(matrix))
p_away = np.sum(np.triu(matrix, 1))

res_col1, res_col2, res_col3 = st.columns(3)
res_col1.metric(f"1 ({home_team})", f"{p_home * 100:.1f}%")
res_col2.metric("X (Pareggio)", f"{p_draw * 100:.1f}%")
res_col3.metric(f"2 ({away_team})", f"{p_away * 100:.1f}%")

# Tabella visuale della matrice di score
with st.expander("Visualizza Matrice Risultati Esatti"):
  df_matrix = pd.DataFrame(
      matrix,
      index=[f"Casa {i}" for i in range(6)],
      columns=[f"Ospite {j}" for j in range(6)],
  )
  st.dataframe(
      df_matrix.style.highlight_max(axis=None, color="lightgreen"),
      use_container_width=True,
  )
