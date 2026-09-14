import numpy as np
import pandas as pd
from scipy.stats import poisson
import plotly.graph_objects as go

def calcola_moltiplicatore_forma(form_list):
    """
    Calcola un moltiplicatore di forma basato sulle ultime 5 partite.
    Vittoria (W) = 3pt, Pareggio (D) = 1pt, Sconfitta (L) = 0pt.
    """
    if not form_list:
        return 1.0, ["D", "D", "D", "D", "D"]
    
    punti = 0
    for res in form_list:
        if res == "W": punti += 3
        elif res == "D": punti += 1
        
    punti_max = len(form_list) * 3
    if punti_max == 0:
        return 1.0, form_list
        
    rapporto = punti / punti_max
    # Moltiplicatore compreso tra 0.85 (forma pessima) e 1.15 (forma eccellente)
    moltiplicatore = 0.85 + (rapporto * 0.30)
    return moltiplicatore, form_list

def render_form_badges(form_list):
    """Genera l'HTML per mostrare i badge W/D/L delle ultime 5 partite."""
    html_badges = ""
    for res in form_list:
        color_class = f"form-{res}" if res in ["W", "D", "L"] else "form-D"
        html_badges += f'<span class="form-badge {color_class}">{res}</span>'
    return html_badges

def calcola_pronostico(gf_casa, ga_casa, form_casa, gf_trasferta, ga_trasferta, form_trasferta):
    """
    Calcola le aspettative di gol e la matrice di probabilità di Poisson
    pesata sullo stato di forma delle due squadre.
    """
    mult_c, _ = calcola_moltiplicatore_forma(form_casa)
    mult_t, _ = calcola_moltiplicatore_forma(form_trasferta)

    # Stima dei gol attesi basata sul potenziale d'attacco e difesa
    exp_gol_casa = max(0.2, (gf_casa * ga_trasferta / 1.1) * mult_c)
    exp_gol_trasferta = max(0.2, (gf_trasferta * ga_casa / 1.1) * mult_t)

    # Costruzione della matrice di probabilità (fino a 6 gol per squadra)
    max_goals = 6
    matrice_p = np.zeros((max_goals, max_goals))

    for i in range(max_goals):
        for j in range(max_goals):
            matrice_p[i, j] = poisson.pmf(i, exp_gol_casa) * poisson.pmf(j, exp_gol_trasferta)

    # Normalizzazione probabilità
    matrice_p = matrice_p / np.sum(matrice_p)

    prob_1 = np.sum(np.tril(matrice_p, -1))
    prob_x = np.sum(np.diag(matrice_p))
    prob_2 = np.sum(np.triu(matrice_p, 1))

    # Risultato più probabile
    idx_max = np.unravel_index(np.argmax(matrice_p, axis=None), matrice_p.shape)
    g_casa_pred = idx_max[0]
    g_trasferta_pred = idx_max[1]
    prob_esatto = matrice_p[g_casa_pred, g_trasferta_pred]

    return prob_1, prob_x, prob_2, g_casa_pred, g_trasferta_pred, prob_esatto, exp_gol_casa, exp_gol_trasferta, matrice_p

def calcola_probabilita_scommesse(matrice_p, prob_1, prob_x, prob_2):
    """Genera la tabella con probabilità di scommessa e quote eque stimate."""
    prob_over15 = np.sum([matrice_p[i, j] for i in range(6) for j in range(6) if (i + j) > 1.5])
    prob_over25 = np.sum([matrice_p[i, j] for i in range(6) for j in range(6) if (i + j) > 2.5])
    prob_gg = np.sum([matrice_p[i, j] for i in range(1, 6) for j in range(1, 6)])

    data = [
        {"Mercato": "1 (Vittoria Casa)", "Probabilità": f"{prob_1*100:.1f}%", "Quota Equa": f"{1/prob_1:.2f}" if prob_1 > 0 else "N/A"},
        {"Mercato": "X (Pareggio)", "Probabilità": f"{prob_x*100:.1f}%", "Quota Equa": f"{1/prob_x:.2f}" if prob_x > 0 else "N/A"},
        {"Mercato": "2 (Vittoria Trasferta)", "Probabilità": f"{prob_2*100:.1f}%", "Quota Equa": f"{1/prob_2:.2f}" if prob_2 > 0 else "N/A"},
        {"Mercato": "Gol / Gol (Entrambe segnano)", "Probabilità": f"{prob_gg*100:.1f}%", "Quota Equa": f"{1/prob_gg:.2f}" if prob_gg > 0 else "N/A"},
        {"Mercato": "Over 1.5 Gol", "Probabilità": f"{prob_over15*100:.1f}%", "Quota Equa": f"{1/prob_over15:.2f}" if prob_over15 > 0 else "N/A"},
        {"Mercato": "Over 2.5 Gol", "Probabilità": f"{prob_over25*100:.1f}%", "Quota Equa": f"{1/prob_over25:.2f}" if prob_over25 > 0 else "N/A"}
    ]
    return pd.DataFrame(data)

def genera_plotly_heatmap(matrice_p, squadra_casa, squadra_trasferta):
    """Genera la Heatmap interattiva della distribuzione dei gol stimata."""
    z_data = (matrice_p[:5, :5] * 100).round(1)
    
    fig = go.Figure(data=go.Heatmap(
        z=z_data,
        x=[f"{squadra_trasferta} {i}" for i in range(5)],
        y=[f"{squadra_casa} {i}" for i in range(5)],
        colorscale='Viridis',
        text=z_data,
        texttemplate="%{text}%",
        textfont={"size": 12},
        hoverongaps=False
    ))

    fig.update_layout(
        title="🔥 Distribution Matrix Risultati Esatti (%)",
        xaxis_title=f"Gol {squadra_trasferta}",
        yaxis_title=f"Gol {squadra_casa}",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color="#f8fafc")
    )
    return fig

def estrai_formazioni_match(match_data):
    """
    Estrae le formazioni ufficiali, i moduli, gli allenatori e i panchinari 
    dall'oggetto match restituito dall'API di football-data.org.
    """
    home_team = match_data.get("homeTeam", {})
    away_team = match_data.get("awayTeam", {})

    home_lineup = home_team.get("lineup", [])
    away_lineup = away_team.get("lineup", [])
    
    home_bench = home_team.get("bench", [])
    away_bench = away_team.get("bench", [])

    home_formation = home_team.get("formation", "N/D")
    away_formation = away_team.get("formation", "N/D")

    home_coach = home_team.get("coach", {}).get("name", "N/D")
    away_coach = away_team.get("coach", {}).get("name", "N/D")

    disponibili = len(home_lineup) > 0 and len(away_lineup) > 0

    return {
        "disponibili": disponibili,
        "home": {
            "formation": home_formation,
            "coach": home_coach,
            "lineup": home_lineup,
            "bench": home_bench
        },
        "away": {
            "formation": away_formation,
            "coach": away_coach,
            "lineup": away_lineup,
            "bench": away_bench
        }
    }

def get_team_key_players(squadra, marcatori_dict, stats_squadre):
    """Recupera i giocatori chiave di una squadra o fornisce un fallback generico."""
    if squadra in marcatori_dict and marcatori_dict[squadra]:
        return marcatori_dict[squadra]
    
    return [
        {"name": "Top Scorer di Squadra", "goals": "Leader reti", "is_fallback": True},
        {"name": "Riferimento Offensivo", "goals": "Titolare", "is_fallback": True}
    ]
