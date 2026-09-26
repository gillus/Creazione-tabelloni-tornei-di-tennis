"""Prove dei tabelloni di selezione (programma/selezione.py, selezione_tabellone.py,
controllo_selezione.py) con gli esercizi del manuale.

Le scale del manuale sono nel file prove/esercizi/scale-dei-tabelloni-di-selezione.txt.
Si avviano con:  py -m unittest discover prove
"""

import os
import random
import tempfile
import unittest

from programma import controllo_selezione
from programma.calcoli import QUALIFICATO, calcola
from programma.dati import ERRORE, leggi_righe
from programma.selezione import (Scala, _calcola_posti, controlla_scala, leggi_turno,
                                 scala_migliore, scala_scritta, scrivi_turno)
from programma.selezione_tabellone import (Voce, disegna, prepara, proposta_teste_di_serie,
                                           voci_di)
from programma.sorteggio import GIOCATORE, QUALIFICATO_ENTRANTE
from programma.stampa import pagina
from prove.test_calcoli import CLASSIFICHE, leggi_elenco
from prove.test_sorteggio import giocatori_di_prova
from prove.test_stampa import ControlloDeiTag

FILE_SCALE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "esercizi",
                          "scale-dei-tabelloni-di-selezione.txt")
LIVELLO = {c: i for i, c in enumerate(CLASSIFICHE)}


def leggi_scale():
    esercizi = {}
    nome = None
    for _, riga in leggi_righe(FILE_SCALE):
        if riga.startswith("["):
            nome = riga.strip("[]")
            esercizi[nome] = {}
        else:
            chiave, valore = (parte.strip() for parte in riga.split("=", 1))
            esercizi[nome][chiave] = valore
    return esercizi


def dati(esercizio):
    """Le classifiche dei giocatori (dalla piu' alta), i q e i qualificati uscenti."""
    giocatori = leggi_elenco(esercizio["giocatori"])
    diretti = [c for c in CLASSIFICHE if c in giocatori for _ in range(giocatori[c])]
    return (diretti, int(esercizio.get("qualificati entranti", 0)),
            int(esercizio["qualificati uscenti"]))


def scala_del_manuale(esercizio, prefisso="turno "):
    _, _, Qu = dati(esercizio)
    turni = {int(k[len(prefisso):]): leggi_turno(v) for k, v in esercizio.items()
             if k.startswith(prefisso)}
    scala = Scala([turni[n] for n in range(1, max(turni) + 1)], Qu)
    _calcola_posti(scala.turni, Qu)
    return scala


def firma(scala):
    return [scrivi_turno(t) for t in scala.turni]


def giocatori_per(diretti):
    return giocatori_di_prova([(c, f"Circolo {i}") for i, c in enumerate(diretti)])


def tabellone_dell_esercizio(esercizio, seme=1):
    diretti, q, Qu = dati(esercizio)
    scala = scala_del_manuale(esercizio)
    giocatori = giocatori_per(diretti)
    return prepara(scala, int(esercizio["teste di serie"]), giocatori, LIVELLO, 0,
                   random.Random(seme)), giocatori


def come_testo(radici):
    """Il tabellone scritto come nel file degli esercizi: '(1)3.3/3 3.4/2 q/1 | ...'."""
    parti = []
    for radice in radici:
        voci = []
        for v in voci_di(radice):
            testa = f"({v.testa_di_serie})" if v.testa_di_serie else ""
            nome = "q" if v.tipo == QUALIFICATO_ENTRANTE else v.classifica
            voci.append(f"{testa}{nome}/{v.turno}")
        parti.append(" ".join(voci))
    return " | ".join(parti)


class ProveScala(unittest.TestCase):
    def test_ci_sono_tutti_gli_esercizi(self):
        self.assertEqual(len(leggi_scale()), 32)

    def test_scrivere_e_rileggere_un_turno(self):
        testo = "1 (2.6); coppie 2 (2.7)+q, 1 (2.8)+(2.8)"
        turno = leggi_turno(testo)
        self.assertEqual(turno.singoli, ["2.6"])
        self.assertEqual(turno.coppie, [("2.7", QUALIFICATO)] * 2 + [("2.8", "2.8")])
        self.assertEqual(scrivi_turno(turno), testo)

    def test_le_scale_del_manuale_rispettano_le_regole(self):
        for nome, esercizio in leggi_scale().items():
            with self.subTest(esercizio=nome):
                diretti, q, _ = dati(esercizio)
                self.assertEqual(controlla_scala(scala_del_manuale(esercizio), diretti, q, LIVELLO), [])

    def test_scala_scelta_dal_programma(self):
        # La stessa del manuale, oppure quella scritta in "proposta turno N"
        # (dove il manuale stesso dice che la scelta spetta al giudice arbitro).
        for nome, esercizio in leggi_scale().items():
            with self.subTest(esercizio=nome):
                diretti, q, Qu = dati(esercizio)
                migliore, _ = scala_migliore(diretti, q, Qu, LIVELLO)
                attesa = "proposta turno " if "proposta turno 1" in esercizio else "turno "
                self.assertEqual(firma(migliore), firma(scala_del_manuale(esercizio, attesa)))

    def test_proposta_delle_teste_di_serie(self):
        for nome, esercizio in leggi_scale().items():
            with self.subTest(esercizio=nome):
                diretti, q, Qu = dati(esercizio)
                calcoli = calcola([(c, diretti.count(c)) for c in CLASSIFICHE if c in diretti],
                                  q, Qu)
                attesa = int(esercizio.get("proposta del programma", esercizio["teste di serie"]))
                self.assertEqual(proposta_teste_di_serie(
                    scala_del_manuale(esercizio), calcoli.teste_di_serie_minimo,
                    calcoli.teste_di_serie_massimo, LIVELLO), attesa)

    def test_scala_scritta_di_un_tabellone_finale(self):
        # Esercizio 5.31: il giudice arbitro scrive solo i turni in cui entra qualcuno;
        # la finale (turno 5, senza nessuno che entra) la aggiunge il programma.
        esercizio = leggi_scale()["Volume II, esercizio 5.31"]
        diretti, q, Qu = dati(esercizio)
        impostazioni = {f"turno {n}": esercizio[f"turno {n}"] for n in range(1, 5)}
        scala = scala_scritta(impostazioni, Qu)
        self.assertEqual(firma(scala), firma(scala_del_manuale(esercizio)))
        self.assertEqual(controlla_scala(scala, diretti, q, LIVELLO), [])
        # Un turno vuoto in mezzo invece e' un errore anche nel tabellone finale.
        impostazioni["turno 6"] = impostazioni.pop("turno 4")
        errori = controlla_scala(scala_scritta(impostazioni, Qu), diretti, q, LIVELLO)
        self.assertIn("al turno 4 della scala non entra nessuno", errori)

    def test_scala_sbagliata(self):
        esercizio = leggi_scale()["Volume II, esercizio 3.01"]
        diretti, q, Qu = dati(esercizio)
        # Il (4.2) entra con i (4.3), un turno prima dei (4.1): ma i (4.3) entrano gia' al turno 2.
        scala = Scala([leggi_turno("coppie 4 (4.4)+q"), leggi_turno("4 (4.3)"),
                       leggi_turno("3 (4.1)"), leggi_turno("1 (4.2)")], Qu)
        errori = controlla_scala(scala, diretti, q, LIVELLO)
        self.assertTrue(any("dopo un giocatore di classifica piu' alta" in e for e in errori), errori)


class ProveTabellone(unittest.TestCase):
    def test_tabelloni_disegnati_nel_manuale(self):
        # Esercizi 3.01, 3.03 e 3.04: i posti sono gli stessi del manuale.
        for nome, esercizio in leggi_scale().items():
            if "tabellone" not in esercizio:
                continue
            with self.subTest(esercizio=nome):
                for seme in range(3):
                    tabellone, _ = tabellone_dell_esercizio(esercizio, seme)
                    self.assertEqual(come_testo(tabellone.radici), esercizio["tabellone"])

    def test_tabelloni_del_programma_rispettano_le_regole(self):
        for nome, esercizio in leggi_scale().items():
            with self.subTest(esercizio=nome):
                diretti, q, Qu = dati(esercizio)
                migliore, _ = scala_migliore(diretti, q, Qu, LIVELLO)
                giocatori = giocatori_per(diretti)
                teste = int(esercizio["teste di serie"])
                if "proposta turno 1" in esercizio:
                    # La scala del programma e' diversa: le sue teste di serie.
                    calcoli = calcola([(c, diretti.count(c)) for c in CLASSIFICHE if c in diretti],
                                      q, Qu)
                    teste = proposta_teste_di_serie(migliore, calcoli.teste_di_serie_minimo,
                                                    calcoli.teste_di_serie_massimo, LIVELLO)
                tabellone = prepara(migliore, teste, giocatori, LIVELLO, 0, random.Random(4))
                self.assertEqual(tabellone.problemi, [])
                problemi = controllo_selezione.controlla(tabellone.voci(), giocatori, CLASSIFICHE,
                                                         q, Qu, teste)
                self.assertEqual([str(p) for p in problemi if p.gravita == ERRORE], [])
                self.assertEqual(sum(1 for v in tabellone.voci() if v.giocatore), len(diretti))

    def test_regola_dello_stesso_circolo(self):
        # Esempio 66: quattro coppie di due ammessi al primo turno. Con due circoli
        # soli la regola si puo' rispettare: ogni coppia ha un giocatore di ognuno.
        esercizio = leggi_scale()["Volume I, esempio 66"]
        diretti, q, Qu = dati(esercizio)
        giocatori = giocatori_di_prova([(c, "AB"[i % 2]) for i, c in enumerate(diretti)])
        for seme in range(10):
            tabellone = prepara(scala_del_manuale(esercizio), 4, giocatori, LIVELLO, 0,
                                random.Random(seme))
            self.assertEqual(tabellone.problemi, [])

    def test_regola_impossibile_da_rispettare(self):
        esercizio = leggi_scale()["Volume I, esempio 66"]
        diretti, q, Qu = dati(esercizio)
        giocatori = giocatori_di_prova([(c, "Unico") for c in diretti])
        tabellone = prepara(scala_del_manuale(esercizio), 4, giocatori, LIVELLO, 0, random.Random(0))
        self.assertEqual(len(tabellone.problemi), 1)
        self.assertIn("stesso circolo", tabellone.problemi[0].messaggio)


class ProveControllo(unittest.TestCase):
    def setUp(self):
        self.esercizio = leggi_scale()["Volume II, esercizio 3.03"]
        self.tabellone, self.giocatori = tabellone_dell_esercizio(self.esercizio)
        self.voci = self.tabellone.voci()

    def controlla(self, voci=None):
        return [p.messaggio for p in controllo_selezione.controlla(
            voci or self.voci, self.giocatori, CLASSIFICHE, 4, 4) if p.gravita == ERRORE]

    def assertErrore(self, frase, voci=None):
        trovati = self.controlla(voci)
        self.assertTrue(any(frase in e for e in trovati), f"manca \"{frase}\"; trovati: {trovati}")

    def test_nessun_errore(self):
        self.assertEqual(self.controlla(), [])

    def test_si_rilegge_il_tabellone_salvato(self):
        testo = disegna(self.tabellone, "Prova")
        with tempfile.TemporaryDirectory() as cartella:
            percorso = os.path.join(cartella, "tabellone.txt")
            with open(percorso, "w", encoding="utf-8") as f:
                f.write(testo)
            self.assertTrue(controllo_selezione.e_di_selezione(percorso))
            voci, problemi = controllo_selezione.leggi_tabellone(percorso, self.giocatori)
        self.assertEqual(problemi, [])
        self.assertEqual([(v.turno, v.testa_di_serie, v.giocatore and v.giocatore.codice) for v in voci],
                         [(v.turno, v.testa_di_serie, v.giocatore and v.giocatore.codice)
                          for v in self.voci])
        self.assertEqual(self.controlla(voci), [])

    def test_turni_che_non_formano_un_tabellone(self):
        self.voci[0].turno = 2
        self.assertErrore("non formano un tabellone")

    def test_due_qualificati_al_primo_incontro(self):
        # Il (3.5) della coppia del secondo turno (corridoio Q2) si scambia con il q
        # di una coppia del primo turno: al secondo turno giocano due q.
        a = next(v for v in self.voci if v.turno == 2 and v.classifica == "3.5")
        b = next(v for v in self.voci if v.turno == 1 and v.tipo == QUALIFICATO_ENTRANTE)
        for campo in ("tipo", "classifica", "giocatore"):
            x, y = getattr(a, campo), getattr(b, campo)
            setattr(a, campo, y)
            setattr(b, campo, x)
        self.assertErrore("puo' incontrare un altro qualificato entrante")

    def test_giocatore_che_entra_dopo_uno_piu_forte(self):
        # Un (3.5) del primo turno e un (3.4) del secondo si scambiano il turno.
        a = next(v for v in self.voci if v.turno == 1 and v.tipo == GIOCATORE)
        b = next(v for v in self.voci if v.turno == 2 and v.classifica == "3.4")
        a.giocatore, b.giocatore = b.giocatore, a.giocatore
        a.classifica, b.classifica = b.classifica, a.classifica
        self.assertErrore("nessuno puo' entrare in gara dopo un giocatore di classifica inferiore")

    def test_testa_di_serie_fuori_posto(self):
        # Le teste di serie n. 1 e n. 2 (tutte e due 3.3) si scambiano il numero.
        uno = next(v for v in self.voci if v.testa_di_serie == 1)
        due = next(v for v in self.voci if v.testa_di_serie == 2)
        uno.testa_di_serie, due.testa_di_serie = 2, 1
        self.assertErrore("la testa di serie n. 1 non e' nel suo posto")

    def test_qualificati_non_divisi(self):
        # Il q del corridoio Q1 va nel corridoio Q4 al posto di un (3.5): e' una
        # raccomandazione, quindi un avviso.
        i = next(i for i, v in enumerate(self.voci) if v.tipo == QUALIFICATO_ENTRANTE)
        j = max(i for i, v in enumerate(self.voci) if v.classifica == "3.5")
        self.voci[i], self.voci[j] = self.voci[j], self.voci[i]
        problemi = controllo_selezione.controlla(self.voci, self.giocatori, CLASSIFICHE, 4, 4)
        self.assertTrue(any("non sono divisi in modo uguale" in p.messaggio for p in problemi))


class ProveStampa(unittest.TestCase):
    def test_pagina_ben_fatta(self):
        tabellone, _ = tabellone_dell_esercizio(leggi_scale()["Volume I, esempio 63"])
        testo = pagina(tabellone, {"nome": "Prova <b>", "gara": "Singolare"})
        controllo = ControlloDeiTag()
        controllo.feed(testo)
        self.assertEqual((controllo.errori, controllo.aperti), ([], []))
        self.assertEqual(testo.count('class="foglio"'), 1)
        for k in range(1, 5):
            self.assertIn(f">Q{k}<", testo)
        self.assertIn("Prova &lt;b&gt;", testo)

    def test_tabellone_grande_su_piu_fogli(self):
        # 38 giocatori, 16 qualificati entranti e un vincitore: ogni foglio ha al
        # massimo 32 righe, e il foglio finale ha gli ultimi turni tra i vincenti dei fogli.
        diretti = ["2.4"] + ["2.5"] * 3 + ["2.6"] * 6 + ["2.7"] * 12 + ["2.8"] * 16
        scala, _ = scala_migliore(diretti, 16, 1, LIVELLO)
        tabellone = prepara(scala, 7, giocatori_per(diretti), LIVELLO, 0, random.Random(0))
        testo = pagina(tabellone, {"nome": "Prova", "gara": "Singolare"})
        controllo = ControlloDeiTag()
        controllo.feed(testo)
        self.assertEqual((controllo.errori, controllo.aperti), ([], []))
        fogli = testo.split('class="foglio"')[1:]
        self.assertGreater(len(fogli), 2)
        for foglio in fogli:
            righe = foglio.count('class="codice-svg"') + foglio.count(">vincente del foglio")
            self.assertLessEqual(righe, 32)
        self.assertIn("vincente del foglio 1", fogli[-1])


if __name__ == "__main__":
    unittest.main()
