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

# 1. DATABASE METRICHE SQUADRE E GIOCATORI CHIAVE (SCHEDE TECNICHE COMPATTE)
dati_squadre = {
    'Inter': {
        'xG_fatti': 2.05, 'xGA_subiti': 0.80, 'possesso': 58.4,
        'stelle': [
            {'nome': 'Lautaro Martinez', 'ruolo': 'ATT', 'stat': 'xG/90: 0.65 | Tiri/90: 3.4'},
            {'nome': 'Hakan Calhanoglu', 'ruolo': 'CEN', 'stat': 'Passaggi Chiave: 2.8 | Rigori: 95%'},
            {'nome': 'Nicolò Barella', 'ruolo': 'CEN', 'stat': 'Recuperi: 5.2 | Assist Attesi: 0.25'}
        ]
    },
    'Juventus': {
        'xG_fatti': 1.70, 'xGA_subiti': 0.85, 'possesso': 52.8,
        'stelle': [
            {'nome': 'Dusan Vlahovic', 'ruolo': 'ATT', 'stat': 'xG/90: 0.58 | Conversione: 18%'},
            {'nome': 'Kenan Yildiz', 'ruolo': 'TRQ', 'stat': 'Dribbling Riusciti: 2.3/90'},
            {'nome': 'Gleison Bremer', 'ruolo': 'DIF', 'stat': 'Duelli Vinti: 68% | Contrasti: 3.1'}
        ]
    },
    'Milan': {
        'xG_fatti': 1.85, 'xGA_subiti': 1.10, 'possesso': 54.2,
        'stelle': [
            {'nome': 'Christian Pulisic', 'ruolo': 'TRQ', 'stat': 'Partecipazione Gol: 42%'},
            {'nome': 'Rafael Leao', 'ruolo': 'ATT', 'stat': 'Dribbling: 3.5/90 | Assist Attesi: 0.30'},
            {'nome': 'Tijjani Reijnders', 'ruolo': 'CEN', 'stat': 'Accuratezza Passaggi: 91%'}
        ]
    },
    'Napoli': {
        'xG_fatti': 1.75, 'xGA_subiti': 0.95, 'possesso': 56.1,
        'stelle': [
            {'nome': 'Romelu Lukaku', 'ruolo': 'ATT', 'stat': 'xG+xA/90: 0.72 | Sponde: 4.8'},
            {'nome': 'Khvicha Kvaratskhelia', 'ruolo': 'ATT', 'stat': 'Tiri in Porta: 1.8/90'},
            {'nome': 'Stanislav Lobotka', 'ruolo': 'CEN', 'stat': 'Palloni Recuperati: 6.4/90'}
        ]
    },
    'Atalanta': {
        'xG_fatti': 1.90, 'xGA_subiti': 1.15, 'possesso': 53.5,
        'stelle': [
            {'nome': 'Mateo Retegui', 'ruolo': 'ATT', 'stat': 'xG/90: 0.62 | Colpi di Testa: 2.1'},
            {'nome': 'Ademola Lookman', 'ruolo': 'ATT', 'stat': 'Occasioni Create: 2.6/90'},
            {'nome': 'Charles De Ketelaere', 'ruolo': 'TRQ', 'stat': 'Assist Attesi: 0.28/90'}
        ]
    },
    'Roma': {
        'xG_fatti': 1.55, 'xGA_subiti': 1.05, 'possesso': 51.0,
        'stelle': [
            {'nome': 'Paulo Dybala', 'ruolo': 'TRQ', 'stat': 'xA/90: 0.35 | Tiri da Fuori: 1.4'},
            {'nome': 'Artem Dovbyk', 'ruolo': 'ATT', 'stat': 'xG/90: 0.52 | Protezione Palla: 78%'}
        ]
    },
    'Lazio': {
        'xG_fatti': 1.50, 'xGA_subiti': 1.15, 'possesso': 50.5,
        'stelle': [
            {'nome': 'Taty Castellanos', 'ruolo': 'ATT', 'stat': 'xG/90: 0.48 | Pressioni Alte: 12.3'},
            {'nome': 'Mattia Zaccagni', 'ruolo': 'ATT', 'stat': 'Falli Subiti: 2.8/90 | Cross: 3.2'}
        ]
    },
    'Fiorentina': {
        'xG_fatti': 1.45, 'xGA_subiti': 1.20, 'possesso': 52.0,
        'stelle': [
            {'nome': 'Moise Kean', 'ruolo': 'ATT', 'stat': 'xG/90: 0.50 | Scatti in Profondità: 8.5'},
            {'nome': 'Albert Gudmundsson', 'ruolo': 'TRQ', 'stat': 'Passaggi Chiave: 2.4/90'}
        ]
    },
    'Bologna': {'xG_fatti': 1.35, 'xGA_subiti': 1.10, 'possesso': 53.0, 'stelle': [{'nome': 'Riccardo Orsolini', 'ruolo': 'ATT', 'stat': 'xG/90: 0.42 | Tiri/90: 2.9'}]},
    'Torino': {'xG_fatti': 1.15, 'xGA_subiti': 1.10, 'possesso': 47.5, 'stelle': [{'nome': 'Samuele Ricci', 'ruolo': 'CEN', 'stat': 'Accuratezza Passaggi: 89%'}]},
    'Genoa': {'xG_fatti': 1.10, 'xGA_subiti': 1.25, 'possesso': 45.0, 'stelle': [{'nome': 'Andrea Pinamonti', 'ruolo': 'ATT', 'stat': 'xG/90: 0.38'}]},
    'Monza': {'xG_fatti': 1.10, 'xGA_subiti': 1.35, 'possesso': 46.2, 'stelle': [{'nome': 'Daniel Maldini', 'ruolo': 'TRQ', 'stat': 'Tiri in Porta: 1.2/90'}]},
    'Udinese': {'xG_fatti': 1.15, 'xGA_subiti': 1.30, 'possesso': 44.8, 'stelle': [{'nome': 'Lorenzo Lucca', 'ruolo': 'ATT', 'stat': 'Duelli Aerei Vinti: 4.2/90'}]},
    'Cagliari': {'xG_fatti': 1.00, 'xGA_subiti': 1.40, 'possesso': 43.5, 'stelle': [{'nome': 'Roberto Piccoli', 'ruolo': 'ATT', 'stat': 'xG/90: 0.32'}]},
    'Parma': {'xG_fatti': 1.25, 'xGA_subiti': 1.45, 'possesso': 47.0, 'stelle': [{'nome': 'Dennis Man', 'ruolo': 'ATT', 'stat': 'Dribbling: 2.8/90 | xG: 0.39'}]},
    'Lecce': {'xG_fatti': 0.95, 'xGA_subiti': 1.40, 'possesso': 42.0, 'stelle': [{'nome': 'Nikola Krstovic', 'ruolo': 'ATT', 'stat': 'Tiri Totali: 3.2/90'}]},
    'Verona': {'xG_fatti': 1.00, 'xGA_subiti': 1.45, 'possesso': 41.5, 'stelle': [{'nome': 'Casper Tengstedt', 'ruolo': 'ATT', 'stat': 'Conversione: 22%'}]},
    'Empoli': {'xG_fatti': 0.90, 'xGA_subiti': 1.40, 'possesso': 43.0, 'stelle': [{'nome': 'Sebastiano Esposito', 'ruolo': 'ATT', 'stat': 'Occasioni Create: 1.8/90'}]},
    'Como': {'xG_fatti': 1.10, 'xGA_subiti': 1.50, 'possesso': 48.0, 'stelle': [{'nome': 'Nico Paz', 'ruolo': 'TRQ', 'stat': 'Tiri/90: 2.8 | Assist Attesi: 0.22'}]},
    'Venezia': {'xG_fatti': 0.95, 'xGA_subiti': 1.75, 'possesso': 41.0, 'stelle': [{'nome': 'Joel Pohjanpalo', 'ruolo': 'ATT', 'stat': 'xG/90: 0.40'}]}
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
