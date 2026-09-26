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

from programma.calcoli import SELEZIONE, calcola, conta_per_classifica
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
            chi = "che ha una classifica piu' alta ed entra" if len(dopo) == 1 \
                else "che hanno una classifica piu' alta ed entrano"
            errore(f"{a.giocatore.codice} ({a.classifica}) entra al turno {a.turno}, dopo "
                   f"{_elenco(dopo)}, {chi} prima: nessuno puo' entrare in gara dopo un "
                   f"giocatore di classifica inferiore (Volume II, pagina 4, regola b)")
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
    sezioni = not _potenza_di_due(Qu)
    if q and sezioni and max(q_parti) - min(q_parti) > 1:
        # Nel tabellone a sezioni e' una regola (Volume II, pagina 4, regola f.b).
        errore(f"i qualificati entranti non sono distribuiti in modo uguale tra le sezioni: "
               f"da {min(q_parti)} a {max(q_parti)}; la differenza puo' essere al massimo di uno "
               f"(Volume I, capitolo III, lettera B)")
    elif q and max(q_parti) - min(q_parti) > 1:
        # Nei tabelloni di selezione e' una raccomandazione del metodo: a volte non si puo'
        # (per esempio se alcuni corridoi hanno solo coppie di ammessi, esercizio 3.21).
        avviso(f"i qualificati entranti non sono divisi in modo uguale tra i qualificati uscenti: "
               f"da {min(q_parti)} a {max(q_parti)} (Volume I, capitolo IV, punto 3.9)")
    if sezioni:
        per_sezione = [len(voci_di(r)) for r in radici]
        if max(per_sezione) - min(per_sezione) > 2:
            # Per il manuale il tabellone e' sbagliato (Volume II, esercizio 4.07).
            errore(f"le sezioni hanno un numero di giocatori troppo diverso (da {min(per_sezione)} "
                   f"a {max(per_sezione)}): la differenza puo' essere di due al massimo "
                   f"(Volume I, capitolo III, lettera B; Volume II, esercizio 4.07)")

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
                      qualificati_entranti=q, qualificati_uscenti=Qu, teste_di_serie=T or None,
                      tipo=SELEZIONE)
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
            # Si puo' solo se anche il numero minimo di teste di serie entra in tre turni
            # (Volume II, esercizi 4.13 e 4.14: "e' obbligatorio collocare le teste di
            # serie negli ultimi tre turni").
            piu_forti = sorted(diretti, key=lambda v: (livello[v.classifica], -v.turno))[:minimo]
            turni_minimo = {v.turno for v in piu_forti}
            if max(turni_minimo) - min(turni_minimo) > 1:
                avviso(f"le teste di serie entrano in gara in {len(turni_teste)} turni diversi: "
                       f"si deve, perche' anche le {minimo} teste di serie minime entrano in "
                       f"piu' di due turni (Volume II, esercizio 4.14)")
            else:
                errore("le teste di serie devono entrare in gara nello stesso turno o in due "
                       "turni consecutivi (Volume I, capitolo IV, lettera E)")
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
    for messaggio in raccomandazioni(radici, livello, finale=Qu == 1):
        avviso(messaggio)
    return problemi


def raccomandazioni(radici, livello, finale=False):
    """Le raccomandazioni 2, 3, 5 e 6 (Volume I, capitolo I, lettera H) non seguite.

    Si immagina che vinca sempre il giocatore di classifica piu' alta (a parita',
    quello in alto); un q vale come il giocatore piu' debole, e le sue partite non
    contano per le raccomandazioni sulla differenza di classifica.
    Restituisce i messaggi, uno per raccomandazione."""
    livello_q = max(livello.values()) + 1
    progressioni_pari, salti, compressioni = [], [], []
    a_favore = {}  # id della voce -> [voce, incontri in favore di pronostico, primo avversario]

    def nome(voce):
        return f"{voce.giocatore.codice} ({voce.classifica})" if voce.giocatore else f"({voce.classifica})"

    def visita(nodo):
        """(voce del vincitore previsto oppure None per un q, livello, incontri giocati)."""
        if isinstance(nodo, Voce):
            if nodo.tipo == QUALIFICATO_ENTRANTE:
                return None, livello_q, 0
            a_favore[id(nodo)] = [nodo, 0, None]
            return nodo, livello[nodo.classifica], 0
        a, b = visita(nodo.alto), visita(nodo.basso)
        for (voce, _, giocati), (_, livello_altro, _) in ((a, b), (b, a)):
            if voce and giocati == 0:
                a_favore[id(voce)][2] = livello_altro
        (voce_a, livello_a, giocati_a), (voce_b, livello_b, giocati_b) = a, b
        if voce_a and voce_b and (giocati_a == 0) != (giocati_b == 0):
            # Progressione: chi entra contro il vincitore dei turni prima.
            (entra, livello_e, _), (vinc, livello_v, giocati_v) = (a, b) if giocati_a == 0 else (b, a)
            if livello_e == livello_v and giocati_v == 1:
                progressioni_pari.append(f"{nome(vinc)} contro {nome(entra)}")
        elif voce_a and voce_b and giocati_a == giocati_b == 1 and livello_a != livello_b:
            # Compressione: due ammessi che si incontrano dopo aver vinto il primo incontro.
            compressioni.append(f"{nome(voce_a)} contro {nome(voce_b)}")
        vince, perde = (a, b) if a[1] <= b[1] else (b, a)
        # Raccomandazione 6: chi ha gia' vinto due incontri non dovrebbe trovare un
        # avversario di piu' di due gruppi piu' forte.
        if vince[0] and perde[0] and perde[2] >= 2 and perde[1] - vince[1] > 2:
            salti.append(f"{nome(perde[0])} contro {nome(vince[0])}")
        if vince[0] and perde[1] > vince[1]:
            a_favore[id(vince[0])][1] += 1
        return vince[0], vince[1], vince[2] + 1

    for radice in radici:
        visita(radice)

    messaggi = []
    if compressioni:
        messaggi.append("compressioni tra giocatori di classifica diversa (si raccomanda la stessa "
                        "classifica): " + "; ".join(compressioni)
                        + " (Volume I, capitolo I, H.2)")
    if progressioni_pari:
        messaggi.append("giocatori che, vinto il primo incontro, incontrano un ammesso della stessa "
                        "classifica: " + "; ".join(progressioni_pari)
                        + " (Volume I, capitolo I, H.3)")
    if not finale:
        troppi = [nome(v) for v, n, _ in a_favore.values() if n > 2]
        if troppi:
            messaggi.append("giocatori che devono giocare piu' di due incontri in favore di "
                            "pronostico (mai piu' di due): " + ", ".join(troppi)
                            + " (Volume I, capitolo I, H.5)")
        # Tutti dovrebbero giocare un incontro in favore di pronostico. Il manuale accetta
        # le coppie di pari classifica (esempio 67), ma non che alcuni giocatori comincino
        # contro un piu' forte mentre altri della stessa classifica contro un piu' debole
        # (esempi 33 e 34).
        in_favore, contro = set(), {}
        for voce, _, primo in a_favore.values():
            if primo is None:
                continue
            if primo > livello[voce.classifica]:
                in_favore.add(voce.classifica)
            elif primo < livello[voce.classifica]:
                contro.setdefault(voce.classifica, []).append(nome(voce))
        diversi = [c for c in sorted(contro, key=livello.get) if c in in_favore]
        if diversi:
            messaggi.append("giocatori che cominciano contro un giocatore di classifica piu' alta, "
                            "mentre altri della stessa classifica cominciano in favore di "
                            "pronostico: " + ", ".join(n for c in diversi for n in contro[c])
                            + " (Volume I, capitolo I, H.5)")
    if salti:
        messaggi.append("incontri con piu' di due gruppi di differenza di classifica: "
                        + "; ".join(salti) + " (Volume I, capitolo I, H.6)")
    return messaggi


def _potenza_di_due(n):
    return n >= 1 and n & (n - 1) == 0
