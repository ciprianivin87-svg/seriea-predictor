import streamlit as st
import google.generativeai as genai

# 1. GENERATORE REPORT GEMINI
@st.cache_data(ttl=3600)
def genera_report_gemini(squadra_casa, squadra_trasferta, st_c, st_t, prob_1, prob_x, prob_2, g_c, g_t):
    # ... resto del codice ...
# 1. GENERATORE REPORT GEMINI
@st.cache_data(ttl=3600)
def genera_report_gemini(squadra_casa, squadra_trasferta, st_c, st_t, prob_1, prob_x, prob_2, g_c, g_t):
    if genai is None:
        return "⚠️ La libreria google-generativeai non è installata nei requisiti."
        
    try:
        api_key = st.secrets.get("GEMINI_API_KEY")
        if not api_key:
            return "⚠️ Chiave GEMINI_API_KEY non trovata nei Secrets di Streamlit."
        
        genai.configure(api_key=api_key)
        # Modello aggiornato
        model = genai.GenerativeModel('gemini-3.6-flash')

        pos_c = st_c.get('pos', 'N/D')
        pos_t = st_t.get('pos', 'N/D')
        pt_c = st_c.get('punti', 'N/D')
        pt_t = st_t.get('punti', 'N/D')

        gf_c = st_c.get('gf', 0.0)
        ga_c = st_c.get('ga', 0.0)
        gf_t = st_t.get('gf', 0.0)
        ga_t = st_t.get('ga', 0.0)

        prompt = f"""
Sei un analista tattico e giornalista sportivo professionista.
Genera un'analisi pre-partita dinamica per l'incontro: {squadra_casa} vs {squadra_trasferta}.

Dati a disposizione:
- Classifica: {squadra_casa} ({pos_c}° posto, {pt_c} pt) vs {squadra_trasferta} ({pos_t}° posto, {pt_t} pt)
- Efficacia Offensiva/Difensiva: {squadra_casa} ({gf_c:.2f} gol fatti/gara, {ga_c:.2f} subiti/gara) vs {squadra_trasferta} ({gf_t:.2f} gol fatti/gara, {ga_t:.2f} subiti/gara)
- Ultime 5 gare: {squadra_casa} ({st_c.get('form_list')}) vs {squadra_trasferta} ({st_t.get('form_list')})
- Stima algoritmo Poisson: Vittoria Casa {prob_1:.1f}%, Pareggio {prob_x:.1f}%, Vittoria Trasferta {prob_2:.1f}%. Risultato esatto più probabile: {g_c}-{g_t}.

Struttura la risposta in Markdown con 3 sezioni chiare:
1. **Contesto e Forma Attuale**: Breve panoramica sul momento delle due squadre.
2. **Prospettiva Tattica & Tendenze**: Come si incrociano i valori d'attacco e difesa delle due squadre.
3. **Previsione dell'Analista**: Considerazioni finali sul pronostico stimato.

Usa un tono giornalistico, chiaro, avvincente e conciso (massimo 180 parole in totale). Non inserire introduzioni generiche.
"""

        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ Impossibile generare l'analisi al momento: {str(e)}"
