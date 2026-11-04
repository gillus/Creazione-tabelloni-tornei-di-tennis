"""Prove della lettura del file Excel degli iscritti. Si avviano con:  py -m unittest discover prove

I file Excel delle prove si costruiscono qui, con nomi di fantasia: nel repository
non c'e' (e non ci deve essere) nessun Excel vero.
"""

import io
import os
import tempfile
import unittest
import zipfile

from programma.dati import leggi_classifiche, leggi_giocatori
from programma.excel import ErroreExcel, giocatori_da_excel, righe_del_foglio

NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def xlsx(foglio, condivise=None):
    """Un file .xlsx minimo con un foglio (il testo XML di <sheetData>)."""
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        z.writestr("xl/workbook.xml",
                   f'<x:workbook xmlns:x="{NS}"><x:sheets><x:sheet name="Iscritti" sheetId="1" '
                   f'r:id="R1" xmlns:r="{NS_R}"/></x:sheets></x:workbook>')
        z.writestr("xl/_rels/workbook.xml.rels",
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="R1" Type="worksheet" Target="/xl/worksheets/sheet1.xml"/>'
                   '</Relationships>')
        z.writestr("xl/worksheets/sheet1.xml",
                   f'<x:worksheet xmlns:x="{NS}"><x:sheetData>{foglio}</x:sheetData></x:worksheet>')
        if condivise is not None:
            z.writestr("xl/sharedStrings.xml",
                       f'<sst xmlns="{NS}">' + "".join(f"<si><t>{s}</t></si>" for s in condivise)
                       + "</sst>")
    return memoria.getvalue()


def riga_fitp(*valori):
    """Una riga come nel file del sistema FITP: celle di testo senza la posizione (r)."""
    celle = "".join(f'<x:c s="0" t="str"><x:v>{v}</x:v></x:c>' if isinstance(v, str)
                    else f'<x:c s="4" t="n"><x:v>{v}</x:v></x:c>' for v in valori)
    return f"<x:row>{celle}</x:row>"


INTESTAZIONE = riga_fitp("Cognome", "Nome", "Class.", "Num. Tessera", "Circolo", "Data nascita",
                         "Cat. Età", "Prov.", "Email", "Telefono", "Data Iscrizione", "Note")


class ProveExcel(unittest.TestCase):
    def test_file_come_quello_della_fitp(self):
        dati = xlsx(INTESTAZIONE
                    + riga_fitp("ROSSI", "MARIO LUCA", "3.4", "1234", "TC Fantasia ASD ", 38455,
                                "NOR", "XX", "finto@example.org", "", 46283.2, "")
                    + riga_fitp("D'ANGELO", "anna", "4.nc", "5678", "Circolo Inventato", 39957,
                                "Under 18", "XX", "", "000", 46270.5, ""))
        testo, avvisi = giocatori_da_excel(dati, "iscritti.xlsx", "04/11/2026")
        self.assertEqual(avvisi, [])
        righe = [r for r in testo.splitlines() if r and not r.startswith("#")]
        self.assertEqual(righe, ["ROSSI Mario Luca ; 3.4   ; TC Fantasia ASD",
                                 "D'ANGELO Anna    ; 4.NC  ; Circolo Inventato"])
        # Niente email, tessere, telefoni o date di nascita.
        for cosa in ("finto@example.org", "1234", "38455", "000"):
            self.assertNotIn(cosa, testo)
        self.assertIn("iscritti.xlsx il 04/11/2026", testo)

    def test_il_testo_si_legge_come_file_dei_giocatori(self):
        dati = xlsx(INTESTAZIONE + riga_fitp("ROSSI", "MARIO", "3.4", "1", "TC Uno")
                    + riga_fitp("BIANCHI", "UGO", "4,NC", "2", "TC Due"))
        testo, _ = giocatori_da_excel(dati)
        classifiche, _ = leggi_classifiche(os.path.join("dati", "classifiche.txt"))
        with tempfile.TemporaryDirectory() as cartella:
            percorso = os.path.join(cartella, "giocatori.txt")
            with open(percorso, "w", encoding="utf-8") as f:
                f.write(testo)
            giocatori, problemi = leggi_giocatori(percorso, classifiche)
        self.assertEqual(problemi, [])
        self.assertEqual([(g.codice, g.classifica, g.circolo) for g in giocatori],
                         [("ROSSI Mario", "3.4", "TC Uno"), ("BIANCHI Ugo", "4.NC", "TC Due")])

    def test_stringhe_condivise_e_celle_con_la_posizione(self):
        # Come salva Excel: testi in sharedStrings.xml, celle con r="B2", celle vuote saltate.
        foglio = ('<x:row r="1"><x:c r="A1" t="s"><x:v>0</x:v></x:c><x:c r="B1" t="s"><x:v>1</x:v></x:c>'
                  '<x:c r="D1" t="s"><x:v>2</x:v></x:c><x:c r="E1" t="s"><x:v>3</x:v></x:c></x:row>'
                  '<x:row r="2"><x:c r="A2" t="s"><x:v>4</x:v></x:c><x:c r="B2" t="inlineStr">'
                  '<x:is><x:t>Gino</x:t></x:is></x:c><x:c r="D2" t="n"><x:v>3.2</x:v></x:c>'
                  '<x:c r="E2" t="s"><x:v>5</x:v></x:c></x:row>')
        dati = xlsx(foglio, ["COGNOME", "NOME", "CLASSIFICA", "CIRCOLO", "Verdi", "CT Lago"])
        self.assertEqual(righe_del_foglio(dati)[1], ["Verdi", "Gino", "", "3.2", "CT Lago"])
        testo, _ = giocatori_da_excel(dati)
        self.assertIn("VERDI Gino ; 3.2   ; CT Lago", testo)

    def test_nomi_uguali_e_dati_mancanti(self):
        dati = xlsx(INTESTAZIONE + riga_fitp("ROSSI", "MARIO", "3.4", "1", "TC Uno")
                    + riga_fitp("ROSSI", "Mario", "4.1", "2", "TC Due")
                    + riga_fitp("", "", "", "", "")
                    + riga_fitp("", "SENZA COGNOME", "4.1", "3", "TC Tre")
                    + riga_fitp("NERI", "ADA", "", "4", ""))
        testo, avvisi = giocatori_da_excel(dati)
        self.assertIn("ROSSI Mario (2) ; 4.1", testo)
        self.assertEqual(len(avvisi), 4)
        self.assertIn("riga 5", avvisi[1])

    def test_file_che_non_vanno(self):
        with self.assertRaisesRegex(ErroreExcel, "vecchio formato"):
            giocatori_da_excel(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\0" * 100)
        with self.assertRaisesRegex(ErroreExcel, "non e' un file Excel"):
            giocatori_da_excel("G001 ; 3.1 ; TC Uno\n".encode())
        with self.assertRaisesRegex(ErroreExcel, "rovinato"):
            giocatori_da_excel(b"PK\x03\x04 non e' davvero uno zip")
        with self.assertRaisesRegex(ErroreExcel, "Cognome"):
            giocatori_da_excel(xlsx(riga_fitp("Uno", "Due")))
        with self.assertRaisesRegex(ErroreExcel, "nessun iscritto"):
            giocatori_da_excel(xlsx(INTESTAZIONE))


if __name__ == "__main__":
    unittest.main()
