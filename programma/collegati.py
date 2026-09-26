"""Tabelloni collegati: la divisione dei giocatori in piu' tabelloni (manuale,
Volume I, capitolo VI; Volume II, esercizi da 6.01 a 6.06).

I qualificati uscenti di un tabellone sono i qualificati entranti del tabellone
seguente; l'ultimo tabellone e' il tabellone finale (da' il vincitore), a meno che
in dati/torneo.txt non sia scritto un altro numero di qualificati uscenti.

La divisione si scrive in dati/torneo.txt, una riga per tabellone, dal primo:
    tabellone 1 = 4.NC
    tabellone 2 = 4.6, 4.5, 4.4 ; qualificati uscenti = 4
    tabellone 3 = 4.3, 4.2, 4.1 ; tipo = estrazione ; teste di serie = 4
Se non c'e', e i giocatori sono di categorie diverse, il programma propone un
tabellone per categoria (i non classificati a parte).
"""

import re
from dataclasses import dataclass, field

from programma.calcoli import NON_CLASSIFICATO, e_potenza_di_due, potenza_di_due_successiva
from programma.dati import AVVISO, ERRORE, IMPOSTAZIONI_A_SCELTA, Problema

# Le impostazioni che si possono scrivere per un solo tabellone, dopo il punto e virgola.
IMPOSTAZIONI_DEL_TABELLONE = ("qualificati uscenti", "tipo", "teste di serie")
# Una categoria con meno giocatori di cosi' non fa un tabellone da sola.
MINIMO_PER_TABELLONE = 4
_TABELLONE = re.compile(r"^tabellone (\d+)$")


@dataclass
class Parte:
    """Un tabellone della divisione."""
    numero: int
    classifiche: list  # dalla piu' alta
    impostazioni: dict = field(default_factory=dict)  # scritte dal giudice arbitro
    giocatori: list = field(default_factory=list)
    qualificati_entranti: int = 0
    qualificati_uscenti: int = 1
    uscenti_proposti: bool = False  # True se il numero lo ha scelto il programma


def categoria(classifica):
    """'4.3' -> '4', '4.NC' -> '4.NC' (i non classificati sono un gruppo a parte)."""
    return classifica if classifica == NON_CLASSIFICATO else classifica.split(".")[0]


def nome_categoria(classifica):
    c = categoria(classifica)
    return "non classificati" if c == NON_CLASSIFICATO else f"{c}a categoria"


def e_una_riga_di_tabellone(nome):
    return _TABELLONE.match(nome) is not None


def leggi_divisione(impostazioni, classifiche, percorso=""):
    """Le righe "tabellone N = ..." di dati/torneo.txt. Restituisce le parti (vuoto se
    non ci sono righe) e i problemi."""
    problemi = []
    righe = sorted((int(_TABELLONE.match(nome).group(1)), valore)
                   for nome, valore in impostazioni.items() if _TABELLONE.match(nome))
    if not righe:
        return [], problemi

    def errore(messaggio):
        problemi.append(Problema(ERRORE, percorso, 0, messaggio))

    numeri = [n for n, _ in righe]
    if numeri != list(range(1, len(righe) + 1)):
        errore(f"i tabelloni devono essere numerati 1, 2, 3... senza salti: ci sono i numeri "
               f"{', '.join(map(str, numeri))}")
        return [], problemi
    parti = []
    gia = {}
    for numero, valore in righe:
        elenco, *altre = [p.strip() for p in valore.split(";")]
        parte = Parte(numero, [])
        for testo in elenco.split(","):
            classifica = "".join(testo.split()).replace(",", ".").upper()
            if not classifica:
                continue
            if classifica not in classifiche:
                errore(f"tabellone {numero}: la classifica \"{classifica}\" non esiste "
                       f"(quelle valide sono in dati/classifiche.txt)")
            elif classifica in gia:
                errore(f"la classifica {classifica} e' scritta nel tabellone {gia[classifica]} e "
                       f"nel tabellone {numero}: i giocatori di pari classifica devono stare "
                       f"nello stesso tabellone (Volume II, raccomandazione 7)")
            else:
                gia[classifica] = numero
                parte.classifiche.append(classifica)
        if not parte.classifiche:
            errore(f"tabellone {numero}: mancano le classifiche dei giocatori che ci giocano")
        for testo in altre:
            if "=" not in testo:
                errore(f"tabellone {numero}: \"{testo}\" deve essere nella forma 'nome = valore'")
                continue
            nome, valore_imp = (" ".join(p.split()) for p in testo.split("=", 1))
            nome = nome.lower()
            if nome not in IMPOSTAZIONI_DEL_TABELLONE:
                errore(f"tabellone {numero}: l'impostazione \"{nome}\" non si puo' scrivere qui "
                       f"(si possono scrivere: {', '.join(IMPOSTAZIONI_DEL_TABELLONE)})")
            elif nome in IMPOSTAZIONI_A_SCELTA:
                if valore_imp.lower() not in IMPOSTAZIONI_A_SCELTA[nome]:
                    errore(f"tabellone {numero}: \"{nome}\" puo' essere solo: "
                           f"{', '.join(IMPOSTAZIONI_A_SCELTA[nome])}")
                else:
                    parte.impostazioni[nome] = valore_imp.lower()
            elif not valore_imp.isdigit() or (nome == "qualificati uscenti" and int(valore_imp) < 1):
                errore(f"tabellone {numero}: \"{nome}\" deve essere un numero intero"
                       + (", almeno 1" if nome == "qualificati uscenti" else ""))
            else:
                parte.impostazioni[nome] = int(valore_imp)
        parte.classifiche.sort(key=classifiche.index)
        parti.append(parte)
    return parti, problemi


def proponi_divisione(giocatori, classifiche):
    """Un tabellone per categoria, dalla piu' bassa (Volume I, capitolo VI: "si ottiene
    cosi' un tabellone per categoria"); i non classificati a parte. Una categoria con
    meno di MINIMO_PER_TABELLONE giocatori va nel tabellone della categoria sotto (o,
    se e' la piu' bassa, in quello sopra). Con una sola categoria: un solo tabellone."""
    presenti = [c for c in classifiche if any(g.classifica == c for g in giocatori)]
    gruppi = []  # dalla categoria piu' bassa: liste di classifiche
    for classifica in reversed(presenti):
        if gruppi and categoria(gruppi[-1][0]) == categoria(classifica):
            gruppi[-1].append(classifica)
        else:
            gruppi.append([classifica])

    def quanti(gruppo):
        return sum(1 for g in giocatori if g.classifica in gruppo)

    cambiato = True
    while cambiato and len(gruppi) > 1:
        cambiato = False
        for i, gruppo in enumerate(gruppi):
            if quanti(gruppo) < MINIMO_PER_TABELLONE:
                j = i - 1 if i > 0 else 1
                gruppi[min(i, j)] = gruppi[min(i, j)] + gruppi[max(i, j)]
                del gruppi[max(i, j)]
                cambiato = True
                break
    return [Parte(n, sorted(g, key=classifiche.index)) for n, g in enumerate(gruppi, start=1)]


def qualificati_proposti(giocatori_del_tabellone, vicini_nel_seguente):
    """Quanti giocatori qualificare per il tabellone seguente: la potenza di due piu'
    grande che non supera ne' la meta' dei giocatori di questo tabellone, ne' i
    giocatori ammessi direttamente al tabellone seguente con una classifica al massimo
    due gruppi sopra la piu' alta di questo tabellone (i q li incontrano: Volume II,
    raccomandazione 6; Volume I, capitolo VI, ipotesi 1: "la differenza di classifica
    sarebbe troppo grande"). Come negli esercizi da 6.01 a 6.04; un tabellone che
    qualifica una potenza di due "si adatta piu' facilmente" (Volume I, capitolo VI)."""
    limite = min(vicini_nel_seguente, giocatori_del_tabellone // 2)
    if limite < 1:
        return 0
    potenza = potenza_di_due_successiva(limite)
    return potenza if potenza == limite else potenza // 2


def vicini(parte, seguente, livello):
    """I giocatori del tabellone seguente al massimo due gruppi sopra la classifica piu'
    alta di questo; se non ce n'e' nessuno, quelli della classifica piu' bassa."""
    migliore = min(livello[c] for c in parte.classifiche)
    entro_due = [g for g in seguente.giocatori if livello[g.classifica] >= migliore - 2]
    if entro_due:
        return len(entro_due)
    piu_bassa = max(livello[g.classifica] for g in seguente.giocatori)
    return sum(1 for g in seguente.giocatori if livello[g.classifica] == piu_bassa)


def prepara_divisione(parti, giocatori, classifiche, qualificati_entranti, qualificati_uscenti,
                      percorso=""):
    """Mette i giocatori nelle parti, calcola i qualificati entranti e uscenti di ogni
    tabellone e controlla le regole della divisione. Restituisce i problemi."""
    problemi = []

    def errore(messaggio):
        problemi.append(Problema(ERRORE, percorso, 0, messaggio))

    def avviso(messaggio):
        problemi.append(Problema(AVVISO, percorso, 0, messaggio))

    livello = {c: i for i, c in enumerate(classifiche)}
    assegnate = {c for p in parti for c in p.classifiche}
    senza = sorted({g.classifica for g in giocatori if g.classifica not in assegnate},
                   key=livello.get)
    if senza:
        errore(f"ci sono giocatori con classifiche che non sono in nessun tabellone: "
               f"{', '.join(senza)} (vanno scritte in una riga \"tabellone N = ...\")")
    for parte in parti:
        parte.giocatori = [g for g in giocatori if g.classifica in parte.classifiche]
        if not parte.giocatori:
            errore(f"nel tabellone {parte.numero} non gioca nessuno: nessun giocatore ha le "
                   f"classifiche {', '.join(parte.classifiche)}")
    if problemi:
        return problemi
    # La classifica aumenta da un tabellone al seguente (Volume I, capitolo I).
    for prima, dopo in zip(parti, parti[1:]):
        if max(livello[c] for c in dopo.classifiche) >= min(livello[c] for c in prima.classifiche):
            errore(f"nel tabellone {dopo.numero} ci sono classifiche piu' basse (o uguali) di "
                   f"quelle del tabellone {prima.numero}: i tabelloni vanno scritti dalle "
                   f"classifiche piu' basse alle piu' alte")
            return problemi
    # Categorie diverse nello stesso tabellone (Volume II, raccomandazione 7 b).
    for parte in parti:
        categorie = []
        for c in parte.classifiche:
            if nome_categoria(c) not in categorie:
                categorie.append(nome_categoria(c))
        if len(categorie) > 1:
            avviso(f"nel tabellone {parte.numero} ci sono giocatori di categorie diverse "
                   f"({', '.join(categorie)}): il manuale raccomanda di non farlo "
                   f"(Volume II, raccomandazione 7 b)")
    # Qualificati entranti e uscenti.
    q = qualificati_entranti
    for i, parte in enumerate(parti):
        parte.qualificati_entranti = q
        N = len(parte.giocatori) + q
        if i == len(parti) - 1:
            parte.qualificati_uscenti = parte.impostazioni.get("qualificati uscenti",
                                                               qualificati_uscenti)
        elif "qualificati uscenti" in parte.impostazioni:
            parte.qualificati_uscenti = parte.impostazioni["qualificati uscenti"]
        else:
            parte.qualificati_uscenti = qualificati_proposti(N, vicini(parte, parti[i + 1],
                                                                      livello))
            parte.uscenti_proposti = True
            if parte.qualificati_uscenti < 1:
                errore(f"il tabellone {parte.numero} ha troppo pochi giocatori ({N}) per "
                       f"qualificarne per il tabellone {parte.numero + 1}")
                return problemi
        if i < len(parti) - 1 and parte.qualificati_uscenti > len(parti[i + 1].giocatori):
            errore(f"il tabellone {parte.numero} qualifica {parte.qualificati_uscenti} giocatori, "
                   f"ma nel tabellone {parte.numero + 1} gli ammessi direttamente sono solo "
                   f"{len(parti[i + 1].giocatori)}: i qualificati entranti non possono essere di "
                   f"piu' (Volume I, capitolo I, lettera G)")
        if parte.impostazioni.get("tipo") == "integrale" and i < len(parti) - 1:
            errore(f"tabellone {parte.numero}: il sorteggio integrale si fa solo nel tabellone "
                   f"finale (Volume I, capitolo V, B)")
        q = parte.qualificati_uscenti
    return problemi


def descrivi_divisione(parti):
    """Le righe da mostrare: un tabellone per riga, scritte come in dati/torneo.txt."""
    righe = []
    for parte in parti:
        altre = ""
        if parte.qualificati_uscenti != 1 or parte is not parti[-1]:
            altre = f" ; qualificati uscenti = {parte.qualificati_uscenti}"
        for nome in ("tipo", "teste di serie"):
            if nome in parte.impostazioni:
                altre += f" ; {nome} = {parte.impostazioni[nome]}"
        sezioni = "" if e_potenza_di_due(parte.qualificati_uscenti) else \
            f"   ({parte.qualificati_uscenti} sezioni)"
        righe.append(f"  tabellone {parte.numero} = {', '.join(parte.classifiche)}{altre}"
                     f"   [{len(parte.giocatori)} giocatori"
                     + (f" + {parte.qualificati_entranti} q" if parte.qualificati_entranti else "")
                     + f"]{sezioni}")
    return righe
