import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson

st.set_page_config(page_title="Serie A Predictor Pro", page_icon="⚽", layout="centered")

# Styling CSS per Mobile & Card Giocatori
st.markdown("""
<style>
    .main { background-color: #0f172a; }
    .stButton>button { width: 100%; background-color: #38bdf8; color: black; font-weight: bold; border-radius: 8px; padding: 10px; }
    .stSelectbox label { color: #f8fafc !important; font-weight: bold; }
    .player-card {
        background-color: #1e293b;
        border-left: 4px solid #38bdf8;
        padding: 10px 12px;
        margin-bottom: 8px;
        border-radius: 6px;
    }
    .player-name { font-weight: bold; color: #f8fafc; font-size: 14px; }
    .player-stat { color: #94a3b8; font-size: 12px; }
</style>
""", unsafe_allow_html=True)

# DATABASE METRICHE SQUADRE SERIE A 2026/2027 (AGGIORNATO)
dati_squadre = {
    'Atalanta': {
        'xG_fatti': 1.90, 'xGA_subiti': 1.15, 'possesso': 53.5,
        'stelle': [
            {'nome': 'Mateo Retegui', 'ruolo': 'ATT', 'stat': 'xG/90: 0.62 | Colpi di Testa: 2.1'},
            {'nome': 'Ademola Lookman', 'ruolo': 'ATT', 'stat': 'Occasioni Create: 2.6/90'},
            {'nome': 'Charles De Ketelaere', 'ruolo': 'TRQ', 'stat': 'Assist Attesi: 0.28/90'}
        ]
    },
    'Bologna': {
        'xG_fatti': 1.35, 'xGA_subiti': 1.10, 'possesso': 53.0,
        'stelle': [
            {'nome': 'Riccardo Orsolini', 'ruolo': 'ATT', 'stat': 'xG/90: 0.42 | Tiri/90: 2.9'},
            {'nome': 'Santiago Castro', 'ruolo': 'ATT', 'stat': 'Pressioni Alte: 11.4/90'}
        ]
    },
    'Cagliari': {
        'xG_fatti': 1.00, 'xGA_subiti': 1.40, 'possesso': 43.5,
        'stelle': [
            {'nome': 'Roberto Piccoli', 'ruolo': 'ATT', 'stat': 'xG/90: 0.32 | Duelli: 4.1'},
            {'nome': 'Zito Luvumbo', 'ruolo': 'ATT', 'stat': 'Dribbling: 2.1/90'}
        ]
    },
    'Como': {
        'xG_fatti': 1.45, 'xGA_subiti': 1.25, 'possesso': 52.0,
        'stelle': [
            {'nome': 'Nico Paz', 'ruolo': 'TRQ', 'stat': 'Tiri/90: 2.8 | Assist Attesi: 0.32'},
            {'nome': 'Patrick Cutrone', 'ruolo': 'ATT', 'stat': 'xG/90: 0.45'}
        ]
    },
    'Fiorentina': {
        'xG_fatti': 1.45, 'xGA_subiti': 1.20, 'possesso': 52.0,
        'stelle': [
            {'nome': 'Moise Kean', 'ruolo': 'ATT', 'stat': 'xG/90: 0.50 | Scatti: 8.5'},
            {'nome': 'Albert Gudmundsson', 'ruolo': 'TRQ', 'stat': 'Passaggi Chiave: 2.4/90'}
        ]
    },
    'Frosinone': {
        'xG_fatti': 1.05, 'xGA_subiti': 1.50, 'possesso': 44.0,
        'stelle': [
            {'nome': 'Giuseppe Ambrosino', 'ruolo': 'ATT', 'stat': 'xG/90: 0.35'},
            {'nome': 'Luca Garritano', 'ruolo': 'CEN', 'stat': 'Passaggi Chiave: 1.9/90'}
        ]
    },
    'Genoa': {
        'xG_fatti': 1.10, 'xGA_subiti': 1.25, 'possesso': 45.0,
        'stelle': [
            {'nome': 'Andrea Pinamonti', 'ruolo': 'ATT', 'stat': 'xG/90: 0.38'},
            {'nome': 'Morten Frendrup', 'ruolo': 'CEN', 'stat': 'Contrasti Vinti: 3.4/90'}
        ]
    },
    'Inter': {
        'xG_fatti': 2.10, 'xGA_subiti': 0.80, 'possesso': 58.4,
        'stelle': [
            {'nome': 'Lautaro Martinez', 'ruolo': 'ATT', 'stat': 'xG/90: 0.65 | Tiri/90: 3.4'},
            {'nome': 'Hakan Calhanoglu', 'ruolo': 'CEN', 'stat': 'Passaggi Chiave: 2.8'},
            {'nome': 'Nicolò Barella', 'ruolo': 'CEN', 'stat': 'Recuperi: 5.2/90'}
        ]
    },
    'Juventus': {
        'xG_fatti': 1.70, 'xGA_subiti': 0.85, 'possesso': 53.0,
        'stelle': [
            {'nome': 'Dusan Vlahovic', 'ruolo': 'ATT', 'stat': 'xG/90: 0.58 | Conversione: 18%'},
            {'nome': 'Kenan Yildiz', 'ruolo': 'TRQ', 'stat': 'Dribbling: 2.3/90'},
            {'nome': 'Gleison Bremer', 'ruolo': 'DIF', 'stat': 'Duelli Vinti: 68%'}
        ]
    },
    'Lazio': {
        'xG_fatti': 1.50, 'xGA_subiti': 1.15, 'possesso': 50.5,
        'stelle': [
            {'nome': 'Taty Castellanos', 'ruolo': 'ATT', 'stat': 'xG/90: 0.48'},
            {'nome': 'Mattia Zaccagni', 'ruolo': 'ATT', 'stat': 'Falli Subiti: 2.8/90'}
        ]
    },
    'Lecce': {
        'xG_fatti': 0.95, 'xGA_subiti': 1.40, 'possesso': 42.0,
        'stelle': [
            {'nome': 'Nikola Krstovic', 'ruolo': 'ATT', 'stat': 'Tiri Totali: 3.2/90'},
            {'nome': 'Lameck Banda', 'ruolo': 'ATT', 'stat': 'Dribbling: 2.4/90'}
        ]
    },
    'Milan': {
        'xG_fatti': 1.85, 'xGA_subiti': 1.10, 'possesso': 54.2,
        'stelle': [
            {'nome': 'Christian Pulisic', 'ruolo': 'TRQ', 'stat': 'Partecipazione Gol: 42%'},
            {'nome': 'Rafael Leao', 'ruolo': 'ATT', 'stat': 'Dribbling: 3.5/90'},
            {'nome': 'Tijjani Reijnders', 'ruolo': 'CEN', 'stat': 'Passaggi: 91%'}
        ]
    },
    'Monza': {
        'xG_fatti': 1.10, 'xGA_subiti': 1.35, 'possesso': 46.2,
        'stelle': [
            {'nome': 'Milan Djuric', 'ruolo': 'ATT', 'stat': 'Duelli Aerei: 5.8/90'},
            {'nome': 'Matteo Pessina', 'ruolo': 'CEN', 'stat': 'Accuratezza Passaggi: 88%'}
        ]
    },
    'Napoli': {
        'xG_fatti': 1.75, 'xGA_subiti': 0.95, 'possesso': 56.1,
        'stelle': [
            {'nome': 'Romelu Lukaku', 'ruolo': 'ATT', 'stat': 'xG+xA/90: 0.72'},
            {'nome': 'Khvicha Kvaratskhelia', 'ruolo': 'ATT', 'stat': 'Tiri in Porta: 1.8/90'},
            {'nome': 'Stanislav Lobotka', 'ruolo': 'CEN', 'stat': 'Recuperi: 6.4/90'}
        ]
    },
    'Parma': {
        'xG_fatti': 1.25, 'xGA_subiti': 1.45, 'possesso': 47.0,
        'stelle': [
            {'nome': 'Dennis Man', 'ruolo': 'ATT', 'stat': 'Dribbling: 2.8/90 | xG: 0.39'},
            {'nome': 'Ange-Yoan Bonny', 'ruolo': 'ATT', 'stat': 'Sponde Chiave: 2.1/90'}
        ]
    },
    'Roma': {
        'xG_fatti': 1.60, 'xGA_subiti': 1.00, 'possesso': 52.5,
        'stelle': [
            {'nome': 'Paulo Dybala', 'ruolo': 'TRQ', 'stat': 'xA/90: 0.35 | Tiri: 2.2'},
            {'nome': 'Artem Dovbyk', 'ruolo': 'ATT', 'stat': 'xG/90: 0.54'}
        ]
    },
    'Sassuolo': {
        'xG_fatti': 1.20, 'xGA_subiti': 1.45, 'possesso': 48.5,
        'stelle': [
            {'nome': 'Domenico Berardi', 'ruolo': 'ATT', 'stat': 'xG+xA/90: 0.68'},
            {'nome': 'Armand Laurienté', 'ruolo': 'ATT', 'stat': 'Dribbling: 2.9/90'}
        ]
    },
    'Torino': {
        'xG_fatti': 1.15, 'xGA_subiti': 1.10, 'possesso': 47.5,
        'stelle': [
            {'nome': 'Duvan Zapata', 'ruolo': 'ATT', 'stat': 'xG/90: 0.44'},
            {'nome': 'Samuele Ricci', 'ruolo': 'CEN', 'stat': 'Passaggi: 89%'}
        ]
    },
    'Udinese': {
        'xG_fatti': 1.15, 'xGA_subiti': 1.30, 'possesso': 44.8,
        'stelle': [
            {'nome': 'Lorenzo Lucca', 'ruolo': 'ATT', 'stat': 'Duelli Aerei: 4.2/90'},
            {'nome': 'Florian Thauvin', 'ruolo': 'TRQ', 'stat': 'Passaggi Chiave: 2.1/90'}
        ]
    },
    'Venezia': {
        'xG_fatti': 0.95, 'xGA_subiti': 1.70, 'possesso': 42.0,
        'stelle': [
            {'nome': 'Joel Pohjanpalo', 'ruolo': 'ATT', 'stat': 'xG/90: 0.40'},
            {'nome': 'Gianluca Busio', 'ruolo': 'CEN', 'stat': 'Inserimenti/90: 3.1'}
        ]
    }
}
squadre = sorted(list(dati_squadre.keys()))

st.title("⚽ Serie A Analytics Engine")
st.caption("Previsioni Poisson & Schede Tecniche Sintetiche")

col1, col2 = st.columns(2)
with col1:
    casa = st.selectbox("Squadra CASA", squadre, index=squadre.index('Inter'))
with col2:
    trasferta = st.selectbox("Squadra TRASFERTA", squadre, index=squadre.index('Milan'))

if casa == trasferta:
    st.warning("⚠️ Seleziona due squadre diverse per analizzare il match.")
else:
    if st.button("🚀 CALCOLA ANALISI & GIOCATORI CHIAVE"):
        d_c = dati_squadre[casa]
        d_t = dati_squadre[trasferta]

        # 2. CALCOLO POISSON DINAMICO
        lambda_casa = (d_c['xG_fatti'] + d_t['xGA_subiti']) / 2
        lambda_trasferta = (d_t['xG_fatti'] + d_c['xGA_subiti']) / 2

        matrice_p = np.zeros((6, 6))
        for i in range(6):
            for j in range(6):
                matrice_p[i, j] = poisson.pmf(i, lambda_casa) * poisson.pmf(j, lambda_trasferta) * 100

        prob_1 = np.sum(np.tril(matrice_p, -1))
        prob_x = np.sum(np.diag(matrice_p))
        prob_2 = np.sum(np.triu(matrice_p, 1))

        g_c, g_t = np.unravel_index(np.argmax(matrice_p), matrice_p.shape)
        prob_risultato_top = matrice_p[g_c, g_t]

        # 3. OUTPUT ESITO 1X2 E RISULTATO ESATTO
        st.markdown("---")
        st.subheader("📊 Probabilità Esito 1X2")
        c1, c2, c3 = st.columns(3)
        c1.metric(f"Vittoria {casa}", f"{prob_1:.1f}%")
        c2.metric("Pareggio (X)", f"{prob_x:.1f}%")
        c3.metric(f"Vittoria {trasferta}", f"{prob_2:.1f}%")

        st.success(f"🎯 Risultato Esatto Modellato: **{casa} {g_c} - {g_t} {trasferta}** ({prob_risultato_top:.1f}% di probabilità)")

        # 4. GIOCATORI CHIAVE (SCHEDE SCHEMATICHE NON DISCORSIVE)
        st.markdown("---")
        st.subheader("⭐ Giocatori Chiave del Match")
        
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            st.markdown(f"**🏠 {casa}**")
            for player in d_c.get('stelle', []):
                st.markdown(f"""
                <div class="player-card">
                    <div class="player-name">[{player['ruolo']}] {player['nome']}</div>
                    <div class="player-stat">📊 {player['stat']}</div>
                </div>
                """, unsafe_allow_html=True)

        with col_g2:
            st.markdown(f"**✈️ {trasferta}**")
            for player in d_t.get('stelle', []):
                st.markdown(f"""
                <div class="player-card">
                    <div class="player-name">[{player['ruolo']}] {player['nome']}</div>
                    <div class="player-stat">📊 {player['stat']}</div>
                </div>
                """, unsafe_allow_html=True)
