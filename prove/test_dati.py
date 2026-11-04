"""Prove della lettura dei file. Si avviano con:  py -m unittest discover prove"""

import os
import tempfile
import unittest

from programma.dati import (AVVISO, ERRORE, controlla_date, leggi_classifiche, leggi_giocatori,
                            leggi_torneo)

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

    def test_nomi_al_posto_dei_codici(self):
        percorso = self.file("ROSSI   Mario ; 3.1 ; TC Uno\nrossi mario ; 3.2 ; TC Due\n"
                             "ROSSI Mario (2) ; 3.2 ; TC Due\n")
        giocatori, problemi = leggi_giocatori(percorso, CLASSIFICHE)
        self.assertEqual([g.codice for g in giocatori], ["ROSSI Mario", "ROSSI Mario (2)"])
        self.assertEqual([(p.gravita, p.riga) for p in problemi], [(ERRORE, 2)])
        self.assertIn("gia' usato alla riga 1", problemi[0].messaggio)

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

    def test_tipo_e_scala(self):
        percorso = self.file("nome = Uno\ngara = Due\ntipo = Selezione\n"
                             "turno 2 = 4 (4.3)\nturno 1 = coppie 4 (4.4)+q\n")
        torneo, problemi = leggi_torneo(percorso)
        self.assertEqual(problemi, [])
        self.assertEqual(torneo.impostazioni["tipo"], "selezione")
        self.assertEqual(torneo.impostazioni["turno 1"], "coppie 4 (4.4)+q")

    def test_tipo_sbagliato(self):
        torneo, problemi = leggi_torneo(self.file("nome = Uno\ngara = Due\ntipo = misto\n"))
        self.assertEqual([p.gravita for p in problemi], [ERRORE])
        self.assertIn("selezione, estrazione", problemi[0].messaggio)


    def test_data_che_non_esiste(self):
        # Segnalato dal primo giudice arbitro che ha provato il programma: il 31 novembre.
        torneo, problemi = leggi_torneo(self.file("nome = Uno\ngara = Due\n"
                                                  "date = dal 25 al 31 novembre\n"))
        self.assertEqual([(p.gravita, p.riga) for p in problemi], [(ERRORE, 3)])
        self.assertIn("31 novembre non esiste", problemi[0].messaggio)


class ProveDate(unittest.TestCase):
    def gravita(self, testo):
        return [g for g, _ in controlla_date(testo)]

    def test_date_giuste(self):
        for testo in ("dal 1 al 10 ottobre", "dal 1 al 10 ottobre 2026", "1-10 nov 2026",
                      "dal 28 febbraio al 3 marzo 2027", "29 febbraio 2028", "29 febbraio",
                      "dal 28 dicembre al 3 gennaio 2027", "dal 28 dicembre al 3 gennaio",
                      "01/11/2026 - 30/11/2026", "1-11-2026", "torneo di Natale"):
            self.assertEqual(self.gravita(testo), [], testo)

    def test_giorni_che_non_esistono(self):
        for testo in ("dal 31 novembre al 2 dicembre", "30 febbraio", "29 febbraio 2027",
                      "dal 1/11 al 31/11", "31 aprile 2026", "32 marzo", "0 marzo", "1/13/2026"):
            self.assertEqual(self.gravita(testo), [ERRORE], testo)

    def test_fine_prima_dell_inizio(self):
        self.assertEqual(self.gravita("dal 10 al 3 ottobre"), [ERRORE])
        self.assertEqual(self.gravita("dal 3 novembre al 30 ottobre 2026"), [ERRORE])

    def test_giorni_o_mese_mancanti(self):
        self.assertEqual(self.gravita("dal  al  novembre"), [AVVISO])
        self.assertEqual(self.gravita("dal 1 al 10"), [AVVISO, AVVISO])


if __name__ == "__main__":
    unittest.main()
