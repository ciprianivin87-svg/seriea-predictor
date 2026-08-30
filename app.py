import streamlit as st
import requests
from datetime import datetime

st.set_page_config(page_title="Serie A Hub", page_icon="⚽", layout="centered")

# Styling CSS per le schede delle partite
st.markdown("""
<style>
    .main { background-color: #0f172a; }
    .match-card {
        background-color: #1e293b;
        border-radius: 10px;
        padding: 14px 20px;
        margin-bottom: 10px;
        border-left: 5px solid #38bdf8;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .team-name { font-weight: bold; color: #f8fafc; font-size: 16px; width: 40%; }
    .vs-badge { 
        color: #38bdf8; 
        font-weight: bold; 
        font-size: 13px; 
        background: #0f172a; 
        padding: 4px 10px; 
        border-radius: 6px; 
    }
    .match-date { color: #94a3b8; font-size: 12px; margin-top: 4px; }
</style>
""", unsafe_allow_html=True)

# API KEY GRATUITA (Sostituisci con la tua chiave se ne possiedi una per limiti di rateo più alti)
API_TOKEN = "e87cf7a0bb91419a8bc4a5ec409d5872"  # Token demo pubblico/test per football-data.org

@st.cache_data(ttl=3600)
def fetch_serie_a_matches():
    """Recupera la giornata corrente e le partite dal provider API live."""
    url = "https://api.football-data.org/v4/competitions/SA/matches"
    headers = {"X-Auth-Token": API_TOKEN}
    
    try:
        response = requests.get(url, headers=headers, timeout=8)
        if response.status_code == 200:
            data = response.json()
            matches = data.get("matches", [])
            
            # Identifica la giornata corrente attiva o più vicina
            current_matchday = 1
            for match in matches:
                if match.get("status") in ["IN_PLAY", "PAUSED"]:
                    current_matchday = match.get("matchday")
                    break
                elif match.get("status") == "TIMED":
                    match_date = datetime.strptime(match["utcDate"], "%Y-%m-%dT%H:%M:%SZ")
                    if match_date >= datetime.utcnow():
                        current_matchday = match.get("matchday")
                        break
            
            # Filtra le partite appartenenti alla giornata individuata
            giornata_partite = [m for m in matches if m.get("matchday") == current_matchday]
            return current_matchday, giornata_partite, True
    except Exception as e:
        pass
    
    return None, [], False

# INTERFACCIA UTENTE
st.title("⚽ Serie A Hub")

with st.spinner("Connessione ai server del campionato in corso..."):
    giornata, partite, successo = fetch_serie_a_matches()

if successo and giornata:
    st.markdown(f"### 📅 Giornata Attuale: **{giornata}ª Giornata**")
    st.caption(f"Data di oggi: **{datetime.now().strftime('%d/%m/%Y')}**")
    st.markdown("---")
    
    for match in partite:
        casa = match["homeTeam"]["name"]
        trasferta = match["awayTeam"]["name"]
        
        # Formattazione orario/data partita
        utc_time = datetime.strptime(match["utcDate"], "%Y-%m-%dT%H:%M:%SZ")
        data_ora_str = utc_time.strftime("%d/%m/%Y alle %H:%M")
        
        # Risultato se partita già iniziata o conclusa
        status = match["status"]
        if status in ["FINISHED", "IN_PLAY", "PAUSED"]:
            score_home = match["score"]["fullTime"]["home"]
            score_away = match["score"]["fullTime"]["away"]
            badge_text = f"{score_home} - {score_away}"
        else:
            badge_text = "VS"

        st.markdown(
            f"""
            <div class="match-card">
                <div class="team-name" style="text-align: right;">{casa}</div>
                <div style="text-align: center;">
                    <span class="vs-badge">{badge_text}</span>
                    <div class="match-date">{data_ora_str}</div>
                </div>
                <div class="team-name" style="text-align: left;">{trasferta}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
else:
    st.error("Impossibile recuperare i dati live in questo momento. Verificare la connessione di rete.")
