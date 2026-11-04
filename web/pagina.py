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
from programma import maschera as m
from programma.dati import normalizza_classifica
from programma.excel import ErroreExcel, giocatori_da_excel

tabelloni.APRI_BROWSER = False  # il browser c'e' gia': la pagina da stampare si mostra qui sotto

# I quattro riquadri di testo: chiave -> file nella cartella finta.
FILE = dict(tabelloni.FILE_DATI)
FILE["tabellone"] = tabelloni.FILE_DA_CONTROLLARE
NOMI = {"giocatori": "Giocatori", "torneo": "Torneo", "classifiche": "Classifiche",
        "tabellone": "Tabellone da controllare"}

ESEMPI = {}  # il contenuto dei file come sono nel repository, per "Rimetti l'esempio"
ULTIMI_RISULTATI = {"titolo": "", "testo": ""}
MASCHERA = {"maschera": None}  # i campi della maschera "Compila il torneo"


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


# --- la maschera "Compila il torneo" ---
#
# La maschera scrive il riquadro "Torneo": ogni volta che si cambia un campo, il
# testo del riquadro si rifa'. Se invece si scrive nel riquadro (o si carica un
# file), la maschera si rilegge dal testo.

def classifiche_dal_testo(testo):
    """Le classifiche del riquadro "Classifiche", dalla piu' alta (come leggi_classifiche)."""
    classifiche = []
    for riga in testo.splitlines():
        riga = riga.strip()
        if riga and not riga.startswith("#"):
            c = normalizza_classifica(riga)
            if c not in classifiche:
                classifiche.append(c)
    return classifiche


def _scelta(identificatore, valori, scelto, disabilitato=False):
    """Un menu' a tendina: valori e' un elenco di (valore, testo)."""
    opzioni = "".join(
        f'<option value="{html.escape(str(v))}"{" selected" if str(v) == str(scelto) else ""}>'
        f'{html.escape(t)}</option>' for v, t in valori)
    return (f'<select id="{identificatore}"{" disabled" if disabilitato else ""}>'
            f'{opzioni}</select>')


def _valore_numero(numero):
    return "" if numero is m.AUTOMATICO else str(numero)


def html_della_maschera(maschera, classifiche, conteggio):
    """Il contenuto HTML della maschera (i campi hanno id che cominciano con "m-")."""
    e = html.escape
    pezzi = ['<div class="campi">']
    pezzi.append(f'<label for="m-nome">Nome del torneo</label>'
                 f'<input id="m-nome" type="text" value="{e(maschera.nome)}">')
    pezzi.append(f'<label for="m-gara">Gara</label><input id="m-gara" type="text" list="m-gare" '
                 f'value="{e(maschera.gara)}"><datalist id="m-gare">'
                 + "".join(f'<option value="{e(g)}">' for g in m.GARE) + '</datalist>')
    for chiave, etichetta in (("inizio", "Primo giorno"), ("fine", "Ultimo giorno")):
        data = getattr(maschera, chiave)
        pezzi.append(f'<label for="m-{chiave}">{etichetta}</label><input id="m-{chiave}" type="date" '
                     f'value="{data.isoformat() if data else ""}">')
    if maschera.date_scritte:
        pezzi.append(f'<label for="m-date-scritte">Date scritte a mano</label>'
                     f'<div><input id="m-date-scritte" type="text" value="{e(maschera.date_scritte)}">'
                     f'<div class="nota">Usate solo se i giorni qui sopra sono vuoti: '
                     f'cancellarle se non servono.</div></div>')
    pezzi.append('<label for="m-entranti">Qualificati entranti nel primo tabellone</label><div>'
                 + _scelta("m-entranti", [(n, str(n)) for n in range(0, m.MASSIMO_NUMERO + 1)],
                           maschera.qualificati_entranti)
                 + '<span class="nota"> di solito 0: servono solo se il primo tabellone riceve '
                   'giocatori da un tabellone fatto a parte</span></div>')
    quanti = 0 if maschera.divisione_automatica else len(maschera.tabelloni)
    pezzi.append('<label for="m-quanti">Quanti tabelloni</label><div>'
                 + _scelta("m-quanti", [(0, "decisi dal programma")] + [
                     (n, "1 tabellone" if n == 1 else f"{n} tabelloni collegati")
                     for n in range(1, m.MASSIMO_TABELLONI + 1)], quanti)
                 + ' <button type="button" class="piccolo" id="m-per-categoria"'
                 + ('' if conteggio else ' disabled')
                 + '>Uno per categoria, secondo gli iscritti</button></div>')
    pezzi.append('</div>')

    automatica = maschera.divisione_automatica
    elenchi = m.classifiche_dei_tabelloni(maschera, classifiche)
    pezzi.append('<table class="tabelloni"><thead><tr><th></th>'
                 + ('' if automatica else '<th>Classifiche fino a</th><th>Chi gioca</th>')
                 + '<th>Tipo</th><th>Teste di serie</th><th>Qualificati uscenti</th></tr></thead><tbody>')
    for numero, tabellone in enumerate(maschera.tabelloni):
        ultimo = numero == len(maschera.tabelloni) - 1
        pezzi.append(f'<tr><th>{"Tutto il torneo" if automatica else f"Tabellone {numero + 1}"}</th>')
        if not automatica:
            if ultimo:
                pezzi.append("<td>fino alla più alta</td>")
            else:
                scelte = m.scelte_della_piu_alta(maschera, numero, classifiche)
                pezzi.append("<td>" + _scelta(f"m-alta-{numero}", [(c, c) for c in scelte],
                                              tabellone.piu_alta) + "</td>")
            pezzi.append(f"<td>{e(m.descrivi_tabellone(elenchi[numero], conteggio or None))}</td>")
        tipi = [(k, v) for k, v in m.TIPI.items() if k != "integrale" or ultimo]
        pezzi.append("<td>" + _scelta(f"m-tipo-{numero}", tipi, tabellone.tipo) + "</td>")
        if not automatica and m.solo_non_classificati(elenchi[numero]):
            pezzi.append("<td>" + _scelta(f"m-teste-{numero}", [("", "nessuna (non classificati)")], "",
                                          disabilitato=True) + "</td>")
        else:
            pezzi.append("<td>" + _scelta(f"m-teste-{numero}", [("", "proposte dal programma")] + [
                (n, str(n)) for n in range(0, m.MASSIMO_NUMERO + 1)],
                _valore_numero(tabellone.teste_di_serie)) + "</td>")
        if ultimo:
            uscenti = [("1", "1 (il vincitore)")] + [(n, str(n)) for n in range(2, m.MASSIMO_NUMERO + 1)]
            scelto = _valore_numero(tabellone.qualificati_uscenti) or "1"
        else:
            uscenti = [("", "proposti dal programma")] + [(n, str(n)) for n in range(1, m.MASSIMO_NUMERO + 1)]
            scelto = _valore_numero(tabellone.qualificati_uscenti)
        pezzi.append("<td>" + _scelta(f"m-uscenti-{numero}", uscenti, scelto) + "</td></tr>")
    pezzi.append("</tbody></table>")
    return "".join(pezzi)


def _numero_dal_valore(valore):
    valore = (valore or "").strip()
    return int(valore) if valore.isdigit() else m.AUTOMATICO


def maschera_dai_valori(valori, maschera, classifiche):
    """Dai campi della pagina (id -> valore) alla maschera. Cambia la maschera e la
    restituisce. Se cambia il numero dei tabelloni, si tolgono o si aggiungono
    tabelloni prima dell'ultimo (che resta l'ultimo)."""
    maschera.nome = valori.get("m-nome", maschera.nome)
    maschera.gara = valori.get("m-gara", maschera.gara)
    for chiave in ("inizio", "fine"):
        testo = valori.get(f"m-{chiave}", "")
        try:
            setattr(maschera, chiave, datetime.date.fromisoformat(testo) if testo else None)
        except ValueError:
            setattr(maschera, chiave, None)
    if maschera.inizio or maschera.fine:
        maschera.date_scritte = ""
    else:
        maschera.date_scritte = valori.get("m-date-scritte", maschera.date_scritte)
    maschera.qualificati_entranti = _numero_dal_valore(valori.get("m-entranti")) or 0
    for numero, tabellone in enumerate(maschera.tabelloni):
        if f"m-alta-{numero}" in valori:
            tabellone.piu_alta = valori[f"m-alta-{numero}"]
        if f"m-tipo-{numero}" in valori:
            tabellone.tipo = valori[f"m-tipo-{numero}"]
        if f"m-teste-{numero}" in valori:
            tabellone.teste_di_serie = _numero_dal_valore(valori[f"m-teste-{numero}"])
        if f"m-uscenti-{numero}" in valori:
            tabellone.qualificati_uscenti = _numero_dal_valore(valori[f"m-uscenti-{numero}"])
    quanti = _numero_dal_valore(valori.get("m-quanti"))
    if quanti is not m.AUTOMATICO:
        maschera.divisione_automatica = quanti == 0
        quanti = max(quanti, 1)
        tabelloni = maschera.tabelloni
        if len(tabelloni) > quanti:
            del tabelloni[quanti - 1:-1]
        while len(tabelloni) < quanti:
            tabelloni.insert(-1, m.TabelloneDellaMaschera())
    # Le classifiche scelte devono restare possibili (per esempio dopo aver aggiunto tabelloni).
    if not maschera.divisione_automatica:
        for numero, tabellone in enumerate(maschera.tabelloni[:-1]):
            scelte = m.scelte_della_piu_alta(maschera, numero, classifiche)
            if tabellone.piu_alta not in scelte and scelte:
                tabellone.piu_alta = scelte[0]
    return maschera


def uno_per_categoria(maschera, classifiche, conteggio):
    piu_alte = m.un_tabellone_per_categoria(classifiche, set(conteggio))
    vecchi = maschera.tabelloni
    maschera.tabelloni = [vecchi[i] if i < len(vecchi) - 1 else m.TabelloneDellaMaschera()
                          for i in range(len(piu_alte) - 1)] + [vecchi[-1]]
    for tabellone, piu_alta in zip(maschera.tabelloni, piu_alte):
        tabellone.piu_alta = piu_alta
    maschera.divisione_automatica = False
    return maschera


def _classifiche_e_conteggio():
    return (classifiche_dal_testo(riquadro("classifiche").value),
            m.giocatori_per_classifica(riquadro("giocatori").value))


def disegna_maschera():
    classifiche, conteggio = _classifiche_e_conteggio()
    contenitore = document.getElementById("maschera")
    if not classifiche:
        contenitore.innerHTML = '<p class="nota">Prima servono le classifiche (riquadro "Classifiche").</p>'
        return
    maschera = MASCHERA["maschera"]
    contenitore.innerHTML = html_della_maschera(maschera, classifiche, conteggio)
    problemi = m.problemi_della_maschera(maschera, classifiche)
    document.getElementById("maschera-problemi").innerHTML = (
        "<strong>Da correggere:</strong> " + "; ".join(html.escape(p) for p in problemi)) if problemi else ""


def rileggi_maschera():
    """Dal testo del riquadro "Torneo" alla maschera."""
    classifiche, _ = _classifiche_e_conteggio()
    MASCHERA["maschera"] = m.maschera_dal_testo(riquadro("torneo").value, classifiche)
    disegna_maschera()


def valori_della_maschera():
    valori = {}
    for campo in document.querySelectorAll("#maschera input, #maschera select"):
        if campo.id and not campo.disabled:
            valori[campo.id] = campo.value
    return valori


def scrivi_dalla_maschera(ridisegna):
    classifiche, conteggio = _classifiche_e_conteggio()
    maschera_dai_valori(valori_della_maschera(), MASCHERA["maschera"], classifiche)
    riquadro("torneo").value = m.testo_dalla_maschera(MASCHERA["maschera"], classifiche,
                                                      set(conteggio) or None)
    if ridisegna:
        disegna_maschera()
    else:
        problemi = m.problemi_della_maschera(MASCHERA["maschera"], classifiche)
        document.getElementById("maschera-problemi").innerHTML = (
            "<strong>Da correggere:</strong> " + "; ".join(html.escape(p) for p in problemi)) \
            if problemi else ""


@when("change", "#maschera")
def campo_cambiato(event):
    # I menu' cambiano chi gioca in ogni tabellone: si ridisegna tutto.
    scrivi_dalla_maschera(ridisegna=event.target.tagName == "SELECT")


@when("input", "#maschera")
def campo_scritto(event):
    if event.target.tagName == "INPUT" and event.target.type == "text":
        scrivi_dalla_maschera(ridisegna=False)


@when("click", "#maschera")
def clic_nella_maschera(event):
    if event.target.id == "m-per-categoria":
        classifiche, conteggio = _classifiche_e_conteggio()
        maschera_dai_valori(valori_della_maschera(), MASCHERA["maschera"], classifiche)
        uno_per_categoria(MASCHERA["maschera"], classifiche, conteggio)
        riquadro("torneo").value = m.testo_dalla_maschera(MASCHERA["maschera"], classifiche,
                                                          set(conteggio) or None)
        disegna_maschera()


@when("input", "#testo-torneo")
def torneo_scritto_a_mano(event):
    rileggi_maschera()


@when("input", "#testo-giocatori")
def giocatori_cambiati(event):
    disegna_maschera()  # cambia quanti giocatori ci sono in ogni tabellone


@when("input", "#testo-classifiche")
def classifiche_cambiate(event):
    rileggi_maschera()


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
    contenuto = (await scelto.arrayBuffer()).to_bytes()
    event.target.value = ""
    if chiave == "giocatori" and e_un_excel(contenuto):
        try:
            testo, avvisi = giocatori_da_excel(contenuto, scelto.name,
                                               f"{datetime.date.today():%d/%m/%Y}")
        except ErroreExcel as errore:
            stato(f"Il file {scelto.name} non si puo' usare: {errore}.", "errore")
            return
        riquadro(chiave).value = testo
        quanti = sum(1 for r in testo.splitlines() if r.strip() and not r.startswith("#"))
        messaggio = (f"Presi {quanti} giocatori dall'Excel {scelto.name} (solo cognome, nome, "
                     f"classifica e circolo).")
        if avvisi:
            messaggio += " Da controllare: " + "; ".join(avvisi) + "."
        stato(messaggio, "pronto")
    else:
        riquadro(chiave).value = decodifica(contenuto)
        stato(f"Caricato il file {scelto.name} nel riquadro \"{NOMI[chiave]}\".", "pronto")
    dopo_un_cambio(chiave)


def e_un_excel(contenuto):
    """I file .xlsx cominciano con "PK" (sono archivi zip), i vecchi .xls con D0 CF 11 E0."""
    return contenuto[:4] == b"PK\x03\x04" or contenuto[:4] == b"\xd0\xcf\x11\xe0"


def dopo_un_cambio(chiave):
    """Quando un riquadro cambia da solo (file caricato, esempio rimesso) la maschera si
    aggiorna."""
    if chiave in ("torneo", "classifiche"):
        rileggi_maschera()
    elif chiave == "giocatori":
        disegna_maschera()


@when("click", ".esempio")
def rimetti_esempio(event):
    chiave = event.target.dataset.per
    riquadro(chiave).value = ESEMPI[chiave]
    stato(f"Rimesso l'esempio nel riquadro \"{NOMI[chiave]}\".", "pronto")
    dopo_un_cambio(chiave)


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
    rileggi_maschera()
    abilita(True)
    stato("Pronto. Controllare i dati e premere \"Fai il tabellone\".", "pronto")


avvia()
