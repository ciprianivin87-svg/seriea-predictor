# Pesi dei malus basati su Ruolo e Importanza del giocatore assente
IMPACT_WEIGHTS = {
    "GK": {"key": 0.12, "regular": 0.05},  # Portiere titolare assente impatta molto la difesa
    "DF": {"key": 0.08, "regular": 0.03},  # Difensore
    "MF": {"key": 0.07, "regular": 0.03},  # Centrocampista (impatto bilanciato)
    "FW": {"key": 0.10, "regular": 0.04},  # Attaccante titolare assente impatta l'attacco
}


def calculate_team_malus(absentees_list):
  """Calcola le percentuali totali di penalità per Attacco e Difesa.

  absentees_list è una lista di dict: [{'name': '...', 'role': 'FW',
  'importance': 'key'}, ...]
  """
  attack_malus = 0.0
  defense_malus = 0.0

  for player in absentees_list:
    role = player.get("role", "MF")
    importance = player.get("importance", "regular")

    # Recupera i pesi di riferimento
    weights = IMPACT_WEIGHTS.get(role, IMPACT_WEIGHTS["MF"])
    weight_val = weights.get(importance, 0.03)

    # Distribuzione dell'impatto in base al ruolo
    if role == "FW":
      attack_malus += weight_val
      defense_malus += weight_val * 0.2  # Un attacco debole pressa meno
    elif role == "GK":
      defense_malus += weight_val
    elif role == "DF":
      defense_malus += weight_val
      attack_malus += weight_val * 0.15  # Meno spinta dai terzini
    elif role == "MF":
      attack_malus += weight_val * 0.6
      defense_malus += weight_val * 0.6

  # Cap massimo di malus cumulabile (es. max 40% di ridimensionamento)
  attack_malus = min(attack_malus, 0.40)
  defense_malus = min(defense_malus, 0.40)

  return attack_malus, defense_malus


def adjust_lambda_for_absences(
    lambda_home_att, lambda_away_att, home_absentees, away_absentees
):
  """Applica i malus ai Lambda di partenza calcolati sul modello storico/Poisson."""
  home_att_malus, home_def_malus = calculate_team_malus(home_absentees)
  away_att_malus, away_def_malus = calculate_team_malus(away_absentees)

  # Riduzione attacco squadra di casa
  adj_lambda_home = lambda_home_att * (1 - home_att_malus)
  # Se la difesa ospite è indebolita, l'attacco di casa guadagna un piccolo bonus compensativo
  adj_lambda_home *= 1 + (away_def_malus * 0.5)

  # Riduzione attacco squadra ospite
  adj_lambda_away = lambda_away_att * (1 - away_att_malus)
  # Se la difesa di casa è indebolita, l'attacco ospite guadagna un piccolo bonus compensativo
  adj_lambda_away *= 1 + (home_def_malus * 0.5)

  return round(adj_lambda_home, 3), round(adj_lambda_away, 3)


# --- TEST RAPIDO ---
if __name__ == "__main__":
  print("Avvio test calcolo impatto assenze...")

  # Simulia assenze per la squadra di casa (es. Attaccante e Portiere titolari out)
  sample_home_absentees = [
      {"name": "VLAHOVIC", "role": "FW", "importance": "key"},
      {"name": "PERIN", "role": "GK", "importance": "key"},
  ]

  # Simulia assenze per la squadra ospite (es. 1 centrocampista riserva)
  sample_away_absentees = [
      {"name": "ROVELLA", "role": "MF", "importance": "regular"}
  ]

  base_lambda_home = 1.85
  base_lambda_away = 1.10

  adj_home, adj_away = adjust_lambda_for_absences(
      base_lambda_home,
      base_lambda_away,
      sample_home_absentees,
      sample_away_absentees,
  )

  print(f"\nLambda Casa base: {base_lambda_home} ➔ Rettificato: {adj_home}")
  print(f"Lambda Ospite base: {base_lambda_away} ➔ Rettificato: {adj_away}")
