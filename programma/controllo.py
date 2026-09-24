"""Controllo di un tabellone di estrazione con le regole del manuale.

Il tabellone da controllare puo' essere fatto dal programma oppure scritto
(o corretto) a mano in un file di testo: un posto per riga, dall'alto in basso.
Ogni riga puo' essere:
    G001            un giocatore (il suo codice, come in dati/giocatori.txt)
    (1) G001        un giocatore testa di serie numero 1
    posto libero    un posto libero (bye); va bene anche solo "libero"
    q               il posto di un qualificato entrante
Prima puo' esserci il numero del posto (1, 2, 3...) e dopo il codice si
puo' scrivere quello che si vuole (classifica, circolo): il programma
prende classifica e circolo da dati/giocatori.txt.
E' lo stesso modo in cui il programma salva il tabellone in risultati/.

Il controllo segue il manuale (Volume I, capitoli I, II e III) e segnala:
  ERRORE  una regola non rispettata: il tabellone va corretto;
  AVVISO  una raccomandazione non seguita, o una cosa da guardare.
"""

import random
import re

from programma.calcoli import (calcola, conta_per_classifica, dimensione_del_tabellone,
                               e_potenza_di_due)
from programma.dati import AVVISO, ERRORE, Problema, leggi_righe
from programma.sorteggio import (GIOCATORE, LIBERO, QUALIFICATO_ENTRANTE, Posto, Tabellone,
                                 giocatori_per_sezione, incontri_stesso_circolo, schema,
                                 sorteggia)

_RIGA = re.compile(r"^(?:(\d+)\s+)?(?:\(\s*(\d+)\s*\)\s*)?(\S+)(.*)$")


def leggi_tabellone(percorso, giocatori):
    """Legge un tabellone da un file di testo. Restituisce i posti e i problemi."""
    per_codice = {g.codice.upper(): g for g in giocatori}
    posti = []
    problemi = []
    gia_messi = {}  # codice -> riga dove compare la prima volta
    numeri_sbagliati = False

    for numero_riga, riga in leggi_righe(percorso):
        trovato = _RIGA.match(riga)
        numero, testa, parola, resto = trovato.groups()
        testa = int(testa) if testa else 0
        if numero and int(numero) != len(posti) + 1 and not numeri_sbagliati:
            problemi.append(Problema(
                ERRORE, percorso, numero_riga,
                f"la riga dice posto {numero}, ma e' il posto {len(posti) + 1}: "
                f"forse manca una riga, o ce n'e' una in piu'"))
            numeri_sbagliati = True  # uno basta: gli altri numeri sarebbero tutti spostati
        parola_minuscola = parola.lower()
        if parola_minuscola in ("libero", "bye", "-") or (
                parola_minuscola == "posto" and resto.strip().lower().startswith("libero")):
            posti.append(Posto(LIBERO, testa))
        elif parola_minuscola == "q":
            posti.append(Posto(QUALIFICATO_ENTRANTE, testa))
        elif parola.upper() in per_codice:
            codice = parola.upper()
            if codice in gia_messi:
                problemi.append(Problema(
                    ERRORE, percorso, numero_riga,
                    f"il giocatore {parola} e' gia' nel tabellone alla riga {gia_messi[codice]}"))
            gia_messi.setdefault(codice, numero_riga)
            posti.append(Posto(GIOCATORE, testa, per_codice[codice]))
        else:
            problemi.append(Problema(
                ERRORE, percorso, numero_riga,
                f"\"{parola}\" non e' un giocatore di dati/giocatori.txt, "
                f"ne' \"posto libero\", ne' \"q\""))
            posti.append(Posto(GIOCATORE, testa))

    if not posti:
        problemi.append(Problema(ERRORE, percorso, 0, "il tabellone e' vuoto"))
    return posti, problemi


def _elenco_posti(numeri):
    """[3, 7, 12] -> 'ai posti 3, 7 e 12'; [5] -> 'al posto 5'"""
    numeri = [str(n) for n in numeri]
    if len(numeri) == 1:
        return f"al posto {numeri[0]}"
    return f"ai posti {', '.join(numeri[:-1])} e {numeri[-1]}"


def _descrivi(posto):
    g = posto.giocatore
    return f"{g.codice} ({g.classifica})"


def controlla(posti, giocatori, classifiche, qualificati_entranti=0, qualificati_uscenti=1,
              teste_di_serie_impostate=None):
    """Controlla un tabellone e restituisce l'elenco dei problemi trovati.

    posti          i posti del tabellone, dall'alto in basso (oggetti Posto)
    giocatori      i giocatori iscritti (tutti devono essere nel tabellone)
    classifiche    le classifiche, dalla piu' alta alla piu' bassa
    """
    problemi = []

    def errore(messaggio):
        problemi.append(Problema(ERRORE, "", 0, messaggio))

    def avviso(messaggio):
        problemi.append(Problema(AVVISO, "", 0, messaggio))

    livello = {c: i for i, c in enumerate(classifiche)}  # 0 = classifica piu' alta
    D = len(posti)
    Qu = qualificati_uscenti
    sezioni = 0 if e_potenza_di_due(Qu) else Qu

    # --- Dimensione e giocatori -------------------------------------------------
    if sezioni:
        if D % sezioni or not e_potenza_di_due(D // sezioni) or D < 2 * sezioni:
            errore(f"il tabellone ha {D} posti: con {sezioni} qualificati uscenti e' un tabellone "
                   f"a {sezioni} sezioni, e i posti devono essere {sezioni} per 2, 4, 8, 16... "
                   f"({', '.join(str(sezioni * 2 ** k) for k in range(1, 5))}...)")
            return problemi
    elif D < 2 or not e_potenza_di_due(D):
        errore(f"il tabellone ha {D} posti: i posti devono essere 2, 4, 8, 16, 32, 64...")
        return problemi
    larghezza_sezione = D // sezioni if sezioni else D
    coppie_per_sezione = larghezza_sezione // 2

    nel_tabellone = {p.giocatore.codice.upper() for p in posti if p.giocatore}
    mancano = [g.codice for g in giocatori if g.codice.upper() not in nel_tabellone]
    if mancano:
        errore(f"mancano nel tabellone questi giocatori iscritti: {', '.join(mancano)}")

    q = sum(1 for p in posti if p.tipo == QUALIFICATO_ENTRANTE)
    if q != qualificati_entranti:
        errore(f"nel tabellone ci sono {q} posti per i qualificati entranti (q), "
               f"ma in dati/torneo.txt i qualificati entranti sono {qualificati_entranti}")

    diretti = [p for p in posti if p.tipo == GIOCATORE and p.giocatore]
    N = len(diretti) + q
    giusta = dimensione_del_tabellone(N, Qu)
    if D != giusta:
        errore(f"con {N} giocatori il tabellone deve avere {giusta} posti, invece ne ha {D} "
               + ("(Volume I, capitolo III, lettera C)" if sezioni
                  else "(Volume I, capitolo II, lettera B)"))
        return problemi
    if mancano:
        return problemi

    coppie = [(i, i + 1) for i in range(0, D, 2)]
    for alto, basso in coppie:
        if posti[alto].tipo == LIBERO and posti[basso].tipo == LIBERO:
            errore(f"ai posti {alto + 1} e {basso + 1} ci sono due posti liberi uno contro l'altro")

    # --- Teste di serie ----------------------------------------------------------
    teste = {}
    for i, posto in enumerate(posti):
        if not posto.testa_di_serie:
            continue
        if posto.tipo == LIBERO:
            errore(f"al posto {i + 1} c'e' un numero di testa di serie su un posto libero")
        elif posto.tipo == QUALIFICATO_ENTRANTE:
            errore(f"al posto {i + 1} un qualificato entrante e' testa di serie: "
                   f"un qualificato non puo' mai essere testa di serie (Volume I, capitolo I, lettera E)")
        elif posto.testa_di_serie in teste:
            errore(f"la testa di serie n. {posto.testa_di_serie} compare due volte "
                   f"(posti {teste[posto.testa_di_serie] + 1} e {i + 1})")
        else:
            teste[posto.testa_di_serie] = i
    T = len(teste)
    if T and sorted(teste) != list(range(1, T + 1)):
        errore(f"le teste di serie devono essere numerate da 1 a {T} senza salti: "
               f"ci sono i numeri {', '.join(map(str, sorted(teste)))}")
        return problemi
    if any(p.tipo != GIOCATORE and p.testa_di_serie for p in posti):
        return problemi

    calcoli = calcola(conta_per_classifica([p.giocatore for p in diretti], classifiche),
                      qualificati_entranti=q, qualificati_uscenti=qualificati_uscenti,
                      teste_di_serie=T)
    if calcoli.teste_di_serie_minimo is None:
        if T:
            errore("con soli giocatori non classificati (4.NC) non si fanno teste di serie")
            return problemi
    elif T == 0:
        errore(f"mancano le teste di serie: devono essere tra {calcoli.teste_di_serie_minimo} "
               f"e {calcoli.teste_di_serie_massimo} (Volume I, capitolo I, lettera C)")
        return problemi
    problemi += calcoli.problemi
    if any(p.gravita == ERRORE for p in calcoli.problemi):
        return problemi
    if teste_di_serie_impostate is not None and teste_di_serie_impostate != T:
        avviso(f"nel tabellone ci sono {T} teste di serie, ma in dati/torneo.txt "
               f"ne sono indicate {teste_di_serie_impostate}")

    # Le teste di serie sono i giocatori con la classifica piu' alta, in ordine.
    for k in range(1, T):
        prima, dopo = posti[teste[k]], posti[teste[k + 1]]
        if livello[dopo.giocatore.classifica] < livello[prima.giocatore.classifica]:
            errore(f"la testa di serie n. {k + 1}, {_descrivi(dopo)}, ha una classifica piu' alta "
                   f"della n. {k}, {_descrivi(prima)}: le teste di serie si numerano dalla "
                   f"classifica piu' alta (Volume I, capitolo I, lettera D)")
    if T:
        ultima = max(livello[posti[i].giocatore.classifica] for i in teste.values())
        piu_forti = [_descrivi(p) for p in diretti
                     if not p.testa_di_serie and livello[p.giocatore.classifica] < ultima]
        if piu_forti:
            errore(f"non sono teste di serie, ma hanno una classifica piu' alta di una testa "
                   f"di serie: {', '.join(piu_forti)} (Volume I, capitolo I, lettera D)")

    # --- Confronto con lo schema del manuale --------------------------------------
    atteso = schema(calcoli, random.Random(0))
    for k, i in sorted(teste.items()):
        giusto = next(j for j, p in enumerate(atteso) if p.testa_di_serie == k)
        if i != giusto:
            errore(f"la testa di serie n. {k} e' al posto {i + 1}, ma secondo il manuale "
                   f"deve stare al posto {giusto + 1} (Volume I, capitolo I, lettera E)")

    def aspettito(lista, i):
        return lista[i ^ 1].tipo == LIBERO

    liberi_attesi = [i + 1 for i, p in enumerate(atteso) if p.tipo == LIBERO]
    liberi = [i + 1 for i, p in enumerate(posti) if p.tipo == LIBERO]
    if liberi != liberi_attesi:
        errore(f"i posti liberi sono {_elenco_posti(liberi)}, ma secondo il manuale devono "
               f"essere {_elenco_posti(liberi_attesi)}: gli aspettiti vanno messi come se "
               f"fossero teste di serie (Volume I, capitolo II)")
    else:
        q_attesi = [i + 1 for i, p in enumerate(atteso)
                    if p.tipo == QUALIFICATO_ENTRANTE and aspettito(atteso, i)]
        q_messi = [i + 1 for i, p in enumerate(posti)
                   if p.tipo == QUALIFICATO_ENTRANTE and aspettito(posti, i)]
        if q_messi != q_attesi:
            errore(f"i qualificati entranti con il posto libero sono {_elenco_posti(q_messi)}, "
                   f"ma secondo il manuale devono essere {_elenco_posti(q_attesi)}: vanno "
                   f"contro le teste di serie piu' deboli (Volume I, capitolo II, lettera D)")

    # --- Chi entra al primo turno e chi al secondo ---------------------------------
    al_secondo = [p for i, p in enumerate(posti) if p in diretti and aspettito(posti, i)]
    al_primo = [p for i, p in enumerate(posti) if p in diretti and not aspettito(posti, i)]
    if al_secondo and al_primo:
        piu_bassa_al_secondo = max(livello[p.giocatore.classifica] for p in al_secondo)
        piu_alti_al_primo = [p for p in al_primo
                             if livello[p.giocatore.classifica] < piu_bassa_al_secondo]
        if piu_alti_al_primo:
            errore(f"giocano il primo turno {', '.join(_descrivi(p) for p in piu_alti_al_primo)}, "
                   f"mentre entrano al secondo turno giocatori di classifica piu' bassa: "
                   f"nessuno puo' entrare in gara dopo un giocatore di classifica inferiore "
                   f"(Volume I, capitolo I, lettera G)")
    teste_al_primo = [k for k, i in teste.items() if not aspettito(posti, i)]
    teste_al_secondo = [k for k, i in teste.items() if aspettito(posti, i)]
    if teste_al_primo and teste_al_secondo and min(teste_al_primo) < max(teste_al_secondo):
        errore(f"la testa di serie n. {min(teste_al_primo)} gioca il primo turno, mentre la "
               f"n. {max(teste_al_secondo)} entra al secondo: una testa di serie non puo' "
               f"entrare in gara dopo una con il numero piu' basso (Volume I, capitolo I, lettera E)")

    # --- Qualificati entranti -----------------------------------------------------
    def nella_meta_superiore(indice_posto):
        """Se il posto e' nella meta' superiore del tabellone (o della sua sezione)."""
        return (indice_posto // 2) % coppie_per_sezione < max(1, coppie_per_sezione // 2)

    di_cosa = "della sua sezione" if sezioni else "del tabellone"
    for alto, basso in coppie:
        tipi = (posti[alto].tipo, posti[basso].tipo)
        if tipi == (QUALIFICATO_ENTRANTE, QUALIFICATO_ENTRANTE):
            errore(f"ai posti {alto + 1} e {basso + 1} due qualificati entranti si incontrano "
                   f"al primo turno (Volume I, capitolo I, lettera G)")
        elif QUALIFICATO_ENTRANTE in tipi and LIBERO not in tipi:
            superiore = nella_meta_superiore(alto)
            giusto = basso if superiore else alto
            if posti[giusto].tipo != QUALIFICATO_ENTRANTE:
                dove = "in basso" if superiore else "in alto"
                meta_nome = "superiore" if superiore else "inferiore"
                errore(f"il qualificato entrante al posto {(alto if giusto == basso else basso) + 1} "
                       f"deve stare {dove} nel suo incontro (al posto {giusto + 1}), perche' e' "
                       f"nella meta' {meta_nome} {di_cosa} (Volume I, capitolo I, lettera F)")
    # Un q che entra al secondo turno non deve trovare un altro q al suo primo incontro.
    for i, posto in enumerate(posti):
        if posto.tipo == QUALIFICATO_ENTRANTE and aspettito(posti, i):
            vicini = range(((i // 4) * 4), (i // 4) * 4 + 4)
            altri = [j for j in vicini if j // 2 != i // 2 and posti[j].tipo == QUALIFICATO_ENTRANTE]
            if altri:
                errore(f"il qualificato entrante al posto {i + 1} puo' incontrare al suo primo "
                       f"incontro il qualificato al posto {altri[0] + 1}: due qualificati non "
                       f"possono incontrarsi al loro primo incontro (Volume I, capitolo I, lettera G)")
    # Se un q entra al secondo turno, non ci devono essere incontri tra ammessi al primo turno.
    q_al_secondo = [i + 1 for i, p in enumerate(posti)
                    if p.tipo == QUALIFICATO_ENTRANTE and aspettito(posti, i)]
    tra_ammessi = [(a, b) for a, b in coppie
                   if posti[a].tipo == GIOCATORE and posti[b].tipo == GIOCATORE]
    if q_al_secondo and tra_ammessi:
        errore(f"il qualificato entrante {_elenco_posti(q_al_secondo)} entra al secondo turno, "
               f"mentre al primo turno ci sono incontri tra giocatori ammessi direttamente: "
               f"i qualificati vanno messi prima al primo turno (Volume I, capitolo I, lettera G)")
    # Distribuzione dei q tra le sezioni, con una differenza di uno al massimo.
    if sezioni:
        q_sezioni = [sum(1 for p in posti[i:i + larghezza_sezione] if p.tipo == QUALIFICATO_ENTRANTE)
                     for i in range(0, D, larghezza_sezione)]
        if max(q_sezioni) - min(q_sezioni) > 1:
            piu, meno = q_sezioni.index(max(q_sezioni)), q_sezioni.index(min(q_sezioni))
            errore(f"i qualificati entranti non sono distribuiti in modo uguale tra le sezioni: "
                   f"la sezione {piu + 1} ne ha {max(q_sezioni)}, la sezione {meno + 1} ne ha "
                   f"{min(q_sezioni)}; la differenza puo' essere al massimo di uno "
                   f"(Volume I, capitolo III, lettera B)")
    # Distribuzione dei q nelle frazioni del tabellone (o di ogni sezione): meta', quarti...
    larghezza = larghezza_sezione
    squilibrio = None
    while larghezza >= 4 and squilibrio is None:
        for inizio in range(0, D, larghezza):
            su = sum(1 for p in posti[inizio:inizio + larghezza // 2] if p.tipo == QUALIFICATO_ENTRANTE)
            giu = sum(1 for p in posti[inizio + larghezza // 2:inizio + larghezza]
                      if p.tipo == QUALIFICATO_ENTRANTE)
            if abs(su - giu) > 1:
                squilibrio = (inizio, larghezza, su, giu)
                break
        larghezza //= 2
    if squilibrio:
        inizio, larghezza, su, giu = squilibrio
        errore(f"i qualificati entranti non sono distribuiti in modo uguale: dal posto {inizio + 1} "
               f"al {inizio + larghezza // 2} ce ne sono {su}, dal {inizio + larghezza // 2 + 1} "
               f"al {inizio + larghezza} ce ne sono {giu} (Volume I, capitolo I, lettera G)")

    # --- Sezioni con lo stesso numero di giocatori -----------------------------------
    if sezioni:
        per_sezione = giocatori_per_sezione(posti, sezioni)
        if max(per_sezione) - min(per_sezione) > 2:
            avviso(f"le sezioni hanno un numero di giocatori troppo diverso (da {min(per_sezione)} "
                   f"a {max(per_sezione)}): la differenza dovrebbe essere di due al massimo "
                   f"(Volume I, capitolo III, lettera B; Volume II, esercizio 2.23)")

    # --- Regola dello stesso circolo ------------------------------------------------
    stessi = incontri_stesso_circolo(Tabellone(calcoli, posti))
    if stessi:
        elenco = "; ".join(f"{a.giocatore.codice} e {b.giocatore.codice} ({a.giocatore.circolo})"
                           for a, b in stessi)
        prova = sorteggia(calcoli, [p.giocatore for p in diretti], random.Random(0), classifiche)
        migliore = len(incontri_stesso_circolo(prova))
        if migliore < len(stessi):
            quanti = "senza incontri" if migliore == 0 else f"con solo {migliore} incontri"
            errore(f"al primo turno si incontrano giocatori dello stesso circolo: {elenco}. "
                   f"Si poteva evitare: esiste un sorteggio {quanti} di questo tipo")
        else:
            avviso(f"al primo turno si incontrano giocatori dello stesso circolo: {elenco}. "
                   f"Il programma non ha trovato un sorteggio con meno incontri di questo tipo")
    return problemi
