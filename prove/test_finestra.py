"""Prove della finestra (programma/finestra.py).

Servono tkinter e uno schermo: se mancano, queste prove vengono saltate.
Si avviano con:  py -m unittest discover prove
"""

import os
import unittest

try:
    import tkinter as tk
    from programma import finestra
    tk.Tk().destroy()
    MANCA = None
except Exception as problema:  # manca tkinter o manca lo schermo
    MANCA = str(problema)


@unittest.skipIf(MANCA, f"finestra non disponibile: {MANCA}")
class ProveFinestra(unittest.TestCase):
    def setUp(self):
        self.chiamate = []
        self.radice = tk.Tk()
        self.radice.withdraw()
        self.addCleanup(self.radice.destroy)

        def fai_tabellone(file_dati):
            self.chiamate.append(("fai", file_dati))
            print("Tabellone salvato")
            return True

        def controlla_file(percorso, file_dati):
            self.chiamate.append(("controlla", percorso))
            print("ERRORE: qualcosa non va")
            return False

        self.finestra = finestra.Finestra(
            self.radice, fai_tabellone=fai_tabellone, controlla_file=controlla_file,
            file_dati={"giocatori": "g.txt", "torneo": "t.txt", "classifiche": "c.txt"},
            file_da_controllare="dati/x.txt", file_da_stampare="non-esiste.html",
            cartella_risultati="risultati")

    def testo(self):
        return self.finestra.testo.get("1.0", "end")

    def test_fai_il_tabellone(self):
        self.assertTrue(self.finestra.fai())
        self.assertEqual(self.chiamate, [("fai", {"giocatori": "g.txt", "torneo": "t.txt",
                                                  "classifiche": "c.txt"})])
        self.assertIn("Tabellone salvato", self.testo())

    def test_controlla_mostra_gli_errori_in_rosso(self):
        self.assertFalse(self.finestra.controlla("prova.txt"))
        self.assertEqual(self.chiamate[0], ("controlla", "prova.txt"))
        rossi = self.finestra.testo.tag_ranges("errore")
        self.assertTrue(rossi)
        self.assertIn("qualcosa non va", self.finestra.testo.get(rossi[0], rossi[1]))

    def test_un_errore_inatteso_non_chiude_il_programma(self):
        def guasta(file_dati):
            raise ValueError("guasto di prova")
        self.finestra.fai_tabellone = guasta
        self.assertFalse(self.finestra.fai())
        self.assertIn("ERRORE inatteso", self.testo())
        self.assertIn("guasto di prova", self.testo())

    def test_pulsante_stampa_spento_se_manca_il_file(self):
        pulsante = self.finestra.pulsanti["Apri il tabellone da stampare"]
        self.assertIn("disabled", pulsante.state())

    def test_percorsi_relativi(self):
        dentro = os.path.join(os.getcwd(), "dati", "giocatori.txt")
        self.assertEqual(finestra.percorso_relativo(dentro), os.path.join("dati", "giocatori.txt"))
        fuori = os.path.abspath(os.path.join(os.getcwd(), "..", "altro.txt"))
        self.assertEqual(finestra.percorso_relativo(fuori), fuori)


if __name__ == "__main__":
    unittest.main()
