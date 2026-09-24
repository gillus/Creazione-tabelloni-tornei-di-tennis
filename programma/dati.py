"""Lettura dei file di testo con classifiche, giocatori e impostazioni del torneo.

Ogni funzione di lettura restituisce i dati letti e un elenco di problemi.
Un problema e' un "errore" (il file va corretto) oppure un "avviso"
(il programma puo' andare avanti, ma conviene controllare).
"""

from dataclasses import dataclass, field

ERRORE = "ERRORE"
AVVISO = "AVVISO"

# Impostazioni del torneo che il programma conosce, e quali sono obbligatorie.
IMPOSTAZIONI_OBBLIGATORIE = ("nome", "gara")
IMPOSTAZIONI_FACOLTATIVE = ("date",)


@dataclass
class Problema:
    gravita: str  # ERRORE oppure AVVISO
    file: str
    riga: int  # 0 quando il problema riguarda il file intero
    messaggio: str

    def __str__(self):
        dove = self.file if self.riga == 0 else f"{self.file}, riga {self.riga}"
        return f"{self.gravita} - {dove}: {self.messaggio}"


@dataclass
class Giocatore:
    codice: str
    classifica: str
    circolo: str
    riga: int = 0

    @property
    def chiave_circolo(self):
        """Il circolo scritto in modo da confrontarlo: maiuscole e spazi non contano."""
        return " ".join(self.circolo.split()).upper()


@dataclass
class Torneo:
    impostazioni: dict = field(default_factory=dict)


def leggi_righe(percorso):
    """Legge un file di testo e restituisce le righe utili, con il loro numero.

    Salta le righe vuote e i commenti (che cominciano con #).
    Accetta i file salvati sia in UTF-8 sia con la codifica classica di Windows.
    """
    with open(percorso, "rb") as f:
        contenuto = f.read()
    try:
        testo = contenuto.decode("utf-8-sig")
    except UnicodeDecodeError:
        testo = contenuto.decode("cp1252", errors="replace")
    righe = []
    for numero, riga in enumerate(testo.splitlines(), start=1):
        riga = riga.strip()
        if riga and not riga.startswith("#"):
            righe.append((numero, riga))
    return righe


def normalizza_classifica(testo):
    """Scrive la classifica sempre allo stesso modo: '3,4' -> '3.4', '4.nc' -> '4.NC'."""
    return "".join(testo.split()).replace(",", ".").upper()


def leggi_classifiche(percorso):
    """Restituisce l'elenco delle classifiche, dalla piu' alta alla piu' bassa."""
    classifiche = []
    problemi = []
    for numero, riga in leggi_righe(percorso):
        classifica = normalizza_classifica(riga)
        if classifica in classifiche:
            problemi.append(Problema(ERRORE, percorso, numero,
                                     f"la classifica {classifica} e' scritta due volte"))
        else:
            classifiche.append(classifica)
    if not classifiche:
        problemi.append(Problema(ERRORE, percorso, 0, "non c'e' nessuna classifica"))
    return classifiche, problemi


def leggi_giocatori(percorso, classifiche):
    """Legge l'elenco dei giocatori e controlla che ogni riga sia scritta bene."""
    giocatori = []
    problemi = []
    codici_visti = {}  # codice in maiuscolo -> riga dove compare la prima volta

    for numero, riga in leggi_righe(percorso):
        parti = [parte.strip() for parte in riga.split(";")]
        if len(parti) != 3:
            problemi.append(Problema(
                ERRORE, percorso, numero,
                f"servono 3 dati separati da punto e virgola (codice ; classifica ; circolo), "
                f"invece ce ne sono {len(parti)}: \"{riga}\""))
            continue

        codice, classifica, circolo = parti
        classifica = normalizza_classifica(classifica)
        riga_ok = True

        if not codice:
            problemi.append(Problema(ERRORE, percorso, numero, "manca il codice del giocatore"))
            riga_ok = False
        elif codice.upper() in codici_visti:
            problemi.append(Problema(
                ERRORE, percorso, numero,
                f"il codice {codice} e' gia' usato alla riga {codici_visti[codice.upper()]}"))
            riga_ok = False
        else:
            codici_visti[codice.upper()] = numero

        if not classifica:
            problemi.append(Problema(ERRORE, percorso, numero,
                                     f"manca la classifica del giocatore {codice}"))
            riga_ok = False
        elif classifica not in classifiche:
            problemi.append(Problema(
                ERRORE, percorso, numero,
                f"la classifica \"{classifica}\" del giocatore {codice} non esiste "
                f"(quelle valide sono in dati/classifiche.txt)"))
            riga_ok = False

        if not circolo:
            problemi.append(Problema(ERRORE, percorso, numero,
                                     f"manca il circolo del giocatore {codice}"))
            riga_ok = False

        if riga_ok:
            giocatori.append(Giocatore(codice, classifica, circolo, numero))

    if not giocatori and not problemi:
        problemi.append(Problema(ERRORE, percorso, 0, "non c'e' nessun giocatore"))
    return giocatori, problemi


def leggi_torneo(percorso):
    """Legge le impostazioni del torneo (righe 'nome = valore')."""
    torneo = Torneo()
    problemi = []
    conosciute = IMPOSTAZIONI_OBBLIGATORIE + IMPOSTAZIONI_FACOLTATIVE

    for numero, riga in leggi_righe(percorso):
        if "=" not in riga:
            problemi.append(Problema(
                ERRORE, percorso, numero,
                f"la riga deve essere nella forma 'nome = valore': \"{riga}\""))
            continue
        nome, valore = riga.split("=", 1)
        nome = nome.strip().lower()
        valore = valore.strip()
        if nome not in conosciute:
            problemi.append(Problema(
                AVVISO, percorso, numero,
                f"l'impostazione \"{nome}\" non e' conosciuta e viene ignorata "
                f"(quelle valide sono: {', '.join(conosciute)})"))
        elif nome in torneo.impostazioni:
            problemi.append(Problema(ERRORE, percorso, numero,
                                     f"l'impostazione \"{nome}\" e' scritta due volte"))
        elif not valore:
            problemi.append(Problema(ERRORE, percorso, numero,
                                     f"manca il valore dell'impostazione \"{nome}\""))
        else:
            torneo.impostazioni[nome] = valore

    for nome in IMPOSTAZIONI_OBBLIGATORIE:
        if nome not in torneo.impostazioni:
            problemi.append(Problema(ERRORE, percorso, 0,
                                     f"manca l'impostazione obbligatoria \"{nome}\""))
    return torneo, problemi
