import streamlit as st
from datetime import date, datetime

st.set_page_config(page_title="Serie A Predictor", page_icon="⚽", layout="centered")

# 1. STRUTTURA DATI: CALENDARIO GIORNATE SERIE A (Esempio date)
# Puoi estendere questo dizionario con tutte le 38 giornate e i relativi match
CALENDARIO_GIORNATE = {
    1: {
        "inizio": date(2026, 8, 22),
        "fine": date(2026, 8, 24),
        "partite": [
            ("Inter", "Torino"),
            ("Juventus", "Parma"),
            ("Milan", "Cremonese"),
            ("Napoli", "Sassuolo")
        ]
    },
    2: {
        "inizio": date(2026, 8, 29),
        "fine": date(2026, 8, 31),
        "partite": [
            ("Lazio", "Venezia"),
            ("Roma", "Bologna"),
            ("Atalanta", "Pisa"),
            ("Fiorentina", "Udinese")
        ]
    },
    3: {
        "inizio": date(2026, 9, 12),
        "fine": date(2026, 9, 14),
        "partite": [
            ("Inter", "Milan"),
            ("Juventus", "Roma"),
            ("Napoli", "Atalanta"),
            ("Bologna", "Lazio")
        ]
    }
}

def get_giornata_corrente():
    """Riconosce la giornata attuale in base alla data odierna."""
    oggi = date.today()
    
    # Cerca la giornata corrispondente al periodo corrente
    for num_giornata, info in CALENDARIO_GIORNATE.items():
        if info["inizio"] <= oggi <= info["fine"]:
            return num_giornata, info["partite"], "in_corso"
    
    # Se oggi si trova in una pausa/infrasettimanale, prende la prossima giornata disponibile
    for num_giornata, info in CALENDARIO_GIORNATE.items():
        if oggi < info["inizio"]:
            return num_giornata, info["partite"], "prossima"
            
    # Default (ultima giornata se il campionato è finito)
    ultima = max(CALENDARIO_GIORNATE.keys())
    return ultima, CALENDARIO_GIORNATE[ultima]["partite"], "conclusa"

# 2. LOGICA DELL'INTERFACCIA
st.title("⚽ Serie A Hub")

giornata_num, partite_giornata, stato = get_giornata_corrente()
data_oggi_str = datetime.now().strftime("%d/%m/%Y")

# Header Sezione Giornata
st.markdown(f"### 📅 Giornata Attuale: **{giornata_num}ª Giornata**")
st.caption(f"Data rilevata dal sistema: **{data_oggi_str}**")

if stato == "in_corso":
    st.info("🔥 Giornata di campionato attualmente in svolgimento.")
elif stato == "prossima":
    st.warning("⏳ Prossima giornata in programma.")

# 3. MOSTRA LE PARTITE DELLA GIORNATA
st.subheader("Match in programma:")

for casa, trasferta in partite_giornata:
    st.markdown(
        f"""
        <div style="background-color: #1e293b; padding: 12px 20px; border-radius: 8px; margin-bottom: 8px; border-left: 4px solid #38bdf8; display: flex; justify-content: space-between; align-items: center;">
            <span style="font-weight: bold; color: #f8fafc; font-size: 16px;">{casa}</span>
            <span style="color: #94a3b8; font-weight: bold;">VS</span>
            <span style="font-weight: bold; color: #f8fafc; font-size: 16px;">{trasferta}</span>
        </div>
        """,
        unsafe_allow_html=True
    )
