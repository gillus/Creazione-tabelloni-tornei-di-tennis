"""La finestra del programma, con i pulsanti (si usa tkinter, che e' dentro Python).

La finestra non fa i conti da sola: chiama le stesse funzioni che si usano
dalla riga di comando (fai il tabellone, controlla un tabellone) e mostra
nel riquadro in basso quello che scrivono.
"""

import contextlib
import datetime
import io
import os
import pathlib
import traceback
import webbrowser

import tkinter as tk
from tkinter import filedialog, font, ttk

from programma import maschera as m
from programma.dati import MESI, leggi_classifiche
from programma.excel import ErroreExcel, giocatori_da_excel

TITOLO = "Tabelloni dei tornei FITP"
NOMI_DEI_FILE = {"giocatori": "Giocatori", "torneo": "Torneo", "classifiche": "Classifiche"}
TIPI_DI_FILE = [("File di testo", "*.txt"), ("Tutti i file", "*.*")]
TIPI_EXCEL = [("File Excel", "*.xlsx"), ("Tutti i file", "*.*")]
# Gli elenchi veri (dall'Excel) e i tornei compilati con la maschera: questa cartella
# non va nel repository (vedi .gitignore), perche' contiene nomi di persone.
CARTELLA_DATI_VERI = "dati-veri"


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
        ttk.Button(dati, text="Carica dall'Excel...", command=self.carica_excel).grid(
            row=0, column=4, padx=2, sticky="ew")
        ttk.Button(dati, text="Compila con la maschera...", command=self.apri_maschera).grid(
            row=1, column=4, padx=2, sticky="ew")

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
        self.scrivi("1. Controllare i file dei dati. I giocatori si possono prendere dal file\n"
                    "   Excel degli iscritti (\"Carica dall'Excel...\"); il torneo si compila con\n"
                    "   i menu' a tendina (\"Compila con la maschera...\"). Per correggere a mano:\n"
                    "   \"Apri e modifica\".\n"
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

    def carica_excel(self, percorso=None):
        """L'elenco degli iscritti dal file Excel: diventa il file dei giocatori
        (in dati-veri/, che resta su questo computer)."""
        if percorso is None:
            percorso = filedialog.askopenfilename(
                parent=self.radice, title="Scegli il file Excel degli iscritti",
                filetypes=TIPI_EXCEL)
            if not percorso:
                return None
        nome = os.path.basename(percorso)
        try:
            with open(percorso, "rb") as f:
                testo, avvisi = giocatori_da_excel(f.read(), nome, f"{datetime.date.today():%d/%m/%Y}")
        except (OSError, ErroreExcel) as errore:
            self.scrivi(f"ERRORE - il file {nome} non si puo' usare: {errore}", pulisci=True)
            return False
        os.makedirs(CARTELLA_DATI_VERI, exist_ok=True)
        destinazione = os.path.join(CARTELLA_DATI_VERI,
                                    f"giocatori - {os.path.splitext(nome)[0]}.txt")
        with open(destinazione, "w", encoding="utf-8") as f:
            f.write(testo)
        self.file_dati["giocatori"].set(destinazione)
        quanti = sum(1 for r in testo.splitlines() if r.strip() and not r.startswith("#"))
        self.scrivi("Elenco caricato dall'Excel", pulisci=True, titolo=True)
        self.scrivi(f"Presi {quanti} giocatori da {nome} (solo cognome, nome, classifica e circolo).\n"
                    f"Salvati in {destinazione}: ora e' questo il file dei giocatori.\n"
                    f"Si puo' controllare e correggere con \"Apri e modifica\".")
        for avviso in avvisi:
            self.scrivi(f"AVVISO: {avviso}")
        return True

    def apri_maschera(self):
        """La maschera con i menu' a tendina per compilare il file del torneo."""
        classifiche, _ = leggi_classifiche(self.file_dati["classifiche"].get()) \
            if os.path.exists(self.file_dati["classifiche"].get()) else ([], [])
        if not classifiche:
            self.scrivi("ERRORE - prima serve un file delle classifiche giusto", pulisci=True)
            return None
        percorso = self.file_dati["torneo"].get()
        testo = ""
        if os.path.exists(percorso):
            with open(percorso, encoding="utf-8-sig", errors="replace") as f:
                testo = f.read()
        conteggio = {}
        if os.path.exists(self.file_dati["giocatori"].get()):
            with open(self.file_dati["giocatori"].get(), encoding="utf-8-sig", errors="replace") as f:
                conteggio = m.giocatori_per_classifica(f.read())
        return MascheraTorneo(self.radice, m.maschera_dal_testo(testo, classifiche), classifiche,
                              conteggio, self.salva_maschera)

    def salva_maschera(self, testo):
        """Scrive il torneo compilato con la maschera. Il file di esempio in dati/ non
        si tocca: in quel caso il torneo va in dati-veri/torneo.txt."""
        percorso = self.file_dati["torneo"].get()
        if os.path.normpath(percorso) == os.path.normpath(os.path.join("dati", "torneo.txt")) \
                or not percorso:
            os.makedirs(CARTELLA_DATI_VERI, exist_ok=True)
            percorso = os.path.join(CARTELLA_DATI_VERI, "torneo.txt")
        with open(percorso, "w", encoding="utf-8") as f:
            f.write(testo)
        self.file_dati["torneo"].set(percorso)
        self.scrivi("Torneo compilato con la maschera", pulisci=True, titolo=True)
        self.scrivi(f"Salvato in {percorso}: ora e' questo il file del torneo.\n\n" + testo)

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


class MascheraTorneo:
    """La finestra "Compila il torneo": campi e menu' a tendina. Alla fine chiama
    salva(testo) con il testo del file del torneo."""

    def __init__(self, radice, maschera, classifiche, conteggio, salva):
        self.maschera = maschera
        self.classifiche = classifiche
        self.conteggio = conteggio  # giocatori per classifica (puo' essere vuoto)
        self.salva = salva
        self.finestra = tk.Toplevel(radice)
        self.finestra.title("Compila il torneo")
        self.finestra.transient(radice)
        cornice = ttk.Frame(self.finestra, padding=12)
        cornice.pack(fill="both", expand=True)

        generale = ttk.LabelFrame(cornice, text="Il torneo", padding=8)
        generale.pack(fill="x")
        self.nome = tk.StringVar(self.finestra, maschera.nome)
        self.gara = tk.StringVar(self.finestra, maschera.gara)
        ttk.Label(generale, text="Nome del torneo").grid(row=0, column=0, sticky="w")
        ttk.Entry(generale, textvariable=self.nome, width=50).grid(
            row=0, column=1, columnspan=4, sticky="ew", pady=2)
        ttk.Label(generale, text="Gara").grid(row=1, column=0, sticky="w")
        ttk.Combobox(generale, textvariable=self.gara, values=m.GARE, width=30).grid(
            row=1, column=1, columnspan=3, sticky="w", pady=2)
        anno = datetime.date.today().year
        anni = [str(a) for a in range(anno - 1, anno + 3)]
        self.date = {}
        for riga, (chiave, etichetta, data) in enumerate(
                (("inizio", "Primo giorno", maschera.inizio), ("fine", "Ultimo giorno", maschera.fine)),
                start=2):
            ttk.Label(generale, text=etichetta).grid(row=riga, column=0, sticky="w")
            variabili = (tk.StringVar(self.finestra, str(data.day) if data else ""),
                         tk.StringVar(self.finestra, MESI[data.month - 1] if data else ""),
                         tk.StringVar(self.finestra, str(data.year) if data else str(anno)))
            pezzi = ttk.Frame(generale)
            pezzi.grid(row=riga, column=1, columnspan=4, sticky="w", pady=2)
            for variabile, valori, larghezza in zip(
                    variabili, ([""] + [str(g) for g in range(1, 32)], [""] + list(MESI), anni),
                    (4, 11, 6)):
                ttk.Combobox(pezzi, textvariable=variabile, values=valori, width=larghezza,
                             state="readonly").pack(side="left", padx=(0, 4))
            self.date[chiave] = variabili
        self.date_scritte = tk.StringVar(self.finestra, maschera.date_scritte)
        if maschera.date_scritte:
            ttk.Label(generale, text="Date scritte a mano").grid(row=4, column=0, sticky="w")
            ttk.Entry(generale, textvariable=self.date_scritte, width=40).grid(
                row=4, column=1, columnspan=4, sticky="ew", pady=2)
            ttk.Label(generale, text="(usate solo se i giorni qui sopra sono vuoti; "
                                     "cancellarle se non servono)",
                      foreground="#666").grid(row=5, column=1, columnspan=4, sticky="w")
        self.entranti = tk.StringVar(self.finestra, str(maschera.qualificati_entranti))
        ttk.Label(generale, text="Qualificati entranti\nnel primo tabellone").grid(
            row=6, column=0, sticky="w", pady=(6, 0))
        ttk.Combobox(generale, textvariable=self.entranti, width=4, state="readonly",
                     values=[str(n) for n in range(0, m.MASSIMO_NUMERO + 1)]).grid(
            row=6, column=1, sticky="w", pady=(6, 0))
        ttk.Label(generale, text="(di solito 0: servono solo se il primo tabellone riceve\n"
                                 "giocatori da un tabellone fatto a parte)", foreground="#666").grid(
            row=6, column=2, columnspan=3, sticky="w", pady=(6, 0))

        iscritti = ttk.LabelFrame(cornice, text="Iscritti per classifica", padding=8)
        iscritti.pack(fill="x", pady=(10, 0))
        righe = m.riepilogo_iscritti(conteggio, classifiche)
        self.iscritti = ttk.Label(iscritti, justify="left", text="\n".join(righe) if righe else
                                  "Nessun giocatore nel file dei giocatori (si puo' caricare "
                                  "l'Excel degli iscritti con \"Carica dall'Excel...\").")
        self.iscritti.pack(anchor="w")

        divisione = ttk.LabelFrame(cornice, text="I tabelloni", padding=8)
        divisione.pack(fill="x", pady=(10, 0))
        scelte = ["decisi dal programma"] + [
            "1 tabellone" if n == 1 else f"{n} tabelloni collegati" for n in range(1, m.MASSIMO_TABELLONI + 1)]
        self.scelte_quanti = scelte
        self.quanti = tk.StringVar(self.finestra, scelte[0] if maschera.divisione_automatica
                                   else scelte[len(maschera.tabelloni)])
        ttk.Label(divisione, text="Quanti tabelloni").grid(row=0, column=0, sticky="w")
        quanti = ttk.Combobox(divisione, textvariable=self.quanti, values=scelte, state="readonly",
                              width=24)
        quanti.grid(row=0, column=1, sticky="w")
        quanti.bind("<<ComboboxSelected>>", lambda e: self.cambia_quanti())
        self.per_categoria = ttk.Button(divisione, text="Uno per categoria, secondo gli iscritti",
                                        command=self.uno_per_categoria)
        self.per_categoria.grid(row=0, column=2, padx=8)
        if not conteggio:
            self.per_categoria.configure(state="disabled")
        self.tabella = ttk.Frame(divisione)
        self.tabella.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(8, 0))
        self.righe = []

        self.messaggio = ttk.Label(cornice, text="", foreground="#b00020", justify="left")
        self.messaggio.pack(fill="x", pady=(8, 0))
        pulsanti = ttk.Frame(cornice)
        pulsanti.pack(fill="x", pady=(8, 0))
        ttk.Button(pulsanti, text="Salva", command=self.conferma).pack(side="left", ipady=3)
        ttk.Button(pulsanti, text="Annulla", command=self.finestra.destroy).pack(side="left", padx=6, ipady=3)
        self.disegna_tabelloni()

    # --- la tabella dei tabelloni ---

    @staticmethod
    def _numero_in_testo(numero, automatico, ultimo=False):
        if numero is m.AUTOMATICO:
            return automatico
        return "1 (il vincitore)" if ultimo and numero == 1 else str(numero)

    @staticmethod
    def _numero_da_testo(testo):
        testo = testo.split(" ")[0]
        return int(testo) if testo.isdigit() else m.AUTOMATICO

    def leggi_tabelloni(self):
        """Dai menu' della tabella alla maschera."""
        for tabellone, riga in zip(self.maschera.tabelloni, self.righe):
            if riga.get("piu_alta") is not None:
                tabellone.piu_alta = riga["piu_alta"].get()
            tabellone.tipo = next(k for k, v in m.TIPI.items() if v == riga["tipo"].get())
            tabellone.teste_di_serie = self._numero_da_testo(riga["teste"].get())
            tabellone.qualificati_uscenti = self._numero_da_testo(riga["uscenti"].get())

    def disegna_tabelloni(self):
        for figlio in self.tabella.winfo_children():
            figlio.destroy()
        self.righe = []
        automatica = self.maschera.divisione_automatica
        intestazioni = ["", "Classifiche fino a", "Chi gioca", "Tipo", "Teste di serie",
                        "Qualificati uscenti"]
        for colonna, testo in enumerate(intestazioni):
            if automatica and colonna in (1, 2):
                continue
            ttk.Label(self.tabella, text=testo, foreground="#666").grid(
                row=0, column=colonna, sticky="w", padx=(0, 8))
        elenchi = m.classifiche_dei_tabelloni(self.maschera, self.classifiche)
        quanti = len(self.maschera.tabelloni)
        for numero, tabellone in enumerate(self.maschera.tabelloni):
            ultimo = numero == quanti - 1
            riga = {}
            r = numero + 1
            ttk.Label(self.tabella, text="Tutto il torneo" if automatica else f"Tabellone {numero + 1}").grid(
                row=r, column=0, sticky="w", padx=(0, 8), pady=2)
            if not automatica:
                if ultimo:
                    ttk.Label(self.tabella, text="fino alla piu' alta").grid(row=r, column=1, sticky="w")
                else:
                    scelte = m.scelte_della_piu_alta(self.maschera, numero, self.classifiche)
                    if tabellone.piu_alta not in scelte:
                        tabellone.piu_alta = scelte[0] if scelte else ""
                    riga["piu_alta"] = tk.StringVar(self.finestra, tabellone.piu_alta)
                    menu = ttk.Combobox(self.tabella, textvariable=riga["piu_alta"], values=scelte,
                                        width=6, state="readonly")
                    menu.grid(row=r, column=1, sticky="w")
                    menu.bind("<<ComboboxSelected>>", lambda e: self.ridisegna())
                ttk.Label(self.tabella, text=m.descrivi_tabellone(elenchi[numero], self.conteggio or None)).grid(
                    row=r, column=2, sticky="w", padx=(0, 8))
            tipi = [v for k, v in m.TIPI.items() if k != "integrale" or ultimo]
            riga["tipo"] = tk.StringVar(self.finestra, m.TIPI.get(tabellone.tipo, m.TIPI[""]))
            ttk.Combobox(self.tabella, textvariable=riga["tipo"], values=tipi, width=22,
                         state="readonly").grid(row=r, column=3, sticky="w", padx=(0, 8))
            senza_teste = not automatica and m.solo_non_classificati(elenchi[numero])
            riga["teste"] = tk.StringVar(self.finestra, "nessuna (non classificati)" if senza_teste
                                         else self._numero_in_testo(tabellone.teste_di_serie,
                                                                    "proposte dal programma"))
            ttk.Combobox(self.tabella, textvariable=riga["teste"], width=24,
                         state="disabled" if senza_teste else "readonly",
                         values=["proposte dal programma"] + [str(n) for n in range(0, m.MASSIMO_NUMERO + 1)]
                         ).grid(row=r, column=4, sticky="w", padx=(0, 8))
            riga["uscenti"] = tk.StringVar(self.finestra, self._numero_in_testo(
                tabellone.qualificati_uscenti, "1 (il vincitore)" if ultimo else "proposti dal programma",
                ultimo))
            ttk.Combobox(self.tabella, textvariable=riga["uscenti"], width=22, state="readonly",
                         values=(["1 (il vincitore)"] if ultimo else ["proposti dal programma", "1"])
                         + [str(n) for n in range(2, m.MASSIMO_NUMERO + 1)]).grid(row=r, column=5, sticky="w")
            self.righe.append(riga)

    def ridisegna(self):
        self.leggi_tabelloni()
        self.disegna_tabelloni()

    def cambia_quanti(self):
        self.leggi_tabelloni()
        scelta = self.scelte_quanti.index(self.quanti.get())
        tabelloni = self.maschera.tabelloni
        self.maschera.divisione_automatica = scelta == 0
        quanti = max(scelta, 1)
        if len(tabelloni) > quanti:
            del tabelloni[quanti - 1:-1]  # si tolgono quelli in mezzo: l'ultimo resta l'ultimo
        while len(tabelloni) < quanti:
            tabelloni.insert(-1, m.TabelloneDellaMaschera())
        self.disegna_tabelloni()

    def uno_per_categoria(self):
        self.leggi_tabelloni()
        piu_alte = m.un_tabellone_per_categoria(self.classifiche, set(self.conteggio))
        self.maschera.divisione_automatica = False
        vecchi = self.maschera.tabelloni
        self.maschera.tabelloni = [vecchi[i] if i < len(vecchi) - 1 else m.TabelloneDellaMaschera()
                                   for i in range(len(piu_alte) - 1)] + [vecchi[-1]]
        for tabellone, piu_alta in zip(self.maschera.tabelloni, piu_alte):
            tabellone.piu_alta = piu_alta
        self.quanti.set(self.scelte_quanti[len(self.maschera.tabelloni)])
        self.disegna_tabelloni()

    # --- salvare ---

    def leggi_tutto(self):
        """Dai campi alla maschera; restituisce i problemi da correggere."""
        problemi = []
        self.maschera.nome = self.nome.get()
        self.maschera.gara = self.gara.get()
        for chiave, (giorno, mese, anno) in self.date.items():
            data, errore = m.data_da_parti(giorno.get(), mese.get(), anno.get())
            if errore:
                problemi.append(("primo giorno: " if chiave == "inizio" else "ultimo giorno: ") + errore)
            setattr(self.maschera, chiave, data)
        self.maschera.date_scritte = "" if self.maschera.inizio or self.maschera.fine \
            else self.date_scritte.get()
        self.maschera.qualificati_entranti = int(self.entranti.get() or 0)
        self.leggi_tabelloni()
        return problemi + m.problemi_della_maschera(self.maschera, self.classifiche)

    def conferma(self):
        problemi = self.leggi_tutto()
        if problemi:
            self.messaggio.configure(text="Da correggere:\n- " + "\n- ".join(problemi))
            return False
        self.salva(m.testo_dalla_maschera(self.maschera, self.classifiche,
                                          set(self.conteggio) or None))
        self.finestra.destroy()
        return True


def avvia(**impostazioni):
    """Apre la finestra e aspetta che venga chiusa."""
    radice = tk.Tk()
    Finestra(radice, **impostazioni)
    radice.mainloop()
