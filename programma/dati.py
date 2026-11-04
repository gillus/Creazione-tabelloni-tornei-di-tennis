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
IMPOSTAZIONI_FACOLTATIVE = ("date", "tipo", "qualificati entranti", "qualificati uscenti",
                            "teste di serie")
# Valori ammessi per le impostazioni con una scelta tra poche parole.
IMPOSTAZIONI_A_SCELTA = {"tipo": ("selezione", "estrazione", "integrale")}
# "turno 1", "turno 2"...: la scala di un tabellone di selezione scritta dal giudice arbitro.
MASSIMO_TURNO = 12
# "tabellone 1", "tabellone 2"...: i tabelloni collegati.
MASSIMO_TABELLONI = 9
# Impostazioni che devono essere un numero intero, e il numero piu' piccolo ammesso.
IMPOSTAZIONI_NUMERICHE = {"qualificati entranti": 0, "qualificati uscenti": 1, "teste di serie": 0}


@dataclass
class Problema:
    gravita: str  # ERRORE oppure AVVISO
    file: str  # "" quando il problema non riguarda un file
    riga: int  # 0 quando il problema riguarda il file intero
    messaggio: str

    def __str__(self):
        if not self.file:
            return f"{self.gravita}: {self.messaggio}"
        dove = self.file if self.riga == 0 else f"{self.file}, riga {self.riga}"
        return f"{self.gravita} - {dove}: {self.messaggio}"


@dataclass
class Giocatore:
    codice: str
    classifica: str
    circolo: str
    riga: int = 0

    @property
    def chiave(self):
        """Il nome (o codice) scritto in modo da confrontarlo: maiuscole e spazi non contano."""
        return chiave_del_nome(self.codice)

    @property
    def chiave_circolo(self):
        """Il circolo scritto in modo da confrontarlo: maiuscole e spazi non contano."""
        return " ".join(self.circolo.split()).upper()


def chiave_del_nome(testo):
    return " ".join(testo.split()).upper()


def trova_giocatore(testo, per_chiave):
    """Il giocatore il cui nome (o codice) e' all'inizio del testo, e il resto del testo.

    per_chiave  chiave del nome -> giocatore (vedi Giocatore.chiave).
    Il nome puo' avere piu' parole ("ROSSI Mario 3.2 TC Collina"): si prova prima
    con piu' parole possibile. Se non si trova nessuno: None e il testo intero."""
    parole = testo.split()
    for quante in range(len(parole), 0, -1):
        giocatore = per_chiave.get(" ".join(parole[:quante]).upper())
        if giocatore is not None:
            return giocatore, " ".join(parole[quante:])
    return None, testo


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
                f"servono 3 dati separati da punto e virgola (nome ; classifica ; circolo), "
                f"invece ce ne sono {len(parti)}: \"{riga}\""))
            continue

        codice, classifica, circolo = parti
        codice = " ".join(codice.split())  # "ROSSI   Mario" -> "ROSSI Mario"
        classifica = normalizza_classifica(classifica)
        riga_ok = True

        if not codice:
            problemi.append(Problema(ERRORE, percorso, numero, "manca il nome del giocatore"))
            riga_ok = False
        elif codice.upper() in codici_visti:
            problemi.append(Problema(
                ERRORE, percorso, numero,
                f"il nome {codice} e' gia' usato alla riga {codici_visti[codice.upper()]}: "
                f"se sono due giocatori diversi, aggiungere qualcosa per distinguerli "
                f"(per esempio la data di nascita o \"(2)\")"))
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


MESI = ("gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto",
        "settembre", "ottobre", "novembre", "dicembre")
_GIORNI_DEL_MESE = (31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


def giorni_del_mese(mese, anno=None):
    """Quanti giorni ha il mese (1-12); senza l'anno, febbraio ne ha 29."""
    if mese == 2 and anno is not None:
        bisestile = anno % 4 == 0 and (anno % 100 != 0 or anno % 400 == 0)
        return 29 if bisestile else 28
    return _GIORNI_DEL_MESE[mese - 1]


def _cambia_anno(mese_prima, mese_dopo):
    """Da dicembre a gennaio (o simili) un torneo passa all'anno dopo."""
    return mese_dopo is not None and mese_prima - mese_dopo >= 6


def date_del_testo(testo):
    """Le date scritte nel testo, in ordine: elenco di (giorno, mese, anno o None).

    Capisce "dal 1 al 10 ottobre 2026", "dal 28 febbraio al 3 marzo", "1-10 ottobre",
    "01/11/2026", "1.11.26". Restituisce anche i giorni scritti senza mese
    (mese None), per poterli segnalare."""
    import re
    date = []
    giorni = []  # giorni letti che aspettano il loro mese
    # "1/11", "1.11.26", "1-11-2026" sono date; "1-10" (senza anno) e' dal giorno 1 al 10.
    parole = re.findall(r"\d{1,2}[/.]\d{1,2}(?:[/.]\d{2,4})?|\d{1,2}-\d{1,2}-\d{2,4}|\d+|[a-zàèéìòù]+",
                        testo.lower())
    for indice, parola in enumerate(parole):
        numerica = re.fullmatch(r"(\d{1,2})[/.\-](\d{1,2})(?:[/.\-](\d{2,4}))?", parola)
        if numerica:
            giorno, mese, anno = numerica.groups()
            anno = int(anno) if anno else None
            if anno is not None and anno < 100:
                anno += 2000
            date.append((int(giorno), int(mese), anno))
        elif parola.isdigit() and len(parola) <= 2:
            giorni.append(int(parola))
        elif parola[:3] in [m[:3] for m in MESI] and (parola in MESI or len(parola) == 3):
            mese = [m[:3] for m in MESI].index(parola[:3]) + 1
            anno = None
            if indice + 1 < len(parole) and parole[indice + 1].isdigit() \
                    and len(parole[indice + 1]) == 4:
                anno = int(parole[indice + 1])
            date += [(giorno, mese, anno) for giorno in giorni]
            if not giorni:
                date.append((None, mese, anno))
            giorni = []
    date += [(giorno, None, None) for giorno in giorni]
    # Un anno scritto solo in fondo ("dal 28 dicembre al 3 gennaio 2027") vale per
    # tutte: per le date prima, l'anno e' lo stesso (o quello prima, se si passa da
    # fine anno all'inizio dell'anno dopo).
    anno_noto = None
    for i in range(len(date) - 1, -1, -1):
        giorno, mese, anno = date[i]
        if anno is not None:
            anno_noto, mese_noto = anno, mese
        elif anno_noto is not None and mese is not None:
            anno_noto = anno_noto - 1 if _cambia_anno(mese, mese_noto) else anno_noto
            mese_noto = mese
            date[i] = (giorno, mese, anno_noto)
    return date


def controlla_date(testo):
    """Controlla che le date del torneo esistano davvero (niente 31 novembre) e che la
    fine non venga prima dell'inizio. Restituisce un elenco di (gravita, messaggio)."""
    problemi = []
    date = date_del_testo(testo)
    complete = []
    for giorno, mese, anno in date:
        if mese is None:
            problemi.append((AVVISO, f"nelle date c'e' il giorno {giorno} senza il mese: "
                                     f"scrivere per esempio \"dal 1 al 10 novembre\""))
        elif not 1 <= mese <= 12:
            problemi.append((ERRORE, f"nelle date il mese {mese} non esiste"))
        elif giorno is None:
            problemi.append((AVVISO, f"nelle date manca il giorno di {MESI[mese - 1]}"))
        elif not 1 <= giorno <= giorni_del_mese(mese, anno):
            quale = f"{giorno} {MESI[mese - 1]}" + (f" {anno}" if anno else "")
            problemi.append((ERRORE, f"la data {quale} non esiste ({MESI[mese - 1]} ha "
                                     f"{giorni_del_mese(mese, anno)} giorni)"))
        else:
            complete.append((giorno, mese, anno))
    if not problemi:
        for (g1, m1, a1), (g2, m2, a2) in zip(complete, complete[1:]):
            if (a1 is None) == (a2 is None) and (a1 or 0, m1, g1) > (a2 or 0, m2, g2) \
                    and not (a1 is None and _cambia_anno(m1, m2)):
                problemi.append((ERRORE, f"nelle date il {g2} {MESI[m2 - 1]} viene prima del "
                                         f"{g1} {MESI[m1 - 1]}: la fine e' prima dell'inizio"))
    return problemi


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
        nome = " ".join(nome.split()).lower()
        valore = valore.strip()
        turno_della_scala = nome.startswith("turno ") and nome[6:].isdigit() \
            and 1 <= int(nome[6:]) <= MASSIMO_TURNO
        # "tabellone 1 = 4.NC", "tabellone 2 = 4.6, 4.5 ; qualificati uscenti = 4":
        # i tabelloni collegati (li legge programma.collegati).
        riga_di_tabellone = nome.startswith("tabellone ") and nome[10:].isdigit() \
            and 1 <= int(nome[10:]) <= MASSIMO_TABELLONI
        turno_della_scala = turno_della_scala or riga_di_tabellone
        if turno_della_scala and nome not in torneo.impostazioni and valore:
            torneo.impostazioni[nome] = valore
        elif nome not in conosciute and not turno_della_scala:
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
        elif nome in IMPOSTAZIONI_A_SCELTA:
            if valore.lower() not in IMPOSTAZIONI_A_SCELTA[nome]:
                problemi.append(Problema(
                    ERRORE, percorso, numero,
                    f"l'impostazione \"{nome}\" puo' essere solo: "
                    f"{', '.join(IMPOSTAZIONI_A_SCELTA[nome])}; invece e' \"{valore}\""))
            else:
                torneo.impostazioni[nome] = valore.lower()
        elif nome in IMPOSTAZIONI_NUMERICHE:
            minimo = IMPOSTAZIONI_NUMERICHE[nome]
            if not valore.isdigit() or int(valore) < minimo:
                problemi.append(Problema(
                    ERRORE, percorso, numero,
                    f"l'impostazione \"{nome}\" deve essere un numero intero, almeno {minimo}: \"{valore}\""))
            else:
                torneo.impostazioni[nome] = int(valore)
        else:
            if nome == "date":
                for gravita, messaggio in controlla_date(valore):
                    problemi.append(Problema(gravita, percorso, numero, messaggio))
            torneo.impostazioni[nome] = valore

    for nome in IMPOSTAZIONI_OBBLIGATORIE:
        if nome not in torneo.impostazioni:
            problemi.append(Problema(ERRORE, percorso, 0,
                                     f"manca l'impostazione obbligatoria \"{nome}\""))
    return torneo, problemi
