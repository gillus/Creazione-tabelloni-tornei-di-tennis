"""Compilazione e sorteggio di un tabellone di estrazione (manuale, Volume I, capitolo II).

Il lavoro si fa in due tempi, come sul foglio del giudice arbitro:

1. lo SCHEMA: dove vanno le teste di serie, i posti liberi (bye), i
   qualificati entranti (q) e gli incontri del primo turno. Dipende solo
   dai calcoli preliminari;
2. il SORTEGGIO: quale giocatore va in quale posto. Rispetta la regola
   dello stesso circolo al primo turno, se esiste almeno un sorteggio
   che la rispetta.

Come si numerano i posti (regole del manuale, controllate sugli esempi
da 39 a 47 del Volume I e sugli esercizi del Volume II):
  - il tabellone di D posti ha D/2 coppie (gli incontri del primo turno);
  - ogni coppia ha un "numero d'ordine" da 1 a D/2, disposto come le teste
    di serie: la somma dei numeri nella stessa frazione e' sempre la stessa;
  - la coppia numero k ospita la testa di serie n. k, nella riga alta se
    la coppia e' nella meta' superiore, nella riga bassa se e' nella meta'
    inferiore; l'altra riga e' dell'avversario (o del posto libero);
  - gli aspettiti occupano le coppie con i numeri piu' bassi, come se
    fossero teste di serie;
  - i qualificati entranti in aspettito vanno contro gli aspettiti piu'
    deboli (quelli con il numero piu' alto): di solito sono le teste di
    serie in aspettito, come dice il manuale; se i q sono di piu', anche
    gli altri aspettiti, cosi' due q non si incontrano mai al loro primo
    incontro;
  - nelle coppie rimaste si gioca il primo turno.

Tabellone a sezioni (Volume I, capitolo III): e' fatto di tante sezioni
quanti sono i qualificati uscenti, ognuna un piccolo tabellone.
  - Dentro ogni sezione le coppie si numerano come sopra; poi i numeri
    si danno "a serpentina": il numero 1 della sezione 1, il numero 1 della
    sezione 2... fino all'ultima sezione, poi i numeri 2 dall'ultima sezione
    alla prima, poi i numeri 3 dalla prima all'ultima, e cosi' via. Cosi' la
    testa di serie n. 1 e' in alto nella sezione 1, la n. 2 in alto nella
    sezione 2, e dopo l'ultima sezione si torna indietro dal basso.
  - Alto e basso (per le teste di serie e per i q) si decidono dentro la
    sezione: ogni sezione ha la sua meta' superiore e inferiore.
  - Le sezioni devono avere lo stesso numero di giocatori, con una differenza
    di due al massimo: se non e' cosi', alcuni incontri del primo turno si
    spostano nelle sezioni con meno giocatori (Volume II, esercizio 2.23).
  - I q si dividono tra le sezioni con una differenza di uno al massimo.
"""

import random
from collections import Counter
from dataclasses import dataclass, field

from programma.armonizzazione import Armonizzazione
from programma.calcoli import QUALIFICATO
from programma.dati import AVVISO, ERRORE, Problema

# Tipi di posto nel tabellone
GIOCATORE = "giocatore"
LIBERO = "libero"  # posto libero (bye): chi e' nella stessa coppia entra al secondo turno
QUALIFICATO_ENTRANTE = "q"

# Oltre questo numero di tentativi il programma smette di cercare un sorteggio
# che rispetti la regola dello stesso circolo (serve solo nei casi molto difficili).
LIMITE_TENTATIVI = 20_000
# Lo stesso, per ognuna delle disposizioni delle classifiche del sorteggio mirato.
LIMITE_TENTATIVI_MIRATO = 3_000


@dataclass
class Posto:
    tipo: str  # GIOCATORE, LIBERO oppure QUALIFICATO_ENTRANTE
    testa_di_serie: int = 0  # 0 se non e' una testa di serie
    giocatore: object = None  # il Giocatore, dopo il sorteggio


@dataclass
class Tabellone:
    calcoli: object
    posti: list  # D posti, dall'alto in basso
    problemi: list = field(default_factory=list)

    @property
    def coppie(self):
        """Gli incontri del primo turno: coppie di posti (alto, basso)."""
        return [(self.posti[i], self.posti[i + 1]) for i in range(0, len(self.posti), 2)]


def ordine_delle_coppie(numero_coppie):
    """Il numero d'ordine di ogni coppia, dall'alto in basso.

    Si costruisce raddoppiando: da [1, 2] si passa a [1, 4, 3, 2], poi a
    [1, 8, 4, 5, 6, 3, 7, 2] e cosi' via. Nella meta' superiore ogni numero x
    diventa (x, opposto), nella meta' inferiore (opposto, x), dove x + opposto
    e' sempre uguale al nuovo numero di coppie + 1.
    """
    ordine = [1]
    while len(ordine) < numero_coppie:
        nuovo = 2 * len(ordine)
        meta = len(ordine) // 2
        raddoppiato = []
        for posizione, numero in enumerate(ordine):
            opposto = nuovo + 1 - numero
            if posizione < meta or len(ordine) == 1:
                raddoppiato += [numero, opposto]
            else:
                raddoppiato += [opposto, numero]
        ordine = raddoppiato
    return ordine


def numeri_delle_coppie(D, sezioni=0):
    """Il numero d'ordine di ogni coppia, dall'alto in basso, anche con le sezioni.

    Senza sezioni e' ordine_delle_coppie(D / 2). Con le sezioni ogni sezione e'
    numerata come un piccolo tabellone e i numeri vanno a serpentina tra le sezioni.
    """
    S = sezioni or 1
    locale = ordine_delle_coppie(D // 2 // S)
    numeri = []
    for sezione in range(S):
        for j in locale:
            giro = j - 1
            numeri.append(giro * S + (sezione + 1 if giro % 2 == 0 else S - sezione))
    return numeri


def _riga_principale(indice_coppia, coppie_per_sezione):
    """0 = riga alta della coppia (meta' superiore), 1 = riga bassa (meta' inferiore).
    Con le sezioni conta la meta' della sezione."""
    locale = indice_coppia % coppie_per_sezione
    return 0 if locale < max(1, coppie_per_sezione // 2) else 1


def scegli_equilibrati(disponibili, fissi, quanti, rng, inizio, fine, preferiti=()):
    """Sceglie 'quanti' coppie tra le 'disponibili' (indici da inizio a fine escluso)
    in modo che meta', quarti, ottavi... ricevano lo stesso numero di qualificati,
    contando anche quelli gia' 'fissi', con differenza al massimo di uno.
    A parita', sceglie prima le coppie 'preferite', e poi decide il sorteggio.
    """
    if quanti == 0:
        return []
    if fine - inizio == 1:
        return [inizio]

    def conta(elenco, da, a):
        return sum(1 for i in elenco if da <= i < a)

    meta = (inizio + fine) // 2
    liberi_alto, liberi_basso = conta(disponibili, inizio, meta), conta(disponibili, meta, fine)
    fissi_alto, fissi_basso = conta(fissi, inizio, meta), conta(fissi, meta, fine)
    preferiti_alto, preferiti_basso = conta(preferiti, inizio, meta), conta(preferiti, meta, fine)
    possibili = []
    for in_alto in range(quanti + 1):
        in_basso = quanti - in_alto
        if in_alto <= liberi_alto and in_basso <= liberi_basso:
            differenza = abs((in_alto + fissi_alto) - (in_basso + fissi_basso))
            coperti = min(in_alto, preferiti_alto) + min(in_basso, preferiti_basso)
            possibili.append((differenza, -coperti, rng.random(), in_alto))
    in_alto = min(possibili)[-1]
    if fine - inizio == 2:
        # Ultima scelta tra due coppie vicine: prima quella preferita.
        scelte = sorted((i for i in disponibili if inizio <= i < fine),
                        key=lambda i: (i not in preferiti, rng.random()))
        return scelte[:quanti]
    return (scegli_equilibrati(disponibili, fissi, in_alto, rng, inizio, meta, preferiti)
            + scegli_equilibrati(disponibili, fissi, quanti - in_alto, rng, meta, fine, preferiti))


def _classifiche_ordinate(calcoli):
    """Le classifiche dei giocatori ammessi, una per giocatore, dalla piu' alta."""
    return [c for c, n in calcoli.ammessi for _ in range(n)]


def _aspettiti_diretti(calcoli):
    return sum(n for c, n in calcoli.aspettiti if c != QUALIFICATO)


def schema(calcoli, rng=None):
    """Prepara i posti del tabellone, senza ancora i nomi dei giocatori.

    Il sorteggio serve solo quando i qualificati entranti al primo turno sono
    meno degli incontri: allora si sceglie in quali incontri metterli.
    """
    rng = rng or random.Random()
    D = calcoli.D
    numero_coppie = D // 2
    S = calcoli.sezioni or 1
    coppie_per_sezione = numero_coppie // S
    T = calcoli.teste_di_serie
    diretti_aspettiti = _aspettiti_diretti(calcoli)
    teste_aspettiti = min(T, diretti_aspettiti)
    q_aspettiti = sum(n for c, n in calcoli.aspettiti if c == QUALIFICATO)
    q_primo_turno = sum(n for c, n in calcoli.non_aspettiti if c == QUALIFICATO)

    ordine = numeri_delle_coppie(D, calcoli.sezioni)
    coppia_del_numero = {numero: indice for indice, numero in enumerate(ordine)}

    def compagna(numero):
        """Il numero della coppia che si incontra con questa al secondo turno."""
        if coppie_per_sezione == 1:
            return None
        return ordine[coppia_del_numero[numero] ^ 1]

    # Cosa c'e' nella coppia con un certo numero d'ordine.
    teste = set(range(1, T + 1))
    # Gli aspettiti diretti: prima le teste di serie, poi gli altri, con i numeri
    # subito dopo le teste di serie (come se fossero teste di serie).
    aspettiti_non_teste = list(range(T + 1, diretti_aspettiti + 1))
    numeri_aspettiti = list(range(1, teste_aspettiti + 1)) + aspettiti_non_teste
    occupati = teste | set(aspettiti_non_teste)
    # I q in aspettito vanno contro gli aspettiti piu' deboli (numero piu' alto):
    # nella coppia che al secondo turno incontra la loro.
    q_in_aspettito = []
    for k in reversed(numeri_aspettiti):
        if len(q_in_aspettito) == q_aspettiti:
            break
        numero = compagna(k)
        if numero is not None and numero not in occupati:
            q_in_aspettito.append(numero)
            occupati.add(numero)
    # Se non bastano (succede solo in casi molto particolari), i primi numeri liberi.
    liberi = [n for n in range(1, numero_coppie + 1) if n not in occupati]
    while len(q_in_aspettito) < q_aspettiti:
        q_in_aspettito.append(liberi.pop(0))
    if S > 1:
        _bilancia_le_sezioni(q_in_aspettito, set(numeri_aspettiti), teste, ordine,
                             coppia_del_numero, compagna, coppie_per_sezione)
        occupati = teste | set(aspettiti_non_teste) | set(q_in_aspettito)
        liberi = [n for n in range(1, numero_coppie + 1) if n not in occupati]
    # Tutte le altre coppie giocano il primo turno.
    primo_turno = [k for k in range(teste_aspettiti + 1, T + 1)] + liberi

    # Quali incontri del primo turno hanno un qualificato entrante: uno per ogni
    # frazione del tabellone (o della sezione); a parita', quelli senza testa di serie,
    # perche' i q devono incontrare i giocatori di classifica piu' bassa (raccomandazione 1).
    fissi = [coppia_del_numero[n] for n in q_in_aspettito]
    disponibili = [coppia_del_numero[n] for n in primo_turno]
    preferiti = {coppia_del_numero[n] for n in primo_turno if n not in teste}
    if S == 1:
        con_q = set(scegli_equilibrati(disponibili, fissi, q_primo_turno, rng, 0, numero_coppie,
                                       preferiti))
    else:
        con_q = set()
        quanti = _q_per_sezione(disponibili, fissi, preferiti, q_primo_turno, S,
                                coppie_per_sezione, rng)
        for sezione, numero in enumerate(quanti):
            inizio, fine = sezione * coppie_per_sezione, (sezione + 1) * coppie_per_sezione
            con_q |= set(scegli_equilibrati([i for i in disponibili if inizio <= i < fine],
                                            fissi, numero, rng, inizio, fine, preferiti))

    posti = [None] * D
    for indice, numero in enumerate(ordine):
        principale = 2 * indice + _riga_principale(indice, coppie_per_sezione)
        altro = 2 * indice + 1 - _riga_principale(indice, coppie_per_sezione)
        testa = numero if numero in teste else 0
        if numero in q_in_aspettito:
            posti[principale] = Posto(QUALIFICATO_ENTRANTE)
            posti[altro] = Posto(LIBERO)
        elif numero <= teste_aspettiti or numero in aspettiti_non_teste:
            posti[principale] = Posto(GIOCATORE, testa)
            posti[altro] = Posto(LIBERO)
        else:
            posti[principale] = Posto(GIOCATORE, testa)
            posti[altro] = Posto(QUALIFICATO_ENTRANTE if indice in con_q else GIOCATORE)
    return posti


def giocatori_per_sezione(posti, sezioni):
    """Quanti giocatori (compresi i q) ci sono in ogni sezione."""
    larghezza = len(posti) // sezioni
    return [sum(1 for p in posti[i:i + larghezza] if p.tipo != LIBERO)
            for i in range(0, len(posti), larghezza)]


def _bilancia_le_sezioni(q_in_aspettito, numeri_aspettiti, teste, ordine, coppia_del_numero,
                         compagna, coppie_per_sezione):
    """Le sezioni devono avere lo stesso numero di giocatori, con una differenza di due
    al massimo. Se non e' cosi', un incontro del primo turno passa dalla sezione piu'
    piena a quella piu' vuota, al posto di un q in aspettito (Volume II, esercizio 2.23):
    nella sezione piu' vuota il q che avrebbe incontrato l'aspettito piu' forte gioca
    il primo turno, e nella sezione piu' piena al suo posto va un q in aspettito.
    """
    def sezione(numero):
        return coppia_del_numero[numero] // coppie_per_sezione

    numero_sezioni = len(ordine) // coppie_per_sezione
    while True:
        conta = [0] * numero_sezioni
        for numero in ordine:
            conta[sezione(numero)] += 1 if (numero in numeri_aspettiti
                                           or numero in q_in_aspettito) else 2
        if max(conta) - min(conta) <= 2:
            return
        # Dove si puo' togliere un incontro: una coppia senza testa di serie che al
        # secondo turno incontra un aspettito (il q poi incontrera' lui).
        da_togliere = sorted(
            (conta[sezione(n)] * -1, compagna(n), n) for n in ordine
            if n not in numeri_aspettiti and n not in q_in_aspettito and n not in teste
            and compagna(n) in numeri_aspettiti)
        da_aggiungere = sorted((conta[sezione(n)], compagna(n), n) for n in q_in_aspettito)
        if not da_togliere or not da_aggiungere:
            return
        piu_piena, piu_vuota = da_togliere[0], da_aggiungere[0]
        if -piu_piena[0] - piu_vuota[0] <= 2:
            return
        q_in_aspettito.remove(piu_vuota[2])
        q_in_aspettito.append(piu_piena[2])


def _q_per_sezione(disponibili, fissi, preferiti, quanti, sezioni, coppie_per_sezione, rng):
    """Quanti q al primo turno in ogni sezione: tutte le sezioni devono averne lo stesso
    numero (contando anche i q in aspettito), con una differenza di uno al massimo."""
    def sezione(indice):
        return indice // coppie_per_sezione

    totale = [0] * sezioni
    for indice in fissi:
        totale[sezione(indice)] += 1
    posti = [0] * sezioni
    buoni = [0] * sezioni  # incontri senza testa di serie, dove i q stanno meglio
    for indice in disponibili:
        posti[sezione(indice)] += 1
        buoni[sezione(indice)] += indice in preferiti
    risultato = [0] * sezioni
    for _ in range(quanti):
        possibili = [s for s in range(sezioni) if risultato[s] < posti[s]]
        if not possibili:
            break
        scelta = min(possibili, key=lambda s: (totale[s], risultato[s] >= buoni[s], rng.random()))
        risultato[scelta] += 1
        totale[scelta] += 1
    return risultato


class _TroppiTentativi(Exception):
    pass


class _Ricerca:
    """Cerca come riempire i posti del primo turno rispettando la regola dello
    stesso circolo, ammettendo al massimo un certo numero di eccezioni.

    Riempie i posti uno alla volta e torna indietro quando arriva a un vicolo
    cieco, quindi se non trova niente vuol dire che non c'e' nessuna soluzione.
    Per non perdere tempo:
      - due giocatori con la stessa classifica e lo stesso circolo sono
        intercambiabili, quindi se ne prova uno solo;
      - a ogni passo conta, circolo per circolo, quanti giocatori dovranno per
        forza giocare contro un compagno di circolo; se sono piu' delle
        eccezioni ammesse, quella strada e' chiusa e si torna subito indietro.

    I giocatori si provano in ordine casuale: e' questo il sorteggio.
    """

    def __init__(self, tra_ammessi, contro_q, avversario, richiesta, pedine, quote,
                 posti_aspettiti, rng, limite=LIMITE_TENTATIVI):
        self.limite = limite
        # Gli incontri tra due ammessi si riempiono in ordine casuale, non dall'alto.
        incontri = [tra_ammessi[i:i + 2] for i in range(0, len(tra_ammessi), 2)]
        rng.shuffle(incontri)
        tra_ammessi = [posto for incontro in incontri for posto in incontro]
        self.tra_ammessi = tra_ammessi  # posti degli incontri tra due ammessi, a coppie
        self.posti = tra_ammessi + contro_q
        self.avversario = avversario
        self.richiesta = richiesta  # classifica richiesta dal posto (None = qualunque)
        self.pedine = pedine  # in ordine casuale: e' questo che rende casuale il sorteggio
        self.quote_iniziali = quote
        # Quanti posti restano per ogni classifica fuori dagli incontri tra ammessi
        # (aspettiti e incontri contro un q): li' la regola del circolo non conta.
        self.fuori = Counter(posti_aspettiti)
        self.fuori_liberi = 0  # posti contro un q senza una classifica richiesta
        for j in contro_q:
            if richiesta[j] is None:
                self.fuori_liberi += 1
            else:
                self.fuori[richiesta[j]] += 1

    def prova(self, violazioni_ammesse):
        """Restituisce i posti riempiti {posto: pedina}, oppure None se e' impossibile."""
        for pedina in self.pedine:
            pedina.usato = False
        # restanti: circolo -> Counter(classifica -> quanti non ancora messi)
        self.prova_vuota()
        self.tentativi = 0
        return dict(self.assegnati) if self._cerca(violazioni_ammesse) else None

    def violazioni_inevitabili(self):
        """Quanti incontri tra compagni di circolo ci saranno per forza, al minimo."""
        self.prova_vuota()
        return self._violazioni_inevitabili()

    def prova_vuota(self):
        self.quote = Counter(self.quote_iniziali)
        self.restanti = {}
        for pedina in self.pedine:
            self.restanti.setdefault(pedina.chiave_circolo, Counter())[pedina.classifica] += 1
        self.assegnati = {}

    def _violazioni_inevitabili(self):
        messi = len(self.assegnati)
        vincolati = len(self.tra_ammessi)
        if messi >= vincolati:
            return 0
        rivale = None
        if messi % 2 == 1:
            rivale = self.assegnati[self.tra_ammessi[messi - 1]].chiave_circolo
        coppie_vuote = (vincolati - messi) // 2
        totale = 0
        for circolo, per_classifica in self.restanti.items():
            quanti = sum(per_classifica.values())
            if not quanti:
                continue
            # Quanti di questo circolo possono stare fuori dagli incontri tra ammessi:
            # nei posti riservati alla loro classifica, e poi nei posti contro un q
            # che non sono di testa di serie (per le classifiche che ci possono andare).
            fuori = sum(min(n, self.fuori[c]) for c, n in per_classifica.items())
            avanzano = sum(min(max(0, n - self.fuori[c]), self.quote[c])
                           for c, n in per_classifica.items())
            fuori += min(self.fuori_liberi, avanzano)
            dentro = quanti - fuori
            # Senza eccezioni, al massimo uno per incontro ancora vuoto
            senza_eccezioni = coppie_vuote + (1 if rivale is not None and rivale != circolo else 0)
            totale += max(0, dentro - senza_eccezioni)
        return totale

    def _cerca(self, violazioni_ammesse):
        self.tentativi += 1
        if self.tentativi > self.limite:
            raise _TroppiTentativi()
        if len(self.assegnati) == len(self.posti):
            return True
        if self._violazioni_inevitabili() > violazioni_ammesse:
            return False
        posto = self.posti[len(self.assegnati)]
        rivale = self.assegnati.get(self.avversario.get(posto))
        classifica_richiesta = self.richiesta[posto]
        provati = set()
        for pedina in self.pedine:
            if pedina.usato:
                continue
            if classifica_richiesta is None:
                if self.quote[pedina.classifica] == 0:
                    continue
            elif pedina.classifica != classifica_richiesta:
                continue
            classe = (pedina.classifica, pedina.chiave_circolo)
            if classe in provati:
                continue
            provati.add(classe)
            stesso_circolo = rivale is not None and rivale.chiave_circolo == pedina.chiave_circolo
            if stesso_circolo and violazioni_ammesse == 0:
                continue
            self._metti(posto, pedina, +1)
            if self._cerca(violazioni_ammesse - stesso_circolo):
                return True
            self._metti(posto, pedina, -1)
        return False

    def _metti(self, posto, pedina, verso):
        """verso = +1 mette la pedina nel posto, -1 la toglie."""
        if self.richiesta[posto] is None:
            self.quote[pedina.classifica] -= verso
        self.restanti[pedina.chiave_circolo][pedina.classifica] -= verso
        pedina.usato = verso > 0
        if verso > 0:
            self.assegnati[posto] = pedina
        else:
            del self.assegnati[posto]


_TIPO_ARMONIA = {GIOCATORE: "G", LIBERO: "L", QUALIFICATO_ENTRANTE: "Q"}


class _Pedina:
    """Un giocatore durante il sorteggio (per segnare se e' gia' stato messo)."""

    def __init__(self, giocatore):
        self.giocatore = giocatore
        self.classifica = giocatore.classifica
        self.chiave_circolo = giocatore.chiave_circolo
        self.usato = False


# Quante disposizioni diverse dei qualificati entranti provare, quando la
# regola dello stesso circolo non si riesce a rispettare con la prima.
PROVE_DEI_QUALIFICATI = 30


def sorteggia(calcoli, giocatori, rng=None, classifiche=None):
    """Compila il tabellone: schema e sorteggio dei giocatori.

    calcoli      i calcoli preliminari (programma.calcoli.calcola), senza errori
    giocatori    i giocatori ammessi direttamente
    rng          il generatore di numeri casuali (per le prove si puo' fissare)
    classifiche  tutte le classifiche, dalla piu' alta (servono per misurare le
                 differenze di classifica); se mancano, quelle dei giocatori
    """
    rng = rng or random.Random()
    livello = {c: i for i, c in enumerate(classifiche or [c for c, _ in calcoli.ammessi])}
    tabellone = _sorteggio(calcoli, giocatori, rng, schema(calcoli, rng), livello)
    q_primo_turno = sum(n for c, n in calcoli.non_aspettiti if c == QUALIFICATO)
    scelta_dei_q = 0 < q_primo_turno < calcoli.I1
    if not tabellone.problemi or not scelta_dei_q:
        return tabellone
    # Si puo' scegliere in quali incontri mettere i q: si provano altre disposizioni.
    migliore = tabellone
    for _ in range(PROVE_DEI_QUALIFICATI):
        prova = _sorteggio(calcoli, giocatori, rng, schema(calcoli, rng), livello)
        if len(incontri_stesso_circolo(prova)) < len(incontri_stesso_circolo(migliore)):
            migliore = prova
        if not migliore.problemi:
            return migliore
    for problema in migliore.problemi:
        problema.messaggio = problema.messaggio.replace(
            "il minimo possibile di questi incontri",
            "il minimo possibile di questi incontri, tra le disposizioni dei qualificati "
            "entranti che ha provato")
    return migliore


def _classifiche_fisse(calcoli, posti):
    """La classifica dei posti gia' decisi: le teste di serie e gli aspettiti.

    La testa di serie n. k ha la k-esima classifica dall'alto; gli aspettiti che
    non sono teste di serie hanno i numeri subito dopo, anche loro dalla
    classifica piu' alta: cosi' i q in aspettito incontrano i piu' deboli.
    """
    ordinati = _classifiche_ordinate(calcoli)
    numeri = numeri_delle_coppie(len(posti), calcoli.sezioni)
    fisse = {}
    for j, posto in enumerate(posti):
        if posto.tipo != GIOCATORE:
            continue
        if posto.testa_di_serie:
            fisse[j] = ordinati[posto.testa_di_serie - 1]
        elif posti[j ^ 1].tipo == LIBERO:
            fisse[j] = ordinati[numeri[j // 2] - 1]
    return fisse


def _sorteggio(calcoli, giocatori, rng, posti, livello):
    """Il sorteggio dei giocatori in uno schema gia' pronto.

    1. Il sorteggio mirato decide quale classifica va in ogni posto del primo
       turno (programma.armonizzazione).
    2. Il sorteggio vero sceglie i giocatori, rispettando la regola dello stesso
       circolo. Se con le disposizioni migliori del sorteggio mirato la regola
       non si puo' rispettare, la regola vince: si sorteggia senza disposizione
       e poi si migliora la disposizione con scambi che non la violano.
    """
    tabellone = Tabellone(calcoli, posti)
    ordinati = _classifiche_ordinate(calcoli)
    T = calcoli.teste_di_serie
    diretti_aspettiti = _aspettiti_diretti(calcoli)
    fisse = _classifiche_fisse(calcoli, posti)

    # Quanti giocatori di ogni classifica vanno nei posti non di testa di serie
    # del primo turno (li sceglie il sorteggio tra quelli di quella classifica).
    quote = Counter(ordinati[max(T, diretti_aspettiti):])

    # I posti del primo turno con un giocatore ammesso direttamente.
    # Prima gli incontri tra due ammessi (quelli dove conta la regola del circolo).
    tra_ammessi, contro_q = [], []
    avversario = {}
    for i in range(0, len(posti), 2):
        alto, basso = posti[i], posti[i + 1]
        if LIBERO in (alto.tipo, basso.tipo):
            continue
        diretti = [j for j in (i, i + 1) if posti[j].tipo == GIOCATORE]
        if len(diretti) == 2:
            avversario[i], avversario[i + 1] = i + 1, i
            tra_ammessi += diretti
        else:
            contro_q += diretti
    # Posti degli aspettiti, per classifica: teste di serie e altri aspettiti.
    posti_aspettiti = Counter(ordinati[k - 1] for k in range(1, min(T, diretti_aspettiti) + 1))
    posti_aspettiti.update(ordinati[T:diretti_aspettiti])

    pedine = [_Pedina(g) for g in giocatori]
    rng.shuffle(pedine)

    def nuova_ricerca(richiesta, limite=LIMITE_TENTATIVI):
        return _Ricerca(tra_ammessi, contro_q, avversario, richiesta, pedine, quote,
                        posti_aspettiti, rng, limite)

    # 1. Il sorteggio mirato: le disposizioni delle classifiche, dalla migliore.
    liberi = [j for j in tra_ammessi + contro_q if j not in fisse]
    armonia = Armonizzazione(
        [_TIPO_ARMONIA[p.tipo] for p in posti], {j: livello[c] for j, c in fisse.items()},
        liberi, [livello[c] for c in quote.elements()], len(posti) // 2 // (calcoli.sezioni or 1))
    di_livello = {v: c for c, v in livello.items()}
    assegnati = None
    for disposizione, _ in armonia.cerca(rng):
        richiesta = {j: fisse.get(j) or di_livello[disposizione[j]] for j in tra_ammessi + contro_q}
        try:
            assegnati = nuova_ricerca(richiesta, LIMITE_TENTATIVI_MIRATO).prova(0)
        except _TroppiTentativi:
            assegnati = None
        if assegnati is not None:
            break

    # 2. Se non si e' trovato: il sorteggio che rispetta la regola dello stesso circolo.
    ricerca = nuova_ricerca({j: fisse.get(j) for j in tra_ammessi + contro_q})
    esaurito = False
    if assegnati is None:
        try:
            assegnati = ricerca.prova(0)
            esaurito = assegnati is None  # provati tutti i casi: nessuno la rispetta
        except _TroppiTentativi:
            assegnati = None
        if assegnati is None:
            # Un sorteggio qualsiasi (con eccezioni ammesse si trova subito),
            # poi si migliora scambiando i giocatori.
            assegnati = ricerca.prova(len(tra_ammessi))
    for pedina in pedine:
        pedina.usato = False
    for j, pedina in assegnati.items():
        pedina.usato = True
        posti[j].giocatore = pedina.giocatore

    # Gli aspettiti: ognuno con la classifica del suo numero, per sorteggio tra
    # i giocatori di quella classifica.
    rimasti = [p for p in pedine if not p.usato]
    for j, posto in enumerate(posti):
        if posto.tipo == GIOCATORE and posto.giocatore is None:
            pedina = next(p for p in rimasti if p.classifica == fisse[j])
            rimasti.remove(pedina)
            posto.giocatore = pedina.giocatore

    if incontri_stesso_circolo(tabellone):
        minimo = ricerca.violazioni_inevitabili()
        _meno_incontri_stesso_circolo(tabellone, avversario, rng, minimo)
        incontri = incontri_stesso_circolo(tabellone)
        if len(incontri) == minimo:
            spiegazione = ("non esiste nessun sorteggio che la rispetti del tutto; il programma "
                           "ha scelto un sorteggio con il minimo possibile di questi incontri")
        elif esaurito:
            spiegazione = ("non esiste nessun sorteggio che la rispetti del tutto; il programma "
                           "ha cercato un sorteggio con pochi incontri di questo tipo, ma non "
                           "puo' garantire che siano il minimo possibile")
        else:
            spiegazione = ("il programma non e' riuscito a trovare un sorteggio che la rispetti "
                           "(i casi possibili sono troppi per provarli tutti); ha cercato un "
                           "sorteggio con pochi incontri di questo tipo")
        coppie = [f"{a.giocatore.codice} e {b.giocatore.codice} ({a.giocatore.circolo})"
                  for a, b in incontri]
        tabellone.problemi.append(Problema(
            AVVISO, "", 0,
            f"regola dello stesso circolo al primo turno non rispettata: {spiegazione}. "
            f"Incontri tra giocatori dello stesso circolo: {'; '.join(coppie)}"))
    _migliora_la_disposizione(posti, armonia, liberi, avversario, livello, rng)
    return tabellone


def _migliora_la_disposizione(posti, armonia, liberi, avversario, livello, rng):
    """Dopo il sorteggio, scambia due giocatori del primo turno (non teste di serie)
    quando la disposizione delle classifiche migliora e la regola dello stesso
    circolo non peggiora. Serve quando la regola ha impedito il sorteggio mirato."""
    for j in liberi:
        armonia.livelli[j] = livello[posti[j].giocatore.classifica]

    def stessi(j, giocatore):
        rivale = avversario.get(j)
        return rivale is not None and posti[rivale].giocatore.chiave_circolo == giocatore.chiave_circolo

    migliorato = True
    while migliorato:
        migliorato = False
        ordine = list(liberi)
        rng.shuffle(ordine)
        for x, a in enumerate(ordine):
            for b in ordine[x + 1:]:
                ga, gb = posti[a].giocatore, posti[b].giocatore
                if ga.classifica == gb.classifica or avversario.get(a) == b:
                    continue
                if stessi(a, gb) + stessi(b, ga) > stessi(a, ga) + stessi(b, gb):
                    continue
                if armonia.prova_scambio(a, b):
                    posti[a].giocatore, posti[b].giocatore = gb, ga
                    migliorato = True


def _meno_incontri_stesso_circolo(tabellone, avversario, rng, minimo, giri=20_000):
    """Riduce gli incontri del primo turno tra giocatori dello stesso circolo
    scambiando di posto due giocatori alla volta.

    Si scambiano solo giocatori che possono stare l'uno al posto dell'altro:
    con la stessa classifica, oppure due giocatori del primo turno che non sono
    teste di serie. Cosi' il tabellone resta giusto per il manuale.
    """
    posti = tabellone.posti
    aspettito = {j: posti[j ^ 1].tipo == LIBERO for j in range(len(posti))}
    mobili = [j for j, p in enumerate(posti) if p.tipo == GIOCATORE]

    def scambiabili(j, k):
        a, b = posti[j], posti[k]
        if a.giocatore.classifica == b.giocatore.classifica:
            return True
        return (not a.testa_di_serie and not b.testa_di_serie
                and not aspettito[j] and not aspettito[k])

    def stesso_circolo(j, giocatore):
        rivale = avversario.get(j)
        return rivale is not None and posti[rivale].giocatore.chiave_circolo == giocatore.chiave_circolo

    for _ in range(giri):
        sbagliati = [j for j in avversario if j < avversario[j]
                     and stesso_circolo(j, posti[j].giocatore)]
        if len(sbagliati) <= minimo:
            return
        coppia = rng.choice(sbagliati)
        j = rng.choice((coppia, avversario[coppia]))
        rng.shuffle(mobili)
        di_lato = None
        for k in mobili:
            if k in (j, avversario[j]) or not scambiabili(j, k):
                continue
            a, b = posti[j].giocatore, posti[k].giocatore
            prima = 1 + stesso_circolo(k, b)
            dopo = stesso_circolo(j, b) + stesso_circolo(k, a)
            if dopo < prima:
                posti[j].giocatore, posti[k].giocatore = b, a
                break
            if dopo == prima and di_lato is None:
                di_lato = k
        else:
            # Nessuno scambio migliora: se ne fa uno che non peggiora, per uscire dall'impasse.
            if di_lato is not None:
                posti[j].giocatore, posti[di_lato].giocatore = posti[di_lato].giocatore, posti[j].giocatore


def incontri_stesso_circolo(tabellone):
    """Gli incontri del primo turno tra due giocatori dello stesso circolo."""
    return [(a, b) for a, b in tabellone.coppie
            if a.giocatore and b.giocatore
            and a.giocatore.chiave_circolo == b.giocatore.chiave_circolo]


def _riga(numero, posto):
    testa = f"({posto.testa_di_serie})" if posto.testa_di_serie else ""
    if posto.tipo == LIBERO:
        descrizione = "posto libero"
    elif posto.tipo == QUALIFICATO_ENTRANTE:
        descrizione = "q  (qualificato entrante)"
    elif posto.giocatore is None:
        descrizione = "?"
    else:
        g = posto.giocatore
        descrizione = f"{g.codice:<10} {g.classifica:<5} {g.circolo}"
    return f"{numero:>4}  {testa:>4}  {descrizione}"


def disegna(tabellone, titolo=""):
    """Il tabellone come testo, un posto per riga, con gli incontri del primo turno
    separati da una riga vuota e le parti che danno ciascun qualificato uscente.

    Le righe di spiegazione cominciano con #: cosi' il testo si puo' salvare,
    correggere a mano e far controllare dal programma (py tabelloni.py controlla).
    """
    calcoli = tabellone.calcoli
    D = len(tabellone.posti)
    Qu = calcoli.qualificati_uscenti
    righe = []
    if titolo:
        righe += [f"# {titolo}", "# " + "=" * len(titolo)]
    uscita = "il vincitore" if Qu == 1 else f"{Qu} qualificati (da Q1 a Q{Qu})"
    righe.append(f"# Tabellone di {D} posti, {calcoli.N} giocatori, esce {uscita}.")
    righe.append("# Il numero tra parentesi indica la testa di serie.")
    parte = D // Qu if Qu and D % Qu == 0 else D
    for i, posto in enumerate(tabellone.posti):
        if i % parte == 0 and calcoli.sezioni:
            righe += ["", f"# --- sezione {i // parte + 1}: qualificato Q{i // parte + 1} ---"]
        elif i % parte == 0 and Qu > 1:
            righe += ["", f"# --- parte del qualificato Q{i // parte + 1} ---"]
        elif i % 2 == 0:
            righe.append("")
        righe.append(_riga(i + 1, posto))
    return "\n".join(righe)
