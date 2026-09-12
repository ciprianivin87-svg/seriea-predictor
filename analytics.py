import pandas as pd

def calcola_metriche_storico(df, puntata_fissa=10.0):
    """Calcola Accuracy (%) e ROI (%) sulle partite concluse."""
    df_concluse = df[df['esito_corretto'].notnull()].copy()

    if df_concluse.empty:
        return None

    totale_partite = len(df_concluse)
    partite_vinte = df_concluse['esito_corretto'].sum()
    accuracy = (partite_vinte / totale_partite) * 100

    def ottieni_quota_scelta(row):
        probs = {'1': row['prob_home'], 'X': row['prob_draw'], '2': row['prob_away']}
        prob_max = max(probs.values()) / 100.0
        return 1.0 / prob_max if prob_max > 0 else 1.0

    df_concluse['quota_modello'] = df_concluse.apply(ottieni_quota_scelta, axis=1)

    spesa_totale = totale_partite * puntata_fissa
    incasso_totale = sum(
        puntata_fissa * row['quota_modello'] 
        for _, row in df_concluse.iterrows() if row['esito_corretto'] == 1
    )

    profitto_netto = incasso_totale - spesa_totale
    roi = (profitto_netto / spesa_totale) * 100

    return {
        "totale_giocate": totale_partite,
        "vinte": int(partite_vinte),
        "accuracy": accuracy,
        "profitto_netto": profitto_netto,
        "roi": roi
    }
