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
    adesso = adesso or datetime.datetime.now()
    calcoli = tabellone.calcoli
    nome = impostazioni.get("nome", "Tabellone")
    gara = impostazioni.get("gara", "")
    date = impostazioni.get("date", "")
    Qu = calcoli.qualificati_uscenti
    uscita = "il vincitore" if Qu == 1 else f"{Qu} qualificati"
    riassunto = (f"Tabellone di {len(tabellone.posti)} posti &middot; {calcoli.N} giocatori"
                 f" &middot; esce {uscita}")
    if calcoli.sezioni:
        riassunto += f" &middot; {calcoli.sezioni} sezioni"
    if calcoli.teste_di_serie:
        riassunto += f" &middot; {calcoli.teste_di_serie} teste di serie"
    griglie = fogli(tabellone)
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
