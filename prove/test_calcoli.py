"""Prove dei calcoli preliminari con gli esercizi del manuale.

Gli esercizi sono nel file prove/esercizi/calcoli-preliminari.txt.
Si avviano con:  py -m unittest discover prove
"""

import os
import re
import unittest

from programma.calcoli import QUALIFICATO, calcola, descrivi
from programma.dati import AVVISO, ERRORE, leggi_classifiche, leggi_righe

CARTELLA = os.path.dirname(os.path.abspath(__file__))
FILE_ESERCIZI = os.path.join(CARTELLA, "esercizi", "calcoli-preliminari.txt")
CLASSIFICHE, _ = leggi_classifiche(os.path.join(CARTELLA, "..", "dati", "classifiche.txt"))


def leggi_elenco(testo):
    """'3 q, 2 (4.6)' -> {'q': 3, '4.6': 2}"""
    if testo.strip() == "nessuna":
        return {}
    elenco = {}
    for numero, qualificati, classifica in re.findall(r"(\d+)\s*(?:(q)\b|\(([^)]+)\))", testo):
        elenco[QUALIFICATO if qualificati else classifica] = int(numero)
    return elenco


def leggi_esercizi():
    esercizi = {}
    nome = None
    for _, riga in leggi_righe(FILE_ESERCIZI):
        if riga.startswith("["):
            nome = riga.strip("[]")
            esercizi[nome] = {}
        else:
            chiave, valore = (parte.strip() for parte in riga.split("=", 1))
            esercizi[nome][chiave] = valore
    return esercizi


def calcola_esercizio(esercizio, teste_di_serie=None):
    giocatori = leggi_elenco(esercizio["giocatori"])
    ammessi = [(c, giocatori[c]) for c in CLASSIFICHE if c in giocatori]
    return calcola(ammessi,
                   qualificati_entranti=int(esercizio.get("qualificati entranti", 0)),
                   qualificati_uscenti=int(esercizio["qualificati uscenti"]),
                   teste_di_serie=teste_di_serie)


class ProveEserciziDelManuale(unittest.TestCase):
    def test_ci_sono_tutti_gli_esercizi(self):
        self.assertEqual(len(leggi_esercizi()), 22)

    def test_calcoli_come_nel_manuale(self):
        for nome, esercizio in leggi_esercizi().items():
            with self.subTest(esercizio=nome):
                teste = leggi_elenco(esercizio["teste di serie"])
                calcoli = calcola_esercizio(esercizio, sum(teste.values()) if teste else None)
                self.assertEqual([p for p in calcoli.problemi if p.gravita == ERRORE], [])
                for sigla in ("N", "D", "A", "NA", "I1"):
                    self.assertEqual(getattr(calcoli, sigla), int(esercizio[sigla]), sigla)
                self.assertEqual(dict(calcoli.non_aspettiti), leggi_elenco(esercizio["primo turno"]))
                self.assertEqual(dict(calcoli.aspettiti), leggi_elenco(esercizio["secondo turno"]))
                self.assertEqual({c: prese for c, prese, _ in calcoli.composizione_teste_di_serie},
                                 teste)
                if "teste di serie possibili" in esercizio:
                    minimo, massimo = map(int, re.findall(r"\d+", esercizio["teste di serie possibili"]))
                    self.assertEqual(calcoli.teste_di_serie_minimo, minimo)
                    self.assertEqual(calcoli.teste_di_serie_massimo, massimo)
                else:
                    self.assertIsNone(calcoli.teste_di_serie_minimo)

    def test_proposta_delle_teste_di_serie(self):
        for nome, esercizio in leggi_esercizi().items():
            with self.subTest(esercizio=nome):
                attesa = esercizio.get("proposta del programma")
                if attesa is None:
                    attesa = sum(leggi_elenco(esercizio["teste di serie"]).values())
                calcoli = calcola_esercizio(esercizio)
                self.assertEqual(calcoli.teste_di_serie, int(attesa))


class ProveCasiParticolari(unittest.TestCase):
    def test_numero_di_giocatori_potenza_di_due(self):
        calcoli = calcola([("3.1", 8)], qualificati_entranti=8, qualificati_uscenti=4)
        self.assertEqual((calcoli.D, calcoli.A, calcoli.NA, calcoli.I1), (16, 0, 16, 8))
        self.assertEqual(dict(calcoli.non_aspettiti), {"q": 8, "3.1": 8})

    def test_qualificati_uscenti_non_potenza_di_due(self):
        calcoli = calcola([("4.NC", 24)], qualificati_uscenti=3)
        self.assertIn("sezioni", calcoli.problemi[0].messaggio)

    def test_troppi_qualificati_uscenti(self):
        calcoli = calcola([("4.NC", 5)], qualificati_uscenti=4)
        self.assertEqual(calcoli.problemi[0].gravita, ERRORE)

    def test_piu_qualificati_entranti_che_ammessi(self):
        calcoli = calcola([("3.1", 3)], qualificati_entranti=5, qualificati_uscenti=2)
        self.assertTrue(any("piu' dei giocatori ammessi" in p.messaggio for p in calcoli.problemi))

    def test_incontri_tra_ammessi_al_primo_turno(self):
        # 2 q e 10 ammessi: 12 giocatori, 4 incontri al primo turno, solo 2 hanno un q.
        calcoli = calcola([("3.1", 4), ("3.2", 6)], qualificati_entranti=2, qualificati_uscenti=2)
        self.assertEqual(calcoli.I1, 4)
        self.assertEqual(dict(calcoli.non_aspettiti), {"q": 2, "3.2": 6})
        self.assertEqual([p.gravita for p in calcoli.problemi], [AVVISO])

    def test_teste_di_serie_fuori_dai_limiti(self):
        calcoli = calcola([("3.1", 4), ("3.2", 6)], teste_di_serie=9)
        self.assertEqual(calcoli.problemi[0].gravita, ERRORE)

    def test_vincitore_del_tabellone(self):
        # Senza qualificati uscenti indicati, il tabellone da' il vincitore: Qu = 1.
        calcoli = calcola([("3.1", 1), ("3.2", 4)])
        self.assertEqual(calcoli.problemi, [])
        self.assertEqual((calcoli.teste_di_serie_minimo, calcoli.teste_di_serie_massimo), (1, 2))

    def test_descrizione(self):
        esercizio = leggi_esercizi()["Volume II, esercizio 1.08"]
        testo = descrivi(calcola_esercizio(esercizio, 8))
        self.assertIn("I1 = 20 / 2 = 10", testo)
        self.assertIn("2 dei 6 (4.2), per sorteggio", testo)
        self.assertIn("il programma avrebbe proposto 12", testo)


if __name__ == "__main__":
    unittest.main()
