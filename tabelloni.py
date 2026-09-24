"""Programma dei tabelloni dei tornei di tennis.

Per ora legge i file nella cartella dati/, dice se sono scritti bene,
fa i calcoli preliminari del tabellone di estrazione e il sorteggio.
Il tabellone viene mostrato e salvato in risultati/tabellone.txt.
Si avvia con:  py tabelloni.py
"""

import os
import sys

from programma.calcoli import calcola, conta_per_classifica, descrivi
from programma.dati import ERRORE, leggi_classifiche, leggi_giocatori, leggi_torneo
from programma.sorteggio import disegna, sorteggia

FILE_CLASSIFICHE = os.path.join("dati", "classifiche.txt")
FILE_GIOCATORI = os.path.join("dati", "giocatori.txt")
FILE_TORNEO = os.path.join("dati", "torneo.txt")
CARTELLA_RISULTATI = "risultati"
FILE_TABELLONE = os.path.join(CARTELLA_RISULTATI, "tabellone.txt")


def controlla_dati():
    """Legge i tre file, stampa un riepilogo e i problemi. Restituisce True se non ci sono errori."""
    problemi = []
    for percorso in (FILE_CLASSIFICHE, FILE_GIOCATORI, FILE_TORNEO):
        if not os.path.exists(percorso):
            print(f"ERRORE - manca il file {percorso}")
            return False

    classifiche, trovati = leggi_classifiche(FILE_CLASSIFICHE)
    problemi += trovati
    giocatori, trovati = leggi_giocatori(FILE_GIOCATORI, classifiche)
    problemi += trovati
    torneo, trovati = leggi_torneo(FILE_TORNEO)
    problemi += trovati

    print(f"Torneo: {torneo.impostazioni.get('nome', '(senza nome)')}"
          f" - {torneo.impostazioni.get('gara', '(gara non indicata)')}")
    print(f"Giocatori letti: {len(giocatori)}")
    for classifica in classifiche:
        quanti = sum(1 for g in giocatori if g.classifica == classifica)
        if quanti:
            print(f"  {classifica}: {quanti}")
    circoli = {g.chiave_circolo for g in giocatori}
    print(f"Circoli diversi: {len(circoli)}")
    print()

    if giocatori and not any(p.gravita == ERRORE for p in problemi):
        calcoli = calcola(conta_per_classifica(giocatori, classifiche),
                          qualificati_entranti=torneo.impostazioni.get("qualificati entranti", 0),
                          qualificati_uscenti=torneo.impostazioni.get("qualificati uscenti", 1),
                          teste_di_serie=torneo.impostazioni.get("teste di serie"))
        print("CALCOLI PRELIMINARI")
        print(descrivi(calcoli))
        print()
        problemi += calcoli.problemi
        if not any(p.gravita == ERRORE for p in calcoli.problemi):
            tabellone = sorteggia(calcoli, giocatori)
            problemi += tabellone.problemi
            titolo = (f"{torneo.impostazioni['nome']} - {torneo.impostazioni['gara']}"
                      + (f" - {torneo.impostazioni['date']}" if "date" in torneo.impostazioni else ""))
            testo = disegna(tabellone, titolo)
            print(testo)
            print()
            os.makedirs(CARTELLA_RISULTATI, exist_ok=True)
            with open(FILE_TABELLONE, "w", encoding="utf-8") as f:
                f.write(testo + "\n")
            print(f"Tabellone salvato in {FILE_TABELLONE}")
            print()

    if problemi:
        print("PROBLEMI TROVATI:")
        for problema in problemi:
            print(f"  {problema}")
    else:
        print("Nessun problema.")
    return not any(p.gravita == ERRORE for p in problemi)


def main():
    # Il programma lavora sempre dalla sua cartella, cosi' i percorsi relativi funzionano
    # anche se viene avviato con un doppio clic.
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    tutto_bene = controlla_dati()
    if sys.stdin and sys.stdin.isatty():
        input("\nPremi Invio per chiudere...")
    return 0 if tutto_bene else 1


if __name__ == "__main__":
    sys.exit(main())
