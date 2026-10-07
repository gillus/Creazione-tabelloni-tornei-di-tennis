"""Programma dei tabelloni dei tornei di tennis.

Legge i file nella cartella dati/, dice se sono scritti bene e fa il tabellone
(di selezione, di estrazione o a sorteggio integrale), oppure i tabelloni
collegati se i giocatori sono di categorie diverse (o se in dati/torneo.txt ci
sono le righe "tabellone 1 = ...").
Il tabellone viene mostrato e salvato in risultati/tabellone.txt (con i tabelloni
collegati: risultati/tabellone-1.txt, tabellone-2.txt...); la pagina da stampare,
con tutti i tabelloni, viene salvata in risultati/tabellone.html e aperta nel browser.

Si avvia con:  py tabelloni.py        (si apre la finestra con i pulsanti)
Senza finestra, scrivendo i comandi:
    py tabelloni.py tabellone                      fa il tabellone
    py tabelloni.py controlla                      controlla dati/tabellone-da-controllare.txt
    py tabelloni.py controlla risultati/tabellone.txt   controlla un altro file
"""

import os
import pathlib
import re
import sys
import webbrowser

from programma import controllo_selezione, selezione_tabellone
from programma.collegati import (descrivi_divisione, leggi_divisione, prepara_divisione,
                                 proponi_divisione)
from programma.calcoli import (ESTRAZIONE, INTEGRALE, SELEZIONE, calcola, conta_per_classifica,
                               descrivi)
from programma.controllo import controlla, leggi_tabellone
from programma.dati import AVVISO, ERRORE, Problema, leggi_classifiche, leggi_giocatori, leggi_torneo
from programma.selezione import controlla_scala, descrivi_scala, scala_migliore, scala_scritta
from programma.sorteggio import disegna, sorteggia, sorteggia_integrale
from programma.stampa import pagina, pagina_collegati

FILE_CLASSIFICHE = os.path.join("dati", "classifiche.txt")
FILE_GIOCATORI = os.path.join("dati", "giocatori.txt")
FILE_TORNEO = os.path.join("dati", "torneo.txt")
FILE_DATI = {"giocatori": FILE_GIOCATORI, "torneo": FILE_TORNEO, "classifiche": FILE_CLASSIFICHE}
FILE_DA_CONTROLLARE = os.path.join("dati", "tabellone-da-controllare.txt")
CARTELLA_RISULTATI = "risultati"
FILE_TABELLONE = os.path.join(CARTELLA_RISULTATI, "tabellone.txt")
FILE_DA_STAMPARE = os.path.join(CARTELLA_RISULTATI, "tabellone.html")

# Dopo il tabellone, la pagina da stampare si apre da sola nel browser. La pagina
# web (web/pagina.py) mette False: li' il browser c'e' gia'.
APRI_BROWSER = True


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


def controlla_tabellone(giocatori, classifiche, impostazioni, posti):
    return controlla(posti, giocatori, classifiche,
                     qualificati_entranti=impostazioni.get("qualificati entranti", 0),
                     qualificati_uscenti=impostazioni.get("qualificati uscenti", 1),
                     teste_di_serie_impostate=impostazioni.get("teste di serie"),
                     tipo=INTEGRALE if impostazioni.get("tipo") == INTEGRALE else ESTRAZIONE)


def apri_nel_browser(percorso):
    if not APRI_BROWSER:
        return
    try:
        webbrowser.open(pathlib.Path(percorso).resolve().as_uri())
    except Exception:
        print(f"Non si e' aperto il browser: aprire a mano il file {percorso}")


def ci_sono_errori(problemi):
    return any(p.gravita == ERRORE for p in problemi)


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
    if not giocatori or ci_sono_errori(problemi):
        return stampa_problemi(problemi)

    impostazioni = torneo.impostazioni
    parti, trovati = leggi_divisione(impostazioni, classifiche, FILE_TORNEO)
    problemi += trovati
    if ci_sono_errori(problemi):
        return stampa_problemi(problemi)
    scritta = bool(parti)
    if not parti:
        parti = proponi_divisione(giocatori, classifiche)
    if len(parti) == 1:
        if scritta:
            problemi += prepara_divisione(parti, giocatori, classifiche,
                                          impostazioni.get("qualificati entranti", 0),
                                          impostazioni.get("qualificati uscenti", 1), FILE_TORNEO)
            if ci_sono_errori(problemi):
                return stampa_problemi(problemi)
        una = dict(impostazioni)
        una.update(parti[0].impostazioni)
        trovati, risultato = fai_un_tabellone(giocatori, classifiche, una, titolo_del_torneo(torneo))
        problemi += trovati
        if risultato:
            tabellone, testo, controllo = risultato
            salva_e_controlla([(tabellone, testo, controllo, una)], impostazioni)
        return stampa_problemi(problemi)
    return fai_tabelloni_collegati(parti, scritta, giocatori, classifiche, torneo, problemi)


def fai_tabelloni_collegati(parti, scritta, giocatori, classifiche, torneo, problemi):
    """Tutti i tabelloni della divisione, uno dopo l'altro: i qualificati uscenti di
    ognuno sono i qualificati entranti del seguente (Volume I, capitolo VI)."""
    impostazioni = torneo.impostazioni
    problemi += prepara_divisione(parti, giocatori, classifiche,
                                  impostazioni.get("qualificati entranti", 0),
                                  impostazioni.get("qualificati uscenti", 1), FILE_TORNEO)
    print(f"TABELLONI COLLEGATI: {len(parti)}, "
          + ("scritti in dati/torneo.txt" if scritta else
             "proposti dal programma (un tabellone per categoria)"))
    for riga in descrivi_divisione(parti):
        print(riga)
    if any(p.uscenti_proposti for p in parti):
        print("  (i qualificati uscenti li propone il programma: la potenza di due piu' grande che "
              "non supera\n   ne' la meta' dei giocatori, ne' gli ammessi al tabellone seguente "
              "con una classifica\n   al massimo due gruppi sopra la piu' alta del tabellone)")
    print("  (per cambiarli, scriverli in dati/torneo.txt con le righe \"tabellone 1 = ...\")")
    print()
    if ci_sono_errori(problemi):
        return stampa_problemi(problemi)
    for nome in ("teste di serie",):
        if nome in impostazioni:
            problemi.append(Problema(AVVISO, FILE_TORNEO, 0,
                                     f"\"{nome}\" vale per un solo tabellone: con i tabelloni "
                                     f"collegati va scritto nella riga del tabellone"))
    if any(nome.startswith("turno ") for nome in impostazioni):
        problemi.append(Problema(AVVISO, FILE_TORNEO, 0,
                                 "le righe \"turno N\" (la scala) valgono per un solo tabellone: "
                                 "con i tabelloni collegati il programma propone la scala di ognuno"))
    fatti = []
    for parte in parti:
        una = impostazioni_della_parte(impostazioni, parte, len(parti))
        titolo = titolo_del_torneo(torneo) + f" - {una['tabellone']}"
        print("=" * 70)
        print(f"TABELLONE {parte.numero} DI {len(parti)}  ({', '.join(parte.classifiche)})")
        print("=" * 70)
        trovati, risultato = fai_un_tabellone(parte.giocatori, classifiche, una, titolo)
        problemi += [Problema(p.gravita, p.file, p.riga, f"tabellone {parte.numero}: {p.messaggio}")
                     for p in trovati]
        if risultato:
            tabellone, testo, controllo = risultato
            fatti.append((tabellone, testo, controllo, una))
    if fatti:
        salva_e_controlla(fatti, impostazioni)
    return stampa_problemi(problemi)


def impostazioni_della_parte(impostazioni, parte, quante):
    """Le impostazioni di un tabellone della divisione, come se fosse un torneo a se'."""
    una = {nome: impostazioni[nome] for nome in ("nome", "gara", "date", "tipo")
           if nome in impostazioni}
    if una.get("tipo") == INTEGRALE and parte.numero < quante:
        del una["tipo"]  # il sorteggio integrale e' solo per il tabellone finale
    una.update(parte.impostazioni)
    una["qualificati entranti"] = parte.qualificati_entranti
    una["qualificati uscenti"] = parte.qualificati_uscenti
    una["tabellone"] = f"Tabellone {parte.numero} di {quante} ({', '.join(parte.classifiche)})"
    provenienza = f" · {parte.qualificati_entranti} qualificati dal tabellone {parte.numero - 1}" \
        if parte.numero > 1 and parte.qualificati_entranti else ""
    una["gara"] = f"{impostazioni.get('gara', '')} · {una['tabellone']}{provenienza}".strip(" ·")
    return una


def fai_un_tabellone(giocatori, classifiche, impostazioni, titolo):
    """Un tabellone: di selezione (se non e' possibile, di estrazione), di estrazione o a
    sorteggio integrale. Restituisce i problemi e (tabellone, testo, controllo), oppure None."""
    problemi = []
    tipo = impostazioni.get("tipo", SELEZIONE)
    if tipo == INTEGRALE and impostazioni.get("qualificati uscenti", 1) != 1:
        return [Problema(ERRORE, FILE_TORNEO, 0,
                         "il tabellone a sorteggio integrale si fa solo come tabellone "
                         "finale (qualificati uscenti = 1): Volume I, capitolo V, B")], None
    if tipo == SELEZIONE:
        trovati, risultato = fai_selezione(giocatori, classifiche, impostazioni, titolo)
        if risultato == IN_DUE_TURNI:
            print("La scala migliore fa entrare i giocatori in due turni soltanto: e' un tabellone "
                  "di estrazione\n(Volume II, terminologia: il tabellone di selezione ha l'ingresso "
                  "in tre o piu' turni).\n")
        elif risultato or ci_sono_errori(trovati):
            return trovati, risultato
        else:
            print("Con questi giocatori non si trova nessun tabellone di selezione che rispetti "
                  "le regole del manuale\n(per esempio perche' le classifiche sono solo una o due): "
                  "il programma fa il tabellone di estrazione.\n")
            trovati = trovati + [Problema(AVVISO, "", 0,
                                          "fatto il tabellone di estrazione al posto di quello di "
                                          "selezione, che con questi giocatori non e' possibile")]
        problemi = trovati
    calcoli = calcola(conta_per_classifica(giocatori, classifiche),
                      qualificati_entranti=impostazioni.get("qualificati entranti", 0),
                      qualificati_uscenti=impostazioni.get("qualificati uscenti", 1),
                      teste_di_serie=impostazioni.get("teste di serie"),
                      tipo=INTEGRALE if tipo == INTEGRALE else ESTRAZIONE)
    if tipo == INTEGRALE:
        print("TABELLONE FINALE DI ESTRAZIONE A SORTEGGIO INTEGRALE")
    print("CALCOLI PRELIMINARI")
    print(descrivi(calcoli))
    print()
    problemi += calcoli.problemi
    if ci_sono_errori(calcoli.problemi):
        return problemi, None
    if tipo == INTEGRALE:
        tabellone = sorteggia_integrale(calcoli, giocatori, classifiche=classifiche)
    else:
        tabellone = sorteggia(calcoli, giocatori, classifiche=classifiche)
    problemi += tabellone.problemi
    controllo = controlla_tabellone(giocatori, classifiche, impostazioni, tabellone.posti)
    return problemi, (tabellone, disegna(tabellone, titolo), controllo)


def titolo_del_torneo(torneo):
    return (f"{torneo.impostazioni['nome']} - {torneo.impostazioni['gara']}"
            + (f" - {torneo.impostazioni['date']}" if "date" in torneo.impostazioni else ""))


def salva_e_controlla(fatti, impostazioni):
    """Mostra e salva i tabelloni (testo e pagina da stampare), e dice se il controllo
    con le regole del manuale ha trovato errori.

    fatti  elenco di (tabellone, testo, controllo, impostazioni del tabellone)
    Con un solo tabellone: risultati/tabellone.txt; con i tabelloni collegati:
    risultati/tabellone-1.txt, tabellone-2.txt... In tutti e due i casi una sola
    pagina da stampare, risultati/tabellone.html."""
    os.makedirs(CARTELLA_RISULTATI, exist_ok=True)
    for numero, (tabellone, testo, controllo, _) in enumerate(fatti, start=1):
        print(testo)
        print()
        percorso = FILE_TABELLONE if len(fatti) == 1 else \
            os.path.join(CARTELLA_RISULTATI, f"tabellone-{numero}.txt")
        with open(percorso, "w", encoding="utf-8") as f:
            f.write(testo + "\n")
        print(f"Tabellone salvato in {percorso}")
        # Il programma controlla anche i suoi tabelloni, per sicurezza.
        if not ci_sono_errori(controllo):
            print("Controllo del tabellone con le regole del manuale: nessun errore.")
        else:
            print("ATTENZIONE: il controllo ha trovato errori nel tabellone fatto dal programma:")
            for problema in controllo:
                print(f"  {problema}")
        print()
    with open(FILE_DA_STAMPARE, "w", encoding="utf-8") as f:
        if len(fatti) == 1:
            f.write(pagina(fatti[0][0], fatti[0][3]))
        else:
            f.write(pagina_collegati([(t, una) for t, _, _, una in fatti], impostazioni))
    print(f"Da stampare: {FILE_DA_STAMPARE}"
          + (f" (tutti i {len(fatti)} tabelloni)" if len(fatti) > 1 else "")
          + " (si apre nel browser; per stampare premere il pulsante Stampa)")
    apri_nel_browser(FILE_DA_STAMPARE)
    print()


def fai_selezione(giocatori, classifiche, impostazioni, titolo):
    """Il tabellone di selezione: scala, teste di serie, sorteggio.

    Restituisce i problemi e (tabellone, testo, controllo); None al posto del
    tabellone, senza errori, vuol dire che con questi giocatori un tabellone di
    selezione non si puo' fare."""
    q = impostazioni.get("qualificati entranti", 0)
    Qu = impostazioni.get("qualificati uscenti", 1)
    calcoli = calcola(conta_per_classifica(giocatori, classifiche),
                      qualificati_entranti=q, qualificati_uscenti=Qu, tipo=SELEZIONE)
    # Dei calcoli del tabellone di estrazione servono solo gli errori e le teste di serie.
    problemi = [p for p in calcoli.problemi if p.gravita == ERRORE]
    if problemi:
        return problemi, None
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
                if p.gravita == ERRORE], None
    scala = scala_scritta(impostazioni, Qu)
    if scala is not None:
        errori = controlla_scala(scala, diretti, q, livello)
        if errori:
            return [Problema(ERRORE, "", 0, f"la scala scritta in dati/torneo.txt: {e}")
                    for e in errori], None
        scala, teste = selezione_tabellone.scegli_scala([scala], minimo, massimo, livello,
                                                        calcoli.sezioni, scelte)
        if scala is None:
            return [Problema(ERRORE, "", 0,
                             "con la scala scritta in dati/torneo.txt le teste di serie non possono "
                             "stare al loro posto (ogni testa di serie n. k nel posto numero k, e "
                             "tutte in uno o due turni consecutivi), oppure le sezioni non possono "
                             "avere lo stesso numero di giocatori (due di differenza al massimo) e "
                             "di qualificati entranti (uno di differenza al massimo): cambiare la "
                             "scala o il numero delle teste di serie")], None
        print("Scala scritta dal giudice arbitro in dati/torneo.txt:")
    else:
        _, tutte = scala_migliore(diretti, q, Qu, livello)
        scala, teste = selezione_tabellone.scegli_scala(tutte, minimo, massimo, livello,
                                                        calcoli.sezioni, scelte)
        if scala is None:
            return [], None
        if sum(1 for t in scala.turni if t.singoli or t.coppie) < 3:
            return [], IN_DUE_TURNI
        print(f"Scala proposta dal programma (la migliore tra {len(tutte)} possibili):")
    for riga in descrivi_scala(scala):
        print(riga)
    if "tabellone" not in impostazioni:
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
    return problemi, (tabellone, selezione_tabellone.disegna(tabellone, titolo), controllo)


# fai_selezione: la scala migliore ha l'ingresso in due turni, quindi si fa l'estrazione.
IN_DUE_TURNI = "in due turni"

_QUALE_TABELLONE = re.compile(r"Tabellone (\d+) di (\d+)")


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
    # Con i tabelloni collegati: quale dei tabelloni e' (scritto in cima al file).
    impostazioni = torneo.impostazioni
    parti, problemi = leggi_divisione(impostazioni, classifiche, FILE_TORNEO)
    if not parti:
        parti = proponi_divisione(giocatori, classifiche)
    if len(parti) > 1 and not ci_sono_errori(problemi):
        problemi += prepara_divisione(parti, giocatori, classifiche,
                                      impostazioni.get("qualificati entranti", 0),
                                      impostazioni.get("qualificati uscenti", 1), FILE_TORNEO)
        with open(percorso, encoding="utf-8", errors="replace") as f:
            trovato = _QUALE_TABELLONE.search(f.read())
        if not ci_sono_errori(problemi) and (not trovato or not 1 <= int(trovato.group(1)) <= len(parti)):
            problemi.append(Problema(
                ERRORE, percorso, 0,
                f"il torneo ha {len(parti)} tabelloni collegati: scrivere in cima al file quale "
                f"e', per esempio con la riga \"# Tabellone 2 di {len(parti)}\""))
        if ci_sono_errori(problemi):
            return stampa_problemi(problemi)
        parte = parti[int(trovato.group(1)) - 1]
        impostazioni = impostazioni_della_parte(impostazioni, parte, len(parti))
        giocatori = parte.giocatori
        print(f"({impostazioni['tabellone']})")
    elif ci_sono_errori(problemi):
        return stampa_problemi(problemi)
    elif len(parti) == 1:
        impostazioni = dict(impostazioni)
        impostazioni.update(parti[0].impostazioni)
    if controllo_selezione.e_di_selezione(percorso):
        print("(tabellone di selezione)")
        voci, problemi = controllo_selezione.leggi_tabellone(percorso, giocatori)
        if not ci_sono_errori(problemi):
            problemi += controllo_selezione.controlla(
                voci, giocatori, classifiche,
                impostazioni.get("qualificati entranti", 0),
                impostazioni.get("qualificati uscenti", 1),
                impostazioni.get("teste di serie"))
        return stampa_problemi(problemi, se_nessuno="Il tabellone rispetta le regole del manuale: "
                                                    "nessun problema.")
    posti, problemi = leggi_tabellone(percorso, giocatori)
    if not ci_sono_errori(problemi):
        problemi += controlla_tabellone(giocatori, classifiche, impostazioni, posti)
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
