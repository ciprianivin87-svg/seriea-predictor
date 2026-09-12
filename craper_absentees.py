import re
import requests
from bs4 import BeautifulSoup

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

    for i, team in enumerate(SERIE_A_TEAMS):
      next_team = (
          SERIE_A_TEAMS[i + 1] if i + 1 < len(SERIE_A_TEAMS) else "Indisponibili"
      )

      pattern = rf"{team}\s+Infortunati(.*?)(?={next_team}|$)"
      match = re.search(pattern, full_text, re.DOTALL | re.IGNORECASE)

      if match:
        team_section = match.group(1)
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
  print(fetch_live_absentees())
