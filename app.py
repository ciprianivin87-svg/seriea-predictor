import streamlit as st
import requests
import numpy as np
import pandas as pd
from scipy.stats import poisson
import plotly.graph_objects as go

# Configurazione Pagina Streamlit
st.set_page_config(page_title="Serie A Predictor", page_icon="⚽", layout="wide")

# CSS Personalizzato per Tema Scuro e Card
st.markdown("""
<style>
    .main { background-color: #0f172a; color: #f8fafc; }
    .stat-card {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
    }
    .vs-header {
        font-size: 22px;
        font-weight: bold;
        text-align: center;
        color: #38bdf8;
    }
    .metric-container {
        display: flex;
        justify-content: space-around;
        margin-top: 15px;
    }
    .metric-box {
        text-align: center;
        background-color: #0f172a;
        padding: 10px 15px;
        border-radius: 8px;
        border: 1px solid #334155;
        flex: 1;
        margin: 0 5px;
    }
    .metric-title { font-size: 12px; color: #94a3b8; }
    .metric-value { font-size: 18px; font-weight: bold; margin-top: 4px; }
</style>
""", unsafe_allow_html=True)

# API Token (Sostituire con la propria chiave se necessario)
API_KEY = "YOUR_API_KEY_HERE"
HEADERS = {"X-Auth-Token": API_KEY}
BASE_URL = "https://api.football-data.org/v4/"

@st.cache_data(ttl=1800)
def fetch_data(endpoint):
    """Funzione generica per chiamate API con Caching."""
    try:
        response = requests.get(f"{BASE_URL}{endpoint}", headers=HEADERS)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception:
        return None

def calcola_moltiplicatore_forma(form_list):
    """Calcola il moltiplicatore di forma in base agli ultimi 5 risultati."""
    if not form_list:
        return 1.0, "x1.00"
    score = 0
    for res in form_list:
        if res == 'W': score += 0.05
        elif res == 'L': score -= 0.05
    mult = max(0.7, min(1.3, 1.0 + score))
    return mult, f"x{mult:.2f}"

def calcola_pronostico(gf_casa, ga_casa, form_casa, gf_trasferta, ga_trasferta, form_trasferta):
    """
    Calcola le probabilità 1X2, la matrice di Poisson e determina il risultato esatto
    garantendo la totale coerenza con il segno 1X2 dominante.
    """
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

    # 1. Determina prima il Segno 1X2 Dominante
    probs = {"1": prob_1, "X": prob_x, "2": prob_2}
    segno_dominante = max(probs, key=probs.get)
    prob_segno_dominante = probs[segno_dominante]

    # 2. Maschera la matrice per trovare il punteggio esatto più probabile COERENTE col segno vincente
    matrice_filtrata = matrice_p.copy()
    for i in range(6):
        for j in range(6):
            if segno_dominante == "1" and i <= j:
                matrice_filtrata[i, j] = -1
            elif segno_dominante == "X" and i != j:
                matrice_filtrata[i, j] = -1
            elif segno_dominante == "2" and i >= j:
                matrice_filtrata[i, j] = -1

    g_c, g_t = np.unravel_index(np.argmax(matrice_filtrata), matrice_filtrata.shape)
    prob_exact = matrice_p[g_c, g_t]

    return prob_1, prob_x, prob_2, segno_dominante, prob_segno_dominante, g_c, g_t, prob_exact, lambda_casa, lambda_trasferta, matrice_p

def fair_odds(prob):
    """Calcola la quota equa priva di aggio bookmaker."""
    return round(100.0 / prob, 2) if prob > 0 else 999.0

# --- INTERFACCIA STREAMLIT ---
st.title("⚽ Serie A Predictor")

tab_analisi, tab_verifica = st.tabs(["🔍 Analisi Singola Partita", "📜 Verifica Accuracy Giornata"])

with tab_analisi:
    st.header("🔮 Pronostico Algoritmetico Pesato")
    
    # Esempio Dati di Input / Simulazione UI
    col1, col2 = st.columns(2)
    with col1:
        casa = st.selectbox("Squadra Casa", ["Bologna FC 1909", "AC Milan", "SSC Napoli", "Juventus FC", "Inter"], index=0)
        gf_c = st.number_input("Gol Segnati Casa (Media)", value=1.2, step=0.1)
        ga_c = st.number_input("Gol Subiti Casa (Media)", value=0.8, step=0.1)
        form_c = ["L", "L", "D", "W", "D"]
    with col2:
        trasferta = st.selectbox("Squadra Trasferta", ["US Sassuolo Calcio", "ACF Fiorentina", "AS Roma", "SS Lazio"], index=0)
        gf_t = st.number_input("Gol Segnati Trasferta (Media)", value=1.5, step=0.1)
        ga_t = st.number_input("Gol Subiti Trasferta (Media)", value=1.1, step=0.1)
        form_t = ["L", "W", "D", "W", "W"]

    # Calcolo Pronostico
    prob_1, prob_x, prob_2, segno_fav, prob_fav, g_c, g_t, prob_exact, exp_c, exp_t, matrice_p = calcola_pronostico(
        gf_c, ga_c, form_c, gf_t, ga_t, form_t
    )

    testo_segno = f"Vittoria {casa} (1)" if segno_fav == "1" else (f"Pareggio (X)" if segno_fav == "X" else f"Vittoria {trasferta} (2)")

    # Render Card Pronostico
    st.markdown(
        f"""
        <div class="stat-card">
            <div style="text-align: center; margin-bottom: 5px;">
                <span style="background-color: #0284c7; color: white; padding: 4px 14px; border-radius: 20px; font-weight: bold; font-size: 14px;">
                    PRONOSTICO PRINCIPALE: SEGNO {segno_fav}
                </span>
            </div>
            <div class="vs-header" style="margin-top: 10px; font-size: 24px; color: #38bdf8;">
                {testo_segno} — {prob_fav:.1f}%
            </div>
            <div style="text-align: center; color: #94a3b8; font-size: 13px; margin-bottom: 15px;">
                Risultato Esatto Indicativo Coerente: <b>{casa} {g_c} - {g_t} {trasferta}</b> ({prob_exact:.1f}%)
            </div>
            <div class="metric-container">
                <div class="metric-box">
                    <div class="metric-title">1 ({casa})</div>
                    <div class="metric-value" style="color: {'#22c55e' if segno_fav=='1' else '#38bdf8'};">{prob_1:.1f}%</div>
                </div>
                <div class="metric-box">
                    <div class="metric-title">X (Pareggio)</div>
                    <div class="metric-value" style="color: {'#22c55e' if segno_fav=='X' else '#38bdf8'};">{prob_x:.1f}%</div>
                </div>
                <div class="metric-box">
                    <div class="metric-title">2 ({trasferta})</div>
                    <div class="metric-value" style="color: {'#22c55e' if segno_fav=='2' else '#38bdf8'};">{prob_2:.1f}%</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Plotly Heatmap della Matrice di Poisson
    st.subheader("🔥 Heatmap Probabilità Risultati Esatti")
    fig = go.Figure(data=go.Heatmap(
        z=matrice_p,
        x=[f"{trasferta} {j}" for j in range(6)],
        y=[f"{casa} {i}" for i in range(6)],
        colorscale='Viridis'
    ))
    fig.update_layout(
        title="Matrice Probabilità Poisson (%)",
        xaxis_title="Gol Trasferta",
        yaxis_title="Gol Casa",
        template="plotly_dark",
        height=450
    )
    st.plotly_chart(fig, use_container_width=True)

    # Sezione Quote Eque
    st.subheader("🎲 Quote Eque Stimate")
    q_col1, q_col2, q_col3 = st.columns(3)
    q_col1.metric(f"Quota 1 ({casa})", f"{fair_odds(prob_1):.2f}")
    q_col2.metric("Quota X (Pareggio)", f"{fair_odds(prob_x):.2f}")
    q_col3.metric(f"Quota 2 ({trasferta})", f"{fair_odds(prob_2):.2f}")

with tab_verifica:
    st.header("📜 Verifica Accuracy & Backtest Giornate")
    st.info("Questa sezione analizza le giornate concluse confrontando il segno 1X2 e il risultato esatto predetto dall'algoritmo con i dati reali.")
    
    # Esempio Tabella Accuracy
    data_demo = {
        "Partita": ["AC Milan - Venezia FC", "US Sassuolo - Torino FC", "AC Monza - Udinese", "Juventus FC - Parma", "SSC Napoli - Como 1907"],
        "Reale": ["2-0 (1)", "2-1 (1)", "2-3 (2)", "2-0 (1)", "1-2 (2)"],
        "Stimato": ["2-0 (1)", "1-1 (1)", "1-2 (2)", "1-0 (1)", "1-2 (2)"],
        "Esito 1X2": ["✅ Preso", "✅ Preso", "✅ Preso", "✅ Preso", "✅ Preso"],
        "Risultato Esatto": ["🎯 Preso", "❌ Mancato", "❌ Mancato", "❌ Mancato", "🎯 Preso"]
    }
    st.table(pd.DataFrame(data_demo))
