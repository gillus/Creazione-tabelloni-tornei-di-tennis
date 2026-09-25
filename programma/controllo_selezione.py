"""Controllo di un tabellone di selezione con le regole del manuale (Volume I, capitolo IV).

Il tabellone si scrive in un file di testo, un giocatore per riga, dall'alto in
basso, con il turno in cui entra in gara:
    turno 4  (1) G001     la testa di serie n. 1, che entra al quarto turno
    turno 2      G007     un giocatore che entra al secondo turno
    turno 1      q        un qualificato entrante, al primo turno
E' lo stesso modo in cui il programma salva il tabellone in risultati/.
Il programma ricostruisce gli incontri: due vicini pronti per lo stesso turno
si incontrano, e il vincitore e' pronto per il turno dopo.

Il controllo segnala:
  ERRORE  una regola non rispettata: il tabellone va corretto;
  AVVISO  una raccomandazione non seguita, o una cosa da guardare.
"""

import re

from programma.calcoli import calcola, conta_per_classifica
from programma.dati import AVVISO, ERRORE, Problema, leggi_righe
from programma.selezione_tabellone import (Incontro, Posti, TabelloneSelezione, Voce,
                                           albero_dalle_voci, coppie_di_ammessi, incontri_di,
                                           numeri_dei_lati, stesso_circolo, voci_di)
from programma.sorteggio import GIOCATORE, QUALIFICATO_ENTRANTE

_RIGA = re.compile(r"^turno\s+(\d+)\s+(?:\(\s*(\d+)\s*\)\s*)?(\S+)(.*)$", re.IGNORECASE)


def e_di_selezione(percorso):
    """Se il file contiene un tabellone di selezione (righe che cominciano con "turno")."""
    return any(riga.lower().startswith("turno") for _, riga in leggi_righe(percorso))


def leggi_tabellone(percorso, giocatori):
    """Legge un tabellone di selezione. Restituisce le voci (dall'alto) e i problemi."""
    per_codice = {g.codice.upper(): g for g in giocatori}
    voci, problemi = [], []
    gia_messi = {}
    for numero_riga, riga in leggi_righe(percorso):
        trovato = _RIGA.match(riga)
        if not trovato:
            problemi.append(Problema(ERRORE, percorso, numero_riga,
                                     f"la riga deve cominciare con \"turno\" e il numero del turno: "
                                     f"\"{riga}\""))
            continue
        turno, testa, parola, _ = trovato.groups()
        turno, testa = int(turno), int(testa) if testa else 0
        if turno < 1:
            problemi.append(Problema(ERRORE, percorso, numero_riga, "il turno deve essere almeno 1"))
            continue
        if parola.lower() == "q":
            voci.append(Voce(QUALIFICATO_ENTRANTE, turno, testa_di_serie=testa))
        elif parola.upper() in per_codice:
            codice = parola.upper()
            if codice in gia_messi:
                problemi.append(Problema(
                    ERRORE, percorso, numero_riga,
                    f"il giocatore {parola} e' gia' nel tabellone alla riga {gia_messi[codice]}"))
            gia_messi.setdefault(codice, numero_riga)
            g = per_codice[codice]
            voci.append(Voce(GIOCATORE, turno, g.classifica, testa, g))
        else:
            problemi.append(Problema(
                ERRORE, percorso, numero_riga,
                f"\"{parola}\" non e' un giocatore di dati/giocatori.txt, ne' \"q\""))
    if not voci:
        problemi.append(Problema(ERRORE, percorso, 0, "il tabellone e' vuoto"))
    return voci, problemi


def _elenco(voci):
    return ", ".join(f"{v.giocatore.codice} ({v.classifica})" for v in voci)


def controlla(voci, giocatori, classifiche, qualificati_entranti=0, qualificati_uscenti=1,
              teste_di_serie_impostate=None):
    """Controlla un tabellone di selezione e restituisce l'elenco dei problemi trovati."""
    problemi = []

    def errore(messaggio):
        problemi.append(Problema(ERRORE, "", 0, messaggio))

    def avviso(messaggio):
        problemi.append(Problema(AVVISO, "", 0, messaggio))

    livello = {c: i for i, c in enumerate(classifiche)}
    Qu = qualificati_uscenti

    # --- Forma del tabellone ----------------------------------------------------------
    # L'ultimo turno e' quello in cui restano tanti incontri quanti i qualificati uscenti.
    for R in range(max(v.turno for v in voci), max(v.turno for v in voci) + 12):
        radici, bene = albero_dalle_voci(voci, R)
        if not bene or len(radici) <= Qu:
            break
    if not bene or any(isinstance(r, Voce) for r in radici):
        errore("i turni scritti non formano un tabellone: ogni giocatore deve avere accanto un "
               "avversario pronto per lo stesso turno (un altro giocatore che entra in quel turno, "
               "o il vincitore degli incontri sopra o sotto di lui)")
        return problemi
    if len(radici) != Qu:
        errore(f"il tabellone da' {len(radici)} qualificati, ma in dati/torneo.txt i qualificati "
               f"uscenti sono {Qu}")
        return problemi
    ultimi = {r.turno for r in radici}
    if len(ultimi) > 1:
        errore(f"i qualificati uscenti devono essere noti tutti nello stesso turno, invece "
               f"escono ai turni {', '.join(map(str, sorted(ultimi)))} (Volume II, pagina 4, regola d)")
        return problemi
    R = ultimi.pop()

    # --- Giocatori -----------------------------------------------------------------
    nel_tabellone = {v.giocatore.codice.upper() for v in voci if v.giocatore}
    mancano = [g.codice for g in giocatori if g.codice.upper() not in nel_tabellone]
    if mancano:
        errore(f"mancano nel tabellone questi giocatori iscritti: {', '.join(mancano)}")
        return problemi
    q = sum(1 for v in voci if v.tipo == QUALIFICATO_ENTRANTE)
    if q != qualificati_entranti:
        errore(f"nel tabellone ci sono {q} qualificati entranti (q), ma in dati/torneo.txt "
               f"sono {qualificati_entranti}")
    diretti = [v for v in voci if v.tipo == GIOCATORE]

    # --- Chi entra in quale turno ---------------------------------------------------
    for a in diretti:
        dopo = [b for b in diretti if livello[b.classifica] < livello[a.classifica]
                and b.turno < a.turno]
        if dopo:
            errore(f"{a.giocatore.codice} ({a.classifica}) entra al turno {a.turno}, dopo "
                   f"{_elenco(dopo)} che hanno una classifica piu' alta ed entrano prima: nessuno "
                   f"puo' entrare in gara dopo un giocatore di classifica inferiore "
                   f"(Volume II, pagina 4, regola b)")
            break
    gruppi = {}
    for v in voci:
        gruppi.setdefault("q" if v.tipo == QUALIFICATO_ENTRANTE else v.classifica, set()).add(v.turno)
    for gruppo, turni in sorted(gruppi.items()):
        if len(turni) > 2 or max(turni) - min(turni) > len(turni) - 1:
            chi = "i qualificati entranti" if gruppo == "q" else f"i giocatori ({gruppo})"
            errore(f"{chi} entrano ai turni {', '.join(map(str, sorted(turni)))}: devono entrare "
                   f"in un turno o in due turni consecutivi (Volume II, pagina 4, regola a)")

    # --- Qualificati entranti ---------------------------------------------------------
    def primo_incontro(voce):
        """L'incontro in cui la voce gioca per la prima volta, e il lato dell'avversario."""
        for radice in radici:
            for incontro in incontri_di(radice):
                if incontro.alto is voce:
                    return incontro.basso
                if incontro.basso is voce:
                    return incontro.alto
        return None

    for v in voci:
        if v.tipo != QUALIFICATO_ENTRANTE:
            continue
        avversario = primo_incontro(v)
        if avversario is not None and any(x.tipo == QUALIFICATO_ENTRANTE for x in voci_di(avversario)):
            posto = voci.index(v) + 1
            errore(f"il qualificato entrante al posto {posto} puo' incontrare un altro qualificato "
                   f"entrante al suo primo incontro (Volume II, pagina 4, regola c)")
    q_parti = [sum(1 for x in voci_di(r) if x.tipo == QUALIFICATO_ENTRANTE) for r in radici]
    if q and max(q_parti) - min(q_parti) > 1:
        # Nei tabelloni di selezione e' una raccomandazione del metodo: a volte non si puo'
        # (per esempio se alcuni corridoi hanno solo coppie di ammessi, esercizio 3.21).
        avviso(f"i qualificati entranti non sono divisi in modo uguale tra i qualificati uscenti: "
               f"da {min(q_parti)} a {max(q_parti)} (Volume I, capitolo IV, punto 3.9)")

    # --- Teste di serie ----------------------------------------------------------------
    teste = {}
    for v in voci:
        if not v.testa_di_serie:
            continue
        if v.tipo == QUALIFICATO_ENTRANTE:
            errore("un qualificato entrante non puo' mai essere testa di serie "
                   "(Volume I, capitolo I, lettera E)")
            return problemi
        if v.testa_di_serie in teste:
            errore(f"la testa di serie n. {v.testa_di_serie} compare due volte")
            return problemi
        teste[v.testa_di_serie] = v
    T = len(teste)
    if T and sorted(teste) != list(range(1, T + 1)):
        errore(f"le teste di serie devono essere numerate da 1 a {T} senza salti")
        return problemi
    calcoli = calcola(conta_per_classifica([v.giocatore for v in diretti], classifiche),
                      qualificati_entranti=q, qualificati_uscenti=Qu, teste_di_serie=T or None)
    minimo, massimo = calcoli.teste_di_serie_minimo, calcoli.teste_di_serie_massimo
    if minimo is None:
        if T:
            errore("con soli giocatori non classificati (4.NC) non si fanno teste di serie")
    elif not T:
        errore(f"mancano le teste di serie: devono essere tra {minimo} e {massimo} "
               f"(Volume I, capitolo I, lettera C)")
    else:
        problemi.extend(p for p in calcoli.problemi if "teste di serie" in p.messaggio)
        if teste_di_serie_impostate is not None and teste_di_serie_impostate != T:
            avviso(f"nel tabellone ci sono {T} teste di serie, ma in dati/torneo.txt ne sono "
                   f"indicate {teste_di_serie_impostate}")
        for k in range(1, T):
            if livello[teste[k + 1].classifica] < livello[teste[k].classifica]:
                errore(f"la testa di serie n. {k + 1} ha una classifica piu' alta della n. {k}: "
                       f"le teste di serie si numerano dalla classifica piu' alta "
                       f"(Volume I, capitolo I, lettera D)")
        ultima = max(livello[v.classifica] for v in teste.values())
        piu_forti = [v for v in diretti if not v.testa_di_serie and livello[v.classifica] < ultima]
        if piu_forti:
            errore(f"non sono teste di serie, ma hanno una classifica piu' alta di una testa di "
                   f"serie: {_elenco(piu_forti)} (Volume I, capitolo I, lettera D)")
        turni_teste = {v.turno for v in teste.values()}
        if max(turni_teste) - min(turni_teste) > 1:
            errore("le teste di serie devono entrare in gara nello stesso turno o in due turni "
                   "consecutivi (Volume I, capitolo IV, lettera E)")
        tabellone = TabelloneSelezione(None, Qu, 0 if _potenza_di_due(Qu) else Qu, T, radici)
        numeri = numeri_dei_lati(tabellone, Posti(R, Qu, tabellone.sezioni))
        for k, v in sorted(teste.items()):
            if numeri[id(v)] != k:
                errore(f"la testa di serie n. {k} non e' nel suo posto: deve stare dove, nella "
                       f"stessa frazione del tabellone, la somma dei numeri delle teste di serie "
                       f"e' costante (Volume I, capitolo I, lettera E)")
                break

    # --- Regola dello stesso circolo ----------------------------------------------------
    tabellone = TabelloneSelezione(None, Qu, 0, T, radici)
    stessi = stesso_circolo(tabellone)
    if stessi:
        elenco = "; ".join(f"{a.giocatore.codice} e {b.giocatore.codice} ({a.giocatore.circolo})"
                           for a, b in stessi)
        avviso(f"al loro primo incontro si incontrano giocatori dello stesso circolo: {elenco}")

    # --- Raccomandazioni -----------------------------------------------------------------
    uguali = [i for i in coppie_di_ammessi(tabellone) if i.alto.classifica != i.basso.classifica]
    if uguali:
        avviso("ci sono coppie di giocatori ammessi di classifica diversa che si incontrano al "
               "loro primo incontro: " + "; ".join(f"{i.alto.giocatore.codice} ({i.alto.classifica}) "
                                                   f"e {i.basso.giocatore.codice} ({i.basso.classifica})"
                                                   for i in uguali))
    return problemi


def _potenza_di_due(n):
    return n >= 1 and n & (n - 1) == 0
