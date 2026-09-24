"""Prove del controllo dei tabelloni.

L'idea: si prende un tabellone giusto, si controlla che il programma non trovi
errori; poi lo si guasta apposta in tanti modi diversi e si controlla che il
programma trovi ogni volta l'errore giusto.
Si avviano con:  py -m unittest discover prove
"""

import os
import random
import tempfile
import unittest

from programma.calcoli import calcola, conta_per_classifica
from programma.controllo import controlla, leggi_tabellone
from programma.dati import ERRORE, Giocatore
from programma.sorteggio import (GIOCATORE, LIBERO, QUALIFICATO_ENTRANTE, Posto, disegna,
                                 sorteggia)
from prove.test_calcoli import CLASSIFICHE
from prove.test_sorteggio import calcoli_esempio, giocatori_di_prova, leggi_schemi


def errori(problemi):
    return [p.messaggio for p in problemi if p.gravita == ERRORE]


class ProvaTabellone(unittest.TestCase):
    """Un tabellone giusto come l'esempio 46 del Volume I:
    5 (4.5), 7 (4.6), 9 qualificati entranti, 8 qualificati uscenti, 8 teste di serie."""

    def setUp(self):
        elenco = [("4.5", f"Circolo {i}") for i in range(5)] + \
                 [("4.6", f"Circolo {i + 5}") for i in range(7)]
        self.giocatori = giocatori_di_prova(elenco)
        self.impostazioni = dict(qualificati_entranti=9, qualificati_uscenti=8)
        calcoli = calcola(conta_per_classifica(self.giocatori, CLASSIFICHE),
                          teste_di_serie=8, **self.impostazioni)
        self.posti = sorteggia(calcoli, self.giocatori, random.Random(3)).posti

    def controlla(self, posti=None):
        return controlla(posti or self.posti, self.giocatori, CLASSIFICHE, **self.impostazioni)

    def posto_della_testa(self, numero):
        return next(i for i, p in enumerate(self.posti) if p.testa_di_serie == numero)

    def scambia(self, i, j):
        self.posti[i], self.posti[j] = self.posti[j], self.posti[i]

    def assertErrore(self, frase):
        trovati = errori(self.controlla())
        self.assertTrue(any(frase in e for e in trovati),
                        f"manca l'errore con \"{frase}\"; trovati: {trovati}")


class ProveTabelloneGiusto(ProvaTabellone):
    def test_nessun_errore(self):
        self.assertEqual(errori(self.controlla()), [])

    def test_tabelloni_del_manuale(self):
        for nome, esempio in leggi_schemi().items():
            with self.subTest(esempio=nome):
                calcoli = calcoli_esempio(esempio)
                elenco = [(c, f"Circolo {i}")
                          for i, c in enumerate(c for c, n in calcoli.ammessi for _ in range(n))]
                giocatori = giocatori_di_prova(elenco)
                tabellone = sorteggia(calcoli, giocatori, random.Random(1))
                problemi = controlla(tabellone.posti, giocatori, CLASSIFICHE,
                                     calcoli.qualificati_entranti, calcoli.qualificati_uscenti)
                self.assertEqual(errori(problemi), [])

    def test_tabelloni_fatti_dal_programma(self):
        # Tanti tornei a caso: il programma non deve mai fare un tabellone sbagliato.
        rng = random.Random(11)
        classifiche = ["3.5", "4.1", "4.2", "4.3", "4.4", "4.5", "4.6", "4.NC"]
        provati = 0
        while provati < 90:
            n = rng.randint(2, 70)
            scelte = rng.sample(classifiche, rng.randint(1, 4))
            elenco = [(rng.choice(scelte), f"C{rng.randint(0, 6)}") for _ in range(n)]
            giocatori = giocatori_di_prova(elenco)
            q = rng.randint(0, n)
            Qu = rng.choice([1, 2, 3, 4, 5, 6, 7, 8])  # 3, 5, 6, 7: tabelloni a sezioni
            calcoli = calcola(conta_per_classifica(giocatori, CLASSIFICHE),
                              qualificati_entranti=q, qualificati_uscenti=Qu)
            if any(p.gravita == ERRORE for p in calcoli.problemi):
                continue
            provati += 1
            tabellone = sorteggia(calcoli, giocatori, rng)
            with self.subTest(giocatori=n, q=q, Qu=Qu):
                self.assertEqual(errori(controlla(tabellone.posti, giocatori, CLASSIFICHE, q, Qu)), [])


class ProveTabelloneASezioni(unittest.TestCase):
    """Un tabellone a 5 sezioni come l'esercizio 2.22 del Volume II:
    12 qualificati entranti, 7 (4.6), 5 (4.5), 7 (4.4), 5 qualificati uscenti."""

    def setUp(self):
        elenco = [(c, f"Circolo {i}") for i, c in enumerate(["4.6"] * 7 + ["4.5"] * 5 + ["4.4"] * 7)]
        self.giocatori = giocatori_di_prova(elenco)
        calcoli = calcola(conta_per_classifica(self.giocatori, CLASSIFICHE), qualificati_entranti=12,
                          qualificati_uscenti=5, teste_di_serie=5)
        self.posti = sorteggia(calcoli, self.giocatori, random.Random(2)).posti

    def controlla(self):
        return controlla(self.posti, self.giocatori, CLASSIFICHE, 12, 5)

    def test_nessun_errore(self):
        self.assertEqual(len(self.posti), 40)
        self.assertEqual(self.controlla(), [])

    def test_numero_di_posti_sbagliato(self):
        self.posti += [Posto(LIBERO), Posto(LIBERO)]
        self.assertIn("i posti devono essere 5 per 2, 4, 8, 16", " ".join(errori(self.controlla())))

    def test_qualificato_nella_riga_sbagliata(self):
        # Sezione 2 (posti da 9 a 16): nella sua meta' superiore il q sta in basso.
        i = next(i for i in range(8, 12, 2) if self.posti[i + 1].tipo == QUALIFICATO_ENTRANTE)
        self.posti[i], self.posti[i + 1] = self.posti[i + 1], self.posti[i]
        self.assertIn(f"il qualificato entrante al posto {i + 1} deve stare in basso nel suo "
                      f"incontro (al posto {i + 2}), perche' e' nella meta' superiore della sua sezione",
                      errori(self.controlla())[0])

    def test_qualificati_non_divisi_tra_le_sezioni(self):
        # Un q della sezione 5 va al posto libero della sezione 1: la sezione 1 ha 4 q,
        # la sezione 5 ne ha solo 1.
        q = next(i for i in range(32, 40) if self.posti[i].tipo == QUALIFICATO_ENTRANTE)
        libero = next(i for i in range(0, 8) if self.posti[i].tipo == LIBERO)
        self.posti[q], self.posti[libero] = self.posti[libero], self.posti[q]
        self.assertTrue(any("tra le sezioni" in e for e in errori(self.controlla())))

    def test_teste_di_serie_non_multiple_delle_sezioni(self):
        # Una testa di serie in piu': 6 teste di serie con 5 sezioni.
        altro = next(p for p in self.posti if p.tipo == GIOCATORE and not p.testa_di_serie
                     and p.giocatore.classifica == "4.4")
        altro.testa_di_serie = 6
        self.assertTrue(any("multiplo di 5" in e for e in errori(self.controlla())))

    def test_sezioni_troppo_diverse(self):
        # Volume II, esercizio 2.23, soluzione 1 (sbagliata): sezioni da 7 e da 4 giocatori.
        elenco = [(c, f"Circolo {i}") for i, c in enumerate(["4.6"] * 4 + ["4.5"] * 16)]
        giocatori = giocatori_di_prova(elenco)
        testo = ("(1) - | x q | q x | q (14) | (2) - | x q | q x | q (13) | (3) - | x q | - q | "
                 "- (12) | (4) - | x q | - q | - (11) | (5) - | q - | - q | - (10) | "
                 "(6) - | q - | - q | - (9) | (7) - | q - | - q | - (8)")
        posti = []
        for segno in testo.replace("|", " ").split():
            if segno == "-":
                posti.append(Posto(LIBERO))
            elif segno == "q":
                posti.append(Posto(QUALIFICATO_ENTRANTE))
            else:
                posti.append(Posto(GIOCATORE, int(segno.strip("()")) if segno != "x" else 0))
        # Le teste di serie sono i 14 (4.5); gli altri posti ai 4 (4.6) e ai 2 (4.5) rimasti.
        teste = [g for g in giocatori if g.classifica == "4.5"][:14]
        altri = [g for g in giocatori if g not in teste]
        for posto in posti:
            if posto.tipo == GIOCATORE:
                posto.giocatore = teste[posto.testa_di_serie - 1] if posto.testa_di_serie \
                    else altri.pop()
        problemi = controlla(posti, giocatori, CLASSIFICHE, 16, 7)
        self.assertTrue(any("sezioni hanno un numero di giocatori troppo diverso (da 4 a 7)"
                            in p.messaggio for p in problemi), [str(p) for p in problemi])


class ProveTabelloneSbagliato(ProvaTabellone):
    def test_teste_di_serie_scambiate_di_posto(self):
        self.scambia(self.posto_della_testa(1), self.posto_della_testa(2))
        self.assertErrore("la testa di serie n. 1 e' al posto 32")

    def test_posto_libero_nel_posto_sbagliato(self):
        libero = next(i for i, p in enumerate(self.posti) if p.tipo == LIBERO)
        al_primo_turno = next(i for i, p in enumerate(self.posti)
                              if p.tipo == GIOCATORE and self.posti[i ^ 1].tipo != LIBERO
                              and not p.testa_di_serie)
        self.scambia(libero, al_primo_turno)
        self.assertErrore("i posti liberi sono")

    def test_qualificato_testa_di_serie(self):
        q = next(p for p in self.posti if p.tipo == QUALIFICATO_ENTRANTE)
        testa = self.posti[self.posto_della_testa(8)]
        q.testa_di_serie, testa.testa_di_serie = 8, 0
        self.assertErrore("non puo' mai essere testa di serie")

    def test_giocatore_mancante(self):
        i = next(i for i, p in enumerate(self.posti) if p.tipo == GIOCATORE and not p.testa_di_serie)
        codice = self.posti[i].giocatore.codice
        self.posti[i] = Posto(QUALIFICATO_ENTRANTE)
        self.assertErrore(f"mancano nel tabellone questi giocatori iscritti: {codice}")

    def test_due_qualificati_al_primo_turno(self):
        # Il q di un incontro prende il posto dell'avversario di un altro q.
        coppie = [i for i in range(0, len(self.posti), 2)
                  if QUALIFICATO_ENTRANTE in (self.posti[i].tipo, self.posti[i + 1].tipo)
                  and LIBERO not in (self.posti[i].tipo, self.posti[i + 1].tipo)
                  and not self.posti[i].testa_di_serie and not self.posti[i + 1].testa_di_serie]
        a, b = coppie[0], coppie[1]
        q_di_a = a if self.posti[a].tipo == QUALIFICATO_ENTRANTE else a + 1
        giocatore_di_b = b if self.posti[b].tipo == GIOCATORE else b + 1
        self.scambia(q_di_a, giocatore_di_b)
        self.assertErrore("due qualificati entranti si incontrano al primo turno")

    def test_qualificato_nella_riga_sbagliata(self):
        # Nella meta' superiore il q deve stare in basso nel suo incontro.
        i = next(i for i in range(0, len(self.posti) // 2, 2)
                 if self.posti[i + 1].tipo == QUALIFICATO_ENTRANTE
                 and self.posti[i].tipo == GIOCATORE and not self.posti[i].testa_di_serie)
        self.scambia(i, i + 1)
        self.assertErrore(f"il qualificato entrante al posto {i + 1} deve stare in basso")

    def test_teste_di_serie_in_ordine_sbagliato(self):
        # La testa di serie n. 2 (4.5) e la n. 7 (4.6) si scambiano i giocatori.
        due, sette = self.posti[self.posto_della_testa(2)], self.posti[self.posto_della_testa(7)]
        due.giocatore, sette.giocatore = sette.giocatore, due.giocatore
        self.assertErrore("la testa di serie n. 3")

    def test_giocatore_piu_forte_non_testa_di_serie(self):
        # La testa di serie n. 1 (4.5) si scambia con un 4.6 che gioca il primo turno.
        uno = self.posti[self.posto_della_testa(1)]
        altro = next(p for p in self.posti if p.tipo == GIOCATORE and not p.testa_di_serie)
        uno.giocatore, altro.giocatore = altro.giocatore, uno.giocatore
        self.assertErrore("hanno una classifica piu' alta di una testa di serie")
        self.assertErrore("nessuno puo' entrare in gara dopo un giocatore di classifica inferiore")

    def test_numero_di_posti_sbagliato(self):
        self.posti.pop()
        self.assertErrore("i posti devono essere 2, 4, 8, 16")

    def test_numeri_delle_teste_di_serie_con_un_salto(self):
        self.posti[self.posto_della_testa(8)].testa_di_serie = 9
        self.assertErrore("senza salti")


class ProveStessoCircolo(unittest.TestCase):
    def test_incontro_che_si_poteva_evitare(self):
        # 8 non classificati, 4 del circolo A e 4 del circolo B: si possono sempre
        # fare incontri A contro B. Qui si mettono apposta due A uno contro l'altro.
        giocatori = giocatori_di_prova([("4.NC", "A")] * 4 + [("4.NC", "B")] * 4)
        posti = [Posto(GIOCATORE, 0, g) for g in giocatori]
        problemi = controlla(posti, giocatori, CLASSIFICHE)
        self.assertTrue(any("Si poteva evitare" in e for e in errori(problemi)))

    def test_incontro_inevitabile(self):
        giocatori = giocatori_di_prova([("4.NC", "A")] * 3 + [("4.NC", "B")])
        posti = [Posto(GIOCATORE, 0, g) for g in giocatori]
        problemi = controlla(posti, giocatori, CLASSIFICHE)
        self.assertEqual(errori(problemi), [])
        self.assertIn("stesso circolo", problemi[0].messaggio)


class ProveLetturaDelFile(ProvaTabellone):
    def scrivi(self, testo):
        f = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8")
        f.write(testo)
        f.close()
        self.addCleanup(os.remove, f.name)
        return f.name

    def test_si_rilegge_il_tabellone_salvato(self):
        calcoli = calcola(conta_per_classifica(self.giocatori, CLASSIFICHE),
                          teste_di_serie=8, **self.impostazioni)
        tabellone = sorteggia(calcoli, self.giocatori, random.Random(5))
        percorso = self.scrivi(disegna(tabellone, "Prova"))
        posti, problemi = leggi_tabellone(percorso, self.giocatori)
        self.assertEqual(problemi, [])
        self.assertEqual(posti, tabellone.posti)
        self.assertEqual(errori(self.controlla(posti)), [])

    def test_modo_semplice_di_scrivere(self):
        percorso = self.scrivi("(1) g001\nlibero\n\n(2) G002 scritto a mano\n- \n")
        giocatori = giocatori_di_prova([("3.1", "A"), ("3.2", "B")])
        posti, problemi = leggi_tabellone(percorso, giocatori)
        self.assertEqual(problemi, [])
        self.assertEqual([(p.tipo, p.testa_di_serie) for p in posti],
                         [(GIOCATORE, 1), (LIBERO, 0), (GIOCATORE, 2), (LIBERO, 0)])

    def test_errori_nel_file(self):
        percorso = self.scrivi("1 G001\n2 G001\n3 X99\n5 q\n")
        posti, problemi = leggi_tabellone(percorso, self.giocatori)
        messaggi = [(p.riga, p.messaggio) for p in problemi]
        self.assertIn("gia' nel tabellone", messaggi[0][1])
        self.assertIn("X99", messaggi[1][1])
        self.assertEqual(messaggi[2][0], 4)
        self.assertIn("forse manca una riga", messaggi[2][1])


if __name__ == "__main__":
    unittest.main()
