"""La finestra del programma, con i pulsanti (si usa tkinter, che e' dentro Python).

La finestra non fa i conti da sola: chiama le stesse funzioni che si usano
dalla riga di comando (fai il tabellone, controlla un tabellone) e mostra
nel riquadro in basso quello che scrivono.
"""

import contextlib
import io
import os
import pathlib
import traceback
import webbrowser

import tkinter as tk
from tkinter import filedialog, font, ttk

TITOLO = "Tabelloni dei tornei FITP"
NOMI_DEI_FILE = {"giocatori": "Giocatori", "torneo": "Torneo", "classifiche": "Classifiche"}
TIPI_DI_FILE = [("File di testo", "*.txt"), ("Tutti i file", "*.*")]


def percorso_relativo(scelto):
    """Il percorso a partire dalla cartella del programma, se il file sta li' dentro."""
    try:
        relativo = os.path.relpath(scelto)
    except ValueError:  # su Windows: un file su un'altra unita' (per esempio D:)
        return os.path.normpath(scelto)
    return os.path.normpath(scelto) if relativo.startswith("..") else relativo


def apri(percorso):
    """Apre un file o una cartella con il programma che il computer usa di solito."""
    if hasattr(os, "startfile"):  # Windows
        os.startfile(os.path.abspath(percorso))
    else:
        webbrowser.open(pathlib.Path(percorso).resolve().as_uri())


class Finestra:
    """fai_tabellone(file_dati) e controlla_file(percorso, file_dati) sono le funzioni
    di tabelloni.py; file_dati dice quali file dei dati usare all'inizio."""

    def __init__(self, radice, fai_tabellone, controlla_file, file_dati,
                 file_da_controllare, file_da_stampare, cartella_risultati):
        self.radice = radice
        self.fai_tabellone = fai_tabellone
        self.controlla_file = controlla_file
        self.file_da_controllare = file_da_controllare
        self.file_da_stampare = file_da_stampare
        self.cartella_risultati = cartella_risultati
        self.file_dati = {chiave: tk.StringVar(radice, value=percorso)
                          for chiave, percorso in file_dati.items()}

        radice.title(TITOLO)
        radice.minsize(760, 520)
        radice.geometry("980x680")
        cornice = ttk.Frame(radice, padding=12)
        cornice.pack(fill="both", expand=True)

        grande = font.nametofont("TkDefaultFont").copy()
        grande.configure(size=grande.cget("size") + 5, weight="bold")
        ttk.Label(cornice, text=TITOLO, font=grande).pack(anchor="w")

        # I file dei dati: si possono aprire per modificarli o sceglierne altri.
        dati = ttk.LabelFrame(cornice, text="File dei dati", padding=8)
        dati.pack(fill="x", pady=(10, 8))
        dati.columnconfigure(1, weight=1)
        for riga, (chiave, nome) in enumerate(NOMI_DEI_FILE.items()):
            ttk.Label(dati, text=nome, width=12).grid(row=riga, column=0, sticky="w")
            ttk.Entry(dati, textvariable=self.file_dati[chiave], state="readonly").grid(
                row=riga, column=1, sticky="ew", padx=6, pady=2)
            ttk.Button(dati, text="Scegli un altro file...",
                       command=lambda c=chiave: self.scegli_file(c)).grid(row=riga, column=2, padx=2)
            ttk.Button(dati, text="Apri e modifica",
                       command=lambda c=chiave: self.apri_file_dati(c)).grid(row=riga, column=3, padx=2)

        # Le cose da fare.
        comandi = ttk.Frame(cornice)
        comandi.pack(fill="x", pady=(0, 8))
        self.pulsanti = {}
        for testo, azione in (("Fai il tabellone", self.fai),
                              ("Controlla un tabellone...", self.controlla),
                              ("Apri il tabellone da stampare", self.apri_da_stampare),
                              ("Apri la cartella dei risultati", self.apri_risultati)):
            pulsante = ttk.Button(comandi, text=testo, command=azione)
            pulsante.pack(side="left", padx=(0, 6), ipady=4)
            self.pulsanti[testo] = pulsante

        # Il riquadro dove si leggono i risultati.
        riquadro = ttk.Frame(cornice)
        riquadro.pack(fill="both", expand=True)
        self.testo = tk.Text(riquadro, wrap="word", font="TkFixedFont", padx=8, pady=6,
                             state="disabled")
        barra = ttk.Scrollbar(riquadro, command=self.testo.yview)
        self.testo.configure(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y")
        self.testo.pack(side="left", fill="both", expand=True)
        self.testo.tag_configure("errore", foreground="#b00020")
        self.testo.tag_configure("avviso", foreground="#9a5b00")
        self.testo.tag_configure("titolo", font=grande)

        self.scrivi("Benvenuto.", pulisci=True, titolo=True)
        self.scrivi("1. Controllare i file dei dati (pulsanti \"Apri e modifica\").\n"
                    "2. Premere \"Fai il tabellone\": il tabellone si apre nel browser,\n"
                    "   da dove si stampa con il pulsante \"Stampa\".\n"
                    "3. Per controllare un tabellone fatto o corretto a mano, premere\n"
                    "   \"Controlla un tabellone...\" e scegliere il file.")
        self.aggiorna_pulsanti()

    # --- il riquadro dei risultati ---

    def scrivi(self, messaggio, pulisci=False, titolo=False):
        self.testo.configure(state="normal")
        if pulisci:
            self.testo.delete("1.0", "end")
        for riga in messaggio.splitlines():
            tag = ()
            if titolo:
                tag = ("titolo",)
            elif "ERRORE" in riga or "ATTENZIONE" in riga:
                tag = ("errore",)
            elif "AVVISO" in riga:
                tag = ("avviso",)
            self.testo.insert("end", riga + "\n", tag)
        self.testo.configure(state="disabled")

    def esegui(self, titolo, funzione, *argomenti):
        """Fa partire una funzione e mostra nel riquadro quello che scrive."""
        self.scrivi(titolo, pulisci=True, titolo=True)
        self.radice.configure(cursor="watch")
        self.radice.update()
        uscita = io.StringIO()
        try:
            with contextlib.redirect_stdout(uscita):
                tutto_bene = funzione(*argomenti)
        except Exception:
            tutto_bene = False
            uscita.write("\nERRORE inatteso del programma. Questo e' il dettaglio tecnico,\n"
                         "da mandare a chi segue il programma:\n\n" + traceback.format_exc())
        finally:
            self.radice.configure(cursor="")
        self.scrivi(uscita.getvalue())
        self.testo.see("end")  # la conclusione (problemi trovati o no) e' in fondo
        self.aggiorna_pulsanti()
        return tutto_bene

    def aggiorna_pulsanti(self):
        stato = "normal" if os.path.exists(self.file_da_stampare) else "disabled"
        self.pulsanti["Apri il tabellone da stampare"].configure(state=stato)

    # --- i pulsanti ---

    def dati_scelti(self):
        return {chiave: variabile.get() for chiave, variabile in self.file_dati.items()}

    def scegli_file(self, chiave):
        attuale = self.file_dati[chiave].get()
        scelto = filedialog.askopenfilename(
            parent=self.radice, title=f"Scegli il file: {NOMI_DEI_FILE[chiave]}",
            initialdir=os.path.abspath(os.path.dirname(attuale) or "."),
            initialfile=os.path.basename(attuale), filetypes=TIPI_DI_FILE)
        if scelto:
            self.file_dati[chiave].set(percorso_relativo(scelto))

    def apri_file_dati(self, chiave):
        percorso = self.file_dati[chiave].get()
        if os.path.exists(percorso):
            apri(percorso)
        else:
            self.scrivi(f"ERRORE - manca il file {percorso}", pulisci=True)

    def fai(self):
        return self.esegui("Tabellone", self.fai_tabellone, self.dati_scelti())

    def controlla(self, percorso=None):
        if percorso is None:
            percorso = filedialog.askopenfilename(
                parent=self.radice, title="Scegli il tabellone da controllare",
                initialdir=os.path.abspath(os.path.dirname(self.file_da_controllare)),
                initialfile=os.path.basename(self.file_da_controllare), filetypes=TIPI_DI_FILE)
            if not percorso:
                return None
            percorso = percorso_relativo(percorso)
        return self.esegui("Controllo del tabellone", self.controlla_file, percorso,
                           self.dati_scelti())

    def apri_da_stampare(self):
        if os.path.exists(self.file_da_stampare):
            apri(self.file_da_stampare)

    def apri_risultati(self):
        os.makedirs(self.cartella_risultati, exist_ok=True)
        apri(self.cartella_risultati)


def avvia(**impostazioni):
    """Apre la finestra e aspetta che venga chiusa."""
    radice = tk.Tk()
    Finestra(radice, **impostazioni)
    radice.mainloop()
