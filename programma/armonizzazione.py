"""Il "sorteggio mirato": in quali posti del primo turno mettere ogni classifica.

Il manuale (Volume I, capitolo IV, "armonizzazione"; Volume II, esercizi 1.09,
1.27, 2.06, 2.10, 2.11, 2.12, 2.22, 2.23) chiede di non mettere le classifiche
a caso nei posti del primo turno, ma in modo che i giocatori destinati a
incontrarsi abbiano classifiche vicine. Il programma sceglie la disposizione
delle classifiche con il "costo" piu' basso; poi il sorteggio sceglie, tra i
giocatori della stessa classifica, chi va in ogni posto.

Il costo somma le raccomandazioni non seguite (Volume II, pagina 4):
  - primo turno tra due ammessi: la differenza di classifica (raccomandazione 6);
  - un ammesso contro un qualificato entrante: meglio i giocatori di classifica
    piu' bassa (raccomandazione 1);
  - secondo turno tra due vincitori del primo turno ("compressione"): meglio
    se hanno la stessa classifica (raccomandazione 2); se no, il piu' forte
    gioca due volte di fila contro uno piu' debole (raccomandazione 5);
  - secondo turno tra il vincitore del primo turno e chi entra al secondo
    turno ("progressione"): meglio se non hanno la stessa classifica
    (raccomandazione 3) e se la differenza non e' troppo grande (raccomandazione 6).
Per fare i conti si immagina che vinca sempre il giocatore di classifica piu'
alta, e che un qualificato entrante perda contro un giocatore ammesso direttamente.
"""

# Che cosa c'e' in un posto (per non dipendere da programma.sorteggio).
GIOCATORE, LIBERO, Q = "G", "L", "Q"

# Quante volte si ricomincia la ricerca da una disposizione a caso.
PARTENZE = 12


def _rappresentante(tipi, livelli, a, b):
    """Chi esce da un incontro del primo turno, e il costo dell'incontro stesso.

    Restituisce (tipo, livello, costo): tipo "aspettito" (entra al secondo turno),
    "q in aspettito" oppure "vincitore" (ha giocato il primo turno).
    """
    if tipi[a] == LIBERO or tipi[b] == LIBERO:
        altro = b if tipi[a] == LIBERO else a
        if tipi[altro] == GIOCATORE:
            return "aspettito", livelli[altro], 0
        return "q in aspettito", None, 0
    diretti = [livelli[j] for j in (a, b) if tipi[j] == GIOCATORE]
    if len(diretti) == 2:
        return "vincitore", min(diretti), abs(diretti[0] - diretti[1])
    if len(diretti) == 1:
        return "vincitore", diretti[0], 0
    return "vincitore", None, 0


def _costo_secondo_turno(primo, secondo):
    (tipo1, livello1, _), (tipo2, livello2, _) = primo, secondo
    if livello1 is None or livello2 is None:
        return 0
    differenza = abs(livello1 - livello2)
    if tipo1 == tipo2 == "vincitore":
        return 2 * differenza
    if {tipo1, tipo2} == {"aspettito", "vincitore"}:
        return 2 if differenza == 0 else differenza - 1
    return 0


class Armonizzazione:
    """tipi        che cosa c'e' in ogni posto: GIOCATORE, LIBERO oppure Q
    livelli_fissi  {posto: livello} per le teste di serie e gli aspettiti
    liberi         i posti del primo turno ancora senza classifica
    livelli        i livelli da mettere nei posti liberi (0 = classifica piu' alta)
    coppie_per_sezione  quante coppie ha ogni sezione (o il tabellone intero)
    """

    def __init__(self, tipi, livelli_fissi, liberi, livelli, coppie_per_sezione):
        self.tipi = list(tipi)
        self.livelli = [None] * len(tipi)
        for j, livello in livelli_fissi.items():
            self.livelli[j] = livello
        self.liberi = list(liberi)
        self.da_mettere = sorted(livelli)
        self.piu_basso = max(livelli) if livelli else 0
        # I gruppi di posti che contano insieme: due incontri che al secondo turno
        # si incontrano (quattro posti), oppure un incontro solo.
        larghezza = 4 if coppie_per_sezione > 1 else 2
        self.gruppo = {j: j - j % larghezza for j in range(len(tipi))}
        self.larghezza = larghezza

    def costo_gruppo(self, inizio):
        tipi, livelli = self.tipi, self.livelli
        rappresentanti = [_rappresentante(tipi, livelli, i, i + 1)
                          for i in range(inizio, inizio + self.larghezza, 2)]
        costo = sum(r[2] for r in rappresentanti)
        for i in range(inizio, inizio + self.larghezza, 2):
            # Un ammesso contro un q: meglio se ha la classifica piu' bassa.
            if LIBERO not in (tipi[i], tipi[i + 1]) and GIOCATORE in (tipi[i], tipi[i + 1]) \
                    and tipi[i] != tipi[i + 1]:
                j = i if tipi[i] == GIOCATORE else i + 1
                if livelli[j] is not None:
                    costo += 2 * (self.piu_basso - livelli[j])
        if len(rappresentanti) == 2:
            costo += _costo_secondo_turno(*rappresentanti)
        return costo

    def costo(self):
        return sum(self.costo_gruppo(inizio) for inizio in set(self.gruppo.values()))

    def prova_scambio(self, a, b):
        """Scambia le classifiche dei posti a e b se il costo scende."""
        gruppi = {self.gruppo[a], self.gruppo[b]}
        prima = sum(self.costo_gruppo(g) for g in gruppi)
        livelli = self.livelli
        livelli[a], livelli[b] = livelli[b], livelli[a]
        dopo = sum(self.costo_gruppo(g) for g in gruppi)
        if dopo < prima:
            return True
        livelli[a], livelli[b] = livelli[b], livelli[a]
        return False

    def cerca(self, rng, partenze=PARTENZE):
        """Le disposizioni migliori trovate: elenco di {posto: livello}, dalla migliore.
        A parita' di costo, l'ordine e' casuale."""
        trovate = {}
        for _ in range(partenze):
            livelli = list(self.da_mettere)
            rng.shuffle(livelli)
            for j, livello in zip(self.liberi, livelli):
                self.livelli[j] = livello
            migliorato = True
            while migliorato:
                migliorato = False
                ordine = list(self.liberi)
                rng.shuffle(ordine)
                for x, a in enumerate(ordine):
                    for b in ordine[x + 1:]:
                        if self.livelli[a] != self.livelli[b] and self.prova_scambio(a, b):
                            migliorato = True
            disposizione = tuple(self.livelli[j] for j in self.liberi)
            trovate[disposizione] = self.costo()
        elenco = list(trovate.items())
        rng.shuffle(elenco)
        elenco.sort(key=lambda voce: voce[1])
        return [(dict(zip(self.liberi, disposizione)), costo) for disposizione, costo in elenco]
