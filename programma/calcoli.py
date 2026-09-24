"""Calcoli preliminari di un tabellone di estrazione (manuale, Volume I, capitoli II e III).

Sono i conti che il giudice arbitro fa prima di disegnare il tabellone:
dimensione, aspettiti, incontri del primo turno, chi gioca il primo turno,
quante teste di serie e quali.

Le sigle sono quelle del manuale:
  Qu  qualificati uscenti (quanti giocatori escono dal tabellone)
  S   sezioni: quando Qu non e' una potenza di due (1, 2, 4, 8...) il tabellone
      e' diviso in Qu sezioni, piccoli tabelloni che danno un qualificato
      ciascuno (manuale, Volume I, capitolo III)
  q   qualificati entranti (arrivano da un tabellone precedente)
  N   numero dei giocatori partecipanti (direttamente ammessi + q)
  D   dimensione del tabellone
  A   aspettiti (entrano in gara al secondo turno)
  NA  non aspettiti (giocano il primo turno, detto anche pre-turno)
  I1  incontri del primo turno
"""

from dataclasses import dataclass, field

from programma.dati import AVVISO, ERRORE, Problema

QUALIFICATO = "q"
NON_CLASSIFICATO = "4.NC"


@dataclass
class Calcoli:
    qualificati_uscenti: int
    qualificati_entranti: int
    # Giocatori direttamente ammessi: coppie (classifica, quanti), dalla classifica piu' alta.
    ammessi: list
    N: int = 0
    sezioni: int = 0  # 0 = tabellone senza sezioni
    D: int = 0
    A: int = 0
    NA: int = 0
    I1: int = 0
    # Coppie (classifica oppure "q", quanti). Prima i q, poi dalla classifica piu' bassa.
    non_aspettiti: list = field(default_factory=list)
    aspettiti: list = field(default_factory=list)
    # Numero minimo e massimo di teste di serie (None se non si fanno teste di serie).
    # Con le sezioni sono multipli del numero delle sezioni.
    teste_di_serie_minimo: int = None
    teste_di_serie_massimo: int = None
    teste_di_serie_proposta: int = None
    teste_di_serie: int = 0
    teste_di_serie_scelte_dal_giudice: bool = False
    # Terne (classifica, quante sono teste di serie, quanti giocatori hanno quella classifica).
    composizione_teste_di_serie: list = field(default_factory=list)
    problemi: list = field(default_factory=list)


def conta_per_classifica(giocatori, classifiche):
    """Da un elenco di giocatori alle coppie (classifica, quanti), dalla classifica piu' alta."""
    return [(c, n) for c in classifiche
            if (n := sum(1 for g in giocatori if g.classifica == c))]


def potenza_di_due_successiva(numero):
    """La potenza di due uguale o immediatamente superiore al numero (1, 2, 4, 8, 16, ...)."""
    potenza = 1
    while potenza < numero:
        potenza *= 2
    return potenza


def e_potenza_di_due(numero):
    return numero >= 1 and potenza_di_due_successiva(numero) == numero


def dimensione_del_tabellone(giocatori, qualificati_uscenti=1):
    """Quanti posti deve avere il tabellone.

    Senza sezioni: la potenza di due uguale o subito superiore ai giocatori.
    Con le sezioni (qualificati uscenti diversi da 1, 2, 4, 8...): il numero delle
    sezioni per una potenza di due (per esempio 5 x 4 = 20, 3 x 8 = 24).
    """
    if e_potenza_di_due(qualificati_uscenti):
        return potenza_di_due_successiva(giocatori)
    sezioni = qualificati_uscenti
    return sezioni * potenza_di_due_successiva(-(-giocatori // sezioni))


def togli_dal_basso(ammessi, quanti):
    """Prende 'quanti' giocatori partendo dalla classifica piu' bassa.

    Restituisce le coppie prese (dalla classifica piu' bassa) e quelle rimaste
    (dalla classifica piu' alta).
    """
    presi = []
    rimasti = list(ammessi)
    while quanti > 0 and rimasti:
        classifica, numero = rimasti.pop()
        prendo = min(numero, quanti)
        presi.append((classifica, prendo))
        if numero > prendo:
            rimasti.append((classifica, numero - prendo))
        quanti -= prendo
    return presi, rimasti


def proposta_teste_di_serie(ammessi, minimo, massimo):
    """Propone quante teste di serie fare.

    Regola usata (ricavata dagli esercizi del Volume II): il numero piu' piccolo
    tra minimo e massimo che prende tutti i giocatori di una classifica, senza
    dividerla a meta'; se non ce n'e' nessuno, il minimo.
    """
    somma = 0
    for _, numero in ammessi:
        somma += numero
        if minimo <= somma <= massimo:
            return somma
    return minimo


def proposta_teste_di_serie_sezioni(aspettiti_diretti, minimo, massimo, sezioni):
    """Propone quante teste di serie fare in un tabellone a sezioni.

    Il numero deve essere un multiplo delle sezioni. Regola usata (ricavata dagli
    esercizi del Volume II, capitolo 2): il multiplo piu' piccolo che fa teste di
    serie tutti i giocatori ammessi direttamente al secondo turno; se non c'e',
    il massimo.
    """
    for numero in range(minimo, massimo + 1, sezioni):
        if numero >= aspettiti_diretti:
            return numero
    return massimo


def calcola(ammessi, qualificati_entranti=0, qualificati_uscenti=1, teste_di_serie=None):
    """Fa i calcoli preliminari.

    ammessi               coppie (classifica, quanti), dalla classifica piu' alta
    qualificati_entranti  quanti q arrivano da un tabellone precedente
    qualificati_uscenti   quanti giocatori escono dal tabellone (1 = il vincitore)
    teste_di_serie        il numero scelto dal giudice arbitro; se manca lo propone il programma
    """
    ammessi = [(c, n) for c, n in ammessi if n > 0]
    q = qualificati_entranti
    Qu = qualificati_uscenti
    calcoli = Calcoli(Qu, q, ammessi)
    problemi = calcoli.problemi

    diretti = sum(n for _, n in ammessi)
    calcoli.N = N = diretti + q
    if N < 2:
        problemi.append(Problema(ERRORE, "", 0, f"servono almeno 2 giocatori, invece ce ne sono {N}"))
        return calcoli

    # Numeri del tabellone
    calcoli.sezioni = S = 0 if e_potenza_di_due(Qu) else Qu
    calcoli.D = D = dimensione_del_tabellone(N, Qu)
    calcoli.A = A = D - N
    calcoli.NA = NA = N - A
    calcoli.I1 = I1 = NA // 2

    if 2 * Qu > N:
        problemi.append(Problema(
            ERRORE, "", 0,
            f"troppi qualificati uscenti ({Qu}) per {N} giocatori: "
            f"possono essere al massimo la meta' dei giocatori"))
    if q > diretti:
        problemi.append(Problema(
            ERRORE, "", 0,
            f"i qualificati entranti ({q}) sono piu' dei giocatori ammessi direttamente ({diretti}): "
            f"il manuale non lo permette (Volume I, capitolo I, lettera G)"))

    # Chi gioca il primo turno: un qualificato entrante per ogni incontro, se ce ne sono
    # abbastanza (cosi' i q incontrano i giocatori di classifica piu' bassa e due q non
    # si incontrano tra loro); gli altri posti vanno ai giocatori di classifica piu' bassa.
    q_primo_turno = min(q, I1)
    diretti_primo_turno, diretti_aspettiti = togli_dal_basso(ammessi, NA - q_primo_turno)
    calcoli.non_aspettiti = ([(QUALIFICATO, q_primo_turno)] if q_primo_turno else []) + diretti_primo_turno
    calcoli.aspettiti = ([(QUALIFICATO, q - q_primo_turno)] if q > q_primo_turno else []) \
        + list(reversed(diretti_aspettiti))

    incontri_tra_diretti = I1 - q_primo_turno
    if incontri_tra_diretti and q:
        problemi.append(Problema(
            AVVISO, "", 0,
            f"al primo turno ci sono {incontri_tra_diretti} incontri tra giocatori ammessi "
            f"direttamente: il manuale raccomanda di evitarlo scegliendo un numero diverso "
            f"di qualificati entranti (Volume I, raccomandazione 4)"))

    # Teste di serie: non si fanno se giocano solo non classificati.
    if all(classifica == NON_CLASSIFICATO for classifica, _ in ammessi):
        if teste_di_serie:
            problemi.append(Problema(
                ERRORE, "", 0,
                "con soli giocatori non classificati (4.NC) non si fanno teste di serie"))
        return calcoli

    minimo = max(-(-N // 8), Qu)  # un ottavo dei giocatori, arrotondato per eccesso
    massimo = min(N // 2, diretti)  # la meta' dei giocatori; i q non possono essere teste di serie
    if S:
        # Ogni sezione deve avere lo stesso numero di teste di serie.
        minimo = -(-minimo // S) * S
        massimo = massimo // S * S
    calcoli.teste_di_serie_minimo = minimo
    calcoli.teste_di_serie_massimo = massimo
    if minimo > massimo:
        problemi.append(Problema(
            ERRORE, "", 0,
            f"non si possono fare le teste di serie: ne servono almeno {minimo} "
            f"ma al massimo se ne possono fare {massimo}"
            + (f" (con {S} sezioni devono essere un multiplo di {S})" if S else "")))
        return calcoli
    if S:
        calcoli.teste_di_serie_proposta = proposta_teste_di_serie_sezioni(
            sum(n for c, n in calcoli.aspettiti if c != QUALIFICATO), minimo, massimo, S)
    else:
        calcoli.teste_di_serie_proposta = proposta_teste_di_serie(ammessi, minimo, massimo)

    if teste_di_serie is None:
        calcoli.teste_di_serie = calcoli.teste_di_serie_proposta
    elif minimo <= teste_di_serie <= massimo and (not S or teste_di_serie % S == 0):
        calcoli.teste_di_serie = teste_di_serie
        calcoli.teste_di_serie_scelte_dal_giudice = True
    else:
        multiplo = (f" e, con {S} sezioni, essere un multiplo di {S} (lo stesso numero "
                    f"in ogni sezione)") if S else ""
        problemi.append(Problema(
            ERRORE, "", 0,
            f"le teste di serie scelte ({teste_di_serie}) devono essere tra {minimo} e {massimo}"
            f"{multiplo}"))
        return calcoli

    # Le teste di serie sono i giocatori con la classifica piu' alta.
    da_prendere = calcoli.teste_di_serie
    for classifica, numero in ammessi:
        if da_prendere == 0:
            break
        prese = min(numero, da_prendere)
        calcoli.composizione_teste_di_serie.append((classifica, prese, numero))
        da_prendere -= prese
    return calcoli


def _elenco(coppie):
    parti = [f"{n} {c}" if c == QUALIFICATO else f"{n} ({c})" for c, n in coppie]
    return ", ".join(parti) if parti else "nessuno"


def descrivi(calcoli):
    """I calcoli scritti come nel manuale, una riga per voce."""
    righe = [
        f"Qualificati uscenti            Qu = {calcoli.qualificati_uscenti}",
        f"Qualificati entranti           q  = {calcoli.qualificati_entranti}",
        f"Numero dei giocatori           N  = {calcoli.N}",
    ]
    if not calcoli.D:
        return "\n".join(righe)
    S = calcoli.sezioni
    if S:
        righe.append(f"Sezioni (una per qualificato)  {S}, da {calcoli.D // S} posti ciascuna")
    righe += [
        f"Dimensione del tabellone       D  = {calcoli.D}"
        + (f" ({S} x {calcoli.D // S})" if S else ""),
        f"Aspettiti (entrano al 2 turno) A  = {calcoli.D} - {calcoli.N} = {calcoli.A}",
        f"Non aspettiti (primo turno)    NA = {calcoli.N} - {calcoli.A} = {calcoli.NA}",
        f"Incontri del primo turno       I1 = {calcoli.NA} / 2 = {calcoli.I1}",
        f"Giocano il primo turno:        {_elenco(calcoli.non_aspettiti)}",
        f"Entrano al secondo turno:      {_elenco(calcoli.aspettiti)}",
    ]
    if calcoli.teste_di_serie_minimo is None:
        righe.append("Teste di serie:                nessuna (giocano solo non classificati)")
        return "\n".join(righe)
    righe.append(f"Teste di serie possibili:      da {calcoli.teste_di_serie_minimo}"
                 f" a {calcoli.teste_di_serie_massimo}"
                 + (f", solo multipli di {S} (lo stesso numero in ogni sezione)" if S else ""))
    if calcoli.composizione_teste_di_serie:
        chi = "scelte dal giudice arbitro" if calcoli.teste_di_serie_scelte_dal_giudice \
            else "proposta del programma"
        parti = []
        for classifica, prese, totale in calcoli.composizione_teste_di_serie:
            if prese == totale:
                parti.append(f"{prese} ({classifica})")
            else:
                parti.append(f"{prese} dei {totale} ({classifica}), per sorteggio")
        righe.append(f"Teste di serie ({chi}): {calcoli.teste_di_serie} = {', '.join(parti)}")
        if calcoli.teste_di_serie_scelte_dal_giudice \
                and calcoli.teste_di_serie != calcoli.teste_di_serie_proposta:
            righe.append(f"  (il programma avrebbe proposto {calcoli.teste_di_serie_proposta})")
    return "\n".join(righe)
