"""Prove della lettura dei file. Si avviano con:  py -m unittest discover prove"""

import os
import tempfile
import unittest

from programma.dati import AVVISO, ERRORE, leggi_classifiche, leggi_giocatori, leggi_torneo

CLASSIFICHE = ["3.1", "3.2", "4.1", "4.NC"]


def scrivi_file(testo, codifica="utf-8"):
    f = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding=codifica)
    f.write(testo)
    f.close()
    return f.name


class ProvaFile(unittest.TestCase):
    def setUp(self):
        self.da_cancellare = []

    def tearDown(self):
        for percorso in self.da_cancellare:
            os.remove(percorso)

    def file(self, testo, codifica="utf-8"):
        percorso = scrivi_file(testo, codifica)
        self.da_cancellare.append(percorso)
        return percorso


class ProveGiocatori(ProvaFile):
    def test_file_corretto(self):
        percorso = self.file("# commento\n\nA1 ; 3.1 ; TC Uno\nA2;4.nc;TC Due\n")
        giocatori, problemi = leggi_giocatori(percorso, CLASSIFICHE)
        self.assertEqual(problemi, [])
        self.assertEqual([g.codice for g in giocatori], ["A1", "A2"])
        self.assertEqual(giocatori[1].classifica, "4.NC")

    def test_classifica_con_la_virgola(self):
        giocatori, problemi = leggi_giocatori(self.file("A1 ; 3,2 ; TC Uno\n"), CLASSIFICHE)
        self.assertEqual(problemi, [])
        self.assertEqual(giocatori[0].classifica, "3.2")

    def test_classifica_sconosciuta(self):
        giocatori, problemi = leggi_giocatori(self.file("A1 ; 5.1 ; TC Uno\n"), CLASSIFICHE)
        self.assertEqual(giocatori, [])
        self.assertEqual(problemi[0].gravita, ERRORE)
        self.assertIn("5.1", problemi[0].messaggio)

    def test_codice_ripetuto(self):
        percorso = self.file("A1 ; 3.1 ; TC Uno\na1 ; 3.2 ; TC Due\n")
        giocatori, problemi = leggi_giocatori(percorso, CLASSIFICHE)
        self.assertEqual(len(giocatori), 1)
        self.assertEqual(problemi[0].riga, 2)
        self.assertIn("riga 1", problemi[0].messaggio)

    def test_dati_mancanti(self):
        percorso = self.file("A1 ; 3.1\nA2 ; ; TC Uno\nA3 ; 3.1 ;\n")
        giocatori, problemi = leggi_giocatori(percorso, CLASSIFICHE)
        self.assertEqual(giocatori, [])
        self.assertEqual([p.riga for p in problemi], [1, 2, 3])

    def test_file_vuoto(self):
        giocatori, problemi = leggi_giocatori(self.file("# solo commenti\n"), CLASSIFICHE)
        self.assertEqual(giocatori, [])
        self.assertEqual(len(problemi), 1)

    def test_file_salvato_con_codifica_windows(self):
        percorso = self.file("A1 ; 3.1 ; Città Tennis\n", codifica="cp1252")
        giocatori, problemi = leggi_giocatori(percorso, CLASSIFICHE)
        self.assertEqual(problemi, [])
        self.assertEqual(giocatori[0].circolo, "Città Tennis")

    def test_stesso_circolo_scritto_diversamente(self):
        percorso = self.file("A1 ; 3.1 ; TC  Uno\nA2 ; 3.1 ; tc uno\n")
        giocatori, _ = leggi_giocatori(percorso, CLASSIFICHE)
        self.assertEqual(giocatori[0].chiave_circolo, giocatori[1].chiave_circolo)


class ProveClassifiche(ProvaFile):
    def test_ordine_e_doppioni(self):
        classifiche, problemi = leggi_classifiche(self.file("3.1\n3.2\n3,1\n"))
        self.assertEqual(classifiche, ["3.1", "3.2"])
        self.assertEqual(len(problemi), 1)

    def test_file_della_cartella_dati(self):
        percorso = os.path.join(os.path.dirname(__file__), "..", "dati", "classifiche.txt")
        classifiche, problemi = leggi_classifiche(percorso)
        self.assertEqual(problemi, [])
        self.assertEqual(classifiche[0], "2.1")
        self.assertEqual(classifiche[-1], "4.NC")
        self.assertEqual(len(classifiche), 8 + 5 + 7)


class ProveTorneo(ProvaFile):
    def test_torneo_corretto(self):
        torneo, problemi = leggi_torneo(self.file("Nome = Torneo = Uno\ngara = Singolare\n"))
        self.assertEqual(problemi, [])
        self.assertEqual(torneo.impostazioni["nome"], "Torneo = Uno")

    def test_impostazioni_sbagliate(self):
        torneo, problemi = leggi_torneo(self.file("nome = Uno\ncolore = rosso\nriga senza uguale\n"))
        gravita = sorted(p.gravita for p in problemi)
        # riga senza "=", "gara" mancante: errori; "colore" sconosciuta: avviso
        self.assertEqual(gravita, [AVVISO, ERRORE, ERRORE])

    def test_impostazioni_con_numeri(self):
        percorso = self.file("nome = Uno\ngara = Due\nqualificati  Entranti = 4\n"
                             "qualificati uscenti = 0\nteste di serie = tre\n")
        torneo, problemi = leggi_torneo(percorso)
        self.assertEqual(torneo.impostazioni["qualificati entranti"], 4)
        self.assertEqual([p.riga for p in problemi], [4, 5])


if __name__ == "__main__":
    unittest.main()
