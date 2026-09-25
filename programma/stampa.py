"""Il tabellone come pagina da aprire nel browser e stampare (foglio A4 orizzontale).

Si usa solo la libreria standard: la pagina e' un unico file HTML, con lo
stile scritto dentro, che funziona anche senza collegamento a internet.

Un foglio contiene al massimo 32 posti. Se il tabellone e' piu' grande:
  - quando ogni qualificato uscente viene da una parte di 32 posti o meno,
    ogni foglio contiene parti intere e finisce con i suoi qualificati
    (nei tabelloni a sezioni, sezioni intere, divise tra i fogli in parti
    quasi uguali, e separate da una linea tratteggiata);
  - altrimenti ogni foglio arriva fino al vincente del foglio, e un ultimo
    foglio contiene i turni finali tra i vincenti dei fogli.
"""

import datetime
import html

from programma.sorteggio import LIBERO, QUALIFICATO_ENTRANTE

POSTI_PER_FOGLIO = 32
ALTEZZA_UTILE_MM = 162  # altezza del tabellone su un foglio A4 orizzontale


def _e(testo):
    return html.escape(str(testo))


def _voce_giocatore(numero, posto):
    """La riga di un posto del primo turno."""
    numero_html = f'<span class="numero">{numero}</span>'
    testa = (f'<span class="testa" title="testa di serie">{posto.testa_di_serie}</span>'
             if posto.testa_di_serie else "")
    if posto.tipo == LIBERO:
        return f'{numero_html}<span class="libero">posto libero</span>'
    if posto.tipo == QUALIFICATO_ENTRANTE:
        return f'{numero_html}{testa}<span class="codice">q</span><span class="nota">qualificato</span>'
    g = posto.giocatore
    if g is None:
        return numero_html
    return (f'{numero_html}{testa}<span class="codice">{_e(g.codice)}</span>'
            f'<span class="classifica">{_e(g.classifica)}</span>'
            f'<span class="circolo">{_e(g.circolo)}</span>')


def _nome_breve(posto):
    """Chi passa direttamente al secondo turno (contro un posto libero)."""
    if posto.tipo == QUALIFICATO_ENTRANTE:
        return '<span class="codice">q</span>'
    if posto.giocatore is None:
        return ""
    testa = f'<span class="testa">{posto.testa_di_serie}</span>' if posto.testa_di_serie else ""
    return f'{testa}<span class="codice">{_e(posto.giocatore.codice)}</span>'


def _griglia(voci, turni, primo_turno, etichette_uscita, titolo_uscita, altezza_riga,
             secondo_turno_gia_scritto=None, righe_per_sezione=0):
    """Disegna un pezzo di tabellone.

    voci                 il contenuto HTML delle righe della prima colonna
    turni                quante colonne di turni seguono la prima
    primo_turno          il numero del turno della prima colonna (1, oppure piu' avanti)
    etichette_uscita     le scritte accanto alle righe dell'ultima colonna (Q1, Q2... o nessuna)
    secondo_turno_gia_scritto  per ogni incontro, chi passa senza giocare (o "")
    righe_per_sezione    nei tabelloni a sezioni, quante righe ha ogni sezione (0 = niente sezioni)
    """
    righe = len(voci)
    colonne = [f"{primo_turno + c}&deg; turno" for c in range(turni)] + [titolo_uscita]
    fitta = " fitta" if altezza_riga < 6 else ""
    parti = [f'<div class="griglia{fitta}" style="--righe:{righe}; --colonne:{turni}; '
             f'--riga:{altezza_riga:.2f}mm">']
    for c, titolo in enumerate(colonne):
        parti.append(f'<div class="intestazione" style="grid-column:{c + 1}">{titolo}</div>')
    if righe_per_sezione:
        for i in range(righe_per_sezione, righe, righe_per_sezione):
            parti.append(f'<div class="separatore" style="grid-column:1 / -1; grid-row:{i + 2}"></div>')
    for i, voce in enumerate(voci):
        parti.append(f'<div class="voce prima" style="grid-column:1; grid-row:{i + 2}">'
                     f'<div class="testo">{voce}</div><div class="linea"></div></div>')
    for c in range(1, turni + 1):
        ampiezza = 2 ** c
        for k in range(righe // ampiezza):
            contenuto = ""
            if c == 1 and secondo_turno_gia_scritto:
                contenuto = secondo_turno_gia_scritto[k]
            if c == turni and etichette_uscita:
                contenuto = f'<span class="uscita">{etichette_uscita[k]}</span>' + contenuto
            parti.append(
                f'<div class="voce" style="grid-column:{c + 1}; '
                f'grid-row:{k * ampiezza + 2} / span {ampiezza}; --ampiezza:{ampiezza}">'
                f'<div class="collegamento"></div><div class="testo">{contenuto}</div>'
                f'<div class="linea"></div></div>')
    parti.append("</div>")
    return "\n".join(parti)


def _altezza_riga(righe):
    return min(9.0, ALTEZZA_UTILE_MM / righe)


def _turni(numero):
    """Quante volte si dimezza 'numero' per arrivare a 1 (log2)."""
    return numero.bit_length() - 1


def fogli(tabellone):
    """Divide il tabellone nei fogli da stampare. Restituisce l'HTML di ogni griglia."""
    posti = tabellone.posti
    D = len(posti)
    Qu = tabellone.calcoli.qualificati_uscenti
    parte = D // Qu  # posti che danno un qualificato uscente
    vincitore = Qu == 1
    titolo_uscita = "Vincitore" if vincitore else "Qualificati"

    sezioni = tabellone.calcoli.sezioni
    per_foglio = min(D, POSTI_PER_FOGLIO)
    pezzi = [(inizio, inizio + per_foglio) for inizio in range(0, D, per_foglio)]
    if sezioni and parte <= POSTI_PER_FOGLIO:
        # Sezioni intere su ogni foglio, divise tra i fogli in parti quasi uguali.
        numero_fogli = -(-D // POSTI_PER_FOGLIO)
        pezzi, inizio = [], 0
        for n in range(numero_fogli):
            quante = sezioni // numero_fogli + (n < sezioni % numero_fogli)
            pezzi.append((inizio, inizio + quante * parte))
            inizio += quante * parte
        per_foglio = max(fine - inizio for inizio, fine in pezzi)
    risultato = []
    for inizio, fine in pezzi:
        pezzo = posti[inizio:fine]
        voci = [_voce_giocatore(inizio + i + 1, p) for i, p in enumerate(pezzo)]
        gia_scritti = []
        for i in range(0, len(pezzo), 2):
            alto, basso = pezzo[i], pezzo[i + 1]
            if alto.tipo == LIBERO:
                gia_scritti.append(_nome_breve(basso))
            elif basso.tipo == LIBERO:
                gia_scritti.append(_nome_breve(alto))
            else:
                gia_scritti.append("")
        if parte <= per_foglio:
            turni = _turni(parte)
            primo_q = inizio // parte
            etichette = ([""] if vincitore else
                         [f"Q{primo_q + k + 1}" for k in range(len(pezzo) // parte)])
            risultato.append(_griglia(voci, turni, 1, etichette, titolo_uscita,
                                      _altezza_riga(len(pezzo)), gia_scritti,
                                      parte if sezioni else 0))
        else:
            numero_foglio = inizio // per_foglio + 1
            risultato.append(_griglia(voci, _turni(per_foglio), 1, [f"al foglio finale"],
                                      f"Vincente foglio {numero_foglio}",
                                      _altezza_riga(len(pezzo)), gia_scritti))

    if parte > per_foglio:
        # Foglio finale: i vincenti dei fogli si incontrano fino ai qualificati uscenti.
        numero_fogli = D // per_foglio
        voci = [f'<span class="nota">vincente del foglio {n + 1}</span>' for n in range(numero_fogli)]
        etichette = [""] if vincitore else [f"Q{k + 1}" for k in range(Qu)]
        risultato.append(_griglia(voci, _turni(numero_fogli // Qu), _turni(per_foglio) + 1,
                                  etichette, titolo_uscita, 9.0))
    return risultato


STILE = """
:root { --inchiostro: #111; --grigio: #666; --chiaro: #999; --carta: #fff; --sfondo: #e9e9e6; }
* { box-sizing: border-box; }
body { margin: 0; background: var(--sfondo); color: var(--inchiostro);
       font-family: "Segoe UI", Arial, Helvetica, sans-serif; font-size: 9pt; }
.comandi { text-align: center; padding: 12px; }
.comandi button { font: inherit; font-size: 11pt; padding: 6px 18px; cursor: pointer; }
.foglio { background: var(--carta); width: 297mm; height: 210mm; margin: 0 auto 12px;
          padding: 10mm 12mm; display: flex; flex-direction: column; overflow: hidden;
          box-shadow: 0 1px 4px rgba(0,0,0,.25); }
.testata { display: flex; justify-content: space-between; align-items: flex-end;
           border-bottom: 1.5px solid var(--inchiostro); padding-bottom: 2mm; margin-bottom: 3mm; }
.testata h1 { font-size: 15pt; margin: 0; }
.testata .gara { font-size: 11pt; margin-top: 1mm; }
.testata .destra { text-align: right; color: var(--grigio); }
.griglia { display: grid; flex: none;
           grid-template-columns: 95mm repeat(var(--colonne), minmax(0, 1fr));
           grid-template-rows: 6mm repeat(var(--righe), var(--riga)); }
.fitta { font-size: 8pt; }
.fitta .testa { min-width: 3.6mm; height: 3.6mm; line-height: 3.3mm; font-size: 6.5pt; }
.intestazione { font-size: 7.5pt; text-transform: uppercase; letter-spacing: .04em;
                color: var(--grigio); padding-left: 2mm; }
.voce { position: relative; }
.albero { display: block; flex: none; }
.albero line { stroke: var(--inchiostro); stroke-width: .25; }
.albero text { font-family: "Segoe UI", Arial, Helvetica, sans-serif; fill: var(--inchiostro); }
.albero .intestazione-svg { fill: var(--grigio); font-size: 2.6px; letter-spacing: .1px; }
.albero .codice-svg { font-weight: 600; }
.albero .circolo-svg, .albero .nota-svg { fill: var(--grigio); }
.albero .nota-svg { font-style: italic; }
.albero .uscita-svg { font-weight: 700; }
.albero circle { fill: none; stroke: var(--inchiostro); stroke-width: .25; }
.separatore { border-top: 1.2px dashed var(--grigio); margin-top: -.6mm; }
.voce .linea { position: absolute; left: 0; right: 0;
               top: calc(50% + var(--riga) / 2); border-top: 1px solid var(--inchiostro); }
.voce .testo { position: absolute; left: 2mm; right: 1mm;
               bottom: calc(50% - var(--riga) / 2 + 0.6mm);
               white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.voce .collegamento { position: absolute; left: 0; top: calc(25% + var(--riga) / 2); height: 50%;
                      border-left: 1px solid var(--inchiostro); }
.numero { display: inline-block; width: 7mm; color: var(--chiaro); font-size: 7.5pt; }
.testa { display: inline-block; min-width: 4.2mm; height: 4.2mm; line-height: 3.9mm;
         border: 1px solid var(--inchiostro); border-radius: 50%; text-align: center;
         font-size: 7pt; font-weight: 600; margin-right: 1.5mm; padding: 0 .5mm; }
.codice { font-weight: 600; }
.classifica { display: inline-block; margin-left: 2mm; min-width: 9mm; }
.circolo { color: var(--grigio); }
.libero, .nota { color: var(--grigio); font-style: italic; }
.nota { margin-left: 2mm; }
.uscita { float: right; font-weight: 700; }
.piede { margin-top: auto; display: flex; justify-content: space-between; align-items: flex-end;
         color: var(--grigio); font-size: 7.5pt; padding-top: 3mm; }
.firma { color: var(--inchiostro); font-size: 9pt; }
.firma span { display: inline-block; width: 60mm; border-bottom: 1px solid var(--inchiostro); }
@page { size: A4 landscape; margin: 0; }
@media print {
  body { background: none; }
  .comandi { display: none; }
  .foglio { margin: 0; box-shadow: none; break-after: page; }
  .foglio:last-child { break-after: auto; }
}
"""


def pagina(tabellone, impostazioni, adesso=None):
    """La pagina HTML completa, pronta da salvare."""
    if hasattr(tabellone, "radici"):
        return pagina_selezione(tabellone, impostazioni, adesso)
    calcoli = tabellone.calcoli
    Qu = calcoli.qualificati_uscenti
    uscita = "il vincitore" if Qu == 1 else f"{Qu} qualificati"
    riassunto = (f"Tabellone di {len(tabellone.posti)} posti &middot; {calcoli.N} giocatori"
                 f" &middot; esce {uscita}")
    if calcoli.sezioni:
        riassunto += f" &middot; {calcoli.sezioni} sezioni"
    if calcoli.teste_di_serie:
        riassunto += f" &middot; {calcoli.teste_di_serie} teste di serie"
    return _documento(impostazioni, riassunto, fogli(tabellone), adesso)


def _documento(impostazioni, riassunto, griglie, adesso=None):
    """La pagina con un foglio per ogni griglia, con testata e piede."""
    adesso = adesso or datetime.datetime.now()
    nome = impostazioni.get("nome", "Tabellone")
    gara = impostazioni.get("gara", "")
    date = impostazioni.get("date", "")
    fogli_html = []
    for n, griglia in enumerate(griglie, start=1):
        numero = f"Foglio {n} di {len(griglie)}<br>" if len(griglie) > 1 else ""
        fogli_html.append(f"""<section class="foglio">
<div class="testata">
  <div><h1>{_e(nome)}</h1><div class="gara">{_e(gara)}{' &middot; ' + _e(date) if date else ''}</div></div>
  <div class="destra">{numero}{riassunto}</div>
</div>
{griglia}
<div class="piede">
  <div>Il numero nel cerchio indica la testa di serie &middot; q = qualificato entrante
  &middot; preparato il {adesso:%d/%m/%Y}</div>
  <div class="firma">Il giudice arbitro <span></span></div>
</div>
</section>""")
    return f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="utf-8">
<title>{_e(nome)} - {_e(gara)}</title>
<style>{STILE}</style>
</head>
<body>
<div class="comandi"><button onclick="window.print()">Stampa</button></div>
{chr(10).join(fogli_html)}
</body>
</html>
"""


# --- Tabellone di selezione: un albero disegnato in SVG -----------------------------

LARGHEZZA_MM = 273
RIGHE_PER_FOGLIO = 32


class _Segnaposto:
    """Al posto di una parte disegnata in un altro foglio: 'vincente del foglio n'."""

    def __init__(self, turno, testo):
        self.turno = turno
        self.testo = testo


def _foglie(nodo):
    from programma.selezione_tabellone import Voce
    if isinstance(nodo, (Voce, _Segnaposto)):
        return [nodo]
    return _foglie(nodo.alto) + _foglie(nodo.basso)


def _testo_voce(voce, x, y, dimensione):
    """Il testo sopra la linea di un giocatore."""
    from programma.sorteggio import QUALIFICATO_ENTRANTE
    parti = []
    if isinstance(voce, _Segnaposto):
        return f'<text x="{x:.2f}" y="{y:.2f}" font-size="{dimensione:.2f}" class="nota-svg">{_e(voce.testo)}</text>'
    if voce.testa_di_serie:
        r = dimensione * 0.62
        parti.append(f'<circle cx="{x + r:.2f}" cy="{y - dimensione * 0.34:.2f}" r="{r:.2f}"/>'
                     f'<text x="{x + r:.2f}" y="{y:.2f}" font-size="{dimensione * 0.8:.2f}" '
                     f'text-anchor="middle" font-weight="600">{voce.testa_di_serie}</text>')
        x += 2 * r + 1
    if voce.tipo == QUALIFICATO_ENTRANTE:
        parti.append(f'<text x="{x:.2f}" y="{y:.2f}" font-size="{dimensione:.2f}">'
                     f'<tspan class="codice-svg">q</tspan>'
                     f'<tspan class="nota-svg" dx="1.5">qualificato</tspan></text>')
    else:
        g = voce.giocatore
        codice = g.codice if g else "?"
        circolo = g.circolo if g else ""
        parti.append(f'<text x="{x:.2f}" y="{y:.2f}" font-size="{dimensione:.2f}">'
                     f'<tspan class="codice-svg">{_e(codice)}</tspan>'
                     f'<tspan dx="1.5">{_e(voce.classifica)}</tspan>'
                     f'<tspan class="circolo-svg" dx="1.5">{_e(circolo)}</tspan></text>')
    return "".join(parti)


def _albero_svg(blocchi, primo_turno, ultimo_turno, etichette, titolo_uscita):
    """Disegna dei pezzi di tabellone uno sotto l'altro.

    blocchi      i nodi da disegnare (incontri o giocatori), dall'alto
    etichette    la scritta alla fine di ogni blocco (Q1, "al foglio finale"...)
    """
    from programma.selezione_tabellone import Voce
    righe = sum(len(_foglie(b)) for b in blocchi)
    colonne = ultimo_turno - primo_turno + 2  # un turno per colonna, piu' l'uscita
    larghezza = LARGHEZZA_MM / colonne
    altezza_riga = min(9.0, ALTEZZA_UTILE_MM / max(righe, 1))
    dimensione = min(3.0, altezza_riga * 0.55, larghezza / 14)
    alto = 6.0
    altezza = alto + righe * altezza_riga + 1
    parti = [f'<svg class="albero" width="{LARGHEZZA_MM}mm" height="{altezza:.1f}mm" '
             f'viewBox="0 0 {LARGHEZZA_MM} {altezza:.1f}" xmlns="http://www.w3.org/2000/svg">']
    for c in range(colonne):
        titolo = f"{primo_turno + c}&#176; TURNO" if c < colonne - 1 else _e(titolo_uscita).upper()
        parti.append(f'<text x="{c * larghezza + 1.5:.2f}" y="3.5" class="intestazione-svg">{titolo}</text>')

    def x(turno):
        return (turno - primo_turno) * larghezza

    riga = [0]

    def disegna(nodo):
        """Disegna il nodo e restituisce la y della sua linea d'uscita."""
        if isinstance(nodo, (Voce, _Segnaposto)):
            y = alto + (riga[0] + 1) * altezza_riga - 0.4
            riga[0] += 1
            parti.append(f'<line x1="{x(nodo.turno):.2f}" y1="{y:.2f}" x2="{x(nodo.turno + 1):.2f}" y2="{y:.2f}"/>')
            parti.append(_testo_voce(nodo, x(nodo.turno) + 1.2, y - 0.8, dimensione))
            return y
        y1, y2 = disegna(nodo.alto), disegna(nodo.basso)
        xm = x(nodo.turno + 1)
        y = (y1 + y2) / 2
        parti.append(f'<line x1="{xm:.2f}" y1="{y1:.2f}" x2="{xm:.2f}" y2="{y2:.2f}"/>')
        parti.append(f'<line x1="{xm:.2f}" y1="{y:.2f}" x2="{x(nodo.turno + 2):.2f}" y2="{y:.2f}"/>')
        return y

    for blocco, etichetta in zip(blocchi, etichette):
        y = disegna(blocco)
        if etichetta:
            parti.append(f'<text x="{LARGHEZZA_MM - 0.5:.2f}" y="{y - 0.8:.2f}" font-size="{dimensione:.2f}" '
                         f'text-anchor="end" class="uscita-svg">{_e(etichetta)}</text>')
    parti.append("</svg>")
    return "\n".join(parti)


def fogli_selezione(tabellone):
    """Divide il tabellone di selezione nei fogli da stampare (al massimo 32 righe l'uno).

    Se un qualificato viene da una parte troppo grande per un foglio, la parte si
    divide in pezzi, e un foglio finale mostra gli ultimi turni con i vincenti
    dei fogli.
    """
    from programma.selezione_tabellone import Voce
    R = tabellone.turni
    Qu = tabellone.qualificati_uscenti
    vincitore = Qu == 1
    titolo_uscita = "Vincitore" if vincitore else "Qualificati"
    blocchi = list(tabellone.radici)
    diviso = False
    while any(len(_foglie(b)) > RIGHE_PER_FOGLIO for b in blocchi):
        nuovi = []
        for b in blocchi:
            if len(_foglie(b)) > RIGHE_PER_FOGLIO and not isinstance(b, Voce):
                # Un giocatore che entra qui resta nel foglio finale.
                nuovi += [c for c in (b.alto, b.basso) if not isinstance(c, Voce)]
                diviso = True
            else:
                nuovi.append(b)
        blocchi = nuovi
    # I blocchi si mettono nei fogli, uno dopo l'altro, finche' ci stanno.
    fogli, corrente = [], []
    for b in blocchi:
        if corrente and sum(len(_foglie(x)) for x in corrente) + len(_foglie(b)) > RIGHE_PER_FOGLIO:
            fogli.append(corrente)
            corrente = []
        corrente.append(b)
    if corrente:
        fogli.append(corrente)
    primo = min(v.turno for v in tabellone.voci())
    risultato = []
    if not diviso:
        k = 0
        for foglio in fogli:
            etichette = [""] * len(foglio) if vincitore else \
                [f"Q{k + i + 1}" for i in range(len(foglio))]
            k += len(foglio)
            risultato.append(_albero_svg(foglio, primo, R, etichette, titolo_uscita))
        return risultato
    # Con parti divise: ogni foglio ha i suoi pezzi, e il foglio finale gli ultimi turni.
    foglio_di = {}
    for n, foglio in enumerate(fogli, start=1):
        for b in foglio:
            foglio_di[id(b)] = n
        ultimo = max(getattr(b, "turno", 0) for b in foglio)
        risultato.append(_albero_svg(foglio, primo, ultimo, ["al foglio finale"] * len(foglio),
                                     f"Vincente foglio {n}"))

    def copia(nodo):
        if id(nodo) in foglio_di:
            return _Segnaposto(nodo.turno + 1, f"vincente del foglio {foglio_di[id(nodo)]}")
        if isinstance(nodo, Voce):
            return nodo
        return type(nodo)(nodo.turno, copia(nodo.alto), copia(nodo.basso))

    finali = [copia(r) for r in tabellone.radici]
    primo_finale = min(f.turno for r in finali for f in _foglie(r))
    etichette = [""] * len(finali) if vincitore else [f"Q{k + 1}" for k in range(len(finali))]
    risultato.append(_albero_svg(finali, primo_finale, R, etichette, titolo_uscita))
    return risultato


def pagina_selezione(tabellone, impostazioni, adesso=None):
    Qu = tabellone.qualificati_uscenti
    uscita = "il vincitore" if Qu == 1 else f"{Qu} qualificati"
    riassunto = (f"Tabellone di selezione &middot; {tabellone.N} giocatori &middot; "
                 f"{tabellone.turni} turni &middot; esce {uscita}")
    if tabellone.sezioni:
        riassunto += f" &middot; {tabellone.sezioni} sezioni"
    if tabellone.teste_di_serie:
        riassunto += f" &middot; {tabellone.teste_di_serie} teste di serie"
    return _documento(impostazioni, riassunto, fogli_selezione(tabellone), adesso)
