"""Prove della pagina nel browser (index.html, web/).

Senza browser si puo' controllare solo che i pezzi siano a posto: che
web/pyscript.toml elenchi tutti i file che servono, che index.html carichi
PyScript con una versione precisa, che .nojekyll esista, e che web/pagina.py
si importi e le sue funzioni "pure" facciano quello che devono.
La prova vera, nel browser, si fa a mano prima di ogni push su main (PIANO.txt, 10d).
Si avviano con:  py -m unittest discover prove
"""

import ast
import datetime
import importlib
import os
import re
import sys
import unittest
from unittest import mock

CARTELLA = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIGURAZIONE = os.path.join(CARTELLA, "web", "pyscript.toml")
PAGINA = os.path.join(CARTELLA, "index.html")


def leggi(percorso):
    with open(percorso, encoding="utf-8") as f:
        return f.read()


def file_della_configurazione():
    """Le coppie (da dove, dove) della sezione [files], come percorsi dalla cartella principale."""
    coppie = []
    for riga in leggi(CONFIGURAZIONE).splitlines():
        trovato = re.match(r'"([^"]+)"\s*=\s*"([^"]+)"', riga.strip())
        if trovato:
            da, a = trovato.groups()
            coppie.append((os.path.normpath(os.path.join("web", da)), os.path.normpath(a)))
    return coppie


class ProveConfigurazione(unittest.TestCase):
    def test_i_file_elencati_esistono_e_vanno_allo_stesso_posto(self):
        coppie = file_della_configurazione()
        self.assertTrue(coppie)
        for da, a in coppie:
            self.assertTrue(os.path.exists(os.path.join(CARTELLA, da)), f"manca {da}")
            self.assertEqual(da, a, "il file deve avere lo stesso nome nella cartella finta")

    def test_tutti_i_moduli_e_i_dati_sono_elencati(self):
        elencati = {a for _, a in file_della_configurazione()}
        attesi = {"tabelloni.py"}
        for nome in os.listdir(os.path.join(CARTELLA, "programma")):
            if nome.endswith(".py") and nome != "finestra.py":  # finestra.py e' solo per tkinter
                attesi.add(os.path.join("programma", nome))
        for nome in ("giocatori.txt", "torneo.txt", "classifiche.txt", "tabellone-da-controllare.txt"):
            attesi.add(os.path.join("dati", nome))
        self.assertEqual(attesi - elencati, set(), "file che mancano in web/pyscript.toml")
        self.assertNotIn(os.path.join("programma", "finestra.py"), elencati)

    def test_nojekyll(self):
        self.assertTrue(os.path.exists(os.path.join(CARTELLA, ".nojekyll")))


class ProvePaginaHtml(unittest.TestCase):
    def test_pyscript_con_versione_precisa(self):
        pagina = leggi(PAGINA)
        versioni = set(re.findall(r"pyscript\.net/releases/([^/]+)/core\.(?:js|css)", pagina))
        self.assertEqual(len(versioni), 1, "core.js e core.css devono avere la stessa versione")
        versione = versioni.pop()
        self.assertRegex(versione, r"^\d{4}\.\d+\.\d+$", "versione precisa, non 'latest'")
        for indirizzo in re.findall(r"https://pyscript\.net/\S+", pagina):
            self.assertNotIn("latest", indirizzo)

    def test_la_pagina_usa_i_file_di_web(self):
        pagina = leggi(PAGINA)
        self.assertIn('src="web/pagina.py"', pagina)
        self.assertIn('config="web/pyscript.toml"', pagina)
        self.assertIn('href="web/stile.css"', pagina)
        for percorso in ("web/pagina.py", "web/pyscript.toml", "web/stile.css"):
            self.assertTrue(os.path.exists(os.path.join(CARTELLA, percorso)))

    def test_percorsi_solo_relativi(self):
        pagina = leggi(PAGINA)
        self.assertNotRegex(pagina, r'(src|href)="/', "niente percorsi che cominciano con /")

    def test_i_pulsanti_della_pagina_esistono(self):
        pagina = leggi(PAGINA)
        for identificatore in ("fai", "controlla", "stampa-tabellone", "apri-scheda", "scarica-html",
                               "scarica-txt", "copia-tutto", "scarica-tutto", "stato", "risultati",
                               "stampa", "testo-giocatori", "testo-torneo", "testo-classifiche",
                               "testo-tabellone"):
            self.assertIn(f'id="{identificatore}"', pagina, f"manca id={identificatore}")


class ProvePaginaPy(unittest.TestCase):
    """web/pagina.py importato con un finto pyscript, per provare le funzioni senza browser."""

    @classmethod
    def setUpClass(cls):
        codice = leggi(os.path.join(CARTELLA, "web", "pagina.py"))
        ast.parse(codice)  # almeno la sintassi
        finto = mock.MagicMock()
        finto.when = lambda *a, **k: (lambda f: f)
        cls.vecchio = sys.modules.get("pyscript")
        sys.modules["pyscript"] = finto
        sys.path.insert(0, os.path.join(CARTELLA, "web"))
        cartella_prima = os.getcwd()
        os.chdir(CARTELLA)  # avvia() legge dati/ con percorsi relativi
        try:
            cls.pagina = importlib.import_module("pagina")
        finally:
            os.chdir(cartella_prima)

    @classmethod
    def tearDownClass(cls):
        sys.path.remove(os.path.join(CARTELLA, "web"))
        sys.modules.pop("pagina", None)
        if cls.vecchio is None:
            sys.modules.pop("pyscript", None)
        else:
            sys.modules["pyscript"] = cls.vecchio

    def test_la_pagina_non_apre_il_browser_da_sola(self):
        import tabelloni
        self.assertFalse(tabelloni.APRI_BROWSER)

    def test_gli_esempi_sono_i_file_di_dati(self):
        self.assertEqual(set(self.pagina.ESEMPI), {"giocatori", "torneo", "classifiche", "tabellone"})
        self.assertIn("nome = Torneo di prova", self.pagina.ESEMPI["torneo"])

    def test_decodifica(self):
        self.assertEqual(self.pagina.decodifica("ciao".encode("utf-8-sig")), "ciao")
        self.assertEqual(self.pagina.decodifica("perché".encode("cp1252")), "perché")

    def test_righe_colorate(self):
        colorate = self.pagina.righe_colorate("tutto bene\nERRORE - manca <x>\nAVVISO - attenzione")
        self.assertEqual(colorate.splitlines()[0], "tutto bene")
        self.assertIn('<span class="errore">ERRORE - manca &lt;x&gt;</span>', colorate)
        self.assertIn('<span class="avviso">AVVISO - attenzione</span>', colorate)

    def test_testo_segnalazione(self):
        testo = self.pagina.testo_segnalazione(
            {"giocatori": "A1 ; 4.6 ; TC Prova\n", "torneo": "nome = X", "classifiche": "4.6"},
            ("Tabellone", "PROBLEMI TROVATI:\n  ERRORE - qualcosa"),
            adesso=datetime.datetime(2026, 10, 7, 9, 30))
        self.assertIn("07/10/2026 09:30", testo)
        self.assertIn("===== dati/giocatori.txt =====\nA1 ; 4.6 ; TC Prova\n", testo.replace("\\", "/"))
        self.assertIn("===== RISULTATI (Tabellone) =====\nPROBLEMI TROVATI:", testo)
        senza = self.pagina.testo_segnalazione({"torneo": "nome = X"}, None)
        self.assertIn("nessuno", senza)


if __name__ == "__main__":
    unittest.main()
