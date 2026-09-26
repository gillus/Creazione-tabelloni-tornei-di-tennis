"""Programma dei tabelloni dei tornei di tennis.

Per ora legge i file nella cartella dati/, dice se sono scritti bene,
fa i calcoli preliminari del tabellone di estrazione e il sorteggio.
Il tabellone viene mostrato e salvato in risultati/tabellone.txt; la pagina
da stampare viene salvata in risultati/tabellone.html e aperta nel browser.

Si avvia con:  py tabelloni.py        (si apre la finestra con i pulsanti)
Senza finestra, scrivendo i comandi:
    py tabelloni.py tabellone                      fa il tabellone
    py tabelloni.py controlla                      controlla dati/tabellone-da-controllare.txt
    py tabelloni.py controlla risultati/tabellone.txt   controlla un altro file
"""

import os
import pathlib
import sys
import webbrowser

from programma import controllo_selezione, selezione_tabellone
from programma.calcoli import SELEZIONE, calcola, conta_per_classifica, descrivi
from programma.controllo import controlla, leggi_tabellone
from programma.dati import AVVISO, ERRORE, Problema, leggi_classifiche, leggi_giocatori, leggi_torneo
from programma.selezione import controlla_scala, descrivi_scala, scala_migliore, scala_scritta
from programma.sorteggio import disegna, sorteggia
from programma.stampa import pagina

FILE_CLASSIFICHE = os.path.join("dati", "classifiche.txt")
FILE_GIOCATORI = os.path.join("dati", "giocatori.txt")
FILE_TORNEO = os.path.join("dati", "torneo.txt")
FILE_DATI = {"giocatori": FILE_GIOCATORI, "torneo": FILE_TORNEO, "classifiche": FILE_CLASSIFICHE}
FILE_DA_CONTROLLARE = os.path.join("dati", "tabellone-da-controllare.txt")
CARTELLA_RISULTATI = "risultati"
FILE_TABELLONE = os.path.join(CARTELLA_RISULTATI, "tabellone.txt")
FILE_DA_STAMPARE = os.path.join(CARTELLA_RISULTATI, "tabellone.html")


def leggi_dati(file_dati=FILE_DATI):
    """Legge i tre file dei dati. Restituisce classifiche, giocatori, torneo e problemi,
    oppure None se manca un file."""
    for percorso in file_dati.values():
        if not os.path.exists(percorso):
            print(f"ERRORE - manca il file {percorso}")
            return None
    problemi = []
    classifiche, trovati = leggi_classifiche(file_dati["classifiche"])
    problemi += trovati
    giocatori, trovati = leggi_giocatori(file_dati["giocatori"], classifiche)
    problemi += trovati
    torneo, trovati = leggi_torneo(file_dati["torneo"])
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


def fai_tabellone(file_dati=FILE_DATI):
    """Legge i dati, fa i calcoli e il sorteggio. Restituisce True se non ci sono errori."""
    letti = leggi_dati(file_dati)
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

    estrazione = torneo.impostazioni.get("tipo", "selezione") == "estrazione"
    if giocatori and not any(p.gravita == ERRORE for p in problemi) and not estrazione:
        trovati, fatto = fai_selezione(giocatori, classifiche, torneo)
        problemi += trovati
        estrazione = not fatto and not any(p.gravita == ERRORE for p in trovati)
        if estrazione:
            print("Con questi giocatori non si trova nessun tabellone di selezione che rispetti "
                  "le regole del manuale\n(per esempio perche' le classifiche sono solo una o due): "
                  "il programma fa il tabellone di estrazione.\n")
            problemi.append(Problema(AVVISO, "", 0,
                                     "fatto il tabellone di estrazione al posto di quello di "
                                     "selezione, che con questi giocatori non e' possibile"))
    if giocatori and not any(p.gravita == ERRORE for p in problemi) and estrazione:
        calcoli = calcola(conta_per_classifica(giocatori, classifiche),
                          qualificati_entranti=torneo.impostazioni.get("qualificati entranti", 0),
                          qualificati_uscenti=torneo.impostazioni.get("qualificati uscenti", 1),
                          teste_di_serie=torneo.impostazioni.get("teste di serie"))
        print("CALCOLI PRELIMINARI")
        print(descrivi(calcoli))
        print()
        problemi += calcoli.problemi
        if not any(p.gravita == ERRORE for p in calcoli.problemi):
            tabellone = sorteggia(calcoli, giocatori, classifiche=classifiche)
            problemi += tabellone.problemi
            salva_e_controlla(tabellone, disegna(tabellone, titolo_del_torneo(torneo)), torneo,
                              controlla_tabellone(giocatori, classifiche, torneo, tabellone.posti))

    return stampa_problemi(problemi)


def titolo_del_torneo(torneo):
    return (f"{torneo.impostazioni['nome']} - {torneo.impostazioni['gara']}"
            + (f" - {torneo.impostazioni['date']}" if "date" in torneo.impostazioni else ""))


def salva_e_controlla(tabellone, testo, torneo, problemi_del_controllo):
    """Mostra e salva il tabellone (testo e pagina da stampare), e dice se il controllo
    con le regole del manuale ha trovato errori."""
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
    if not any(p.gravita == ERRORE for p in problemi_del_controllo):
        print("Controllo del tabellone con le regole del manuale: nessun errore.")
    else:
        print("ATTENZIONE: il controllo ha trovato errori nel tabellone fatto dal programma:")
        for problema in problemi_del_controllo:
            print(f"  {problema}")
    print()


def fai_selezione(giocatori, classifiche, torneo):
    """Il tabellone di selezione: scala, teste di serie, sorteggio.

    Restituisce i problemi e se il tabellone e' stato fatto (False senza errori vuol
    dire che con questi giocatori un tabellone di selezione non si puo' fare)."""
    impostazioni = torneo.impostazioni
    q = impostazioni.get("qualificati entranti", 0)
    Qu = impostazioni.get("qualificati uscenti", 1)
    calcoli = calcola(conta_per_classifica(giocatori, classifiche),
                      qualificati_entranti=q, qualificati_uscenti=Qu, tipo=SELEZIONE)
    # Dei calcoli del tabellone di estrazione servono solo gli errori e le teste di serie.
    problemi = [p for p in calcoli.problemi if p.gravita == ERRORE]
    if problemi:
        return problemi, False
    livello = {c: i for i, c in enumerate(classifiche)}
    diretti = sorted((g.classifica for g in giocatori), key=lambda c: livello[c])

    print("TABELLONE DI SELEZIONE")
    print(f"Giocatori: {len(giocatori)} ammessi direttamente e {q} qualificati entranti, "
          f"in tutto {len(giocatori) + q}")
    print(f"Qualificati uscenti: {Qu}" + (f" (tabellone a {Qu} sezioni)" if calcoli.sezioni else ""))
    minimo, massimo = calcoli.teste_di_serie_minimo, calcoli.teste_di_serie_massimo
    scelte = impostazioni.get("teste di serie")
    if minimo is not None and scelte is not None and (
            not (minimo <= scelte <= massimo) or (calcoli.sezioni and scelte % calcoli.sezioni)):
        return [p for p in calcola(conta_per_classifica(giocatori, classifiche), q, Qu,
                                   teste_di_serie=scelte, tipo=SELEZIONE).problemi
                if p.gravita == ERRORE], False
    scala = scala_scritta(impostazioni, Qu)
    if scala is not None:
        errori = controlla_scala(scala, diretti, q, livello)
        if errori:
            return [Problema(ERRORE, "", 0, f"la scala scritta in dati/torneo.txt: {e}")
                    for e in errori], False
        scala, teste = selezione_tabellone.scegli_scala([scala], minimo, massimo, livello,
                                                        calcoli.sezioni, scelte)
        if scala is None:
            return [Problema(ERRORE, "", 0,
                             "con la scala scritta in dati/torneo.txt le teste di serie non possono "
                             "stare al loro posto (ogni testa di serie n. k nel posto numero k, e "
                             "tutte in uno o due turni consecutivi): cambiare la scala o il numero "
                             "delle teste di serie")], False
        print("Scala scritta dal giudice arbitro in dati/torneo.txt:")
    else:
        _, tutte = scala_migliore(diretti, q, Qu, livello)
        scala, teste = selezione_tabellone.scegli_scala(tutte, minimo, massimo, livello,
                                                        calcoli.sezioni, scelte)
        if scala is None:
            return [], False
        print(f"Scala proposta dal programma (la migliore tra {len(tutte)} possibili):")
    for riga in descrivi_scala(scala):
        print(riga)
    print("  (per usarne una diversa, scriverla in dati/torneo.txt con le righe \"turno 1 = ...\")")
    if minimo is None:
        print("Teste di serie: nessuna (giocano solo non classificati)")
    else:
        chi = "scelte dal giudice arbitro" if scelte is not None else "proposta del programma"
        print(f"Teste di serie ({chi}): {teste}, possibili da {minimo} a {massimo}")
    print()

    tabellone = selezione_tabellone.prepara(scala, teste, giocatori, livello, calcoli.sezioni)
    problemi += tabellone.problemi
    controllo = controllo_selezione.controlla(tabellone.voci(), giocatori, classifiche, q, Qu,
                                              impostazioni.get("teste di serie"))
    salva_e_controlla(tabellone, selezione_tabellone.disegna(tabellone, titolo_del_torneo(torneo)),
                      torneo, controllo)
    return problemi, True


def controlla_file(percorso, file_dati=FILE_DATI):
    """Controlla un tabellone scritto in un file. Restituisce True se non ci sono errori."""
    letti = leggi_dati(file_dati)
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
    if controllo_selezione.e_di_selezione(percorso):
        print("(tabellone di selezione)")
        voci, problemi = controllo_selezione.leggi_tabellone(percorso, giocatori)
        if not any(p.gravita == ERRORE for p in problemi):
            problemi += controllo_selezione.controlla(
                voci, giocatori, classifiche,
                torneo.impostazioni.get("qualificati entranti", 0),
                torneo.impostazioni.get("qualificati uscenti", 1),
                torneo.impostazioni.get("teste di serie"))
        return stampa_problemi(problemi, se_nessuno="Il tabellone rispetta le regole del manuale: "
                                                    "nessun problema.")
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
    if not argomenti:
        try:
            from programma import finestra
        except ImportError:
            print("Non si riesce ad aprire la finestra (manca tkinter): si continua senza.\n")
        else:
            finestra.avvia(fai_tabellone=fai_tabellone, controlla_file=controlla_file,
                           file_dati=FILE_DATI, file_da_controllare=FILE_DA_CONTROLLARE,
                           file_da_stampare=FILE_DA_STAMPARE,
                           cartella_risultati=CARTELLA_RISULTATI)
            return 0
    if argomenti and argomenti[0].lower() == "controlla":
        tutto_bene = controlla_file(argomenti[1] if len(argomenti) > 1 else FILE_DA_CONTROLLARE)
    elif not argomenti or argomenti[0].lower() == "tabellone":
        tutto_bene = fai_tabellone()
    else:
        print(f"Comando sconosciuto: {' '.join(argomenti)}")
        print(__doc__)
        tutto_bene = False
    if sys.stdin and sys.stdin.isatty():
        input("\nPremi Invio per chiudere...")
    return 0 if tutto_bene else 1


if __name__ == "__main__":
    sys.exit(main())
