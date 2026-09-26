"""Prove dei tabelloni collegati (programma/collegati.py) con gli esercizi del manuale.

Le divisioni del manuale sono nel file prove/esercizi/divisioni-in-piu-tabelloni.txt.
Si avviano con:  py -m unittest discover prove
"""

import os
import random
import re
import tempfile
import unittest

from programma.collegati import (leggi_divisione, prepara_divisione, proponi_divisione,
                                 qualificati_proposti)
from programma.dati import AVVISO, ERRORE, leggi_righe
from prove.test_calcoli import CLASSIFICHE, leggi_elenco
from prove.test_sorteggio import giocatori_di_prova

FILE_DIVISIONI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "esercizi",
                              "divisioni-in-piu-tabelloni.txt")


def leggi_divisioni():
    esercizi = {}
    nome = None
    for _, riga in leggi_righe(FILE_DIVISIONI):
        if riga.startswith("["):
            nome = riga.strip("[]")
            esercizi[nome] = {}
        else:
            chiave, valore = (parte.strip() for parte in riga.split("=", 1))
            esercizi[nome][chiave] = valore
    return esercizi


def giocatori_di(esercizio):
    elenco = leggi_elenco(esercizio["giocatori"])
    rng = random.Random(0)
    return giocatori_di_prova([(c, f"Circolo {rng.randint(0, 5)}")
                               for c in CLASSIFICHE for _ in range(elenco.get(c, 0))])


def righe_dei_tabelloni(esercizio, con_uscenti=True):
    righe = {k: v for k, v in esercizio.items() if k.startswith("tabellone ")}
    if not con_uscenti:
        righe = {k: re.sub(r"\s*;\s*qualificati uscenti = \d+", "", v) for k, v in righe.items()}
    return righe


def divisione(esercizio, con_uscenti=True):
    parti, problemi = leggi_divisione(righe_dei_tabelloni(esercizio, con_uscenti), CLASSIFICHE)
    assert not problemi, problemi
    problemi = prepara_divisione(parti, giocatori_di(esercizio), CLASSIFICHE,
                                 int(esercizio.get("qualificati entranti", 0)), 1)
    return parti, problemi


class ProveDivisioniDelManuale(unittest.TestCase):
    def test_ci_sono_tutti_gli_esercizi(self):
        self.assertEqual(len(leggi_divisioni()), 8)

    def test_le_divisioni_del_manuale_rispettano_le_regole(self):
        for nome, esercizio in leggi_divisioni().items():
            with self.subTest(esercizio=nome):
                parti, problemi = divisione(esercizio)
                self.assertEqual([p.messaggio for p in problemi if p.gravita == ERRORE], [])
                # Il numero dei giocatori di ogni tabellone, come nel manuale.
                self.assertEqual(sum(len(p.giocatori) for p in parti), len(giocatori_di(esercizio)))

    def test_qualificati_uscenti_proposti(self):
        for nome, esercizio in leggi_divisioni().items():
            with self.subTest(esercizio=nome):
                manuale, _ = divisione(esercizio)
                attesi = [p.qualificati_uscenti for p in manuale[:-1]]
                if "proposta del programma" in esercizio:
                    attesi = [int(x) for x in esercizio["proposta del programma"].split(",")]
                parti, problemi = divisione(esercizio, con_uscenti=False)
                self.assertEqual([p.messaggio for p in problemi if p.gravita == ERRORE], [])
                self.assertEqual([p.qualificati_uscenti for p in parti[:-1]], attesi)
                self.assertTrue(all(p.uscenti_proposti for p in parti[:-1]))
                self.assertEqual(parti[-1].qualificati_uscenti, 1)

    def test_proposta_per_categoria(self):
        for nome, esercizio in leggi_divisioni().items():
            with self.subTest(esercizio=nome):
                if "proposta per categoria" in esercizio:
                    attesa = [[c.strip() for c in parte.split(",")]
                              for parte in esercizio["proposta per categoria"].split("|")]
                else:
                    attesa = [[c.strip() for c in v.split(";")[0].split(",")]
                              for k, v in sorted(righe_dei_tabelloni(esercizio).items())]
                attesa = [sorted(p, key=CLASSIFICHE.index) for p in attesa]
                parti = proponi_divisione(giocatori_di(esercizio), CLASSIFICHE)
                self.assertEqual([p.classifiche for p in parti], attesa)


class ProveRegoleDellaDivisione(unittest.TestCase):
    def setUp(self):
        self.giocatori = giocatori_di({"giocatori": "8 (4.NC), 6 (4.5), 6 (4.3), 5 (3.5)"})

    def prepara(self, righe, q=0, Qu=1):
        parti, problemi = leggi_divisione(righe, CLASSIFICHE)
        if not problemi:
            problemi = prepara_divisione(parti, self.giocatori, CLASSIFICHE, q, Qu)
        return parti, problemi

    def assertErrore(self, frase, righe, **dati):
        _, problemi = self.prepara(righe, **dati)
        errori = [p.messaggio for p in problemi if p.gravita == ERRORE]
        self.assertTrue(any(frase in e for e in errori), f"manca \"{frase}\": {errori}")

    def test_divisione_giusta(self):
        parti, problemi = self.prepara({"tabellone 1": "4.NC", "tabellone 2": "4.5, 4.3",
                                        "tabellone 3": "3.5 ; tipo = integrale"})
        self.assertEqual(problemi, [])
        self.assertEqual([(p.qualificati_entranti, p.qualificati_uscenti) for p in parti],
                         [(0, 4), (4, 4), (4, 1)])

    def test_classifica_in_nessun_tabellone(self):
        self.assertErrore("non sono in nessun tabellone", {"tabellone 1": "4.NC, 4.5",
                                                           "tabellone 2": "3.5"})

    def test_classifica_in_due_tabelloni(self):
        self.assertErrore("devono stare nello stesso tabellone",
                          {"tabellone 1": "4.NC, 4.5", "tabellone 2": "4.5, 4.3, 3.5"})

    def test_classifiche_in_ordine_sbagliato(self):
        self.assertErrore("dalle classifiche piu' basse alle piu' alte",
                          {"tabellone 1": "4.3, 3.5", "tabellone 2": "4.NC, 4.5"})

    def test_troppi_qualificati_entranti(self):
        # Il primo tabellone qualifica 8 giocatori, ma nel secondo gli ammessi sono 5.
        self.assertErrore("i qualificati entranti non possono essere di piu'",
                          {"tabellone 1": "4.NC, 4.5, 4.3 ; qualificati uscenti = 8",
                           "tabellone 2": "3.5"})

    def test_numeri_con_un_salto(self):
        self.assertErrore("senza salti", {"tabellone 1": "4.NC, 4.5, 4.3", "tabellone 3": "3.5"})

    def test_impostazione_sconosciuta(self):
        self.assertErrore("non si puo' scrivere qui", {"tabellone 1": "4.NC ; nome = Prova",
                                                       "tabellone 2": "4.5, 4.3, 3.5"})

    def test_integrale_solo_nel_finale(self):
        self.assertErrore("solo nel tabellone finale",
                          {"tabellone 1": "4.NC, 4.5, 4.3 ; tipo = integrale", "tabellone 2": "3.5"})

    def test_categorie_diverse_nello_stesso_tabellone(self):
        _, problemi = self.prepara({"tabellone 1": "4.NC", "tabellone 2": "4.5, 4.3, 3.5"})
        self.assertEqual([p.gravita for p in problemi], [AVVISO])
        self.assertIn("categorie diverse", problemi[0].messaggio)

    def test_categoria_con_pochi_giocatori(self):
        # 2 (3.5): troppo pochi per un tabellone, vanno con la quarta categoria.
        giocatori = giocatori_di({"giocatori": "8 (4.NC), 10 (4.4), 2 (3.5)"})
        parti = proponi_divisione(giocatori, CLASSIFICHE)
        self.assertEqual([p.classifiche for p in parti], [["4.NC"], ["3.5", "4.4"]])

    def test_qualificati_proposti(self):
        self.assertEqual(qualificati_proposti(21, 32), 8)   # la meta' di 21 e' 10
        self.assertEqual(qualificati_proposti(40, 5), 4)    # 5 vicini nel seguente
        self.assertEqual(qualificati_proposti(12, 4), 4)
        self.assertEqual(qualificati_proposti(3, 4), 1)


class ProveProgramma(unittest.TestCase):
    """Il programma intero, con i file di prova in una cartella temporanea."""

    def test_tabelloni_collegati(self):
        import contextlib
        import io

        import tabelloni
        esercizio = leggi_divisioni()["Volume I, capitolo VI, ipotesi 2"]
        with tempfile.TemporaryDirectory() as cartella:
            file_dati = {nome: os.path.join(cartella, f"{nome}.txt")
                         for nome in ("giocatori", "torneo", "classifiche")}
            with open(file_dati["classifiche"], "w", encoding="utf-8") as f:
                f.write("\n".join(CLASSIFICHE) + "\n")
            with open(file_dati["giocatori"], "w", encoding="utf-8") as f:
                for g in giocatori_di(esercizio):
                    f.write(f"{g.codice} ; {g.classifica} ; {g.circolo}\n")
            with open(file_dati["torneo"], "w", encoding="utf-8") as f:
                f.write("nome = Prova\ngara = Singolare\n")
            vecchia, apri = os.getcwd(), tabelloni.apri_nel_browser
            os.chdir(cartella)
            tabelloni.apri_nel_browser = lambda percorso: None
            try:
                uscita = io.StringIO()
                with contextlib.redirect_stdout(uscita):
                    tutto_bene = tabelloni.fai_tabellone(file_dati)
                testo = uscita.getvalue()
                self.assertTrue(tutto_bene, testo)
                self.assertIn("TABELLONI COLLEGATI: 4", testo)
                self.assertNotIn("ATTENZIONE", testo)
                for k in range(1, 5):
                    percorso = os.path.join("risultati", f"tabellone-{k}.txt")
                    self.assertTrue(os.path.exists(percorso))
                    with contextlib.redirect_stdout(io.StringIO()) as controllo:
                        self.assertTrue(tabelloni.controlla_file(percorso, file_dati))
                    self.assertIn(f"Tabellone {k} di 4", controllo.getvalue())
                with open(os.path.join("risultati", "tabellone.html"), encoding="utf-8") as f:
                    pagina = f.read()
                for k in range(1, 5):
                    self.assertIn(f"Tabellone {k} di 4", pagina)
            finally:
                os.chdir(vecchia)
                tabelloni.apri_nel_browser = apri
