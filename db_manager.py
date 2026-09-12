import sqlite3
import pandas as pd

DB_NAME = "pronostici.db"

def init_db():
    """Inizializza il database creando la tabella se non esiste."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS storico_pronostici (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_inserimento TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            squadra_casa TEXT,
            squadra_trasferta TEXT,
            prob_home REAL,
            prob_draw REAL,
            prob_away REAL,
            lambda_home REAL,
            lambda_away REAL,
            report_ai TEXT,
            risultato_reale TEXT,
            esito_corretto INTEGER
        )
    ''')
    conn.commit()
    conn.close()

def salva_pronostico(home, away, p_home, p_draw, p_away, l_home, l_away, report):
    """Salva una nuova analisi nel DB."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO storico_pronostici 
        (squadra_casa, squadra_trasferta, prob_home, prob_draw, prob_away, lambda_home, lambda_away, report_ai)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (home, away, p_home, p_draw, p_away, l_home, l_away, report))
    conn.commit()
    conn.close()

def carica_storico():
    """Carica l'intero archivio come DataFrame Pandas."""
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM storico_pronostici ORDER BY data_inserimento DESC", conn)
    conn.close()
    return df

def aggiorna_risultato(record_id, esito_reale, corretto):
    """Aggiorna il risultato finale di una partita."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE storico_pronostici 
        SET risultato_reale = ?, esito_corretto = ?
        WHERE id = ?
    ''', (esito_reale, corretto, record_id))
    conn.commit()
    conn.close()
