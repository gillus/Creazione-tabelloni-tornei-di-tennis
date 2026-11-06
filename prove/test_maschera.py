"""Prove della maschera "Compila il torneo". Si avviano con:  py -m unittest discover prove"""

import datetime
import os
import tempfile
import unittest

from programma.collegati import leggi_divisione
from programma.dati import ERRORE, leggi_classifiche, leggi_torneo
from programma.maschera import (AUTOMATICO, Maschera, TabelloneDellaMaschera,
                                classifiche_dei_tabelloni, data_da_parti, date_dal_testo,
                                descrivi_tabellone, giocatori_per_classifica, maschera_dal_testo,
                                problemi_della_maschera, riepilogo_iscritti, scelte_della_piu_alta,
                                testo_dalla_maschera,
                                testo_delle_date, un_tabellone_per_categoria)

CLASSIFICHE, _ = leggi_classifiche(os.path.join("dati", "classifiche.txt"))

# Il file che il primo giudice arbitro ha scritto per non sbagliare (i numeri vuoti
# li riempiva ogni volta): quattro tabelloni collegati.
FILE_DEL_GIUDICE = """nome = Torneo
gara = Singolare maschile
date = dal  al  novembre
tabellone 1 = 4.NC ; qualificati uscenti =
tabellone 2 = 4.6, 4.5, 4.4, 4.3, 4.2, 4.1 ; qualificati uscenti =  ; teste di serie =
tabellone 3 = 3.5, 3.4, 3.3, 3.2, 3.1 ; qualificati uscenti =  ; teste di serie =
tabellone 4 = 2.7, 2.6, 2.5, 2.4 ; qualificati uscenti =  ; teste di serie =
"""


def leggi(testo):
    """Il testo come lo legge il programma: impostazioni, divisione e tutti i problemi."""
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(testo)
    try:
        torneo, problemi = leggi_torneo(f.name)
    finally:
        os.remove(f.name)
    parti, altri = leggi_divisione(torneo.impostazioni, CLASSIFICHE)
    return torneo.impostazioni, parti, problemi + altri


class ProveDate(unittest.TestCase):
    def test_testo_delle_date(self):
        d = datetime.date
        self.assertEqual(testo_delle_date(d(2026, 11, 1), d(2026, 11, 10)), "dal 1 al 10 novembre 2026")
        self.assertEqual(testo_delle_date(d(2026, 11, 28), d(2026, 12, 3)),
                         "dal 28 novembre al 3 dicembre 2026")
        self.assertEqual(testo_delle_date(d(2026, 12, 28), d(2027, 1, 3)),
                         "dal 28 dicembre 2026 al 3 gennaio 2027")
        self.assertEqual(testo_delle_date(d(2026, 11, 7), d(2026, 11, 7)), "7 novembre 2026")
        self.assertEqual(testo_delle_date(None, None), "")

    def test_si_rilegge(self):
        d = datetime.date
        for inizio, fine in ((d(2026, 11, 1), d(2026, 11, 10)), (d(2026, 11, 28), d(2026, 12, 3)),
                             (d(2026, 12, 28), d(2027, 1, 3)), (d(2028, 2, 29), d(2028, 2, 29))):
            self.assertEqual(date_dal_testo(testo_delle_date(inizio, fine)), (inizio, fine))
        self.assertIsNone(date_dal_testo("dal 31 novembre al 2 dicembre"))
        self.assertIsNone(date_dal_testo("fine novembre"))

    def test_data_dai_menu(self):
        self.assertEqual(data_da_parti("10", "novembre", "2026"), (datetime.date(2026, 11, 10), ""))
        self.assertEqual(data_da_parti("", "", "2026"), (None, ""))
        data, errore = data_da_parti("31", "novembre", "2026")
        self.assertIsNone(data)
        self.assertIn("non esiste", errore)
        self.assertIn("non esiste", data_da_parti("29", "febbraio", "2027")[1])
        self.assertEqual(data_da_parti("29", "febbraio", "2028")[1], "")


class ProveMaschera(unittest.TestCase):
    def test_file_del_giudice_arbitro(self):
        maschera = maschera_dal_testo(FILE_DEL_GIUDICE, CLASSIFICHE)
        self.assertFalse(maschera.divisione_automatica)
        self.assertEqual([t.piu_alta for t in maschera.tabelloni], ["4.NC", "4.1", "3.1", ""])
        self.assertTrue(all(t.qualificati_uscenti is AUTOMATICO for t in maschera.tabelloni))
        self.assertEqual(maschera.date_scritte, "dal  al  novembre")
        # Compilato con la maschera: 4 qualificati da ogni tabellone, teste di serie scelte.
        maschera.date_scritte = ""
        maschera.inizio, maschera.fine = datetime.date(2026, 11, 20), datetime.date(2026, 11, 30)
        for tabellone, uscenti, teste in zip(maschera.tabelloni, (4, 4, 2, 1), (None, 4, 4, 2)):
            tabellone.qualificati_uscenti, tabellone.teste_di_serie = uscenti, teste
        self.assertEqual(problemi_della_maschera(maschera, CLASSIFICHE), [])
        testo = testo_dalla_maschera(maschera, CLASSIFICHE)
        self.assertIn("date = dal 20 al 30 novembre 2026", testo)
        self.assertIn("tabellone 1 = 4.NC ; qualificati uscenti = 4\n", testo)
        self.assertIn("tabellone 2 = 4.1, 4.2, 4.3, 4.4, 4.5, 4.6 ; teste di serie = 4 ; "
                      "qualificati uscenti = 4\n", testo)
        # L'ultimo arriva fino alla classifica piu' alta.
        self.assertIn("tabellone 4 = 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8 ; teste di serie = 2 ; "
                      "qualificati uscenti = 1\n", testo)
        impostazioni, parti, problemi = leggi(testo)
        self.assertEqual(problemi, [])
        self.assertEqual([p.classifiche[-1] for p in parti], ["4.NC", "4.6", "3.5", "2.8"])
        self.assertEqual(parti[1].impostazioni, {"teste di serie": 4, "qualificati uscenti": 4})
        # E rileggendo il testo si ritrova la stessa maschera.
        di_nuovo = maschera_dal_testo(testo, CLASSIFICHE)
        self.assertEqual(di_nuovo.tabelloni, maschera.tabelloni)
        self.assertEqual((di_nuovo.inizio, di_nuovo.fine), (maschera.inizio, maschera.fine))

    def test_solo_le_classifiche_degli_iscritti(self):
        maschera = maschera_dal_testo(FILE_DEL_GIUDICE, CLASSIFICHE)
        presenti = {"4.NC", "4.3", "4.1", "3.2", "2.6", "2.5"}
        testo = testo_dalla_maschera(maschera, CLASSIFICHE, presenti)
        self.assertIn("tabellone 2 = 4.1, 4.3\n", testo)
        self.assertIn("tabellone 4 = 2.5, 2.6\n", testo)

    def test_esempio_della_cartella_dati(self):
        with open(os.path.join("dati", "torneo.txt"), encoding="utf-8") as f:
            originale = f.read()
        maschera = maschera_dal_testo(originale, CLASSIFICHE)
        self.assertTrue(maschera.divisione_automatica)
        self.assertEqual(maschera.qualificati_entranti, 4)
        self.assertEqual(maschera.tabelloni[0].qualificati_uscenti, 4)
        testo = testo_dalla_maschera(maschera, CLASSIFICHE)
        # Le spiegazioni in cima restano.
        self.assertTrue(testo.startswith("# IMPOSTAZIONI DEL TORNEO"))
        self.assertIn("#   nome                  il nome del torneo", testo)
        prima, _, problemi_prima = leggi(originale)
        dopo, _, problemi_dopo = leggi(testo)
        self.assertEqual(problemi_dopo, problemi_prima)
        self.assertEqual({k: v for k, v in dopo.items() if k != "date"},
                         {k: v for k, v in prima.items() if k != "date"})

    def test_righe_scritte_a_mano_restano(self):
        testo = ("nome = Uno\ngara = Due\nturno 3 = 3 (4.1), 1 (4.2)\nturno 1 = coppie 4 (4.4)+q\n"
                 "colore = rosso\nteste di serie = 4\n")
        maschera = maschera_dal_testo(testo, CLASSIFICHE)
        self.assertEqual(maschera.tabelloni[0].teste_di_serie, 4)
        nuovo = testo_dalla_maschera(maschera, CLASSIFICHE)
        for riga in ("turno 3 = 3 (4.1), 1 (4.2)", "turno 1 = coppie 4 (4.4)+q", "colore = rosso",
                     "teste di serie = 4"):
            self.assertIn(riga + "\n", nuovo)
        self.assertTrue(nuovo.startswith("# IMPOSTAZIONI DEL TORNEO"))

    def test_niente_teste_di_serie_tra_i_non_classificati(self):
        maschera = Maschera(nome="Uno", gara="Due", divisione_automatica=False,
                            tabelloni=[TabelloneDellaMaschera("4.NC", teste_di_serie=2),
                                       TabelloneDellaMaschera("", teste_di_serie=4)])
        testo = testo_dalla_maschera(maschera, CLASSIFICHE)
        self.assertIn("tabellone 1 = 4.NC\n", testo)
        self.assertIn("teste di serie = 4", testo)

    def test_scelte_dei_menu(self):
        maschera = Maschera(divisione_automatica=False,
                            tabelloni=[TabelloneDellaMaschera("4.NC"), TabelloneDellaMaschera("4.1"),
                                       TabelloneDellaMaschera("")])
        self.assertEqual(scelte_della_piu_alta(maschera, 0, CLASSIFICHE)[:2], ["4.NC", "4.6"])
        # Ai due tabelloni dopo deve restare almeno una classifica ciascuno.
        self.assertEqual(scelte_della_piu_alta(maschera, 0, CLASSIFICHE)[-1], "2.3")
        self.assertEqual(scelte_della_piu_alta(maschera, 1, CLASSIFICHE)[0], "4.6")
        self.assertEqual(classifiche_dei_tabelloni(maschera, CLASSIFICHE)[2][-1], "3.5")

    def test_un_tabellone_per_categoria(self):
        presenti = {"4.NC", "4.6", "4.1", "3.5", "3.1", "2.7", "2.4"}
        self.assertEqual(un_tabellone_per_categoria(CLASSIFICHE, presenti), ["4.NC", "4.1", "3.1", "2.4"])

    def test_descrizione_con_i_giocatori(self):
        conteggio = giocatori_per_classifica("# commento\nA ; 4.1 ; X\nB ; 4,3 ; Y\nC ; 3.1 ; Z\n")
        self.assertEqual(conteggio, {"4.1": 1, "4.3": 1, "3.1": 1})
        elenco = ["4.1", "4.2", "4.3", "4.4", "4.5", "4.6"]
        self.assertEqual(descrivi_tabellone(elenco, conteggio), "da 4.3 a 4.1 (4a categoria) - 2 giocatori")
        self.assertEqual(descrivi_tabellone(elenco), "da 4.6 a 4.1 (4a categoria)")

    def test_iscritti_per_classifica(self):
        # Chiesto dal primo giudice arbitro: "cat 4.5: 10; cat 4.4: 5; cat 3.3: 12; cat 2.5: 6".
        conteggio = {"4.5": 10, "4.4": 5, "3.3": 12, "2.5": 6, "4.NC": 3, "5.1": 1}
        self.assertEqual(riepilogo_iscritti(conteggio, CLASSIFICHE), [
            "non classificati (3): 4.NC: 3",
            "4a categoria (15): 4.5: 10 · 4.4: 5",
            "3a categoria (12): 3.3: 12",
            "2a categoria (6): 2.5: 6",
            "classifiche sconosciute, da correggere: 5.1: 1",
            "in tutto: 37 iscritti"])
        self.assertEqual(riepilogo_iscritti({}, CLASSIFICHE), [])

    def test_problemi(self):
        maschera = Maschera(inizio=datetime.date(2026, 11, 10), fine=datetime.date(2026, 11, 1),
                            divisione_automatica=False,
                            tabelloni=[TabelloneDellaMaschera("4.NC", tipo="integrale"),
                                       TabelloneDellaMaschera("")])
        problemi = problemi_della_maschera(maschera, CLASSIFICHE)
        self.assertEqual(len(problemi), 4)
        self.assertTrue(any("integrale" in p for p in problemi))


if __name__ == "__main__":
    unittest.main()
