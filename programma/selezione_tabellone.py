"""Il tabellone di selezione, costruito a partire dalla scala (programma.selezione).

Il tabellone e' un albero: ogni incontro ha due "lati", e su ogni lato c'e' o
un giocatore che entra in gara in quel turno, o il vincitore di un incontro
del turno prima. Alla fine ci sono tanti incontri quanti i qualificati uscenti
(i "corridoi", o le sezioni).

Come nel tabellone di estrazione (programma.sorteggio), ogni posto ha un numero
d'ordine, disposto come le teste di serie: la testa di serie n. k va nel posto
numero k. I giocatori piu' forti di ogni turno prendono i posti con i numeri
piu' bassi; poi il programma sposta i giocatori che non sono teste di serie
per avere progressioni e compressioni tra classifiche vicine e i qualificati
entranti divisi in modo uguale (il "sorteggio mirato"). Infine sorteggia chi,
tra i giocatori della stessa classifica, va in ogni posto, rispettando la
regola dello stesso circolo.
"""

import random
from dataclasses import dataclass, field

from programma.calcoli import QUALIFICATO
from programma.dati import AVVISO, Problema
from programma.selezione import (PESO_COMPRESSIONE, PESO_COPPIA_DIVERSA, _costo_progressione,
                                 _vince)
from programma.sorteggio import (GIOCATORE, QUALIFICATO_ENTRANTE, _riga_principale,
                                 numeri_delle_coppie)

# Peso dei qualificati entranti divisi in modo non uguale (regola del manuale).
PESO_Q_SBILANCIATI = 20
# Peso delle parti (corridoi o sezioni) con un numero di giocatori troppo diverso.
PESO_PARTI_SBILANCIATE = 2
# Quanti scambi falliti di fila prima di fermare la ricerca della disposizione migliore.
SCAMBI_A_VUOTO = 400


@dataclass
class Voce:
    """Un giocatore (o un qualificato entrante) che entra in gara in un turno."""
    tipo: str  # GIOCATORE oppure QUALIFICATO_ENTRANTE
    turno: int
    classifica: str = ""
    testa_di_serie: int = 0
    giocatore: object = None
    in_coppia: bool = False  # entra insieme al suo avversario (coppia)


@dataclass
class Incontro:
    turno: int
    alto: object  # Voce oppure Incontro
    basso: object

    @property
    def lati(self):
        return (self.alto, self.basso)


@dataclass
class TabelloneSelezione:
    scala: object
    qualificati_uscenti: int
    sezioni: int
    teste_di_serie: int
    radici: list  # un incontro per ogni qualificato uscente, dall'alto
    N: int = 0
    problemi: list = field(default_factory=list)

    @property
    def turni(self):
        return len(self.scala.turni) if self.scala else max(r.turno for r in self.radici)

    def voci(self):
        """I giocatori dall'alto in basso, come si scrivono sul tabellone."""
        return [v for radice in self.radici for v in voci_di(radice)]


def voci_di(nodo):
    if isinstance(nodo, Voce):
        return [nodo]
    return voci_di(nodo.alto) + voci_di(nodo.basso)


def incontri_di(nodo):
    """Tutti gli incontri sotto un nodo, compreso lui."""
    if isinstance(nodo, Voce):
        return []
    return [nodo] + incontri_di(nodo.alto) + incontri_di(nodo.basso)


# --- Numeri d'ordine dei posti ----------------------------------------------------

class Posti:
    """I numeri d'ordine dei posti di ogni turno, nel tabellone "pieno"."""

    def __init__(self, turni, qualificati_uscenti, sezioni):
        self.turni = turni
        self.qu = qualificati_uscenti
        self.sezioni = sezioni or 1
        self._numeri = {}

    def quanti(self, livello):
        """Quanti incontri ci sono al turno 'livello' nel tabellone pieno (livello 0 = i lati
        degli incontri del primo turno)."""
        return self.qu * 2 ** (self.turni - livello)

    def numeri(self, livello):
        if livello not in self._numeri:
            self._numeri[livello] = numeri_delle_coppie(2 * self.quanti(livello),
                                                        self.sezioni if self.sezioni > 1 else 0)
        return self._numeri[livello]

    def lato_principale(self, livello, posizione):
        """0 se il lato principale (quello con il numero dell'incontro) e' in alto."""
        return _riga_principale(posizione, self.quanti(livello) // self.sezioni)


# --- Costruzione dalla scala -------------------------------------------------------

def _chiave_forza(livello):
    return lambda classifica: livello[classifica]


def costruisci(scala, teste_di_serie, livello, sezioni=0, rng=None):
    """Costruisce il tabellone (senza ancora i nomi dei giocatori) dalla scala.

    I piu' forti di ogni turno vanno nei posti con i numeri piu' bassi; dopo gli
    incontri con un giocatore che entra (progressioni) vengono le compressioni,
    e per ultime le coppie (prima delle compressioni, se ci sono teste di serie
    in coppia con un altro ammesso).
    """
    rng = rng or random.Random()
    R = len(scala.turni)
    Qu = scala.qualificati_uscenti
    posti = Posti(R, Qu, sezioni)
    # Gli incontri di ogni turno, per posizione nel tabellone pieno.
    incontri = {posizione: Incontro(R, None, None) for posizione in range(Qu)}
    radici = [incontri[p] for p in range(Qu)]
    diretti_dopo = 0  # giocatori ammessi che entrano nei turni dopo questo
    for r in range(R, 0, -1):
        turno = scala.turni[r - 1]
        numeri = posti.numeri(r)
        ordinati = sorted(incontri, key=lambda p: numeri[p])
        singoli = sorted(turno.singoli, key=_chiave_forza(livello))
        coppie_q = sorted((c for c in turno.coppie if c[1] == QUALIFICATO), key=lambda c: livello[c[0]])
        membri = sorted((x for c in turno.coppie if c[1] != QUALIFICATO for x in c),
                        key=_chiave_forza(livello))
        n_prog, n_uguali, n_q = len(singoli), len(membri) // 2, len(coppie_q)
        n_comp = len(ordinati) - n_prog - n_uguali - n_q
        # Le teste di serie che entrano qui; se alcune sono in coppia con un altro ammesso
        # (o con un qualificato entrante), le coppie vanno subito dopo le progressioni,
        # perche' le teste di serie devono stare nei posti con i loro numeri (i piu' bassi).
        teste_qui = max(0, min(teste_di_serie - diretti_dopo, len(singoli) + len(membri) + n_q))
        teste_in_coppia = max(0, teste_qui - len(singoli))
        teste_con_q = max(0, teste_in_coppia - len(membri))
        tipi = ["prog"] * n_prog
        if teste_con_q:
            tipi += ["uguali"] * n_uguali + ["q"] * n_q + ["comp"] * n_comp
        elif teste_in_coppia:
            tipi += ["uguali"] * n_uguali + ["comp"] * n_comp + ["q"] * n_q
        else:
            tipi += ["comp"] * n_comp
            # le altre coppie dalla piu' forte, come prima
            coppie = sorted([("uguali", None)] * n_uguali + [("q", c) for c in coppie_q],
                            key=lambda x: 0 if x[0] == "uguali" else 1)
            tipi += [t for t, _ in coppie]
        # I componenti delle coppie di due ammessi, per numero del posto.
        posti_uguali = []
        for indice, posizione in enumerate(ordinati):
            if tipi[indice] == "uguali":
                principale = 2 * posizione + posti.lato_principale(r, posizione)
                posti_uguali += [principale, 4 * posizione + 1 - principale]
        numeri_lati = posti.numeri(r - 1)
        if teste_in_coppia:
            posti_uguali.sort(key=lambda x: numeri_lati[x])
        else:
            posti_uguali.sort(key=lambda x: (numeri_lati[x // 2 * 2], x % 2))  # coppie vicine
        chi_nel_posto = dict(zip(posti_uguali, membri))
        coppie_q = iter(coppie_q)
        singoli = iter(singoli)
        sotto = {}
        for indice, posizione in enumerate(ordinati):
            incontro = incontri[posizione]
            principale = 2 * posizione + posti.lato_principale(r, posizione)
            altro = 4 * posizione + 1 - principale
            if tipi[indice] == "prog":
                lati = {principale: Voce(GIOCATORE, r, next(singoli)), altro: None}
            elif tipi[indice] == "comp":
                lati = {principale: None, altro: None}
            elif tipi[indice] == "q":
                a, _ = next(coppie_q)
                lati = {principale: Voce(GIOCATORE, r, a, in_coppia=True),
                        altro: Voce(QUALIFICATO_ENTRANTE, r, in_coppia=True)}
            else:
                lati = {x: Voce(GIOCATORE, r, chi_nel_posto[x], in_coppia=True)
                        for x in (principale, altro)}
            for posizione_lato, contenuto in lati.items():
                if contenuto is None:
                    contenuto = Incontro(r - 1, None, None)
                    sotto[posizione_lato] = contenuto
                if posizione_lato % 2 == 0:
                    incontro.alto = contenuto
                else:
                    incontro.basso = contenuto
        incontri = sotto
        diretti_dopo += n_prog + len(membri) + n_q
    tabellone = TabelloneSelezione(scala, Qu, sezioni, teste_di_serie, radici,
                                   N=sum(t.entranti() for t in scala.turni))
    _numera_le_teste_di_serie(tabellone, posti, livello, rng)
    return tabellone


def numeri_dei_lati(tabellone, posti=None):
    """Per ogni Voce (per id) il numero d'ordine del suo posto."""
    posti = posti or Posti(tabellone.turni, tabellone.qualificati_uscenti, tabellone.sezioni)
    risultato = {}

    def visita(nodo, livello, posizione):
        # nodo e' nel posto 'posizione' dei lati del turno livello + 1
        if isinstance(nodo, Voce):
            risultato[id(nodo)] = posti.numeri(livello)[posizione]
            return
        for lato, figlio in enumerate(nodo.lati):
            visita(figlio, livello - 1, 2 * posizione + lato)

    for posizione, radice in enumerate(tabellone.radici):
        for lato, figlio in enumerate(radice.lati):
            visita(figlio, tabellone.turni - 1, 2 * posizione + lato)
    return risultato


def _numera_le_teste_di_serie(tabellone, posti, livello, rng):
    """Le teste di serie sono i giocatori piu' forti; la n. k e' nel posto numero k.
    A parita' di classifica l'ordine si decide per sorteggio (qui: per posto)."""
    for voce in tabellone.voci():
        voce.testa_di_serie = 0
    T = tabellone.teste_di_serie
    if not T:
        return
    numeri = numeri_dei_lati(tabellone, posti)
    giocatori = [v for v in tabellone.voci() if v.tipo == GIOCATORE]
    giocatori.sort(key=lambda v: (livello[v.classifica], numeri[id(v)]))
    for k, voce in enumerate(giocatori[:T], start=1):
        voce.testa_di_serie = k


# --- Costo della disposizione e sorteggio mirato -----------------------------------------

def _valuta(nodo, livello, livello_q, finale=False):
    """(vincitore previsto, costo, quanti q, quanti giocatori, e' un giocatore appena entrato)."""
    if isinstance(nodo, Voce):
        if nodo.tipo == QUALIFICATO_ENTRANTE:
            return (livello_q, 0), 0, 1, 1, True
        return (livello[nodo.classifica], 0), 0, 0, 1, True
    a, costo_a, q_a, n_a, fresco_a = _valuta(nodo.alto, livello, livello_q, finale)
    b, costo_b, q_b, n_b, fresco_b = _valuta(nodo.basso, livello, livello_q, finale)
    costo = costo_a + costo_b
    differenza = abs(a[0] - b[0])
    if fresco_a and fresco_b:
        if livello_q not in (a[0], b[0]):
            costo += PESO_COPPIA_DIVERSA * differenza
    elif fresco_a or fresco_b:
        entrante, vincitore = (a, b) if fresco_a else (b, a)
        costo += _costo_progressione(vincitore[0] - entrante[0])
    else:
        costo += PESO_COMPRESSIONE * differenza
        costo += PESO_Q_SBILANCIATI * max(0, abs(q_a - q_b) - 1)
    passa, extra = _vince(a, b, finale)
    return passa, costo + extra, q_a + q_b, n_a + n_b, False


def costo_del_tabellone(tabellone, livello):
    livello_q = max(livello.values()) + 1
    costo = 0
    q_parti, giocatori_parti = [], []
    for radice in tabellone.radici:
        _, c, q, n, _ = _valuta(radice, livello, livello_q, len(tabellone.radici) == 1)
        costo += c
        q_parti.append(q)
        giocatori_parti.append(n)
    costo += PESO_Q_SBILANCIATI * max(0, max(q_parti) - min(q_parti) - 1)
    costo += PESO_PARTI_SBILANCIATE * max(0, max(giocatori_parti) - min(giocatori_parti) - 2)
    return costo


def _contiene_teste(nodo):
    return any(v.testa_di_serie for v in voci_di(nodo))


def _lati_scambiabili(tabellone):
    """I gruppi di lati che si possono scambiare senza cambiare la scala:
    per ogni turno, gli incontri del turno prima, i singoli che entrano, e i
    giocatori ammessi delle coppie con un q. Mai un lato con una testa di serie."""
    gruppi = {}
    for radice in tabellone.radici:
        for incontro in incontri_di(radice):
            coppia = all(isinstance(x, Voce) for x in incontro.lati)
            for lato, figlio in enumerate(incontro.lati):
                if _contiene_teste(figlio):
                    continue
                if isinstance(figlio, Incontro):
                    tipo = ("incontro", incontro.turno)
                elif not coppia:
                    tipo = ("singolo", incontro.turno)
                elif figlio.tipo == GIOCATORE and QUALIFICATO_ENTRANTE in (x.tipo for x in incontro.lati):
                    tipo = ("compagno di un q", incontro.turno)
                elif figlio.tipo == GIOCATORE:
                    tipo = ("in coppia con un ammesso", incontro.turno)
                else:
                    continue
                gruppi.setdefault(tipo, []).append((incontro, lato))
    return [g for g in gruppi.values() if len(g) > 1]


def _scambia(a, b):
    (incontro_a, lato_a), (incontro_b, lato_b) = a, b
    figlio_a, figlio_b = incontro_a.lati[lato_a], incontro_b.lati[lato_b]
    for incontro, lato, figlio in ((incontro_a, lato_a, figlio_b), (incontro_b, lato_b, figlio_a)):
        if lato == 0:
            incontro.alto = figlio
        else:
            incontro.basso = figlio


def migliora(tabellone, livello, rng):
    """Il sorteggio mirato: scambia lati (mai le teste di serie) finche' il costo scende."""
    gruppi = _lati_scambiabili(tabellone)
    if not gruppi:
        return costo_del_tabellone(tabellone, livello)
    migliore = costo_del_tabellone(tabellone, livello)
    a_vuoto = 0
    while a_vuoto < SCAMBI_A_VUOTO:
        gruppo = rng.choice(gruppi)
        a, b = rng.sample(gruppo, 2)
        if a[0] is b[0]:
            a_vuoto += 1
            continue
        _scambia(a, b)
        costo = costo_del_tabellone(tabellone, livello)
        if costo < migliore:
            migliore, a_vuoto = costo, 0
        else:
            _scambia(a, b)  # a parita' resta la disposizione dei numeri d'ordine
            a_vuoto += 1
    return migliore


def orienta(tabellone, livello):
    """Nel disegno, in ogni incontro senza teste di serie il piu' forte va sul lato
    principale (in alto nella meta' superiore, in basso in quella inferiore)."""
    posti = Posti(tabellone.turni, tabellone.qualificati_uscenti, tabellone.sezioni)
    livello_q = max(livello.values()) + 1

    def forza(nodo):
        return _valuta(nodo, livello, livello_q)[0][0]

    def visita(incontro, livello_incontro, posizione):
        principale = posti.lato_principale(livello_incontro, posizione)
        a, b = incontro.alto, incontro.basso
        if not _contiene_teste(a) and not _contiene_teste(b):
            forte, debole = (a, b) if forza(a) <= forza(b) else (b, a)
            if isinstance(a, Voce) != isinstance(b, Voce):
                forte, debole = (a, b) if isinstance(a, Voce) else (b, a)  # chi entra, sul lato principale
            incontro.alto, incontro.basso = (forte, debole) if principale == 0 else (debole, forte)
        for lato, figlio in enumerate(incontro.lati):
            if isinstance(figlio, Incontro):
                visita(figlio, livello_incontro - 1, 2 * posizione + lato)

    for posizione, radice in enumerate(tabellone.radici):
        visita(radice, tabellone.turni, posizione)


# --- Sorteggio dei giocatori: regola dello stesso circolo --------------------------------

LIMITE_TENTATIVI = 20_000


def coppie_di_ammessi(tabellone):
    """Gli incontri in cui due giocatori ammessi direttamente giocano il loro
    primo incontro l'uno contro l'altro (qui vale la regola dello stesso circolo)."""
    return [incontro for radice in tabellone.radici for incontro in incontri_di(radice)
            if all(isinstance(x, Voce) and x.tipo == GIOCATORE for x in incontro.lati)]


def stesso_circolo(tabellone):
    return [(i.alto, i.basso) for i in coppie_di_ammessi(tabellone)
            if i.alto.giocatore.chiave_circolo == i.basso.giocatore.chiave_circolo]


def sorteggia_giocatori(tabellone, giocatori, rng):
    """Mette i giocatori nei posti della loro classifica, per sorteggio.

    Le teste di serie della stessa classifica si sorteggiano tra loro, e cosi'
    gli altri. Negli incontri tra due ammessi che entrano insieme i giocatori
    non devono essere dello stesso circolo: se non si puo' evitare del tutto,
    il programma ne fa il meno possibile e lo segnala.
    """
    per_classifica = {}
    for g in giocatori:
        per_classifica.setdefault(g.classifica, []).append(g)
    for elenco in per_classifica.values():
        rng.shuffle(elenco)
    voci = [v for v in tabellone.voci() if v.tipo == GIOCATORE]
    # Prima i posti delle coppie di due ammessi, uno accanto all'altro.
    coppie = coppie_di_ammessi(tabellone)
    in_coppia = [v for i in coppie for v in i.lati]
    avversario = {}
    for i in coppie:
        avversario[id(i.alto)], avversario[id(i.basso)] = i.basso, i.alto
    ordine = in_coppia + [v for v in voci if id(v) not in avversario]
    # Tra i giocatori della stessa classifica, la testa di serie con il numero piu'
    # basso prende il primo sorteggiato: l'ordine delle teste di serie e' per sorteggio.
    tentativi = [0]

    def cerca(k, usati, ammesse):
        tentativi[0] += 1
        if tentativi[0] > LIMITE_TENTATIVI:
            return None
        if k == len(ordine):
            return {}
        voce = ordine[k]
        rivale = avversario.get(id(voce))
        rivale_giocatore = usati.get(id(rivale)) if rivale is not None else None
        provati = set()
        for g in per_classifica[voce.classifica]:
            if g.codice in {x.codice for x in usati.values()}:
                continue
            if g.chiave_circolo in provati:
                continue
            provati.add(g.chiave_circolo)
            stesso = rivale_giocatore is not None and \
                rivale_giocatore.chiave_circolo == g.chiave_circolo
            if stesso and ammesse == 0:
                continue
            usati[id(voce)] = g
            resto = cerca(k + 1, usati, ammesse - stesso)
            if resto is not None:
                resto[id(voce)] = g
                return resto
            del usati[id(voce)]
        return None

    scelta = None
    for ammesse in range(len(coppie) + 1):
        tentativi[0] = 0
        scelta = cerca(0, {}, ammesse)
        if scelta is not None:
            break
    for voce in voci:
        voce.giocatore = scelta[id(voce)]
    incontri = stesso_circolo(tabellone)
    if incontri:
        elenco = "; ".join(f"{a.giocatore.codice} e {b.giocatore.codice} ({a.giocatore.circolo})"
                           for a, b in incontri)
        tabellone.problemi.append(Problema(
            AVVISO, "", 0,
            f"regola dello stesso circolo non rispettata: non esiste nessun sorteggio che la "
            f"rispetti del tutto (o il programma non l'ha trovato); il programma ha scelto un "
            f"sorteggio con meno incontri possibile tra giocatori dello stesso circolo al loro "
            f"primo incontro. Incontri: {elenco}"))


# --- Il tabellone scritto come testo, e riletto ----------------------------------

def _riga(voce):
    testa = f"({voce.testa_di_serie})" if voce.testa_di_serie else ""
    if voce.tipo == QUALIFICATO_ENTRANTE:
        descrizione = "q  (qualificato entrante)"
    elif voce.giocatore is None:
        descrizione = f"?          {voce.classifica}"
    else:
        g = voce.giocatore
        descrizione = f"{g.codice:<10} {g.classifica:<5} {g.circolo}"
    return f"turno {voce.turno}  {testa:>4}  {descrizione}"


def disegna(tabellone, titolo=""):
    """Il tabellone come testo: un giocatore per riga, dall'alto in basso, con il
    turno in cui entra in gara. Le righe di spiegazione cominciano con #, cosi' il
    testo si puo' correggere a mano e far controllare (py tabelloni.py controlla)."""
    from programma.selezione import scrivi_turno
    Qu = tabellone.qualificati_uscenti
    righe = []
    if titolo:
        righe += [f"# {titolo}", "# " + "=" * len(titolo)]
    uscita = "il vincitore" if Qu == 1 else f"{Qu} qualificati (da Q1 a Q{Qu})"
    righe.append(f"# Tabellone di selezione: {tabellone.N} giocatori, {tabellone.turni} turni, "
                 f"esce {uscita}.")
    righe.append("# Ogni riga: il turno in cui il giocatore entra in gara, poi il giocatore.")
    righe.append("# Il numero tra parentesi indica la testa di serie.")
    if tabellone.scala:
        righe.append("# La scala (chi entra in ogni turno):")
        for numero in range(len(tabellone.scala.turni), 0, -1):
            righe.append(f"#   turno {numero}: {scrivi_turno(tabellone.scala.turni[numero - 1])}")
    for k, radice in enumerate(tabellone.radici, start=1):
        if tabellone.sezioni:
            righe += ["", f"# --- sezione {k}: qualificato Q{k} ---"]
        elif Qu > 1:
            righe += ["", f"# --- corridoio del qualificato Q{k} ---"]
        else:
            righe.append("")
        righe += [_riga(v) for v in voci_di(radice)]
    return "\n".join(righe)


def albero_dalle_voci(voci, ultimo_turno):
    """Ricostruisce gli incontri dall'elenco dei giocatori con il loro turno di entrata.

    Due vicini che sono pronti per lo stesso turno si incontrano; il vincitore e'
    pronto per il turno dopo, fino all'ultimo turno. Restituisce l'elenco degli
    ultimi incontri (o dei giocatori rimasti da soli) e se l'elenco era scritto bene.
    """
    pila = []  # (nodo, turno in cui gioca il prossimo incontro)
    for voce in voci:
        pila.append((voce, voce.turno))
        while len(pila) >= 2 and pila[-1][1] == pila[-2][1] <= ultimo_turno:
            (a, turno), (b, _) = pila[-2], pila[-1]
            pila[-2:] = [(Incontro(turno, a, b), turno + 1)]
        if len(pila) >= 2 and pila[-1][1] > pila[-2][1]:
            return [n for n, _ in pila], False
    return [n for n, _ in pila], True


# --- Tutto insieme: dalla lista dei giocatori al tabellone --------------------------

def proposta_teste_di_serie(scala, minimo, massimo, livello, sezioni=0):
    """Quante teste di serie proporre in un tabellone di selezione.

    Regola usata (ricavata dagli esercizi del Volume II, capitolo 3): i giocatori
    che entrano all'ultimo turno. Se sono meno del minimo, si arriva al minimo; e
    se allora l'ultima testa di serie ha la stessa classifica di altri giocatori,
    e questa classifica entra anche all'ultimo turno, si prendono tutti i
    giocatori di quella classifica (per non dividerla).

    Nel tabellone finale gli ultimi turni (la finale, le semifinali...) sono spesso
    senza nessuno che entra: le teste di serie proposte sono i giocatori che entrano
    negli ultimi due turni in cui entra qualcuno (esercizi 5.31, 5.32, 5.33).
    """
    def entranti_in(turno):
        return len(turno.singoli) + sum(1 + (b != QUALIFICATO) for _, b in turno.coppie)

    ultimo = scala.turni[-1]
    entranti = entranti_in(ultimo)
    if scala.qualificati_uscenti == 1:
        pieni = [t for t in scala.turni if entranti_in(t)]
        ultimo = pieni[-1]
        entranti = sum(entranti_in(t) - sum(1 for _, b in t.coppie if b == QUALIFICATO)
                       for t in pieni[-2:])
    diretti = sorted((c for t in scala.turni for c in t.singoli + [x for coppia in t.coppie
                                                                  for x in coppia if x != QUALIFICATO]),
                     key=lambda c: livello[c])
    T = min(max(entranti, minimo), massimo)
    if entranti < minimo and 0 < T < len(diretti) and diretti[T - 1] == diretti[T]:
        classifica = diretti[T - 1]
        in_ultimo = classifica in ultimo.singoli or any(classifica in c for c in ultimo.coppie)
        tutti = sum(1 for c in diretti if livello[c] <= livello[classifica])
        if in_ultimo and tutti <= massimo:
            T = tutti
    if sezioni and T % sezioni:
        T = min(-(-T // sezioni) * sezioni, massimo)
    return T


def prepara(scala, teste_di_serie, giocatori, livello, sezioni=0, rng=None):
    """Costruisce il tabellone dalla scala: posti, sorteggio mirato, giocatori."""
    rng = rng or random.Random()
    tabellone = costruisci(scala, teste_di_serie, livello, sezioni, rng)
    migliora(tabellone, livello, rng)
    orienta(tabellone, livello)
    sorteggia_giocatori(tabellone, giocatori, rng)
    return tabellone


def teste_al_loro_posto(tabellone):
    """Se ogni testa di serie n. k e' nel posto numero k, e le teste di serie entrano
    in gara in un turno o in due turni consecutivi."""
    teste = [v for v in tabellone.voci() if v.testa_di_serie]
    if not teste:
        return True
    numeri = numeri_dei_lati(tabellone)
    turni = {v.turno for v in teste}
    return all(numeri[id(v)] == v.testa_di_serie for v in teste) and max(turni) - min(turni) <= 1


def scegli_scala(scale, minimo, massimo, livello, sezioni=0, teste_scelte=None):
    """La prima scala (dalla migliore) in cui le teste di serie possono stare al loro
    posto; restituisce la scala e il numero delle teste di serie (o None, None)."""
    for scala in scale:
        if minimo is None:
            return scala, 0
        teste = teste_scelte or proposta_teste_di_serie(scala, minimo, massimo, livello, sezioni)
        if teste_al_loro_posto(costruisci(scala, teste, livello, sezioni, random.Random(0))):
            return scala, teste
    return None, None
