"""Prove della finestra (programma/finestra.py).

Servono tkinter e uno schermo: se mancano, queste prove vengono saltate.
Si avviano con:  py -m unittest discover prove
"""

import os
import tempfile
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
        self.addCleanup(self.radice.update)  # prima di chiudere, finisce quello che resta da fare

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

    def test_carica_dall_excel(self):
        from prove.test_excel import INTESTAZIONE, riga_fitp, xlsx
        with tempfile.TemporaryDirectory() as cartella:
            excel = os.path.join(cartella, "iscritti.xlsx")
            with open(excel, "wb") as f:
                f.write(xlsx(INTESTAZIONE + riga_fitp("ROSSI", "MARIO", "3.4", "1", "TC Uno")))
            vecchia = finestra.CARTELLA_DATI_VERI
            finestra.CARTELLA_DATI_VERI = os.path.join(cartella, "dati-veri")
            self.addCleanup(setattr, finestra, "CARTELLA_DATI_VERI", vecchia)
            self.assertTrue(self.finestra.carica_excel(excel))
            nuovo = self.finestra.file_dati["giocatori"].get()
            self.assertEqual(nuovo, os.path.join(cartella, "dati-veri", "giocatori - iscritti.txt"))
            with open(nuovo, encoding="utf-8") as f:
                self.assertIn("ROSSI Mario ; 3.4", f.read())
            self.assertIn("Presi 1 giocatori", self.testo())
            # Un file che non e' un Excel: si dice perche', e il file dei giocatori non cambia.
            self.assertFalse(self.finestra.carica_excel(os.path.join("dati", "giocatori.txt")))
            self.assertIn("non e' un file Excel", self.testo())
            self.assertEqual(self.finestra.file_dati["giocatori"].get(), nuovo)

    def test_maschera_del_torneo(self):
        from prove.test_maschera import FILE_DEL_GIUDICE
        with tempfile.TemporaryDirectory() as cartella:
            torneo = os.path.join(cartella, "torneo.txt")
            with open(torneo, "w", encoding="utf-8") as f:
                f.write(FILE_DEL_GIUDICE)
            self.finestra.file_dati["torneo"].set(torneo)
            self.finestra.file_dati["classifiche"].set(os.path.join("dati", "classifiche.txt"))
            self.finestra.file_dati["giocatori"].set(os.path.join("dati", "giocatori.txt"))
            maschera = self.finestra.apri_maschera()
            self.assertEqual(maschera.quanti.get(), "4 tabelloni collegati")
            self.assertEqual(len(maschera.righe), 4)
            # Senza giorni: le date scritte a mano ("dal  al  novembre") non vanno bene.
            self.assertFalse(maschera.conferma())
            self.assertIn("manca il giorno", maschera.messaggio.cget("text"))
            maschera.date["inizio"][0].set("20")
            maschera.date["inizio"][1].set("novembre")
            maschera.date["fine"][0].set("31")
            maschera.date["fine"][1].set("novembre")
            self.assertFalse(maschera.conferma())
            self.assertIn("31 novembre", maschera.messaggio.cget("text"))
            maschera.date["fine"][0].set("30")
            maschera.righe[1]["teste"].set("4")
            maschera.righe[1]["uscenti"].set("4")
            # Nel primo tabellone (solo 4.NC) le teste di serie non si scelgono.
            self.assertEqual(maschera.righe[0]["teste"].get(), "nessuna (non classificati)")
            self.assertTrue(maschera.conferma())
            with open(torneo, encoding="utf-8") as f:
                testo = f.read()
        self.assertIn("date = dal 20 al 30 novembre", testo)
        self.assertIn("teste di serie = 4 ; qualificati uscenti = 4", testo)
        self.assertIn("Salvato in", self.testo())

    def test_maschera_non_tocca_il_file_di_esempio(self):
        with tempfile.TemporaryDirectory() as cartella:
            vecchia = finestra.CARTELLA_DATI_VERI
            finestra.CARTELLA_DATI_VERI = os.path.join(cartella, "dati-veri")
            self.addCleanup(setattr, finestra, "CARTELLA_DATI_VERI", vecchia)
            self.finestra.file_dati["torneo"].set(os.path.join("dati", "torneo.txt"))
            self.finestra.file_dati["classifiche"].set(os.path.join("dati", "classifiche.txt"))
            maschera = self.finestra.apri_maschera()
            maschera.cambia_quanti()
            self.assertTrue(maschera.conferma())
            self.assertEqual(self.finestra.file_dati["torneo"].get(),
                             os.path.join(cartella, "dati-veri", "torneo.txt"))

    def test_percorsi_relativi(self):
        dentro = os.path.join(os.getcwd(), "dati", "giocatori.txt")
        self.assertEqual(finestra.percorso_relativo(dentro), os.path.join("dati", "giocatori.txt"))
        fuori = os.path.abspath(os.path.join(os.getcwd(), "..", "altro.txt"))
        self.assertEqual(finestra.percorso_relativo(fuori), fuori)


if __name__ == "__main__":
    unittest.main()
