import streamlit as st
import db_manager as db
import analytics
import news_ai

# Inizializza il DB all'avvio
db.init_db()

st.set_page_config(page_title="Match Analyst AI", layout="wide")
st.title("⚽ Predictor & AI Match Analyst")

tab1, tab2 = st.tabs(["📊 Genera Analisi", "📜 Storico & Accuracy"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        home = st.text_input("Squadra Casa", "Parma Calcio 1913")
    with col2:
        away = st.text_input("Squadra Trasferta", "AC Monza")

    if st.button("Esegui Analisi Completa e Salva"):
        with st.spinner("Ricerca news e calcolo report AI in corso..."):
            # Esempio parametri di Poisson
            p_home, p_draw, p_away = 45.2, 28.5, 26.3
            l_home, l_away = 1.65, 1.10

            # 1. Recupero notizie e generazione report
            notizie = news_ai.cerca_news_partita(home, away)
            report = news_ai.genera_report_avanzato(
                home, away, p_home, p_draw, p_away, l_home, l_away, notizie
            )

            # 2. Salvataggio su DB SQLite
            db.salva_pronostico(home, away, p_home, p_draw, p_away, l_home, l_away, report)

            # 3. Output
            with st.expander("Notizie trovate"):
                st.markdown(notizie)
            st.subheader("Report Generato")
            st.markdown(report)
            st.success("✅ Analisi salvata nello storico!")

with tab2:
    st.subheader("Performance & Archivio")
    df_storico = db.carica_storico()

    if not df_storico.empty:
        stats = analytics.calcola_metriche_storico(df_storico)
        if stats:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Partite Concluse", stats['totale_giocate'])
            c2.metric("Accuracy", f"{stats['accuracy']:.1f}%")
            c3.metric("Profitto Netto (€)", f"{stats['profitto_netto']:+.2f} €")
            c4.metric("ROI Overall", f"{stats['roi']:+.2f}%")
            st.divider()

        st.dataframe(df_storico, use_container_width=True)

        st.markdown("---")
        st.write("**Aggiorna Risultato Reale**")
        col_id, col_res, col_btn = st.columns([1, 2, 1])
        with col_id:
            record_id = st.number_input("ID Partita", min_value=1, step=1)
        with col_res:
            esito = st.selectbox("Esito Reale", ["1", "X", "2"])
        with col_btn:
            if st.button("Aggiorna Esito"):
                row = df_storico[df_storico['id'] == record_id]
                if not row.empty:
                    probs = {'1': row['prob_home'].values[0], 'X': row['prob_draw'].values[0], '2': row['prob_away'].values[0]}
                    scelta_modello = max(probs, key=probs.get)
                    corretto = 1 if scelta_modello == esito else 0
                    db.aggiorna_risultato(record_id, esito, corretto)
                    st.success(f"Partita #{record_id} aggiornata!")
                    st.rerun()
    else:
        st.info("Nessun record salvato.")
