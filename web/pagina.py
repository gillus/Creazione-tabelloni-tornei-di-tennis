"""La pagina nel browser (index.html): collega i pulsanti alle funzioni di tabelloni.py.

Gira dentro il browser grazie a PyScript. Come la finestra (programma/finestra.py),
non fa i conti da sola: chiama fai_tabellone() e controlla_file() di tabelloni.py e
mostra quello che scrivono. I file dei dati e dei risultati stanno nella cartella
"finta" di PyScript, che vive nella memoria del browser: niente esce dal computer.
"""

import asyncio
import contextlib
import datetime
import html
import io
import os
import traceback

from pyscript import document, when, window

import tabelloni

tabelloni.APRI_BROWSER = False  # il browser c'e' gia': la pagina da stampare si mostra qui sotto

# I quattro riquadri di testo: chiave -> file nella cartella finta.
FILE = dict(tabelloni.FILE_DATI)
FILE["tabellone"] = tabelloni.FILE_DA_CONTROLLARE
NOMI = {"giocatori": "Giocatori", "torneo": "Torneo", "classifiche": "Classifiche",
        "tabellone": "Tabellone da controllare"}

ESEMPI = {}  # il contenuto dei file come sono nel repository, per "Rimetti l'esempio"
ULTIMI_RISULTATI = {"titolo": "", "testo": ""}


# --- lettura e scrittura dei file nella cartella finta ---

def decodifica(dati):
    """Da byte a testo, come fa programma/dati.py: UTF-8, altrimenti la codifica di Windows."""
    try:
        return dati.decode("utf-8-sig")
    except UnicodeDecodeError:
        return dati.decode("cp1252", errors="replace")


def leggi(percorso):
    with open(percorso, "rb") as f:
        return decodifica(f.read())


def scrivi(percorso, testo):
    os.makedirs(os.path.dirname(percorso) or ".", exist_ok=True)
    with open(percorso, "w", encoding="utf-8") as f:
        f.write(testo if testo.endswith("\n") else testo + "\n")


def riquadro(chiave):
    return document.getElementById(f"testo-{chiave}")


def salva_riquadri(chiavi):
    """Scrive i riquadri nei file, cosi' tabelloni.py li legge come sul computer."""
    for chiave in chiavi:
        scrivi(FILE[chiave], riquadro(chiave).value)


def svuota_risultati():
    """Toglie i risultati della volta prima, per non mostrarli per sbaglio."""
    cartella = tabelloni.CARTELLA_RISULTATI
    if os.path.isdir(cartella):
        for nome in os.listdir(cartella):
            os.remove(os.path.join(cartella, nome))


def file_di_testo_dei_risultati():
    cartella = tabelloni.CARTELLA_RISULTATI
    if not os.path.isdir(cartella):
        return []
    return sorted(os.path.join(cartella, n) for n in os.listdir(cartella) if n.endswith(".txt"))


# --- cosa si vede nella pagina ---

def stato(messaggio, classe):
    elemento = document.getElementById("stato")
    elemento.textContent = messaggio
    elemento.className = f"stato {classe}"


def abilita(abilitato):
    for selettore in ("#fai", "#controlla", ".esempio"):
        for pulsante in document.querySelectorAll(selettore):
            pulsante.disabled = not abilitato


def righe_colorate(testo):
    """Il testo scritto da tabelloni.py come HTML: ERRORE in rosso, AVVISO in arancione."""
    pezzi = []
    for riga in testo.splitlines():
        classe = ""
        if "ERRORE" in riga or "ATTENZIONE" in riga:
            classe = "errore"
        elif "AVVISO" in riga:
            classe = "avviso"
        riga = html.escape(riga)
        pezzi.append(f'<span class="{classe}">{riga}</span>' if classe else riga)
    return "\n".join(pezzi)


def mostra_risultati(titolo, testo):
    ULTIMI_RISULTATI["titolo"] = titolo
    ULTIMI_RISULTATI["testo"] = testo
    document.getElementById("risultati").innerHTML = (
        f'<span class="titolo">{html.escape(titolo)}</span>\n\n' + righe_colorate(testo))
    document.getElementById("sezione-risultati").hidden = False
    document.getElementById("sezione-risultati").scrollIntoView()
    for pulsante in ("copia-tutto", "scarica-tutto"):
        document.getElementById(pulsante).disabled = False


def mostra_da_stampare():
    """Mette la pagina da stampare nel riquadro in basso e prepara i pulsanti Scarica."""
    sezione = document.getElementById("sezione-stampa")
    if not os.path.exists(tabelloni.FILE_DA_STAMPARE):
        sezione.hidden = True
        return
    document.getElementById("stampa").srcdoc = leggi(tabelloni.FILE_DA_STAMPARE)
    contenitore = document.getElementById("scarica-txt")
    contenitore.innerHTML = ""
    for percorso in file_di_testo_dei_risultati():
        pulsante = document.createElement("button")
        pulsante.textContent = f"Scarica {os.path.basename(percorso)}"
        pulsante.dataset.percorso = percorso
        contenitore.appendChild(pulsante)
    sezione.hidden = False


async def esegui(titolo, funzione, *argomenti):
    """Fa partire una funzione di tabelloni.py e mostra nella pagina quello che scrive."""
    abilita(False)
    stato("Sto lavorando: attendere qualche secondo...", "lavoro")
    await asyncio.sleep(0.05)  # lascia al browser il tempo di mostrare il messaggio
    uscita = io.StringIO()
    try:
        with contextlib.redirect_stdout(uscita):
            tutto_bene = funzione(*argomenti)
    except Exception:
        tutto_bene = False
        uscita.write("\nERRORE inatteso del programma. Questo e' il dettaglio tecnico,\n"
                     "da mandare a chi segue il programma (pulsante \"Copia tutto\" in fondo):\n\n"
                     + traceback.format_exc())
    mostra_risultati(titolo, uscita.getvalue())
    if tutto_bene:
        stato("Fatto: i risultati sono qui sotto.", "pronto")
    else:
        stato("Fatto, ma ci sono errori: vedere i risultati qui sotto.", "errore")
    abilita(True)
    return tutto_bene


# --- i pulsanti ---

@when("click", "#fai")
async def fai(event):
    salva_riquadri(("giocatori", "torneo", "classifiche"))
    svuota_risultati()
    await esegui("Tabellone", tabelloni.fai_tabellone)
    mostra_da_stampare()


@when("click", "#controlla")
async def controlla(event):
    salva_riquadri(("giocatori", "torneo", "classifiche", "tabellone"))
    await esegui("Controllo del tabellone", tabelloni.controlla_file, FILE["tabellone"])


@when("change", ".scegli")
async def scegli_file(event):
    """Un file scelto dal computer di chi usa la pagina finisce nel riquadro accanto."""
    scelto = event.target.files.item(0)
    if scelto is None:
        return
    chiave = event.target.dataset.per
    contenuto = await scelto.arrayBuffer()
    riquadro(chiave).value = decodifica(contenuto.to_bytes())
    event.target.value = ""
    stato(f"Caricato il file {scelto.name} nel riquadro \"{NOMI[chiave]}\".", "pronto")


@when("click", ".esempio")
def rimetti_esempio(event):
    chiave = event.target.dataset.per
    riquadro(chiave).value = ESEMPI[chiave]
    stato(f"Rimesso l'esempio nel riquadro \"{NOMI[chiave]}\".", "pronto")


@when("click", "#stampa-tabellone")
def stampa(event):
    window.stampaRiquadro()


@when("click", "#apri-scheda")
def apri_scheda(event):
    window.apriScheda(leggi(tabelloni.FILE_DA_STAMPARE))


@when("click", "#scarica-html")
def scarica_html(event):
    window.scaricaFile("tabellone.html", leggi(tabelloni.FILE_DA_STAMPARE), "text/html;charset=utf-8")


@when("click", "#scarica-txt")
def scarica_txt(event):
    percorso = getattr(event.target.dataset, "percorso", None)
    if percorso:
        window.scaricaFile(os.path.basename(percorso), leggi(percorso), "text/plain;charset=utf-8")


def testo_segnalazione(riquadri, risultati, adesso=None):
    """Tutto quello che serve per rifare la prova sul computer: i file dei dati e i risultati.

    riquadri   chiave -> testo del riquadro (nell'ordine in cui vanno scritti)
    risultati  (titolo, testo) dell'ultimo risultato, o None
    """
    adesso = adesso or datetime.datetime.now()
    pezzi = [f"SEGNALAZIONE DALLA PAGINA DEI TABELLONI - {adesso:%d/%m/%Y %H:%M}",
             "Per rifare la prova: copiare ogni parte nel file indicato, poi avviare il programma.",
             ""]
    for chiave, testo in riquadri.items():
        pezzi += [f"===== {FILE[chiave]} =====", testo.rstrip("\n"), ""]
    if risultati:
        titolo, testo = risultati
        pezzi += [f"===== RISULTATI ({titolo}) =====", testo.rstrip("\n"), ""]
    else:
        pezzi += ["===== RISULTATI =====", "(nessuno: non e' stato ancora premuto nessun pulsante)", ""]
    return "\n".join(pezzi)


def segnalazione():
    riquadri = {chiave: riquadro(chiave).value for chiave in ("giocatori", "torneo", "classifiche")}
    tabellone = riquadro("tabellone").value
    if tabellone.strip() and tabellone != ESEMPI.get("tabellone"):
        riquadri["tabellone"] = tabellone
    risultati = None
    if ULTIMI_RISULTATI["titolo"]:
        risultati = (ULTIMI_RISULTATI["titolo"], ULTIMI_RISULTATI["testo"])
    return testo_segnalazione(riquadri, risultati)


@when("click", "#copia-tutto")
async def copia_tutto(event):
    if await window.copiaTesto(segnalazione()):
        stato("Copiato: ora incollare il testo in una mail o in un messaggio.", "pronto")
    else:
        stato("Il browser non ha lasciato copiare: usare \"Scarica come file\".", "errore")


@when("click", "#scarica-tutto")
def scarica_tutto(event):
    window.scaricaFile("segnalazione.txt", segnalazione(), "text/plain;charset=utf-8")


# --- all'apertura della pagina ---

def avvia():
    for chiave, percorso in FILE.items():
        ESEMPI[chiave] = leggi(percorso)
        riquadro(chiave).value = ESEMPI[chiave]
    abilita(True)
    stato("Pronto. Controllare i dati e premere \"Fai il tabellone\".", "pronto")


avvia()
