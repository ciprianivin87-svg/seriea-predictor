pip install beautifulsoup4 requests

import re
import requests
from bs4 import BeautifulSoup

# Lista ufficiale squadre Serie A per il matching del parser
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


def fetch_live_absentees():
  """Scrapa e struttura gli assenti di Serie A divisi per squadra."""
  url = "https://www.fantacalcio.it/indisponibili-serie-a"
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like"
          " Gecko) Chrome/120.0.0.0 Safari/537.36"
      )
  }

  try:
    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code != 200:
      return {}

    soup = BeautifulSoup(response.text, "html.parser")
    full_text = soup.get_text(separator=" ", strip=True)

    absentees_by_team = {team: [] for team in SERIE_A_TEAMS}

    # Isoliamo i blocchi di testo per ciascuna squadra
    for i, team in enumerate(SERIE_A_TEAMS):
      next_team = (
          SERIE_A_TEAMS[i + 1] if i + 1 < len(SERIE_A_TEAMS) else "Indisponibili"
      )

      # Pattern Regex per estrarre il testo compreso tra il nome di una squadra e la successiva
      pattern = rf"{team}\s+Infortunati(.*?)(?={next_team}|$)"
      match = re.search(pattern, full_text, re.DOTALL | re.IGNORECASE)

      if match:
        team_section = match.group(1)

        # Estraiamo i cognomi/nomi dei calciatori menzionati prima della descrizione dell'infortunio
        # Esempio catturato: "Yildiz l'attaccante turco...", "Meret Il portiere..."
        players = re.findall(
            r"([A-Z][a-zA-L'\s]+?)\s+(?:il|l'|l’)\s*(?:attaccante|difensore|centrocampista|portiere|regist|ala|cursore|metronomo)",
            team_section,
        )

        for p in players:
          clean_name = p.strip().upper()
          if len(clean_name) > 2 and clean_name not in [
              "INFORTUNATI",
              "SQUALIFICATI",
              "DIFFIDATI",
          ]:
            absentees_by_team[team].append(clean_name)

    return absentees_by_team

  except Exception as e:
    print(f"Errore durante lo scraping: {e}")
    return {}


def get_team_absentees(team_name, absentees_dict):
  """Restituisce la lista di assenti per una determinata squadra."""
  team_upper = team_name.upper()
  for team in absentees_dict:
    if team in team_upper or team_upper in team:
      return absentees_dict[team]
  return []


if __name__ == "__main__":
  print("Avvio test parser indisponibili...")
  data = fetch_live_absentees()

  if data:
    print("\n✅ Scraping e Parsing completati con successo!")
    for team, absentees in data.items():
      if absentees:
        print(f"\n{team}: {', '.join(absentees)}")
  else:
    print("❌ Nessun dato estratto.")
