"""Prove dello schema e del sorteggio del tabellone di estrazione.

Gli schemi del manuale sono nel file prove/esercizi/schemi-dei-tabelloni.txt.
Si avviano con:  py -m unittest discover prove
"""

import os
import random
import unittest

from programma.calcoli import calcola, conta_per_classifica
from programma.dati import AVVISO, ERRORE, Giocatore, leggi_righe
from programma.sorteggio import (GIOCATORE, LIBERO, QUALIFICATO_ENTRANTE, disegna,
                                 incontri_stesso_circolo, ordine_delle_coppie, schema, sorteggia)
from prove.test_calcoli import CLASSIFICHE, leggi_elenco

FILE_SCHEMI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "esercizi",
                           "schemi-dei-tabelloni.txt")


def leggi_schemi():
    esempi = {}
    nome = None
    for _, riga in leggi_righe(FILE_SCHEMI):
        if riga.startswith("["):
            nome = riga.strip("[]")
            esempi[nome] = {}
        else:
            chiave, valore = (parte.strip() for parte in riga.split("=", 1))
            esempi[nome][chiave] = valore
    return esempi


def calcoli_esempio(esempio):
    giocatori = leggi_elenco(esempio["giocatori"])
    teste = esempio.get("teste di serie")
    return calcola([(c, giocatori[c]) for c in CLASSIFICHE if c in giocatori],
                   qualificati_entranti=int(esempio.get("qualificati entranti", 0)),
                   qualificati_uscenti=int(esempio["qualificati uscenti"]),
                   teste_di_serie=int(teste) if teste else None)


def segno(posto):
    if posto.testa_di_serie:
        return f"({posto.testa_di_serie})"
    return {LIBERO: "-", QUALIFICATO_ENTRANTE: "q", GIOCATORE: "x"}[posto.tipo]


def come_testo(posti):
    return " | ".join(f"{segno(posti[i])} {segno(posti[i + 1])}" for i in range(0, len(posti), 2))


def giocatori_di_prova(elenco):
    """elenco: coppie (classifica, circolo), una per giocatore."""
    return [Giocatore(f"G{i:03}", classifica, circolo)
            for i, (classifica, circolo) in enumerate(elenco, start=1)]


def tabellone_di_prova(elenco, rng, **impostazioni):
    giocatori = giocatori_di_prova(elenco)
    calcoli = calcola(conta_per_classifica(giocatori, CLASSIFICHE), **impostazioni)
    return sorteggia(calcoli, giocatori, rng), giocatori


class ProveOrdine(unittest.TestCase):
    def test_ordine_come_nel_manuale(self):
        # Volume I, esempio 5: 16 giocatori, 8 teste di serie
        self.assertEqual(ordine_delle_coppie(8), [1, 8, 4, 5, 6, 3, 7, 2])

    def test_somma_costante_in_ogni_frazione(self):
        for numero_coppie in (2, 4, 8, 16, 32, 64):
            ordine = ordine_delle_coppie(numero_coppie)
            self.assertEqual(sorted(ordine), list(range(1, numero_coppie + 1)))
            larghezza = 2
            while larghezza <= numero_coppie:
                gruppi = [ordine[i:i + larghezza] for i in range(0, numero_coppie, larghezza)]
                # Le due teste di serie piu' forti di ogni frazione danno sempre la stessa somma
                somme = {sum(sorted(g)[:2]) for g in gruppi}
                self.assertEqual(len(somme), 1, (numero_coppie, larghezza))
                larghezza *= 2


class ProveSchemiDelManuale(unittest.TestCase):
    def test_ci_sono_tutti_gli_esempi(self):
        self.assertEqual(len(leggi_schemi()), 37)

    def test_schemi_come_nel_manuale(self):
        for nome, esempio in leggi_schemi().items():
            with self.subTest(esempio=nome):
                calcoli = calcoli_esempio(esempio)
                self.assertEqual([p for p in calcoli.problemi if p.gravita == ERRORE], [])
                atteso = esempio.get("tabellone del programma", esempio["tabellone"])
                self.assertEqual(come_testo(schema(calcoli, random.Random(0))), atteso)

    def test_sorteggio_degli_esempi(self):
        # Il sorteggio mette ogni giocatore in un posto, e le teste di serie
        # hanno la classifica giusta.
        for nome, esempio in leggi_schemi().items():
            with self.subTest(esempio=nome):
                calcoli = calcoli_esempio(esempio)
                elenco = [(c, f"Circolo {i % 5}")
                          for i, c in enumerate(c for c, n in calcoli.ammessi for _ in range(n))]
                giocatori = giocatori_di_prova(elenco)
                tabellone = sorteggia(calcoli, giocatori, random.Random(1))
                messi = [p.giocatore for p in tabellone.posti if p.giocatore]
                self.assertCountEqual([g.codice for g in messi], [g.codice for g in giocatori])
                self.assertEqual(come_testo(tabellone.posti),
                                 esempio.get("tabellone del programma", esempio["tabellone"]))
                teste = sorted((p.testa_di_serie, CLASSIFICHE.index(p.giocatore.classifica))
                               for p in tabellone.posti if p.testa_di_serie)
                self.assertEqual([c for _, c in teste], sorted(c for _, c in teste))


class ProveSorteggio(unittest.TestCase):
    def test_qualificati_distribuiti_in_ogni_meta(self):
        # 2 q e 10 ammessi: 4 incontri al primo turno e solo 2 q; vanno uno per meta'.
        for seme in range(20):
            tabellone, _ = tabellone_di_prova(
                [("3.1", "A")] * 4 + [("3.2", "B")] * 6, random.Random(seme),
                qualificati_entranti=2, qualificati_uscenti=2)
            posti = tabellone.posti
            meta = len(posti) // 2
            q_alto = sum(1 for p in posti[:meta] if p.tipo == QUALIFICATO_ENTRANTE)
            q_basso = sum(1 for p in posti[meta:] if p.tipo == QUALIFICATO_ENTRANTE)
            self.assertEqual((q_alto, q_basso), (1, 1))

    def test_regola_dello_stesso_circolo(self):
        # 8 non classificati, 4 del circolo A e 4 del circolo B: 4 incontri al primo
        # turno. L'unico modo di rispettare la regola e' fare sempre A contro B.
        for seme in range(50):
            tabellone, _ = tabellone_di_prova([("4.NC", "A")] * 4 + [("4.NC", "B")] * 4,
                                              random.Random(seme))
            self.assertEqual(incontri_stesso_circolo(tabellone), [])
            self.assertEqual(tabellone.problemi, [])

    def test_regola_con_classifiche_diverse(self):
        # Il circolo "Grande" ha 5 giocatori su 10: la regola si puo' rispettare.
        elenco = [("3.1", "Grande"), ("3.2", "Grande"), ("3.3", "Grande"), ("3.4", "Grande"),
                  ("3.5", "Grande"), ("3.5", "Uno"), ("4.1", "Due"), ("4.1", "Tre"),
                  ("4.2", "Uno"), ("4.2", "Due")]
        for seme in range(50):
            tabellone, _ = tabellone_di_prova(elenco, random.Random(seme))
            self.assertEqual(incontri_stesso_circolo(tabellone), [])

    def test_regola_impossibile_da_rispettare(self):
        # 4 giocatori, 3 dello stesso circolo: un incontro tra loro e' inevitabile.
        tabellone, _ = tabellone_di_prova([("4.NC", "A")] * 3 + [("4.NC", "B")],
                                          random.Random(0))
        self.assertEqual(len(incontri_stesso_circolo(tabellone)), 1)
        self.assertEqual([p.gravita for p in tabellone.problemi], [AVVISO])
        self.assertIn("non esiste nessun sorteggio", tabellone.problemi[0].messaggio)

    def test_la_regola_vale_solo_al_primo_turno(self):
        # Un aspettito (entra al secondo turno) non conta per la regola.
        tabellone, _ = tabellone_di_prova([("3.1", "A"), ("3.2", "A"), ("3.3", "B")],
                                          random.Random(0))
        self.assertEqual(tabellone.problemi, [])

    def test_sorteggio_diverso_ogni_volta(self):
        elenco = [("4.NC", f"C{i}") for i in range(12)]
        disegni = {come_testo_codici(tabellone_di_prova(elenco, random.Random(s))[0])
                   for s in range(10)}
        self.assertGreater(len(disegni), 1)

    def test_disegno(self):
        tabellone, _ = tabellone_di_prova([("3.1", "TC Uno"), ("3.2", "TC Due"), ("4.1", "TC Tre")],
                                          random.Random(0))
        testo = disegna(tabellone, "Prova")
        self.assertIn("posto libero", testo)
        self.assertIn("(1)  G001", testo)


class ProveSorteggioMirato(unittest.TestCase):
    """Il sorteggio mirato mette le classifiche come negli esercizi del manuale:
    i giocatori destinati a incontrarsi hanno classifiche vicine."""

    def sorteggio(self, esempio, seme=0):
        calcoli = calcoli_esempio(leggi_schemi()[esempio])
        elenco = [(c, f"Circolo {i}")
                  for i, c in enumerate(c for c, n in calcoli.ammessi for _ in range(n))]
        tabellone = sorteggia(calcoli, giocatori_di_prova(elenco), random.Random(seme), CLASSIFICHE)
        self.assertEqual(tabellone.problemi, [])
        return tabellone.posti

    def primo_turno(self, posti, inizio, fine):
        """Le classifiche dei giocatori non teste di serie che giocano il primo turno."""
        return sorted(p.giocatore.classifica for i, p in enumerate(posti[inizio:fine], inizio)
                      if p.tipo == GIOCATORE and not p.testa_di_serie
                      and posti[i ^ 1].tipo != LIBERO)

    def test_esercizio_2_06(self):
        # I (4.2) giocano nelle sezioni delle teste di serie (4.2), cosi' al secondo
        # turno c'e' una compressione tra pari classifica; il (4.3) va nella sezione 1.
        for seme in range(5):
            posti = self.sorteggio("Volume II, esercizio 2.06", seme)
            self.assertEqual(self.primo_turno(posti, 0, 4), ["4.3"])
            self.assertEqual(self.primo_turno(posti, 4, 12), ["4.2", "4.2"])

    def test_esercizio_2_10(self):
        # "In corrispondenza delle teste di serie n. 5 e n. 6 si faranno giocare i (3.4)".
        for seme in range(5):
            posti = self.sorteggio("Volume II, esercizio 2.10", seme)
            self.assertEqual(self.primo_turno(posti, 16, 24), ["3.4", "3.4"])

    def test_esercizio_2_11(self):
        # "Prima della testa di serie n. 7 si fara' giocare quindi il rimanente (4.2)".
        for seme in range(5):
            posti = self.sorteggio("Volume II, esercizio 2.11", seme)
            self.assertEqual(self.primo_turno(posti, 24, 28), ["4.2"])

    def test_esercizio_2_22(self):
        # Compressione tra pari classifica: nella meta' inferiore delle sezioni 1 e 2
        # giocano i (4.6). L'aspettito n. 8 (sezione 3, contro il q) e' il (4.5).
        for seme in range(5):
            posti = self.sorteggio("Volume II, esercizio 2.22", seme)
            self.assertEqual(self.primo_turno(posti, 4, 8), ["4.6", "4.6"])
            self.assertEqual(self.primo_turno(posti, 12, 16), ["4.6", "4.6"])
            self.assertEqual(posti[23].giocatore.classifica, "4.5")
            self.assertEqual(posti[21].tipo, QUALIFICATO_ENTRANTE)

    def test_esempio_44(self):
        # Tabellone di estrazione senza sezioni: al primo turno si incontrano
        # giocatori della stessa classifica (4.NC con 4.NC, 4.6 con 4.6).
        posti = self.sorteggio("Volume I, esempio 44")
        for i in range(0, len(posti), 2):
            if posti[i].tipo == posti[i + 1].tipo == GIOCATORE:
                self.assertEqual(posti[i].giocatore.classifica, posti[i + 1].giocatore.classifica)

    def test_la_regola_del_circolo_vince(self):
        # Il sorteggio mirato vorrebbe (3.2) contro (3.2), ma sono dello stesso circolo:
        # la regola dello stesso circolo viene prima.
        elenco = [("3.1", "X"), ("3.1", "Y"), ("3.2", "A"), ("3.2", "A"),
                  ("3.3", "B"), ("3.3", "C"), ("3.3", "D"), ("3.3", "E")]
        for seme in range(10):
            tabellone, _ = tabellone_di_prova(elenco, random.Random(seme), teste_di_serie=2)
            self.assertEqual(incontri_stesso_circolo(tabellone), [])
            self.assertEqual(tabellone.problemi, [])


def come_testo_codici(tabellone):
    return " ".join(p.giocatore.codice if p.giocatore else segno(p) for p in tabellone.posti)


if __name__ == "__main__":
    unittest.main()
