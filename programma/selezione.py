"""Tabelloni di selezione, ad ingresso progressivo (manuale, Volume I, capitolo IV).

In un tabellone di selezione i giocatori entrano in gara in tre o piu' turni:
i piu' deboli (e i qualificati entranti) al primo turno, i piu' forti negli
ultimi turni. Il giudice arbitro prepara prima la "scala": per ogni turno,
partendo dall'ultimo, quanti giocatori entrano e di quale classifica.

Nella scala, in ogni turno entrano:
  - giocatori "singoli", che incontrano un vincitore del turno prima
    (progressione);
  - "coppie" di giocatori che entrano insieme e giocano tra loro: un
    qualificato entrante con uno dei giocatori di classifica piu' bassa
    (coppia indissolubile), oppure due giocatori della stessa classifica.
I vincitori del turno prima che non incontrano un singolo giocano tra loro
(compressione).

Il programma prova tutte le scale possibili che rispettano le regole e
sceglie quella che segue meglio le raccomandazioni del manuale (costo piu'
basso). Il giudice arbitro puo' scriverne una diversa in dati/torneo.txt.

Regole (Volume II, pagina 4, e Volume I, capitolo IV, punto 2.10):
  - i giocatori della stessa classifica entrano in gara in un turno o in due
    turni consecutivi, e cosi' i qualificati entranti;
  - nessuno entra in gara dopo un giocatore di classifica piu' bassa;
  - i qualificati entranti incontrano i giocatori di classifica piu' bassa.
"""

import re
from collections import Counter
from dataclasses import dataclass, field

from programma.calcoli import QUALIFICATO

# Oltre questo numero di turni una scala non ha senso.
MASSIMO_TURNI = 9
# Quante coppie di due ammessi si possono fare, al massimo, oltre a quelle necessarie.
MASSIMO_COPPIE_IN_PIU = 4
# Quante scale confrontare, almeno, prima di smettere di aggiungere coppie di due ammessi.
SCALE_DA_CONFRONTARE = 1_000
# Oltre questo numero di scale il programma smette di cercarne altre.
MASSIMO_SCALE = 20_000

# Il peso di ogni raccomandazione non seguita, nel costo di una scala.
PESO_COPPIA_DIVERSA = 3      # coppia di due ammessi di classifica diversa
PESO_AMMESSI_TRA_LORO = 1    # raccomandazione 4: due ammessi si incontrano al loro primo incontro
PESO_COPPIE_NON_NECESSARIE = 6  # ... anche quando i q bastano a fare i corridoi
PESO_PROGRESSIONE_PARI = 4   # raccomandazione 3: progressione tra pari classifica
PESO_COMPRESSIONE = 2        # raccomandazione 2: compressione tra classifiche diverse
PESO_DUE_A_FAVORE = 2        # raccomandazione 5: due incontri di fila "in favore di pronostico"
PESO_TRE_A_FAVORE = 6        # raccomandazione 5: mai piu' di due
PESO_CLASSIFICA_DIVISA = 2   # giocatori della stessa classifica in due turni diversi
PESO_MODI_DIVERSI = 2        # ... alcuni in coppia tra loro e altri no
PESO_TURNO = 2               # ogni turno in piu'
PESO_TURNO_VUOTO = 3         # un turno in cui non entra nessuno (solo compressioni)


@dataclass
class Turno:
    singoli: list = field(default_factory=list)  # classifiche, dalla piu' alta
    coppie: list = field(default_factory=list)   # (classifica, classifica oppure "q")
    posti: int = 0

    def entranti(self):
        return len(self.singoli) + 2 * len(self.coppie)


@dataclass
class Scala:
    turni: list  # dal primo turno all'ultimo
    qualificati_uscenti: int
    costo: float = 0

    def compressioni(self):
        """Quante compressioni in ogni turno (vincitori che giocano tra loro)."""
        risultato = []
        vincitori = 0
        for turno in self.turni:
            risultato.append((vincitori - len(turno.singoli)) // 2)
            vincitori = turno.posti // 2
        return risultato


def _calcola_posti(turni, qualificati_uscenti):
    """Riempie i posti di ogni turno, dall'ultimo al primo. Restituisce False se
    la scala non torna (per esempio un turno con un numero dispari di posti)."""
    posti = 2 * qualificati_uscenti
    for turno in reversed(turni):
        turno.posti = posti
        vincitori = posti - turno.entranti()
        if vincitori < len(turno.singoli) or (vincitori - len(turno.singoli)) % 2:
            return False
        posti = 2 * vincitori
    return posti == 0


# --- Tutte le scale possibili ------------------------------------------------------

def scale_possibili(diretti, qualificati_entranti, qualificati_uscenti,
                    massimo_turni=MASSIMO_TURNI, coppie_in_piu=MASSIMO_COPPIE_IN_PIU,
                    solo_con_piu=False):
    """Tutte le scale che rispettano le regole.

    diretti        le classifiche dei giocatori ammessi direttamente, una per
                   giocatore, dalla piu' alta alla piu' bassa
    coppie_in_piu  quante coppie di due ammessi si possono fare oltre a quelle
                   necessarie (quando i q sono meno dei qualificati uscenti)
    solo_con_piu   solo le scale con esattamente 'coppie_in_piu' coppie in piu'
    """
    q = qualificati_entranti
    liberi = diretti[:len(diretti) - q]
    compagni = diretti[len(diretti) - q:]  # i piu' deboli giocano contro i q
    trovate = []

    # Le coppie di due ammessi servono solo a creare i corridoi che mancano
    # (quando i q sono meno dei qualificati uscenti) o poco di piu'.
    necessarie = max(0, qualificati_uscenti - q)
    massimo_coppie_uguali = necessarie + coppie_in_piu

    vicoli_ciechi = set()  # situazioni da cui si e' gia' visto che non si arriva a niente

    def cerca(posti, i, j, turni, turni_di, coppie_uguali_usate=0):
        """i, j: quanti liberi e quanti compagni dei q sono gia' nella scala.
        turni_di: per ogni classifica (e per "q") i turni in cui entra, contati
        dall'ultimo (0 = ultimo turno). Restituisce True se ha trovato qualche scala."""
        if len(trovate) >= MASSIMO_SCALE:
            return True
        livello = len(turni)
        # Quello che conta per il seguito: posti, giocatori rimasti, e i turni gia'
        # usati dalle classifiche che devono ancora entrare.
        situazione = (posti, i, j, livello, coppie_uguali_usate,
                      turni_di.get(liberi[i]) if i < len(liberi) else None,
                      turni_di.get(compagni[j]) if j < len(compagni) else None,
                      turni_di.get(QUALIFICATO))
        if situazione in vicoli_ciechi:
            return False
        trovato = False
        restano_liberi = len(liberi) - i
        restano_compagni = len(compagni) - j
        for k in range(restano_compagni + 1):
            for d in range(min(restano_liberi // 2, massimo_coppie_uguali - coppie_uguali_usate) + 1):
                for s in range(restano_liberi - 2 * d + 1):
                    if k and s + 2 * d != restano_liberi:
                        continue  # i compagni dei q entrano dopo tutti gli altri
                    vincitori = posti - s - 2 * d - 2 * k
                    if vincitori < s:
                        break
                    if (vincitori - s) % 2:
                        continue
                    # Le coppie di due ammessi sono "se possibile" di pari classifica
                    # (Volume I, capitolo IV, B.2): se no, costano di piu'.
                    coppie_uguali = liberi[i + s:i + s + 2 * d]
                    resto = (restano_liberi - s - 2 * d) + 2 * (restano_compagni - k)
                    if vincitori == 0 and (s or resto):
                        continue
                    turni_rimasti = massimo_turni - livello - 1
                    if vincitori and (2 * vincitori > resto or turni_rimasti <= 0
                                      or resto > vincitori * 2 ** turni_rimasti):
                        continue  # i giocatori rimasti non bastano, o sono troppi
                    entrano = liberi[i:i + s + 2 * d] + compagni[j:j + k] + [QUALIFICATO] * (k > 0)
                    nuovi = _aggiorna_turni(turni_di, set(entrano), livello)
                    if nuovi is None:
                        continue
                    turno = Turno(liberi[i:i + s],
                                  [(coppie_uguali[x], coppie_uguali[x + 1]) for x in range(0, 2 * d, 2)]
                                  + [(c, QUALIFICATO) for c in compagni[j:j + k]])
                    if vincitori == 0:
                        if solo_con_piu and coppie_uguali_usate + d < massimo_coppie_uguali:
                            continue
                        scala = Scala(list(reversed(turni + [turno])), qualificati_uscenti)
                        if _calcola_posti(scala.turni, qualificati_uscenti):
                            trovate.append(scala)
                            trovato = True
                    elif cerca(2 * vincitori, i + s + 2 * d, j + k, turni + [turno], nuovi,
                               coppie_uguali_usate + d):
                        trovato = True
        if not trovato:
            vicoli_ciechi.add(situazione)
        return trovato

    cerca(2 * qualificati_uscenti, 0, 0, [], {})
    return trovate


def _aggiorna_turni(turni_di, classifiche, livello):
    """Aggiunge il turno 'livello' alle classifiche che entrano; None se una
    classifica entrerebbe in piu' di due turni, o in turni non consecutivi."""
    nuovi = dict(turni_di)
    for classifica in classifiche:
        gia = nuovi.get(classifica, ())
        if gia and (gia[-1] != livello - 1 or len(gia) >= 2):
            if gia[-1] == livello:
                continue
            return None
        nuovi[classifica] = gia + (livello,)
    return nuovi


# --- Il costo di una scala -------------------------------------------------------

def _costo_progressione(differenza):
    """Chi entra (piu' forte) contro il vincitore del turno prima."""
    if differenza <= 0:
        return PESO_PROGRESSIONE_PARI
    return differenza - 1


def _vince(a, b, finale=False):
    """Chi vince tra due giocatori (livello, incontri a favore): il piu' forte.

    Nel tabellone finale la raccomandazione 5 (mai piu' di due incontri di fila
    "in favore di pronostico") non vale (Volume I, capitolo I, H.5): non costa niente."""
    (livello_a, favore_a), (livello_b, favore_b) = a, b
    if livello_b < livello_a:
        (livello_a, favore_a), (livello_b, favore_b) = (livello_b, favore_b), (livello_a, favore_a)
    favore = favore_a + (livello_b > livello_a)
    if finale:
        return (livello_a, favore), 0
    costo = PESO_DUE_A_FAVORE * (favore == 2) + PESO_TRE_A_FAVORE * (favore >= 3)
    return (livello_a, favore), costo


def _turno_migliore(singoli, vincitori, finale=False):
    """Chi incontra chi in un turno, con il costo piu' basso.

    Si scorrono i vincitori del turno prima, dal piu' forte: ognuno o incontra
    il prossimo singolo (anche i singoli dal piu' forte) o gioca contro un altro
    vincitore (compressione). La scelta migliore si trova provandole tutte con
    la "programmazione dinamica". Restituisce il costo e chi passa il turno.
    """
    singoli = sorted(singoli)
    vincitori = sorted(vincitori)
    n, m = len(vincitori), len(singoli)
    # strati[i][(j, aperto)] = (costo, stato di prima, scelta) dopo i primi i vincitori:
    # j singoli gia' usati, aperto = il vincitore che aspetta un compagno.
    strati = [{(0, None): (0, None, None)}]
    for i in range(n):
        nuovo = {}

        def metti(stato, costo, prima, scelta):
            if stato not in nuovo or costo < nuovo[stato][0]:
                nuovo[stato] = (costo, prima, scelta)

        for (j, aperto), (costo, _, _) in strati[-1].items():
            if j < m:
                _, extra = _vince((singoli[j], 0), vincitori[i], finale)
                metti((j + 1, aperto),
                      costo + _costo_progressione(vincitori[i][0] - singoli[j]) + extra,
                      (j, aperto), ("singolo", j))
            if aperto is None:
                metti((j, i), costo, (j, aperto), ("aspetta",))
            else:
                a, b = vincitori[aperto], vincitori[i]
                _, extra = _vince(a, b, finale)
                metti((j, None), costo + PESO_COMPRESSIONE * abs(a[0] - b[0]) + extra,
                      (j, aperto), ("compressione", aperto))
        strati.append(nuovo)
    fine = (m, None)
    if fine not in strati[-1]:
        return float("inf"), []
    passano = []
    stato = fine
    for i in range(n, 0, -1):
        _, prima, scelta = strati[i][stato]
        if scelta[0] == "singolo":
            passano.append(_vince((singoli[scelta[1]], 0), vincitori[i - 1])[0])
        elif scelta[0] == "compressione":
            passano.append(_vince(vincitori[scelta[1]], vincitori[i - 1])[0])
        stato = prima
    return strati[-1][fine][0], passano


def costo_della_scala(scala, livello, qualificati_entranti=None, memoria=None):
    """Quanto la scala si allontana dalle raccomandazioni: si immagina che vinca
    sempre il giocatore di classifica piu' alta, e che i q perdano contro gli
    ammessi direttamente.

    memoria: un dizionario per non rifare i conti dei primi turni, uguali in
    tante scale diverse.
    """
    livello_q = max(livello.values()) + 1
    finale = scala.qualificati_uscenti == 1
    costo = PESO_TURNO * len(scala.turni)
    vuoti = [not t.singoli and not t.coppie for t in scala.turni]
    if finale:
        # Nel tabellone finale gli ultimi turni senza nessuno che entra (la finale,
        # le semifinali...) sono normali turni di compressione (Volume I, capitolo V, C).
        while vuoti and vuoti[-1]:
            vuoti.pop()
    costo += PESO_TURNO_VUOTO * sum(vuoti)
    turni_di = {}   # classifica -> turni in cui entrano i suoi giocatori (non compagni dei q)
    modi_di = {}    # classifica -> "singolo" e/o "coppia"
    coppie_uguali = 0
    vincitori = []
    parziale = 0
    chiave = ()
    for numero, turno in enumerate(scala.turni):
        chiave += (tuple(turno.singoli), tuple(turno.coppie))
        if memoria is not None and chiave in memoria:
            parziale, vincitori = memoria[chiave]
            conti_fatti = True
        else:
            conti_fatti = False
        nuovi = []
        for a, b in turno.coppie:
            la = livello[a]
            lb = livello_q if b == QUALIFICATO else livello[b]
            if b != QUALIFICATO:
                coppie_uguali += 1
                turni_di.setdefault(a, set()).add(numero)
                modi_di.setdefault(a, set()).add("coppia")
            if conti_fatti:
                continue
            if b != QUALIFICATO:
                parziale += PESO_COPPIA_DIVERSA * abs(la - lb)
            vincitore, extra = _vince((la, 0), (lb, 0), finale)
            nuovi.append(vincitore)
            parziale += extra
        if not conti_fatti:
            extra, passano = _turno_migliore([livello[c] for c in turno.singoli], vincitori, finale)
            parziale += extra
            vincitori = nuovi + passano
            if memoria is not None:
                memoria[chiave] = (parziale, vincitori)
        for classifica in turno.singoli:
            turni_di.setdefault(classifica, set()).add(numero)
            modi_di.setdefault(classifica, set()).add("singolo")
    costo += parziale
    # Coppie di due ammessi: servono solo se i q sono meno dei qualificati uscenti.
    if qualificati_entranti is None:
        qualificati_entranti = sum(1 for t in scala.turni for _, b in t.coppie if b == QUALIFICATO)
    necessarie = max(0, scala.qualificati_uscenti - qualificati_entranti)
    costo += PESO_AMMESSI_TRA_LORO * min(coppie_uguali, necessarie)
    costo += PESO_COPPIE_NON_NECESSARIE * max(0, coppie_uguali - necessarie)
    # Giocatori della stessa classifica trattati in modo diverso.
    costo += PESO_CLASSIFICA_DIVISA * sum(len(t) - 1 for t in turni_di.values())
    costo += PESO_MODI_DIVERSI * sum(1 for m in modi_di.values() if len(m) > 1)
    return costo


def scala_migliore(diretti, qualificati_entranti, qualificati_uscenti, livello):
    """La scala con il costo piu' basso, e l'elenco di tutte, dalla migliore.

    Le coppie di due ammessi si usano il meno possibile (raccomandazione 4): si
    provano prima le scale con il minimo di queste coppie, poi con una in piu', e
    cosi' via finche' le scale da confrontare sono abbastanza.
    """
    scale = []
    for in_piu in range(MASSIMO_COPPIE_IN_PIU + 1):
        scale += scale_possibili(diretti, qualificati_entranti, qualificati_uscenti,
                                 coppie_in_piu=in_piu, solo_con_piu=True)
        if len(scale) >= SCALE_DA_CONFRONTARE:
            break
    memoria = {}
    for scala in scale:
        scala.costo = costo_della_scala(scala, livello, qualificati_entranti, memoria)
    scale.sort(key=lambda s: s.costo)
    return (scale[0] if scale else None), scale


# --- La scala scritta come nel file degli esercizi ----------------------------------

def _elenco(coppie_classifica):
    return ", ".join(f"{n} ({c})" for c, n in coppie_classifica)


def _raggruppa(classifiche):
    """['2.2', '2.2', '2.3'] -> [('2.2', 2), ('2.3', 1)], nell'ordine."""
    gruppi = []
    for c in classifiche:
        if gruppi and gruppi[-1][0] == c:
            gruppi[-1] = (c, gruppi[-1][1] + 1)
        else:
            gruppi.append((c, 1))
    return gruppi


def scrivi_turno(turno):
    """Un turno della scala in una riga: '1 (2.6); coppie 2 (2.7)+q, 1 (2.8)+q'."""
    parti = []
    if turno.singoli:
        parti.append(_elenco(_raggruppa(turno.singoli)))
    if turno.coppie:
        gruppi = _raggruppa([f"({a})+{'q' if b == QUALIFICATO else f'({b})'}"
                             for a, b in turno.coppie])
        parti.append("coppie " + ", ".join(f"{n} {c}" for c, n in gruppi))
    return "; ".join(parti) if parti else "nessuno"


_GRUPPO_SINGOLI = re.compile(r"(\d+)\s*\(([^)]+)\)")
_GRUPPO_COPPIE = re.compile(r"(\d+)\s*\(([^)]+)\)\s*\+\s*(?:(q)\b|\(([^)]+)\))")


def leggi_turno(testo):
    """Il contrario di scrivi_turno."""
    turno = Turno()
    singoli, _, coppie = testo.partition("coppie")
    for numero, classifica in _GRUPPO_SINGOLI.findall(singoli.rstrip("; ")):
        turno.singoli += [classifica.strip()] * int(numero)
    for numero, classifica, q, altra in _GRUPPO_COPPIE.findall(coppie):
        turno.coppie += [(classifica.strip(), QUALIFICATO if q else altra.strip())] * int(numero)
    return turno


# --- La scala scritta dal giudice arbitro in dati/torneo.txt ------------------------

def scala_scritta(impostazioni, qualificati_uscenti):
    """La scala delle righe "turno 1 = ...", "turno 2 = ..." di dati/torneo.txt, o None."""
    turni = {int(nome.split()[1]): leggi_turno(valore) for nome, valore in impostazioni.items()
             if nome.startswith("turno ")}
    if not turni:
        return None
    scala = Scala([turni.get(n, Turno()) for n in range(1, max(turni) + 1)], qualificati_uscenti)
    # Dopo l'ultimo turno scritto, i turni in cui non entra nessuno (nel tabellone
    # finale la semifinale, la finale...) il programma li aggiunge da solo.
    vincitori = 0
    for turno in scala.turni:
        vincitori = (vincitori + turno.entranti()) // 2
    while vincitori > qualificati_uscenti and vincitori % 2 == 0:
        scala.turni.append(Turno())
        vincitori //= 2
    return scala


def controlla_scala(scala, diretti, qualificati_entranti, livello):
    """Gli errori di una scala scritta a mano (elenco di frasi; vuoto se va bene)."""
    errori = []
    scritti = Counter(c for t in scala.turni for c in t.singoli)
    scritti.update(c for t in scala.turni for coppia in t.coppie for c in coppia if c != QUALIFICATO)
    q = sum(1 for t in scala.turni for _, b in t.coppie if b == QUALIFICATO)
    if scritti != Counter(diretti):
        mancano = Counter(diretti) - scritti
        troppi = scritti - Counter(diretti)
        if mancano:
            errori.append("nella scala mancano " + _elenco(sorted(mancano.items(), key=lambda x: livello[x[0]])))
        if troppi:
            errori.append("nella scala ci sono in piu' " + _elenco(sorted(troppi.items(), key=lambda x: livello[x[0]])))
    if q != qualificati_entranti:
        errori.append(f"nella scala ci sono {q} qualificati entranti, ma sono {qualificati_entranti}")
    vuoti = [numero for numero, turno in enumerate(scala.turni, start=1)
             if not turno.singoli and not turno.coppie]
    if scala.qualificati_uscenti == 1:
        # Nel tabellone finale gli ultimi turni possono essere senza nessuno che entra.
        ultimo = len(scala.turni)
        while vuoti and vuoti[-1] == ultimo:
            vuoti.pop()
            ultimo -= 1
    for numero in vuoti:
        errori.append(f"al turno {numero} della scala non entra nessuno")
    if not errori and not _calcola_posti(scala.turni, scala.qualificati_uscenti):
        errori.append(f"i numeri della scala non tornano: all'ultimo turno ci devono essere "
                      f"{2 * scala.qualificati_uscenti} posti, e in ogni turno i giocatori che entrano "
                      f"da soli devono essere al massimo quanti i vincitori del turno prima")
    turni_di = {}
    for numero, turno in enumerate(scala.turni, start=1):
        for c in set(turno.singoli) | {x for coppia in turno.coppie for x in coppia}:
            turni_di.setdefault(c, set()).add(numero)
    for c, turni in sorted(turni_di.items(), key=lambda x: livello.get(x[0], 99)):
        if len(turni) > 2 or max(turni) - min(turni) > len(turni) - 1:
            chi = "i qualificati entranti" if c == QUALIFICATO else f"i giocatori ({c})"
            errori.append(f"{chi} entrano ai turni {', '.join(map(str, sorted(turni)))}: devono "
                          f"entrare in un turno o in due turni consecutivi")
    entrata = [(livello[c], numero) for numero, t in enumerate(scala.turni, start=1)
               for c in t.singoli + [x for coppia in t.coppie for x in coppia if x != QUALIFICATO]]
    for livello_a, turno_a in entrata:
        if any(livello_b < livello_a and turno_b < turno_a for livello_b, turno_b in entrata):
            errori.append("un giocatore entra in gara dopo un giocatore di classifica piu' alta "
                          "(i piu' forti devono entrare negli ultimi turni)")
            break
    return errori


def descrivi_scala(scala):
    """La scala come righe da mostrare, dall'ultimo turno."""
    righe = []
    compressioni = scala.compressioni()
    for numero in range(len(scala.turni), 0, -1):
        turno = scala.turni[numero - 1]
        extra = f"   ({compressioni[numero - 1]} compressioni)" if compressioni[numero - 1] else ""
        righe.append(f"  turno {numero} = {scrivi_turno(turno)}{extra}")
    return righe
