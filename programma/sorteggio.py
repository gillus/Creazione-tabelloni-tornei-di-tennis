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
"""

import random
from collections import Counter
from dataclasses import dataclass, field

from programma.calcoli import QUALIFICATO
from programma.dati import AVVISO, ERRORE, Problema

# Tipi di posto nel tabellone
GIOCATORE = "giocatore"
LIBERO = "libero"  # posto libero (bye): chi e' nella stessa coppia entra al secondo turno
QUALIFICATO_ENTRANTE = "q"

# Oltre questo numero di tentativi il programma smette di cercare un sorteggio
# che rispetti la regola dello stesso circolo (serve solo nei casi molto difficili).
LIMITE_TENTATIVI = 20_000


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


def _riga_principale(indice_coppia, numero_coppie):
    """0 = riga alta della coppia (meta' superiore), 1 = riga bassa (meta' inferiore)."""
    return 0 if indice_coppia < max(1, numero_coppie // 2) else 1


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
    T = calcoli.teste_di_serie
    diretti_aspettiti = _aspettiti_diretti(calcoli)
    teste_aspettiti = min(T, diretti_aspettiti)
    q_aspettiti = sum(n for c, n in calcoli.aspettiti if c == QUALIFICATO)
    q_primo_turno = sum(n for c, n in calcoli.non_aspettiti if c == QUALIFICATO)

    ordine = ordine_delle_coppie(numero_coppie)
    coppia_del_numero = {numero: indice for indice, numero in enumerate(ordine)}

    # Cosa c'e' nella coppia con un certo numero d'ordine.
    teste = set(range(1, T + 1))
    # Gli aspettiti diretti: prima le teste di serie, poi gli altri, con i numeri
    # subito dopo le teste di serie (come se fossero teste di serie).
    aspettiti_non_teste = list(range(T + 1, diretti_aspettiti + 1))
    numeri_aspettiti = list(range(1, teste_aspettiti + 1)) + aspettiti_non_teste
    occupati = teste | set(aspettiti_non_teste)
    # I q in aspettito vanno contro gli aspettiti piu' deboli (numero piu' alto):
    # nel secondo turno la coppia k incontra la coppia (numero delle coppie + 1 - k).
    q_in_aspettito = []
    for k in reversed(numeri_aspettiti):
        if len(q_in_aspettito) == q_aspettiti:
            break
        numero = numero_coppie + 1 - k
        if numero not in occupati:
            q_in_aspettito.append(numero)
            occupati.add(numero)
    # Se non bastano (succede solo in casi molto particolari), i primi numeri liberi.
    liberi = [n for n in range(1, numero_coppie + 1) if n not in occupati]
    while len(q_in_aspettito) < q_aspettiti:
        q_in_aspettito.append(liberi.pop(0))
    # Tutte le altre coppie giocano il primo turno.
    primo_turno = [k for k in range(teste_aspettiti + 1, T + 1)] + liberi

    # Quali incontri del primo turno hanno un qualificato entrante: uno per ogni
    # frazione del tabellone; a parita', quelli senza testa di serie, perche' i q
    # devono incontrare i giocatori di classifica piu' bassa (raccomandazione 1).
    fissi = [coppia_del_numero[n] for n in q_in_aspettito]
    disponibili = [coppia_del_numero[n] for n in primo_turno]
    preferiti = {coppia_del_numero[n] for n in primo_turno if n not in teste}
    con_q = set(scegli_equilibrati(disponibili, fissi, q_primo_turno, rng, 0, numero_coppie,
                                   preferiti))

    posti = [None] * D
    for indice, numero in enumerate(ordine):
        principale = 2 * indice + _riga_principale(indice, numero_coppie)
        altro = 2 * indice + 1 - _riga_principale(indice, numero_coppie)
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
                 posti_aspettiti, rng):
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
        if self.tentativi > LIMITE_TENTATIVI:
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


def sorteggia(calcoli, giocatori, rng=None):
    """Compila il tabellone: schema e sorteggio dei giocatori.

    calcoli    i calcoli preliminari (programma.calcoli.calcola), senza errori
    giocatori  i giocatori ammessi direttamente
    rng        il generatore di numeri casuali (per le prove si puo' fissare)
    """
    rng = rng or random.Random()
    tabellone = _sorteggia_con_schema(calcoli, giocatori, rng, schema(calcoli, rng))
    q_primo_turno = sum(n for c, n in calcoli.non_aspettiti if c == QUALIFICATO)
    scelta_dei_q = 0 < q_primo_turno < calcoli.I1
    if not tabellone.problemi or not scelta_dei_q:
        return tabellone
    # Si puo' scegliere in quali incontri mettere i q: si provano altre disposizioni.
    migliore = tabellone
    for _ in range(PROVE_DEI_QUALIFICATI):
        prova = _sorteggia_con_schema(calcoli, giocatori, rng, schema(calcoli, rng))
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


def _sorteggia_con_schema(calcoli, giocatori, rng, posti):
    """Il sorteggio dei giocatori in uno schema gia' pronto."""
    tabellone = Tabellone(calcoli, posti)
    ordinati = _classifiche_ordinate(calcoli)
    T = calcoli.teste_di_serie
    diretti_aspettiti = _aspettiti_diretti(calcoli)

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
    richiesta = {j: ordinati[posti[j].testa_di_serie - 1] if posti[j].testa_di_serie else None
                 for j in tra_ammessi + contro_q}
    # Posti degli aspettiti, per classifica: teste di serie e altri aspettiti.
    posti_aspettiti = Counter(ordinati[k - 1] for k in range(1, min(T, diretti_aspettiti) + 1))
    posti_aspettiti.update(ordinati[T:diretti_aspettiti])

    pedine = [_Pedina(g) for g in giocatori]
    rng.shuffle(pedine)
    ricerca = _Ricerca(tra_ammessi, contro_q, avversario, richiesta, pedine, quote,
                       posti_aspettiti, rng)

    # Primo tentativo: il sorteggio che rispetta la regola dello stesso circolo.
    try:
        assegnati = ricerca.prova(0)
        esaurito = assegnati is None  # provati tutti i casi: nessuno la rispetta
    except _TroppiTentativi:
        assegnati, esaurito = None, False
    if assegnati is None:
        # Un sorteggio qualsiasi (con eccezioni ammesse si trova subito),
        # poi si migliora scambiando i giocatori.
        assegnati = ricerca.prova(len(tra_ammessi))
    for pedina in pedine:
        pedina.usato = False
    for j, pedina in assegnati.items():
        pedina.usato = True
        posti[j].giocatore = pedina.giocatore

    # Gli aspettiti: prima le teste di serie, poi gli altri, per sorteggio.
    rimasti = [p for p in pedine if not p.usato]
    for posto in posti:
        if posto.tipo == GIOCATORE and posto.giocatore is None and posto.testa_di_serie:
            classifica = ordinati[posto.testa_di_serie - 1]
            pedina = next(p for p in rimasti if p.classifica == classifica)
            rimasti.remove(pedina)
            posto.giocatore = pedina.giocatore
    vuoti = [posto for posto in posti if posto.tipo == GIOCATORE and posto.giocatore is None]
    for posto, pedina in zip(vuoti, rimasti):
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
    return tabellone


def _meno_incontri_stesso_circolo(tabellone, avversario, rng, minimo, giri=20_000):
    """Riduce gli incontri del primo turno tra giocatori dello stesso circolo
    scambiando di posto due giocatori alla volta.

    Si scambiano solo giocatori che possono stare l'uno al posto dell'altro:
    con la stessa classifica, oppure due giocatori che non sono teste di serie
    ed entrano nello stesso turno. Cosi' il tabellone resta giusto per il manuale.
    """
    posti = tabellone.posti
    aspettito = {j: posti[j ^ 1].tipo == LIBERO for j in range(len(posti))}
    mobili = [j for j, p in enumerate(posti) if p.tipo == GIOCATORE]

    def scambiabili(j, k):
        a, b = posti[j], posti[k]
        if a.giocatore.classifica == b.giocatore.classifica:
            return True
        return not a.testa_di_serie and not b.testa_di_serie and aspettito[j] == aspettito[k]

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
        if i % parte == 0 and Qu > 1:
            righe += ["", f"# --- parte del qualificato Q{i // parte + 1} ---"]
        elif i % 2 == 0:
            righe.append("")
        righe.append(_riga(i + 1, posto))
    return "\n".join(righe)
