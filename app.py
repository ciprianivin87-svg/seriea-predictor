import streamlit as st
import requests
from datetime import datetime

st.set_page_config(page_title="Serie A Hub", page_icon="⚽", layout="centered")

# CSS Styling per le schede delle partite
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
    .team-name { font-weight: bold; color: #f8fafc; font-size: 15px; width: 40%; }
    .vs-badge { 
        color: #38bdf8; 
        font-weight: bold; 
        font-size: 13px; 
        background: #0f172a; 
        padding: 4px 10px; 
        border-radius: 6px; 
    }
    .match-date { color: #94a3b8; font-size: 11px; margin-top: 4px; }
</style>
""", unsafe_allow_html=True)

# 🔑 INSERISCI QUI LA TUA API KEY PERSONALE DI FOOTBALL-DATA.ORG
API_TOKEN = "2e52e41c56bc4d85b2cc3df2d03c00af"

@st.cache_data(ttl=1800)
def fetch_serie_a_matches():
    """Recupera la giornata corrente e le partite della Serie A tramite API."""
    url = "https://api.football-data.org/v4/competitions/SA/matches"
    headers = {"X-Auth-Token": API_TOKEN}
    
    try:
        response = requests.get(url, headers=headers, timeout=8)
        if response.status_code == 200:
            data = response.json()
            matches = data.get("matches", [])
            
            # Recupera la giornata corrente della competizione
            current_matchday = None
            if matches:
                # Trova la prima partita in programma o in corso
                for match in matches:
                    if match.get("status") in ["IN_PLAY", "PAUSED", "TIMED"]:
                        current_matchday = match.get("matchday")
                        break
                
                # Se tutte le partite estratte sono terminate, prende l'ultima giornata disputata
                if not current_matchday:
                    current_matchday = matches[-1].get("matchday")

            giornata_partite = [m for m in matches if m.get("matchday") == current_matchday]
            return current_matchday, giornata_partite, True, "OK"
        else:
            return None, [], False, f"Errore API: Codice {response.status_code}"
    except Exception as e:
        return None, [], False, f"Eccezione: {str(e)}"

# INTERFACCIA PRINCIPALE
st.title("⚽ Serie A Hub")

if API_TOKEN == "INSERISCI_QUI_LA_TUA_API_KEY":
    st.warning("⚠️ Inserisci la tua API Key personale di football-data.org nel codice per abilitare la connessione live.")

giornata, partite, successo, messaggio = fetch_serie_a_matches()

if successo and giornata:
    st.sidebar.success("🟢 Connessione API attiva (Serie A)")
    st.markdown(f"### 📅 Giornata Attuale: **{giornata}ª Giornata**")
    st.caption(f"Data di oggi: **{datetime.now().strftime('%d/%m/%Y')}**")
    st.markdown("---")
    
    for match in partite:
        casa = match["homeTeam"]["name"]
        trasferta = match["awayTeam"]["name"]
        
        # Gestione orari UTC -> Stringa formattata
        try:
            utc_time = datetime.strptime(match["utcDate"], "%Y-%m-%dT%H:%M:%SZ")
            data_ora_str = utc_time.strftime("%d/%m/%Y alle %H:%M")
        except ValueError:
            data_ora_str = match["utcDate"]
        
        status = match["status"]
        if status in ["FINISHED", "IN_PLAY", "PAUSED"]:
            score_h = match["score"]["fullTime"]["home"]
            score_a = match["score"]["fullTime"]["away"]
            badge_text = f"{score_h} - {score_a}"
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
    st.error(f"Impossibile caricare le partite: {messaggio}")
