import streamlit as st
import numpy as np
import pandas as pd
from scipy.stats import poisson
import plotly.graph_objects as go

try:
    import google.generativeai as genai
except ImportError:
    genai = None

# 1. GENERATORE REPORT GEMINI
@st.cache_data(ttl=3600)
def genera_report_gemini(squadra_casa, squadra_trasferta, st_c, st_t, prob_1, prob_x, prob_2, g_c, g_t):
    if genai is None:
        return "⚠️ La libreria google-generativeai non è installata nei requisiti."
        
    try:
        api_key = st.secrets.get("GEMINI_API_KEY")
        if not api_key:
            return "⚠️ Chiave GEMINI_API_KEY non trovata nei Secrets di Streamlit."
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')

        pos_c = st_c.get('pos', 'N/D')
        pos_t = st_t.get('pos', 'N/D')
        pt_c = st_c.get('punti', 'N/D')
        pt_t = st_t.get('punti', 'N/D')

        prompt = f"""
        Sei un analista tattico e giornalista sportivo professionista. 
        Genera un'analisi pre-partita dinamica per l'incontro: {squadra_casa} vs {squadra_trasferta}.

        Dati a disposizione:
        - Classifica: {squadra_casa} ({pos_c}° posto, {pt_c} pt) vs {squadra_trasferta} ({pos_t}° posto, {pt_t} pt)
        - Efficacia Offensiva/Difensiva: {squadra_casa} ({st_c['gf']:.2f} gol fatti/gara, {st_c['ga']:.2f} subiti/gara) vs {squadra_trasferta} ({st_t['gf']:.2f} gol fatti/gara, {st_t['ga']:.2f} subiti/gara)
        - Ultime 5 gare: {squadra_casa} ({st_c.get('form_list')}) vs {squadra_trasferta} ({st_t.get('form_list')})
        - Stima algoritmo Poisson: Vittoria Casa {prob_1:.1f}%, Pareggio {prob_x:.1f}%, Vittoria Trasferta {prob_2:.1f}%. Risultato esatto più probabile: {g_c}-{g_t}.

        Struttura la risposta in Markdown con 3 sezioni chiare:
        1. **Contesto e Forma Attuale**: Breve panoramica sul momento delle due squadre.
        2. **Prospettiva Tattica & Tendenze**: Come si incrociano i valori d'attacco e difesa delle due squadre.
        3. **Previsione dell'Analista**: Considerazioni finali sul pronostico stimato.

        Usa un tono giornalistico, chiaro, avvincente e conciso (massimo 180 parole in totale). Non inserire introduzioni generiche.
        """

        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ Impossibile generare l'analisi al momento: {str(e)}"

# 2. MOLTIPLICATORE FORMA
def calcola_moltiplicatore_forma(form_list):
    if not form_list:
        return 1.0, []
    punti = 0
    for res in form_list:
        if res == 'W': punti += 3
        elif res == 'D': punti += 1
    
    max_punti = len(form_list) * 3
    perc = punti / max_punti if max_punti > 0 else 0.5
    
    # Moltiplicatore tra 0.85 e 1.15
    moltiplicatore = 0.85 + (perc * 0.30)
    return moltiplicatore, form_list

# 3. PRONOSTICO POISSON
def calcola_pronostico(gf_c, ga_c, form_c, gf_t, ga_t, form_t):
    m_c, _ = calcola_moltiplicatore_forma(form_c)
    m_t, _ = calcola_moltiplicatore_forma(form_t)

    exp_c = max(0.2, (gf_c * ga_t) * m_c)
    exp_t = max(0.2, (gf_t * ga_c) * m_t)

    max_gol = 6
    matrice = np.zeros((max_gol, max_gol))

    for i in range(max_gol):
        for j in range(max_gol):
            matrice[i, j] = poisson.pmf(i, exp_c) * poisson.pmf(j, exp_t)

    prob_1 = np.sum(np.tril(matrice, -1)) * 100
    prob_x = np.sum(np.diag(matrice)) * 100
    prob_2 = np.sum(np.triu(matrice, 1)) * 100

    idx_max = np.unravel_index(np.argmax(matrice, axis=None), matrice.shape)
    g_c_pred, g_t_pred = idx_max[0], idx_max[1]
    prob_exact = matrice[g_c_pred, g_t_pred] * 100

    return prob_1, prob_x, prob_2, g_c_pred, g_t_pred, prob_exact, exp_c, exp_t, matrice

# 4. PROBABILITÀ SCOMMESSE
def calcola_probabilita_scommesse(matrice, prob_1, prob_x, prob_2):
    prob_over15 = np.sum([matrice[i, j] for i in range(6) for j in range(6) if i + j > 1.5]) * 100
    prob_over25 = np.sum([matrice[i, j] for i in range(6) for j in range(6) if i + j > 2.5]) * 100
    prob_gg = np.sum([matrice[i, j] for i in range(1, 6) for j in range(1, 6)]) * 100

    dati = [
        {"Esito": "1 (Vittoria Casa)", "Probabilità": f"{prob_1:.1f}%", "Quota Equa": f"{100/max(prob_1, 0.1):.2f}"},
        {"Esito": "X (Pareggio)", "Probabilità": f"{prob_x:.1f}%", "Quota Equa": f"{100/max(prob_x, 0.1):.2f}"},
        {"Esito": "2 (Vittoria Trasferta)", "Probabilità": f"{prob_2:.1f}%", "Quota Equa": f"{100/max(prob_2, 0.1):.2f}"},
        {"Esito": "Gol (Entrambe segnano)", "Probabilità": f"{prob_gg:.1f}%", "Quota Equa": f"{100/max(prob_gg, 0.1):.2f}"},
        {"Esito": "Over 1.5 Gol", "Probabilità": f"{prob_over15:.1f}%", "Quota Equa": f"{100/max(prob_over15, 0.1):.2f}"},
        {"Esito": "Over 2.5 Gol", "Probabilità": f"{prob_over25:.1f}%", "Quota Equa": f"{100/max(prob_over25, 0.1):.2f}"},
    ]
    return pd.DataFrame(dati)

# 5. HEATMAP PLOTLY
def genera_plotly_heatmap(matrice, casa, trasferta):
    fig = go.Figure(data=go.Heatmap(
        z=matrice * 100,
        x=[0, 1, 2, 3, 4, 5],
        y=[0, 1, 2, 3, 4, 5],
        colorscale='Viridis',
        texttemplate="%{z:.1f}%",
        textcellsformat=".1f"
    ))
    fig.update_layout(
        title=f"Matrice Risultati Esatti: {casa} vs {trasferta}",
        xaxis_title=f"Gol {trasferta}",
        yaxis_title=f"Gol {casa}",
        template="plotly_dark",
        height=400
    )
    return fig

# 6. BADGES FORMA
def render_form_badges(form_list):
    html = ""
    for res in form_list:
        html += f'<span class="form-badge form-{res}">{res}</span> '
    return html if html else "N/D"

# 7. GIOCATORI CHIAVE
def get_team_key_players(team_name, marcatori_dict, stats_squadre):
    if team_name in marcatori_dict:
        return marcatori_dict[team_name]
    
    st_t = stats_squadre.get(team_name, {})
    gf = st_t.get("tot_gf", 10)
    
    return [
        {"name": "Attaccante Principale", "goals": max(1, int(gf * 0.35))},
        {"name": "Centrocampista Offensivo", "goals": max(1, int(gf * 0.20))}
    ]

# 8. FORMAZIONI MATCH
def estrai_formazioni_match(match_data):
    # Struttura di default per l'API football-data.org
    return {
        "disponibili": False,
        "home": {"formation": "N/D", "coach": "N/D", "lineup": [], "bench": []},
        "away": {"formation": "N/D", "coach": "N/D", "lineup": [], "bench": []}
    }
