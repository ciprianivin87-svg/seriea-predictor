import urllib.parse
import feedparser
from bs4 import BeautifulSoup
import google.generativeai as genai
import streamlit as st

def cerca_news_partita(home_team, away_team):
    """Recupera le notizie recenti da Google News RSS."""
    query = f"{home_team} {away_team} infortuni formazioni"
    query_encoded = urllib.parse.quote(query)
    rss_url = f"https://news.google.com/rss/search?q={query_encoded}&hl=it&gl=IT&ceid=IT:it"
    
    feed = feedparser.parse(rss_url)
    notizie = []
    
    for entry in feed.entries[:5]:
        soup = BeautifulSoup(entry.summary, "html.parser")
        notizie.append(f"- **{entry.title}**: {soup.get_text()}")
        
    return "\n".join(notizie) if notizie else "Nessuna notizia recente trovata."

def genera_report_avanzato(home_team, away_team, prob_home, prob_draw, prob_away, lambda_home, lambda_away, news_text):
    """Invia dati e notizie a Gemini per l'analisi contestuale."""
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')

    prompt = f"""
    Sei un esperto match analyst di calcio. Integra i dati di Poisson con le ultime notizie.

    --- DATI POISSON ---
    Partita: {home_team} vs {away_team}
    Probabilità: 1 ({prob_home:.1f}%), X ({prob_draw:.1f}%), 2 ({prob_away:.1f}%)
    Gol Attesi: {home_team} ({lambda_home:.2f}), {away_team} ({lambda_away:.2f})

    --- NEWS RECENTI ---
    {news_text}

    --- ISTRUZIONI REPORT ---
    1. **Impatto Infortuni & Formazioni:** Squalifiche/assenze rilevanti.
    2. **Analisi Tattica & Contesto:** Stato di forma e contesto del match.
    3. **Pronostico Rettificato:** Raccomandazione finale (1X2, Over/Under, Gol/NoGol).
    """

    response = model.generate_content(prompt)
    return response.text
