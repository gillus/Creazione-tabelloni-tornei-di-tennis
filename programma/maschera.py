"""La maschera per compilare il torneo: campi e menu' a tendina al posto del testo.

La maschera non sostituisce il file dati/torneo.txt: lo scrive. Qui ci sono i
conti comuni alla finestra (programma/finestra.py) e alla pagina nel browser
(web/pagina.py):
  - dal testo del torneo ai campi della maschera (maschera_dal_testo);
  - dai campi al testo (testo_dalla_maschera), con le righe che la maschera non
    conosce (per esempio la scala, "turno 3 = ...") lasciate come sono;
  - il controllo dei campi (problemi_della_maschera), per esempio le date.

I tabelloni collegati si scrivono dal primo (classifiche piu' basse) all'ultimo:
di ognuno si sceglie solo la classifica piu' alta; la piu' bassa e' quella
subito sopra il tabellone prima (il primo comincia dalla classifica piu' bassa).
L'ultimo tabellone arriva sempre fino alla classifica piu' alta.
"""

import datetime
import re
from dataclasses import dataclass, field

from programma.calcoli import NON_CLASSIFICATO
from programma.collegati import categoria, nome_categoria
from programma.dati import MESI, controlla_date, date_del_testo, giorni_del_mese

GARE = ("Singolare maschile", "Singolare femminile", "Doppio maschile", "Doppio femminile",
        "Doppio misto")
# Tipo del tabellone: valore nel file -> come si legge nel menu'.
TIPI = {"": "deciso dal programma", "selezione": "selezione", "estrazione": "estrazione",
        "integrale": "sorteggio integrale (solo tabellone finale)"}
MASSIMO_NUMERO = 32  # i numeri nei menu' (teste di serie, qualificati) arrivano fin qui
MASSIMO_TABELLONI = 6
AUTOMATICO = None  # nei menu': "lo propone il programma"

_NOMI_CONOSCIUTI = ("nome", "gara", "date", "tipo", "qualificati entranti",
                    "qualificati uscenti", "teste di serie")


@dataclass
class TabelloneDellaMaschera:
    piu_alta: str = ""  # la classifica piu' alta che gioca in questo tabellone
    tipo: str = ""  # "" = deciso dal programma
    teste_di_serie: object = AUTOMATICO  # numero, oppure AUTOMATICO
    qualificati_uscenti: object = AUTOMATICO  # numero, oppure AUTOMATICO


@dataclass
class Maschera:
    nome: str = ""
    gara: str = ""
    inizio: object = None  # datetime.date, oppure None
    fine: object = None
    date_scritte: str = ""  # le date scritte a mano, se non si capiscono (si lasciano cosi')
    qualificati_entranti: int = 0
    # Divisione in tabelloni scelta dal programma (nessuna riga "tabellone N"):
    # allora conta solo tabelloni[0], per le impostazioni del torneo intero.
    divisione_automatica: bool = True
    tabelloni: list = field(default_factory=lambda: [TabelloneDellaMaschera()])
    intestazione: list = field(default_factory=list)  # le righe di commento in cima
    altre_righe: list = field(default_factory=list)  # righe che la maschera non conosce


# --- date ---

def testo_delle_date(inizio, fine):
    """(1/11/2026, 10/11/2026) -> "dal 1 al 10 novembre 2026"."""
    if inizio is None and fine is None:
        return ""
    if inizio is None or fine is None or inizio == fine:
        giorno = inizio or fine
        return f"{giorno.day} {MESI[giorno.month - 1]} {giorno.year}"
    if (inizio.year, inizio.month) == (fine.year, fine.month):
        return f"dal {inizio.day} al {fine.day} {MESI[fine.month - 1]} {fine.year}"
    if inizio.year == fine.year:
        return (f"dal {inizio.day} {MESI[inizio.month - 1]} al {fine.day} "
                f"{MESI[fine.month - 1]} {fine.year}")
    return (f"dal {inizio.day} {MESI[inizio.month - 1]} {inizio.year} al {fine.day} "
            f"{MESI[fine.month - 1]} {fine.year}")


def date_dal_testo(testo, anno_se_manca=None):
    """"dal 1 al 10 novembre 2026" -> (inizio, fine) come datetime.date; None se non si
    capisce (le date restano scritte cosi' come sono)."""
    if not testo.strip() or controlla_date(testo):
        return None
    date = date_del_testo(testo)
    if not 1 <= len(date) <= 2 or any(g is None or m is None for g, m, _ in date):
        return None
    anno_se_manca = anno_se_manca or datetime.date.today().year
    try:
        trovate = [datetime.date(a or anno_se_manca, m, g) for g, m, a in date]
    except ValueError:
        return None
    return trovate[0], trovate[-1]


def data_da_parti(giorno, mese, anno):
    """Dai tre menu' della finestra (giorno, mese scritto in lettere, anno) a una data.
    Restituisce (data, messaggio di errore): tutto vuoto -> (None, "")."""
    if not str(giorno).strip() and not str(mese).strip():
        return None, ""
    try:
        g, a = int(str(giorno).strip()), int(str(anno).strip())
    except ValueError:
        return None, "scegliere il giorno, il mese e l'anno"
    mese = str(mese).strip().lower()
    if mese not in MESI:
        return None, "scegliere il mese"
    m = MESI.index(mese) + 1
    if not 1 <= g <= giorni_del_mese(m, a):
        return None, (f"il {g} {mese} {a} non esiste ({mese} {a} ha "
                      f"{giorni_del_mese(m, a)} giorni)")
    return datetime.date(a, m, g), ""


# --- classifiche dei tabelloni ---

def classifiche_dei_tabelloni(maschera, classifiche):
    """Le classifiche di ogni tabellone (dalla piu' alta), dal primo all'ultimo.

    classifiche  l'elenco di dati/classifiche.txt, dalla piu' alta alla piu' bassa."""
    risultato = []
    sotto = len(classifiche)  # indice della classifica piu' bassa non ancora usata, +1
    for numero, tabellone in enumerate(maschera.tabelloni):
        ultimo = numero == len(maschera.tabelloni) - 1
        alta = 0 if ultimo or tabellone.piu_alta not in classifiche \
            else classifiche.index(tabellone.piu_alta)
        alta = min(alta, sotto)
        risultato.append(classifiche[alta:sotto])
        sotto = alta
    return risultato


def scelte_della_piu_alta(maschera, numero, classifiche):
    """Le classifiche che si possono scegliere come "fino a" per il tabellone numero
    (da 0): dalla piu' bassa ancora libera in su, lasciando almeno una classifica a
    ognuno dei tabelloni che seguono."""
    sotto = len(classifiche)
    for tabellone in maschera.tabelloni[:numero]:
        if tabellone.piu_alta in classifiche:
            sotto = min(sotto, classifiche.index(tabellone.piu_alta))
    dopo = len(maschera.tabelloni) - numero - 1
    return list(reversed(classifiche[dopo:sotto]))


def solo_non_classificati(elenco):
    return bool(elenco) and all(c == NON_CLASSIFICATO for c in elenco)


def un_tabellone_per_categoria(classifiche, presenti):
    """La divisione "un tabellone per categoria" (non classificati, quarta, terza,
    seconda...) con le classifiche dei giocatori iscritti: le piu' alte di ogni tabellone."""
    gruppi = []
    for classifica in reversed([c for c in classifiche if c in presenti]):
        if gruppi and categoria(gruppi[-1][-1]) == categoria(classifica):
            gruppi[-1].append(classifica)
        else:
            gruppi.append([classifica])
    return [g[-1] for g in gruppi][:MASSIMO_TABELLONI]


def descrivi_tabellone(elenco, conteggio=None):
    """"da 4.6 a 4.1 (4a categoria) - 12 giocatori", per mostrare nella maschera chi gioca.

    conteggio  giocatori per classifica (giocatori_per_classifica), se si conoscono."""
    if conteggio:
        elenco = [c for c in elenco if conteggio.get(c)] or elenco
    if not elenco:
        return "nessuna classifica"
    categorie = []
    for c in elenco:
        if nome_categoria(c) not in categorie:
            categorie.append(nome_categoria(c))
    testo = elenco[0] if len(elenco) == 1 else f"da {elenco[-1]} a {elenco[0]}"
    testo += f" ({', '.join(reversed(categorie))})"
    if conteggio is not None:
        quanti = sum(conteggio.get(c, 0) for c in elenco)
        testo += f" - {quanti} giocator{'e' if quanti == 1 else 'i'}"
    return testo


# --- dal testo alla maschera ---

def _numero(testo):
    testo = testo.strip()
    return int(testo) if testo.isdigit() else AUTOMATICO


def maschera_dal_testo(testo, classifiche):
    """I campi della maschera dal testo di dati/torneo.txt. Le righe che la maschera non
    conosce restano in altre_righe e si riscrivono uguali."""
    maschera = Maschera()
    impostazioni = {}
    righe_tabellone = {}
    in_cima = True
    for riga in testo.splitlines():
        pulita = riga.strip()
        if in_cima and (not pulita or pulita.startswith("#")):
            maschera.intestazione.append(riga.rstrip())
            continue
        in_cima = False
        if not pulita or pulita.startswith("#"):
            continue  # i commenti in mezzo li riscrive la maschera
        if "=" not in pulita:
            maschera.altre_righe.append(pulita)
            continue
        nome, valore = pulita.split("=", 1)
        nome = " ".join(nome.split()).lower()
        trovato = re.fullmatch(r"tabellone (\d+)", nome)
        if trovato:
            righe_tabellone[int(trovato.group(1))] = valore.strip()
        elif nome in _NOMI_CONOSCIUTI and nome not in impostazioni:
            impostazioni[nome] = valore.strip()
        else:
            maschera.altre_righe.append(pulita)
    while maschera.intestazione and not maschera.intestazione[-1].strip():
        maschera.intestazione.pop()

    maschera.nome = impostazioni.get("nome", "")
    maschera.gara = impostazioni.get("gara", "")
    date = impostazioni.get("date", "")
    trovate = date_dal_testo(date)
    if trovate:
        maschera.inizio, maschera.fine = trovate
    else:
        maschera.date_scritte = date
    maschera.qualificati_entranti = _numero(impostazioni.get("qualificati entranti", "")) or 0

    if not righe_tabellone:
        maschera.divisione_automatica = True
        unico = maschera.tabelloni[0]
        unico.tipo = impostazioni.get("tipo", "").lower() if impostazioni.get("tipo", "").lower() in TIPI else ""
        unico.teste_di_serie = _numero(impostazioni.get("teste di serie", ""))
        unico.qualificati_uscenti = _numero(impostazioni.get("qualificati uscenti", ""))
        return maschera

    maschera.divisione_automatica = False
    maschera.tabelloni = []
    for numero in sorted(righe_tabellone)[:MASSIMO_TABELLONI]:
        elenco, *altre = righe_tabellone[numero].split(";")
        scritte = ["".join(c.split()).replace(",", ".").upper() for c in elenco.split(",")]
        scritte = [c for c in scritte if c in classifiche]
        tabellone = TabelloneDellaMaschera(
            piu_alta=min(scritte, key=classifiche.index) if scritte else "")
        for pezzo in altre:
            if "=" not in pezzo:
                continue
            chiave, valore = (" ".join(p.split()).lower() for p in pezzo.split("=", 1))
            if chiave == "tipo" and valore in TIPI:
                tabellone.tipo = valore
            elif chiave == "teste di serie":
                tabellone.teste_di_serie = _numero(valore)
            elif chiave == "qualificati uscenti":
                tabellone.qualificati_uscenti = _numero(valore)
        maschera.tabelloni.append(tabellone)
    # L'ultimo tabellone arriva sempre fino alla classifica piu' alta: la sua non si sceglie.
    # Le impostazioni scritte per il torneo intero valgono per lui.
    ultimo = maschera.tabelloni[-1]
    ultimo.piu_alta = ""
    if ultimo.qualificati_uscenti is AUTOMATICO:
        ultimo.qualificati_uscenti = _numero(impostazioni.get("qualificati uscenti", ""))
    if not ultimo.tipo and impostazioni.get("tipo", "").lower() in TIPI:
        ultimo.tipo = impostazioni.get("tipo", "").lower()
    return maschera


# --- dalla maschera al testo ---

INTESTAZIONE_BREVE = [
    "# IMPOSTAZIONI DEL TORNEO",
    "# =======================",
    "#",
    "# Scritto con la maschera \"Compila il torneo\": si puo' cambiare li' oppure qui.",
    "# Le spiegazioni complete di ogni riga sono nel file di esempio dati/torneo.txt.",
]


def testo_dalla_maschera(maschera, classifiche, presenti=None):
    """Il testo di dati/torneo.txt con i campi della maschera.

    presenti  le classifiche dei giocatori iscritti (se si conoscono, per esempio le
              chiavi di giocatori_per_classifica): nelle righe "tabellone N" si scrivono
              solo quelle, perche' il tabellone sia piu' chiaro."""
    righe = list(maschera.intestazione or INTESTAZIONE_BREVE)
    righe.append("")
    righe.append(f"nome = {maschera.nome.strip()}")
    righe.append(f"gara = {maschera.gara.strip()}")
    date = testo_delle_date(maschera.inizio, maschera.fine) or maschera.date_scritte.strip()
    if date:
        righe.append(f"date = {date}")
    if maschera.qualificati_entranti:
        righe.append(f"qualificati entranti = {maschera.qualificati_entranti}")

    if maschera.divisione_automatica:
        unico = maschera.tabelloni[0]
        if unico.tipo:
            righe.append(f"tipo = {unico.tipo}")
        if unico.qualificati_uscenti is not AUTOMATICO:
            righe.append(f"qualificati uscenti = {unico.qualificati_uscenti}")
        if unico.teste_di_serie is not AUTOMATICO:
            righe.append(f"teste di serie = {unico.teste_di_serie}")
    else:
        righe.append("")
        righe.append("# Tabelloni collegati, dal primo (classifiche piu' basse) all'ultimo:")
        for numero, (tabellone, elenco) in enumerate(
                zip(maschera.tabelloni, classifiche_dei_tabelloni(maschera, classifiche)), start=1):
            if presenti is not None:
                elenco = [c for c in elenco if c in presenti] or elenco
            pezzi = [", ".join(elenco)]
            if tabellone.tipo:
                pezzi.append(f"tipo = {tabellone.tipo}")
            if tabellone.teste_di_serie is not AUTOMATICO and not solo_non_classificati(elenco):
                pezzi.append(f"teste di serie = {tabellone.teste_di_serie}")
            if tabellone.qualificati_uscenti is not AUTOMATICO:
                pezzi.append(f"qualificati uscenti = {tabellone.qualificati_uscenti}")
            righe.append(f"tabellone {numero} = " + " ; ".join(pezzi))

    if maschera.altre_righe:
        righe.append("")
        righe.append("# Righe scritte a mano (la maschera le lascia come sono):")
        righe += maschera.altre_righe
    return "\n".join(righe) + "\n"


# --- controllo ---

def problemi_della_maschera(maschera, classifiche):
    """Le cose da correggere prima di salvare: elenco di frasi (vuoto se va tutto bene)."""
    problemi = []
    if not maschera.nome.strip():
        problemi.append("manca il nome del torneo")
    if not maschera.gara.strip():
        problemi.append("manca la gara (per esempio Singolare maschile)")
    if (maschera.inizio is None) != (maschera.fine is None) and not maschera.date_scritte:
        problemi.append("scrivere sia il primo sia l'ultimo giorno del torneo")
    if maschera.inizio and maschera.fine and maschera.fine < maschera.inizio:
        problemi.append("l'ultimo giorno del torneo viene prima del primo")
    if maschera.date_scritte:
        problemi += [m for _, m in controlla_date(maschera.date_scritte)]
    if not maschera.divisione_automatica:
        quanti = len(maschera.tabelloni)
        for numero, elenco in enumerate(classifiche_dei_tabelloni(maschera, classifiche), start=1):
            if not elenco:
                problemi.append(f"il tabellone {numero} non ha classifiche: scegliere la "
                                f"classifica piu' alta dei tabelloni prima")
        for numero, tabellone in enumerate(maschera.tabelloni, start=1):
            if tabellone.tipo == "integrale" and numero < quanti:
                problemi.append(f"il sorteggio integrale si fa solo nell'ultimo tabellone "
                                f"(il tabellone finale), non nel tabellone {numero}")
    return problemi


def giocatori_per_classifica(testo_giocatori):
    """Quanti giocatori ci sono per ogni classifica nel testo del file dei giocatori
    (per mostrare nella maschera chi gioca in ogni tabellone)."""
    from programma.dati import normalizza_classifica
    conteggio = {}
    for riga in testo_giocatori.splitlines():
        riga = riga.strip()
        if riga and not riga.startswith("#") and riga.count(";") == 2:
            classifica = normalizza_classifica(riga.split(";")[1])
            conteggio[classifica] = conteggio.get(classifica, 0) + 1
    return conteggio


def riepilogo_iscritti(conteggio, classifiche):
    """Quanti iscritti per classifica, una riga per categoria, dalla piu' bassa
    (come i tabelloni nella maschera):
        "non classificati (6): 4.NC: 6"
        "4a categoria (18): 4.6: 3 · 4.5: 3 · ... · 4.1: 3"
    In fondo le classifiche che non sono in dati/classifiche.txt (vanno corrette)
    e il totale. Restituisce un elenco di righe (vuoto se non c'e' nessun iscritto)."""
    if not conteggio:
        return []
    righe = []
    gruppo, pezzi, quanti = None, [], 0
    for classifica in reversed(classifiche):
        if not conteggio.get(classifica):
            continue
        if gruppo is not None and nome_categoria(classifica) != gruppo:
            righe.append(f"{gruppo} ({quanti}): " + " · ".join(pezzi))
            pezzi, quanti = [], 0
        gruppo = nome_categoria(classifica)
        pezzi.append(f"{classifica}: {conteggio[classifica]}")
        quanti += conteggio[classifica]
    if pezzi:
        righe.append(f"{gruppo} ({quanti}): " + " · ".join(pezzi))
    sconosciute = sorted(c for c in conteggio if c not in classifiche)
    if sconosciute:
        righe.append("classifiche sconosciute, da correggere: "
                     + " · ".join(f"{c or '(vuota)'}: {conteggio[c]}" for c in sconosciute))
    righe.append(f"in tutto: {sum(conteggio.values())} iscritti")
    return righe
