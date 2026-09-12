import numpy as np
import pandas as pd
from scipy.stats import poisson
import plotly.graph_objects as go

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
    """Calcola le probabilità 1X2 coerenti, la matrice di Poisson e il risultato esatto."""
    mult_c, _ = calcola_moltiplicatore_forma(form_casa)
    mult_t, _ = calcola_moltiplicatore_forma(form_trasferta)

    gf_c_adj = gf_casa * mult_c
    ga_c_adj = ga_casa / mult_c
    gf_t_adj = gf_trasferta * mult_t
    ga_t_adj = ga_trasferta / mult_t

    lambda_casa = max(0.5, (gf_c_adj + ga_t_adj) / 2)
    lambda_trasferta = max(0.5, (gf_t_adj + ga_c_adj) / 2)

    g_c = int(round(lambda_casa))
    g_t = int(round(lambda_trasferta))

    matrice_p = np.zeros((6, 6))
    for i in range(6):
        for j in range(6):
            matrice_p[i, j] = poisson.pmf(i, lambda_casa) * poisson.pmf(j, lambda_trasferta) * 100

    raw_prob_1 = np.sum(np.tril(matrice_p, -1))
    raw_prob_x = np.sum(np.diag(matrice_p))
    raw_prob_2 = np.sum(np.triu(matrice_p, 1))

    if g_c > g_t:
        prob_1 = max(raw_prob_1, raw_prob_x + 5.0, raw_prob_2 + 5.0)
        rem = 100.0 - prob_1
        prob_x = rem * (raw_prob_x / (raw_prob_x + raw_prob_2)) if (raw_prob_x + raw_prob_2) > 0 else rem / 2
        prob_2 = rem * (raw_prob_2 / (raw_prob_x + raw_prob_2)) if (raw_prob_x + raw_prob_2) > 0 else rem / 2
    elif g_c < g_t:
        prob_2 = max(raw_prob_2, raw_prob_1 + 5.0, raw_prob_x + 5.0)
        rem = 100.0 - prob_2
        prob_1 = rem * (raw_prob_1 / (raw_prob_1 + raw_prob_x)) if (raw_prob_1 + raw_prob_x) > 0 else rem / 2
        prob_x = rem * (raw_prob_x / (raw_prob_1 + raw_prob_x)) if (raw_prob_1 + raw_prob_x) > 0 else rem / 2
    else:
        prob_x = max(raw_prob_x, raw_prob_1 + 2.0, raw_prob_2 + 2.0)
        rem = 100.0 - prob_x
        prob_1 = rem * (raw_prob_1 / (raw_prob_1 + raw_prob_2)) if (raw_prob_1 + raw_prob_2) > 0 else rem / 2
        prob_2 = rem * (raw_prob_2 / (raw_prob_1 + raw_prob_2)) if (raw_prob_1 + raw_prob_2) > 0 else rem / 2

    prob_exact = matrice_p[min(g_c, 5), min(g_t, 5)]

    return prob_1, prob_x, prob_2, g_c, g_t, prob_exact, lambda_casa, lambda_trasferta, matrice_p

def calcola_probabilita_scommesse(matrice_p, prob_1, prob_x, prob_2):
    """Calcola le probabilità e le quote eque per Under/Over, Gol/NoGol e Doppia Chance."""
    tot_goals_matrix = np.fromfunction(lambda i, j: i + j, (6, 6), dtype=int)
    
    under15 = np.sum(matrice_p[tot_goals_matrix < 1.5])
    over15 = np.sum(matrice_p[tot_goals_matrix > 1.5])
    
    under25 = np.sum(matrice_p[tot_goals_matrix < 2.5])
    over25 = np.sum(matrice_p[tot_goals_matrix > 2.5])
    
    under35 = np.sum(matrice_p[tot_goals_matrix < 3.5])
    over35 = np.sum(matrice_p[tot_goals_matrix > 3.5])

    nogol = np.sum(matrice_p[0, :]) + np.sum(matrice_p[1:, 0])
    gol = 100.0 - nogol

    dc_1x = min(99.0, prob_1 + prob_x)
    dc_x2 = min(99.0, prob_x + prob_2)
    dc_12 = min(99.0, prob_1 + prob_2)

    def fair_odds(prob):
        return round(100.0 / prob, 2) if prob > 0 else 99.0

    scommesse_data = [
        {"Mercato": "Esito Finale (1X2)", "Esito": "1", "Probabilità": f"{prob_1:.1f}%", "Quota Equa": f"{fair_odds(prob_1):.2f}"},
        {"Mercato": "Esito Finale (1X2)", "Esito": "X", "Probabilità": f"{prob_x:.1f}%", "Quota Equa": f"{fair_odds(prob_x):.2f}"},
        {"Mercato": "Esito Finale (1X2)", "Esito": "2", "Probabilità": f"{prob_2:.1f}%", "Quota Equa": f"{fair_odds(prob_2):.2f}"},
        
        {"Mercato": "Doppia Chance", "Esito": "1X", "Probabilità": f"{dc_1x:.1f}%", "Quota Equa": f"{fair_odds(dc_1x):.2f}"},
        {"Mercato": "Doppia Chance", "Esito": "X2", "Probabilità": f"{dc_x2:.1f}%", "Quota Equa": f"{fair_odds(dc_x2):.2f}"},
        {"Mercato": "Doppia Chance", "Esito": "12", "Probabilità": f"{dc_12:.1f}%", "Quota Equa": f"{fair_odds(dc_12):.2f}"},
        
        {"Mercato": "Under / Over 1.5", "Esito": "Under 1.5", "Probabilità": f"{under15:.1f}%", "Quota Equa": f"{fair_odds(under15):.2f}"},
        {"Mercato": "Under / Over 1.5", "Esito": "Over 1.5", "Probabilità": f"{over15:.1f}%", "Quota Equa": f"{fair_odds(over15):.2f}"},
        
        {"Mercato": "Under / Over 2.5", "Esito": "Under 2.5", "Probabilità": f"{under25:.1f}%", "Quota Equa": f"{fair_odds(under25):.2f}"},
        {"Mercato": "Under / Over 2.5", "Esito": "Over 2.5", "Probabilità": f"{over25:.1f}%", "Quota Equa": f"{fair_odds(over25):.2f}"},
        
        {"Mercato": "Under / Over 3.5", "Esito": "Under 3.5", "Probabilità": f"{under35:.1f}%", "Quota Equa": f"{fair_odds(under35):.2f}"},
        {"Mercato": "Under / Over 3.5", "Esito": "Over 3.5", "Probabilità": f"{over35:.1f}%", "Quota Equa": f"{fair_odds(over35):.2f}"},
        
        {"Mercato": "Gol / NoGol", "Esito": "Gol", "Probabilità": f"{gol:.1f}%", "Quota Equa": f"{fair_odds(gol):.2f}"},
        {"Mercato": "Gol / NoGol", "Esito": "NoGol", "Probabilità": f"{nogol:.1f}%", "Quota Equa": f"{fair_odds(nogol):.2f}"},
    ]

    return pd.DataFrame(scommesse_data)

def genera_plotly_heatmap(matrice_p, squadra_casa, squadra_trasferta):
    """Genera una matrice Heatmap interattiva con Plotly per i risultati esatti."""
    gol_labels = ["0", "1", "2", "3", "4", "5"]
    
    annotations = []
    for i in range(6):
        for j in range(6):
            val = matrice_p[i, j]
            annotations.append(
                dict(
                    x=gol_labels[j],
                    y=gol_labels[i],
                    text=f"{val:.1f}%",
                    font=dict(color="white" if val < np.max(matrice_p)*0.7 else "black", size=11, family="sans-serif"),
                    showarrow=False
                )
            )

    fig = go.Figure(data=go.Heatmap(
        z=matrice_p,
        x=gol_labels,
        y=gol_labels,
        colorscale='Viridis',
        hoverinfo='x+y+z',
        hovertemplate=f'Gol {squadra_casa}: %{{y}}<br>Gol {squadra_trasferta}: %{{x}}<br>Probabilità: %{{z:.2f}}%<extra></extra>'
    ))

    fig.update_layout(
        title=f"<b>Matrice Probabilità Risultati Esatti</b><br><sup>{squadra_casa} (Righe) vs {squadra_trasferta} (Colonne)</sup>",
        title_x=0.5,
        title_font=dict(size=15, color="#f8fafc"),
        xaxis=dict(title=f"Gol {squadra_trasferta}", title_font=dict(color="#94a3b8"), tickfont=dict(color="#f8fafc")),
        yaxis=dict(title=f"Gol {squadra_casa}", title_font=dict(color="#94a3b8"), tickfont=dict(color="#f8fafc"), autorange='reversed'),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        annotations=annotations,
        margin=dict(l=40, r=40, t=60, b=40),
        height=400
    )
    return fig

def render_form_badges(form_list):
    """Genera l'HTML per mostrare i badge visuali della forma (W/D/L)."""
    if not form_list:
        return '<span style="color: #94a3b8; font-size: 12px;">Dati non disponibili</span>'
    
    html = ""
    for r in form_list:
        badge_class = r if r in ["W", "D", "L"] else "D"
        html += f'<span class="form-badge form-{badge_class}">{r}</span>'
    return html

def get_team_key_players(team_name, scorers_by_team, stats_squadre):
    """Restituisce i marcatori reali o genera un profilo stimato."""
    if team_name in scorers_by_team and scorers_by_team[team_name]:
        return scorers_by_team[team_name]
    
    st_team = stats_squadre.get(team_name, {"tot_gf": 10})
    tot_gf = max(1, st_team.get("tot_gf", 10))
    
    return [
        {
            "name": "Principale Riferimento Offensivo",
            "position": "Attaccante",
            "goals": max(1, int(tot_gf * 0.30)),
            "assists": 1,
            "penalties": 0,
            "playedMatches": "-",
            "is_fallback": True
        },
        {
            "name": "Seconda Punta / Rigorista",
            "position": "Attaccante/Centrocampista",
            "goals": max(1, int(tot_gf * 0.20)),
            "assists": 2,
            "penalties": 0,
            "playedMatches": "-",
            "is_fallback": True
        }
    ]
