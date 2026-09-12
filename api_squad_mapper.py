import requests
import streamlit as st

# Sostituisci con la tua chiave API di RapidAPI / API-Football
API_KEY = "2a9990ef4f5c9655413c0dd133819c82"
BASE_URL = "https://v3.football.api-sports.io"

HEADERS = {
    "x-apisports-key": API_KEY,
    "x-rapidapi-host": "v3.football.api-sports.io",
}

# Mapping degli ID delle squadre di Serie A per API-Football
# (ID ufficiali di API-Football per le squadre della stagione)
SERIE_A_TEAM_IDS = {
    "ATALANTA": 499,
    "BOLOGNA": 500,
    "CAGLIARI": 490,
    "COMO": 1020,
    "FIORENTINA": 502,
    "FROSINONE": 512,
    "GENOA": 495,
    "INTER": 505,
    "JUVENTUS": 496,
    "LAZIO": 487,
    "LECCE": 867,
    "MILAN": 489,
    "MONZA": 1579,
    "NAPOLI": 492,
    "PARMA": 523,
    "ROMA": 497,
    "SASSUOLO": 488,
    "TORINO": 503,
    "UDINESE": 494,
    "VENEZIA": 517,
}


@st.cache_data(ttl=86400)  # Salva in cache i risultati per 24 ore
def get_team_squad_from_api(team_name):
  """Recupera la rosa ufficiale e i ruoli di una squadra tramite API-Football."""
  team_upper = team_name.upper()
  team_id = SERIE_A_TEAM_IDS.get(team_upper)

  if not team_id:
    print(f"⚠️ ID squadra non trovato per: {team_name}")
    return {}

  url = f"{BASE_URL}/players/squads"
  params = {"team": team_id}

  try:
    response = requests.get(url, headers=HEADERS, params=params, timeout=10)
    data = response.json()

    if not data.get("response"):
      print(f"❌ Nessuna risposta dall'API per {team_name}")
      return {}

    squad_data = {}
    players_list = data["response"][0]["players"]

    for player in players_list:
      name = player["name"].upper()
      position = player["position"]  # Goalkeeper, Defender, Midfielder, Attacker

      # Normalizzazione dei ruoli
      role_map = {
          "Goalkeeper": "GK",
          "Defender": "DF",
          "Midfielder": "MF",
          "Attacker": "FW",
      }

      role = role_map.get(position, "MF")

      # Assegnazione di un'importanza di default basata sul numero di maglia
      # (Se ha un numero <= 11 o è tra i titolari tipici)
      number = player.get("number")
      importance = "key" if number and number <= 11 else "regular"

      squad_data[name] = {"role": role, "importance": importance}

    return squad_data

  except Exception as e:
    print(f"Errore nel recupero della rosa via API: {e}")
    return {}


def parse_absentees_with_squad(raw_absent_list, team_squad_api):
  """Incrocia i nomi estratti dallo scraper con la rosa dell'API per trovare i ruoli e l'importanza."""
  parsed_absentees = []

  for entry in raw_absent_list:
    entry_clean = entry.upper()
    matched = False

    for player_name, info in team_squad_api.items():
      # Controllo sul nome completo o parti del nome (es. cognome)
      name_parts = [p for p in player_name.split() if len(p) > 2]

      if player_name in entry_clean or any(
          part in entry_clean for part in name_parts
      ):
        parsed_absentees.append({
            "name": player_name,
            "role": info["role"],
            "importance": info["importance"],
        })
        matched = True
        break

    # Se un giocatore non viene trovato nella rosa dell'API
    if not matched:
      parsed_absentees.append({
          "name": entry,
          "role": "MF",  # Ruolo neutro di fallback
          "importance": "regular",
      })

  return parsed_absentees


# --- TEST RAPIDO ---
if __name__ == "__main__":
  print("Avvio test API Squad Mapper...")
  # Testiamo recuperando la rosa della Juventus
  juve_squad = get_team_squad_from_api("JUVENTUS")

  if juve_squad:
    print(
        f"\n✅ Rosa recuperata con successo! Trovati {len(juve_squad)} giocatori."
    )
    # Esempio di incrocio con alcuni assenti fittizi o dello scraper
    test_absentees = ["YILDIZ", "LOCATELLI", "CAMBIASO"]
    matched_absentees = parse_absentees_with_squad(test_absentees, juve_squad)

    print("\nEsito matching assenti:")
    for item in matched_absentees:
      print(
          f"  - {item['name']}: Ruolo={item['role']}, Importanza={item['importance']}"
      )
  else:
    print("❌ Inserisci una API_KEY valida per eseguire il test.")
