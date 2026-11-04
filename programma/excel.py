"""Lettura del file Excel degli iscritti (quello che il sistema della FITP fa scaricare).

Dal file si prendono solo quattro colonne: cognome, nome, classifica e circolo.
Tutto il resto (tessera, data di nascita, email, telefono...) viene ignorato e
non viene scritto da nessuna parte.

Si usa solo la libreria standard: un file .xlsx e' un archivio .zip con dentro
dei file XML. Non si leggono i vecchi file .xls (un formato diverso): vanno
salvati da Excel come .xlsx.
"""

import io
import re
import zipfile
import xml.etree.ElementTree as ET

from programma.dati import chiave_del_nome, normalizza_classifica

# Come si possono chiamare le colonne che servono (si confronta senza maiuscole,
# spazi e punti: "Class." -> "class").
COLONNE = {
    "cognome": ("cognome",),
    "nome": ("nome",),
    "classifica": ("class", "classifica", "classificazione", "classifica fitp"),
    "circolo": ("circolo", "societa", "società", "affiliato", "circolo di appartenenza"),
}


class ErroreExcel(Exception):
    """Il file non si puo' leggere: il messaggio spiega perche'."""


def _senza_spazio_dei_nomi(etichetta):
    return etichetta.rsplit("}", 1)[-1]


def _figli(elemento, nome):
    return [e for e in elemento if _senza_spazio_dei_nomi(e.tag) == nome]


def _testo_di(elemento):
    """Tutto il testo dentro un elemento (le parti <t> di una stringa)."""
    return "".join(e.text or "" for e in elemento.iter() if _senza_spazio_dei_nomi(e.tag) == "t")


def _numero_di_colonna(riferimento):
    """"C7" -> 2 (le colonne si contano da 0)."""
    lettere = re.match(r"[A-Z]+", riferimento.upper())
    if not lettere:
        return None
    numero = 0
    for lettera in lettere.group():
        numero = numero * 26 + ord(lettera) - ord("A") + 1
    return numero - 1


def _primo_foglio(archivio):
    """Il percorso, dentro l'archivio, del primo foglio di lavoro."""
    nomi = archivio.namelist()
    try:
        libro = ET.fromstring(archivio.read("xl/workbook.xml"))
        legami = ET.fromstring(archivio.read("xl/_rels/workbook.xml.rels"))
        fogli = [e for e in libro.iter() if _senza_spazio_dei_nomi(e.tag) == "sheet"]
        identificativo = next(v for k, v in fogli[0].attrib.items() if k.endswith("}id"))
        for legame in legami:
            if legame.get("Id") == identificativo:
                obiettivo = legame.get("Target").lstrip("/")
                percorso = obiettivo if obiettivo.startswith("xl/") else "xl/" + obiettivo
                if percorso in nomi:
                    return percorso
    except (KeyError, IndexError, StopIteration, ET.ParseError):
        pass
    fogli = sorted(n for n in nomi if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n))
    if not fogli:
        raise ErroreExcel("nel file non c'e' nessun foglio di lavoro")
    return fogli[0]


def righe_del_foglio(dati):
    """Le righe del primo foglio di un file .xlsx (dati: i byte del file), come elenchi di testi."""
    if dati[:4] != b"PK\x03\x04":
        if dati[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
            raise ErroreExcel("e' un file .xls del vecchio formato: aprirlo con Excel e salvarlo "
                              "come \"Cartella di lavoro di Excel (.xlsx)\"")
        raise ErroreExcel("non e' un file Excel (.xlsx)")
    try:
        archivio = zipfile.ZipFile(io.BytesIO(dati))
        condivise = []
        if "xl/sharedStrings.xml" in archivio.namelist():
            radice = ET.fromstring(archivio.read("xl/sharedStrings.xml"))
            condivise = [_testo_di(si) for si in _figli(radice, "si")]
        foglio = ET.fromstring(archivio.read(_primo_foglio(archivio)))
    except (zipfile.BadZipFile, KeyError, ET.ParseError) as errore:
        raise ErroreExcel(f"il file Excel e' rovinato o non si riesce a leggere ({errore})")

    righe = []
    for riga in foglio.iter():
        if _senza_spazio_dei_nomi(riga.tag) != "row":
            continue
        valori = []
        for cella in _figli(riga, "c"):
            colonna = _numero_di_colonna(cella.get("r", "")) if cella.get("r") else len(valori)
            if colonna is None:
                colonna = len(valori)
            tipo = cella.get("t", "n")
            if tipo == "inlineStr":
                testo = _testo_di(cella)
            else:
                v = _figli(cella, "v")
                testo = (v[0].text or "") if v else ""
                if tipo == "s" and testo.strip().isdigit() and int(testo) < len(condivise):
                    testo = condivise[int(testo)]
            while len(valori) < colonna:
                valori.append("")
            valori.append(testo.strip())
        righe.append(valori)
    return righe


def _normalizza_intestazione(testo):
    return " ".join(testo.lower().replace(".", " ").replace("_", " ").split())


def _nome_proprio(testo):
    """"MARIO NICOLAS" -> "Mario Nicolas", "d'angelo" -> "D'Angelo"."""
    return re.sub(r"[^\W\d_]+", lambda m: m.group().capitalize(), testo.lower())


def giocatori_da_excel(dati, nome_del_file="", data=""):
    """Dal file Excel degli iscritti, il testo del file dei giocatori
    ("COGNOME Nome ; classifica ; circolo", una riga per giocatore).

    Restituisce il testo e un elenco di avvisi (righe saltate, nomi uguali...).
    Se il file non si puo' usare, solleva ErroreExcel con la spiegazione."""
    righe = righe_del_foglio(dati)
    # La riga delle intestazioni: la prima che ha almeno cognome e classifica.
    posizioni = None
    for indice, riga in enumerate(righe[:20]):
        trovate = {}
        for colonna, testo in enumerate(riga):
            normale = _normalizza_intestazione(testo)
            for chiave, nomi in COLONNE.items():
                if normale in nomi and chiave not in trovate:
                    trovate[chiave] = colonna
        if "cognome" in trovate and "classifica" in trovate:
            posizioni, inizio = trovate, indice + 1
            break
    if posizioni is None:
        raise ErroreExcel("non trovo le colonne \"Cognome\" e \"Class.\" (la classifica) nelle "
                          "prime righe del foglio")
    mancanti = [c for c in ("nome", "circolo") if c not in posizioni]
    if mancanti:
        raise ErroreExcel(f"manca la colonna \"{mancanti[0].capitalize()}\"")

    def valore(riga, chiave):
        colonna = posizioni[chiave]
        return " ".join(riga[colonna].split()) if colonna < len(riga) else ""

    avvisi = []
    voci = []
    visti = {}
    for numero, riga in enumerate(righe[inizio:], start=inizio + 1):
        cognome, nome = valore(riga, "cognome"), valore(riga, "nome")
        classifica, circolo = valore(riga, "classifica"), valore(riga, "circolo")
        if not any((cognome, nome, classifica, circolo)):
            continue
        if not cognome:
            avvisi.append(f"riga {numero} dell'Excel saltata: manca il cognome")
            continue
        completo = f"{cognome.upper()} {_nome_proprio(nome)}".strip().replace(";", ",")
        chiave = chiave_del_nome(completo)
        visti[chiave] = visti.get(chiave, 0) + 1
        if visti[chiave] > 1:
            avvisi.append(f"due iscritti si chiamano {completo}: il secondo diventa "
                          f"\"{completo} ({visti[chiave]})\"")
            completo = f"{completo} ({visti[chiave]})"
        if not classifica:
            avvisi.append(f"{completo}: manca la classifica, va scritta a mano")
        if not circolo:
            avvisi.append(f"{completo}: manca il circolo, va scritto a mano")
        voci.append((completo, normalizza_classifica(classifica).replace(";", ","),
                     circolo.replace(";", ",")))
    if not voci:
        raise ErroreExcel("nel foglio non c'e' nessun iscritto")

    larghezza = max(len(v[0]) for v in voci)
    testa = [
        "# ELENCO DEI GIOCATORI ISCRITTI",
        "# =============================",
        "#",
        f"# Preso dal file Excel {nome_del_file}".rstrip() + (f" il {data}" if data else "") + ".",
        "# Dall'Excel si prendono solo cognome, nome, classifica e circolo.",
        "#",
        "# Un giocatore per riga:   nome ; classifica ; circolo",
        "# Si puo' correggere a mano. Contiene nomi veri: non metterlo in internet.",
        "",
    ]
    corpo = [f"{n:<{larghezza}} ; {c:<5} ; {s}" for n, c, s in voci]
    return "\n".join(testa + corpo) + "\n", avvisi
