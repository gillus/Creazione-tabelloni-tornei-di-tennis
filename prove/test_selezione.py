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
from programma.calcoli import QUALIFICATO, SELEZIONE, calcola
from programma.dati import ERRORE, leggi_righe
from programma.selezione import (Scala, _calcola_posti, controlla_scala, leggi_turno,
                                 scala_migliore, scala_scritta, scrivi_turno)
from programma.selezione_tabellone import (Incontro, Voce, disegna, prepara, proposta_teste_di_serie,
                                           scegli_scala,
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


def sezioni_di(Qu):
    """Il numero delle sezioni: 0 se i qualificati uscenti sono 1, 2, 4, 8..."""
    return 0 if Qu & (Qu - 1) == 0 else Qu


def firma(scala):
    return [scrivi_turno(t) for t in scala.turni]


def giocatori_per(diretti):
    return giocatori_di_prova([(c, f"Circolo {i}") for i, c in enumerate(diretti)])


def tabellone_dell_esercizio(esercizio, seme=1):
    diretti, q, Qu = dati(esercizio)
    scala = scala_del_manuale(esercizio)
    giocatori = giocatori_per(diretti)
    return prepara(scala, int(esercizio["teste di serie"]), giocatori, LIVELLO, sezioni_di(Qu),
                   random.Random(seme)), giocatori


def leggi_incontri(testo):
    """Le parti del tabellone scritte come nella riga "incontri" del file degli esercizi."""
    def nodo(i):
        if parole[i] == "[":
            alto, i = nodo(i + 1)
            basso, i = nodo(i)
            assert parole[i] == "]"
            turni = [x.turno + (not isinstance(x, Voce)) for x in (alto, basso)]
            return Incontro(max(turni), alto, basso), i + 1
        classifica, turno = parole[i].split("/")
        if classifica == "q":
            return Voce(QUALIFICATO_ENTRANTE, int(turno)), i + 1
        return Voce(GIOCATORE, int(turno), classifica), i + 1

    radici = []
    for parte in testo.split("|"):
        parole = parte.replace("[", " [ ").replace("]", " ] ").split()
        radici.append(nodo(0)[0])
    return radici


def incontri(radici):
    """Gli incontri di ogni parte, senza contare chi e' scritto sopra (in ordine alfabetico)."""
    def testo(n):
        if isinstance(n, Voce):
            return ("q" if n.tipo == QUALIFICATO_ENTRANTE else n.classifica) + f"/{n.turno}"
        return "[" + " ".join(sorted(testo(x) for x in n.lati)) + "]"
    return [testo(r) for r in radici]


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
        self.assertEqual(len(leggi_scale()), 48)

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
                calcoli = calcola([(c, diretti.count(c)) for c in CLASSIFICHE if c in diretti],
                                  q, Qu, tipo=SELEZIONE)
                _, tutte = scala_migliore(diretti, q, Qu, LIVELLO)
                scelta, _ = scegli_scala(tutte, calcoli.teste_di_serie_minimo,
                                         calcoli.teste_di_serie_massimo, LIVELLO, sezioni_di(Qu))
                attesa = "proposta turno " if "proposta turno 1" in esercizio else "turno "
                self.assertEqual(firma(scelta), firma(scala_del_manuale(esercizio, attesa)))

    def test_proposta_delle_teste_di_serie(self):
        for nome, esercizio in leggi_scale().items():
            with self.subTest(esercizio=nome):
                diretti, q, Qu = dati(esercizio)
                calcoli = calcola([(c, diretti.count(c)) for c in CLASSIFICHE if c in diretti],
                                  q, Qu, tipo=SELEZIONE)
                attesa = int(esercizio.get("proposta del programma", esercizio["teste di serie"]))
                self.assertEqual(proposta_teste_di_serie(
                    scala_del_manuale(esercizio), calcoli.teste_di_serie_minimo,
                    calcoli.teste_di_serie_massimo, LIVELLO, sezioni_di(Qu)), attesa)

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

    def test_i_tabelloni_disegnati_nel_manuale_rispettano_le_regole(self):
        # Il controllo del programma non trova errori nei tabelloni del manuale (le
        # teste di serie non ci sono: quei controlli si saltano).
        for nome, esercizio in leggi_scale().items():
            if "incontri" not in esercizio:
                continue
            with self.subTest(esercizio=nome):
                _, q, Qu = dati(esercizio)
                voci = [v for r in leggi_incontri(esercizio["incontri"]) for v in voci_di(r)]
                giocatori = giocatori_per([v.classifica for v in voci if v.tipo == GIOCATORE])
                persone = iter(giocatori)
                for v in voci:
                    if v.tipo == GIOCATORE:
                        v.giocatore = next(persone)
                errori = [p.messaggio for p in controllo_selezione.controlla(
                    voci, giocatori, CLASSIFICHE, q, Qu) if p.gravita == ERRORE
                          and "teste di serie" not in p.messaggio]
                self.assertEqual(errori, [])

    def test_stessi_incontri_del_manuale(self):
        # Con la scala del manuale il programma fa gli stessi incontri del manuale
        # (le parti possono essere in un altro ordine), o quelli scritti in
        # "incontri del programma".
        for nome, esercizio in leggi_scale().items():
            if "incontri" not in esercizio:
                continue
            with self.subTest(esercizio=nome):
                tabellone, _ = tabellone_dell_esercizio(esercizio)
                atteso = esercizio.get("incontri del programma", esercizio["incontri"])
                self.assertEqual(sorted(incontri(tabellone.radici)),
                                 sorted(incontri(leggi_incontri(atteso))))

    def test_tabelloni_del_programma_rispettano_le_regole(self):
        for nome, esercizio in leggi_scale().items():
            with self.subTest(esercizio=nome):
                diretti, q, Qu = dati(esercizio)
                calcoli = calcola([(c, diretti.count(c)) for c in CLASSIFICHE if c in diretti],
                                  q, Qu, tipo=SELEZIONE)
                _, tutte = scala_migliore(diretti, q, Qu, LIVELLO)
                migliore, teste = scegli_scala(tutte, calcoli.teste_di_serie_minimo,
                                               calcoli.teste_di_serie_massimo, LIVELLO,
                                               sezioni_di(Qu))
                giocatori = giocatori_per(diretti)
                tabellone = prepara(migliore, teste, giocatori, LIVELLO, sezioni_di(Qu),
                                    random.Random(4))
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


def _v(classifica, codice=""):
    """Un ammesso (per le prove delle raccomandazioni)."""
    from programma.dati import Giocatore
    return Voce(GIOCATORE, 1, classifica, giocatore=Giocatore(codice or classifica, classifica, ""))


def _q():
    return Voce(QUALIFICATO_ENTRANTE, 1)


class ProveRaccomandazioni(unittest.TestCase):
    """Le raccomandazioni 2, 3, 5 e 6 del manuale (Volume I, capitolo I, lettera H)."""

    def messaggi(self, radici, finale=False):
        return " | ".join(controllo_selezione.raccomandazioni(radici, LIVELLO, finale))

    def test_compressione_tra_classifiche_diverse(self):
        diverse = Incontro(2, Incontro(1, _v("4.3"), _q()), Incontro(1, _v("4.4"), _q()))
        uguali = Incontro(2, Incontro(1, _v("4.4", "A"), _q()), Incontro(1, _v("4.4", "B"), _q()))
        self.assertIn("compressioni", self.messaggi([diverse]))
        self.assertEqual(self.messaggi([uguali]), "")

    def test_progressione_tra_pari_classifica(self):
        radice = Incontro(2, Incontro(1, _v("4.4", "A"), _q()), _v("4.4", "B"))
        self.assertIn("incontrano un ammesso della stessa classifica", self.messaggi([radice]))

    def test_piu_di_due_incontri_in_favore(self):
        radice = Incontro(3, Incontro(2, Incontro(1, _v("4.1"), _q()), Incontro(1, _v("4.4", "A"), _q())),
                          Incontro(2, Incontro(1, _v("4.4", "B"), _q()), Incontro(1, _v("4.4", "C"), _q())))
        self.assertIn("piu' di due incontri in favore", self.messaggi([radice]))
        # Nel tabellone finale la raccomandazione non vale.
        self.assertNotIn("in favore", self.messaggi([radice], finale=True))

    def test_piu_di_due_gruppi_di_differenza(self):
        # Il (4.6) ha vinto due incontri (un q e un pari classifica) e trova un (4.2).
        radice = Incontro(3, Incontro(2, Incontro(1, _v("4.6", "A"), _q()),
                                      Incontro(1, _v("4.6", "B"), _q())), _v("4.2"))
        self.assertIn("piu' di due gruppi", self.messaggi([radice]))
        # Al primo incontro no: il (4.6) contro un q e poi il (4.3).
        radice = Incontro(2, Incontro(1, _v("4.6"), _q()), _v("4.2"))
        self.assertNotIn("piu' di due gruppi", self.messaggi([radice]))

    def test_trattamento_diverso_a_pari_classifica(self):
        # Un (4.5) comincia contro un q, l'altro contro un (4.3).
        radici = [Incontro(1, _v("4.5", "A"), _q()), Incontro(1, _v("4.3"), _v("4.5", "B"))]
        self.assertIn("cominciano contro un giocatore di classifica piu' alta", self.messaggi(radici))
        # Le coppie di pari classifica vanno bene (Volume I, esempio 67).
        radici = [Incontro(1, _v("4.5", "A"), _q()), Incontro(1, _v("4.5", "B"), _v("4.5", "C"))]
        self.assertEqual(self.messaggi(radici), "")

    def test_i_tabelloni_disegnati_nel_manuale_non_hanno_avvisi(self):
        for nome, esercizio in leggi_scale().items():
            if "tabellone" not in esercizio:
                continue
            with self.subTest(esercizio=nome):
                tabellone, _ = tabellone_dell_esercizio(esercizio)
                _, _, Qu = dati(esercizio)
                self.assertEqual(self.messaggi(tabellone.radici, Qu == 1), "")


class ProveSezioni(unittest.TestCase):
    """Tabellone di selezione a 3 sezioni (Volume I, capitolo III, lettera B)."""

    def setUp(self):
        self.diretti = ["4.3"] * 3 + ["4.4"] * 6 + ["4.5"] * 6
        scala, _ = scala_migliore(self.diretti, 6, 3, LIVELLO)
        self.giocatori = giocatori_per(self.diretti)
        self.tabellone = prepara(scala, 3, self.giocatori, LIVELLO, 3, random.Random(0))
        self.voci = self.tabellone.voci()

    def problemi(self):
        return controllo_selezione.controlla(self.voci, self.giocatori, CLASSIFICHE, 6, 3, 3)

    def test_nessun_errore(self):
        self.assertEqual([str(p) for p in self.problemi() if p.gravita == ERRORE], [])

    def test_qualificati_non_divisi_tra_le_sezioni(self):
        # Il q di una sezione si scambia con un ammesso dello stesso turno di un'altra sezione.
        sezione = {id(v): k for k, r in enumerate(self.tabellone.radici) for v in voci_di(r)}
        i = next(i for i, v in enumerate(self.voci) if v.tipo == QUALIFICATO_ENTRANTE)
        j = next(j for j, v in enumerate(self.voci) if v.tipo == GIOCATORE and not v.testa_di_serie
                 and v.turno == self.voci[i].turno and sezione[id(v)] != sezione[id(self.voci[i])])
        self.voci[i], self.voci[j] = self.voci[j], self.voci[i]
        errori = [p.messaggio for p in self.problemi() if p.gravita == ERRORE]
        self.assertTrue(any("tra le sezioni" in e for e in errori), errori)
