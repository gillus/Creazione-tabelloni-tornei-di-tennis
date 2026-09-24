"""Prove della pagina da stampare (programma/stampa.py).

Si avviano con:  py -m unittest discover prove
"""

import html.parser
import random
import unittest

from programma.calcoli import calcola, conta_per_classifica
from programma.sorteggio import sorteggia
from programma.stampa import pagina
from prove.test_calcoli import CLASSIFICHE
from prove.test_sorteggio import giocatori_di_prova

IMPOSTAZIONI = {"nome": "Torneo di prova", "gara": "Singolare maschile", "date": "ottobre"}
SENZA_CHIUSURA = {"meta", "br"}


class ControlloDeiTag(html.parser.HTMLParser):
    """Controlla che ogni tag aperto venga chiuso, nell'ordine giusto."""

    def __init__(self):
        super().__init__()
        self.aperti = []
        self.errori = []

    def handle_starttag(self, tag, attrs):
        if tag not in SENZA_CHIUSURA:
            self.aperti.append(tag)

    def handle_endtag(self, tag):
        if not self.aperti or self.aperti.pop() != tag:
            self.errori.append(tag)


def fai_pagina(elenco, **impostazioni):
    giocatori = giocatori_di_prova(elenco)
    calcoli = calcola(conta_per_classifica(giocatori, CLASSIFICHE), **impostazioni)
    tabellone = sorteggia(calcoli, giocatori, random.Random(1))
    return tabellone, pagina(tabellone, IMPOSTAZIONI)


class ProvePagina(unittest.TestCase):
    def assertBenFatta(self, testo):
        controllo = ControlloDeiTag()
        controllo.feed(testo)
        self.assertEqual(controllo.errori, [])
        self.assertEqual(controllo.aperti, [])

    def test_ci_sono_tutti_i_giocatori(self):
        elenco = [("4.3", "A"), ("4.4", "B"), ("4.5", "C")] * 4
        tabellone, testo = fai_pagina(elenco)
        self.assertBenFatta(testo)
        for posto in tabellone.posti:
            if posto.giocatore:
                self.assertIn(posto.giocatore.codice, testo)
        for numero in range(1, tabellone.calcoli.teste_di_serie + 1):
            self.assertIn(f'title="testa di serie">{numero}</span>', testo)
        self.assertEqual(testo.count('class="foglio"'), 1)
        self.assertIn("Vincitore", testo)

    def test_tabellone_grande_con_vincitore(self):
        # 64 posti e un vincitore: due fogli da 32 e un foglio finale.
        tabellone, testo = fai_pagina([("4.NC", f"C{i % 5}") for i in range(56)])
        self.assertEqual(len(tabellone.posti), 64)
        self.assertBenFatta(testo)
        self.assertEqual(testo.count('class="foglio"'), 3)
        self.assertIn("Foglio 3 di 3", testo)
        self.assertIn("vincente del foglio 2", testo)
        self.assertIn("6&deg; turno", testo)

    def test_tabellone_grande_con_qualificati(self):
        # 64 posti e 8 qualificati uscenti: due fogli, con Q1-Q4 e Q5-Q8.
        tabellone, testo = fai_pagina([("4.NC", f"C{i % 5}") for i in range(36)],
                                      qualificati_uscenti=8)
        self.assertEqual(len(tabellone.posti), 64)
        self.assertBenFatta(testo)
        self.assertEqual(testo.count('class="foglio"'), 2)
        fogli = testo.split('class="foglio"')
        for q in range(1, 5):
            self.assertIn(f">Q{q}<", fogli[1])
        for q in range(5, 9):
            self.assertIn(f">Q{q}<", fogli[2])

    def test_caratteri_speciali_nel_circolo(self):
        tabellone, testo = fai_pagina([("4.NC", "<b>Circolo & Co</b>"), ("4.NC", "Altro")])
        self.assertBenFatta(testo)
        self.assertIn("&lt;b&gt;Circolo &amp; Co&lt;/b&gt;", testo)


if __name__ == "__main__":
    unittest.main()
