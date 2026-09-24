"""Programma dei tabelloni dei tornei di tennis.

Per ora legge i file nella cartella dati/, dice se sono scritti bene,
fa i calcoli preliminari del tabellone di estrazione e il sorteggio.
Il tabellone viene mostrato e salvato in risultati/tabellone.txt; la pagina
da stampare viene salvata in risultati/tabellone.html e aperta nel browser.

Si avvia con:  py tabelloni.py
Per controllare un tabellone gia' fatto (anche a mano):
    py tabelloni.py controlla                      controlla dati/tabellone-da-controllare.txt
    py tabelloni.py controlla risultati/tabellone.txt   controlla un altro file
"""

import os
import pathlib
import sys
import webbrowser

from programma.calcoli import calcola, conta_per_classifica, descrivi
from programma.controllo import controlla, leggi_tabellone
from programma.dati import ERRORE, leggi_classifiche, leggi_giocatori, leggi_torneo
from programma.sorteggio import disegna, sorteggia
from programma.stampa import pagina

FILE_CLASSIFICHE = os.path.join("dati", "classifiche.txt")
FILE_GIOCATORI = os.path.join("dati", "giocatori.txt")
FILE_TORNEO = os.path.join("dati", "torneo.txt")
FILE_DA_CONTROLLARE = os.path.join("dati", "tabellone-da-controllare.txt")
CARTELLA_RISULTATI = "risultati"
FILE_TABELLONE = os.path.join(CARTELLA_RISULTATI, "tabellone.txt")
FILE_DA_STAMPARE = os.path.join(CARTELLA_RISULTATI, "tabellone.html")


def leggi_dati():
    """Legge i tre file dei dati. Restituisce classifiche, giocatori, torneo e problemi,
    oppure None se manca un file."""
    for percorso in (FILE_CLASSIFICHE, FILE_GIOCATORI, FILE_TORNEO):
        if not os.path.exists(percorso):
            print(f"ERRORE - manca il file {percorso}")
            return None
    problemi = []
    classifiche, trovati = leggi_classifiche(FILE_CLASSIFICHE)
    problemi += trovati
    giocatori, trovati = leggi_giocatori(FILE_GIOCATORI, classifiche)
    problemi += trovati
    torneo, trovati = leggi_torneo(FILE_TORNEO)
    problemi += trovati
    return classifiche, giocatori, torneo, problemi


def stampa_problemi(problemi, se_nessuno="Nessun problema."):
    if problemi:
        print("PROBLEMI TROVATI:")
        for problema in problemi:
            print(f"  {problema}")
    else:
        print(se_nessuno)
    return not any(p.gravita == ERRORE for p in problemi)


def controlla_tabellone(giocatori, classifiche, torneo, posti):
    return controlla(posti, giocatori, classifiche,
                     qualificati_entranti=torneo.impostazioni.get("qualificati entranti", 0),
                     qualificati_uscenti=torneo.impostazioni.get("qualificati uscenti", 1),
                     teste_di_serie_impostate=torneo.impostazioni.get("teste di serie"))


def apri_nel_browser(percorso):
    try:
        webbrowser.open(pathlib.Path(percorso).resolve().as_uri())
    except Exception:
        print(f"Non si e' aperto il browser: aprire a mano il file {percorso}")


def fai_tabellone():
    """Legge i dati, fa i calcoli e il sorteggio. Restituisce True se non ci sono errori."""
    letti = leggi_dati()
    if letti is None:
        return False
    classifiche, giocatori, torneo, problemi = letti

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
            with open(FILE_DA_STAMPARE, "w", encoding="utf-8") as f:
                f.write(pagina(tabellone, torneo.impostazioni))
            print(f"Tabellone da stampare salvato in {FILE_DA_STAMPARE}"
                  " (si apre nel browser; per stampare premere il pulsante Stampa)")
            apri_nel_browser(FILE_DA_STAMPARE)
            # Il programma controlla anche il suo tabellone, per sicurezza.
            if not any(p.gravita == ERRORE
                       for p in controlla_tabellone(giocatori, classifiche, torneo, tabellone.posti)):
                print("Controllo del tabellone con le regole del manuale: nessun errore.")
            else:
                print("ATTENZIONE: il controllo ha trovato errori nel tabellone fatto dal programma.")
                print(f"Si vedono con:  py tabelloni.py controlla {FILE_TABELLONE}")
            print()

    return stampa_problemi(problemi)


def controlla_file(percorso):
    """Controlla un tabellone scritto in un file. Restituisce True se non ci sono errori."""
    letti = leggi_dati()
    if letti is None:
        return False
    classifiche, giocatori, torneo, problemi = letti
    if not stampa_problemi(problemi, se_nessuno=""):
        print("Prima vanno corretti i file dei dati.")
        return False
    if not os.path.exists(percorso):
        print(f"ERRORE - manca il file {percorso}")
        return False
    print(f"CONTROLLO DEL TABELLONE {percorso}")
    print(f"Torneo: {torneo.impostazioni['nome']} - {torneo.impostazioni['gara']}")
    print()
    posti, problemi = leggi_tabellone(percorso, giocatori)
    if not any(p.gravita == ERRORE for p in problemi):
        problemi += controlla_tabellone(giocatori, classifiche, torneo, posti)
    return stampa_problemi(problemi, se_nessuno="Il tabellone rispetta le regole del manuale: "
                                                "nessun problema.")


def main():
    # Il programma lavora sempre dalla sua cartella, cosi' i percorsi relativi funzionano
    # anche se viene avviato con un doppio clic.
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    argomenti = sys.argv[1:]
    if argomenti and argomenti[0].lower() == "controlla":
        tutto_bene = controlla_file(argomenti[1] if len(argomenti) > 1 else FILE_DA_CONTROLLARE)
    elif argomenti:
        print(f"Comando sconosciuto: {' '.join(argomenti)}")
        print(__doc__)
        tutto_bene = False
    else:
        tutto_bene = fai_tabellone()
    if sys.stdin and sys.stdin.isatty():
        input("\nPremi Invio per chiudere...")
    return 0 if tutto_bene else 1


if __name__ == "__main__":
    sys.exit(main())
