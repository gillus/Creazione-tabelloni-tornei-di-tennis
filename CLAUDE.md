# Regole del progetto — Tabelloni tornei di tennis

Questo è un **programma scritto in Python** che funziona in **due modi**:

- **sul computer**, con una finestra con i pulsanti (`tkinter`): è il modo
  normale di lavorare per il giudice arbitro;
- **nel browser**, come **pagina pubblicata su GitHub Pages** dalla copia
  (fork) dell'account `gillus`, grazie a **PyScript** (uno strumento che fa
  girare Python dentro il browser, senza installare niente). Serve per le
  **prove veloci**: chi vuole provare il programma apre l'indirizzo
  https://gillus.github.io/Creazione-tabelloni-tornei-di-tennis/ e basta.

Le due versioni usano **lo stesso codice** (cartella `programma/`): cambia
solo la "facciata" (finestra oppure pagina). Deciso con chi ha proposto il
progetto nell'ottobre 2026 (prima il programma era solo locale; prima
ancora era un sito su GitHub Pages).

Repository originale: https://github.com/daviderobrtoalovisi/Creazione-tabelloni-tornei-di-tennis
Copia (fork) da cui si pubblica la pagina: https://github.com/gillus/Creazione-tabelloni-tornei-di-tennis

Queste regole vanno rispettate sempre, in ogni lavoro su questa cartella.

## Cosa deve fare il programma

Deciso con chi ha proposto il progetto (risposte complete in `DOMANDE.txt`).

- **Chi lo usa**: un **giudice arbitro regionale** che prepara i tabelloni
  di tornei FITP veri. Quindi il programma deve rispettare **alla lettera**
  le regole dei manuali FIT (cartella `manuali/` e i due PDF, che fanno fede).
  I manuali sono l'**ultima versione** in uso (confermato da chi ha proposto
  il progetto).
- **Tabelloni concatenati**: non un solo tabellone, ma **più tabelloni
  collegati** (qualificazioni → tabellone intermedio → tabellone finale),
  con i giocatori che entrano in fasi diverse secondo la classifica.
- **Dati di ogni giocatore**: un **codice anonimo** (userid), la **classifica**
  FITP (per esempio 4.6, 3.2) e il **circolo**.
  Regola dello stesso circolo: **al primo turno due giocatori dello stesso
  circolo non devono incontrarsi**. Vale **solo al primo turno** (il manuale
  dice "nei primi due incontri", ma qui si segue la scelta di chi ha proposto
  il progetto). Chi ha il posto libero (bye) **puo'** incontrare un compagno
  di circolo al secondo turno (confermato, domanda F in `PIANO.txt`). La regola si può non rispettare **solo se non esiste nessun
  sorteggio possibile** che la rispetti; in quel caso il programma lo segnala.
- **Sorteggio fatto dal programma**: teste di serie, posti liberi (bye) e
  tutto il resto li decide il programma. Le correzioni a mano sono
  **l'ultima risorsa**, non il modo normale di lavorare.
- **Controllo delle regole**: il programma deve anche **controllare** che un
  tabellone rispetti le regole del manuale e segnalare cosa non va.
- **Cosa produce**: il **tabellone pronto da stampare**. Oggi viene fatto a
  mano in Excel; va bene qualunque formato più elegante (per esempio una
  pagina da aprire e stampare dal browser, che si può creare con la sola
  libreria standard).
- **Finestra**: il programma ha una **finestra con pulsanti** (`tkinter`).
  La pagina nel browser ha gli **stessi pulsanti** e fa le stesse cose.
- **Prove con gli esercizi del manuale**: gli esercizi risolti del
  **Volume II** (`manuali/manuale-volume2-esercizi.txt`) vanno usati per
  controllare che il programma dia le stesse soluzioni. **Molto importante.**

## 1. Programma semplice, senza niente da installare

- Il programma è scritto in **Python 3**.
- **Solo la libreria standard di Python** (quella che arriva insieme a Python).
  **Niente `pip`**, niente pacchetti da scaricare, niente ambienti virtuali.
  Se serve una finestra grafica si usa `tkinter`, che è già dentro Python.
- **L'unica cosa che viene da fuori è PyScript**, e solo per la pagina nel
  browser: `index.html` lo carica da internet (pyscript.net) indicando **una
  versione precisa** (mai "l'ultima", che potrebbe cambiare e rompere la
  pagina). Nessun altro strumento, libreria o servizio esterno.
- **Nessun passaggio di build**: i file `.py` che stanno nella cartella sono
  esattamente quelli che vengono eseguiti, sul computer e nel browser.
  Niente compilazione, niente strumenti da installare.
- La versione sul computer funziona **anche senza internet**. La pagina nel
  browser invece **ha bisogno di internet** (per aprirla e per scaricare
  PyScript).
- Il codice che fa i conti (cartella `programma/`) **non deve sapere** se
  gira nella finestra o nel browser: niente `tkinter`, niente cose del
  browser lì dentro. Le due "facciate" sono `programma/finestra.py` e la
  cartella `web/`.
- Su questo computer Python si avvia con il comando `py` (non `python`).

## 2. Struttura dei file

- Il file da avviare sul computer si chiama `tabelloni.py` e sta nella
  **cartella principale**.
- La pagina per il browser si chiama `index.html` e sta anche lei nella
  **cartella principale** (GitHub Pages la cerca lì; e da lì la pagina legge
  i file di `programma/` e di `dati/` con percorsi relativi). Gli altri file
  della pagina (stile, pezzo di Python che collega i pulsanti, file di
  configurazione di PyScript) stanno nella cartella `web/`.
- Nella cartella principale deve restare il file vuoto `.nojekyll`: senza di
  esso GitHub Pages **nasconde i file il cui nome comincia con `_`** (come
  `programma/__init__.py`) e la pagina smette di funzionare.
- Usare **solo percorsi relativi** (per esempio `dati/giocatori.txt`),
  mai percorsi completi tipo `C:\Users\...` e mai percorsi che cominciano
  con `/`. Così la cartella si può copiare su un'altra chiavetta o un altro
  computer, e la pagina funziona anche se su GitHub Pages il sito non sta
  nella radice dell'indirizzo.

## 3. Contenuti separati dal codice

- I contenuti (nomi dei tornei, elenchi di partecipanti, testi, impostazioni)
  stanno in **file di testo semplici**, separati dal codice.
- Devono essere leggibili e modificabili **da chi non sa programmare**:
  una riga per voce, con un commento in cima che spiega come si compila.
- Cambiare un contenuto non deve mai richiedere di toccare i file `.py`.
- La pagina nel browser mostra gli stessi file di `dati/` come esempio da
  cui partire: si modificano nella pagina (o se ne carica uno dal proprio
  computer) e si rifà il tabellone.

## 4. Risultati del programma

- Sul computer i tabelloni prodotti vengono **salvati come file nella
  cartella** (in `risultati/`), così si possono riaprire e stampare.
- Nel browser i tabelloni vengono **mostrati nella pagina** e si possono
  **stampare** o **scaricare** sul proprio computer. **Niente viene salvato
  su GitHub**: i dati scritti nella pagina restano nel browser di chi la usa
  e non vengono mandati da nessuna parte.
- I file prodotti dal programma non vanno mai a sovrascrivere i file dei contenuti.

## 5. Come lavorare con git

- Si usa `git` da riga di comando. Si può usare anche **`gh`** (la GitHub CLI),
  che è installata e collegata all'account `gillus`: per esempio per aprire
  issue o pull request, o per il push.
- Il push va sulla **copia (fork)** dell'account `gillus`
  (https://github.com/gillus/Creazione-tabelloni-tornei-di-tennis, remote `fork`),
  perché su quello originale `gillus` non ha il permesso di scrivere.
- **Il push sul ramo `main` del fork pubblica la pagina** su GitHub Pages
  (dalla cartella principale del ramo). I push sugli altri rami non
  pubblicano niente: il lavoro si fa su un ramo di lavoro e si porta su
  `main` solo quando la pagina è stata provata.
- **Prima di aprire issue o pull request va chiesta conferma**: il repository
  è pubblico e tutti le vedono.
- **Prima di accendere, spegnere o cambiare le impostazioni di GitHub Pages
  va chiesta conferma**: cambia quello che tutti vedono all'indirizzo.
- **Commit piccoli e frequenti**: un commit per ogni cosa che cambia,
  non un unico commit gigante.
- Messaggi di commit **in italiano**, che spiegano **cosa è cambiato**
  (esempio: `Aggiunto elenco partecipanti nel file dati/giocatori.txt`).
- **Prima di ogni `git push` va chiesta conferma**. Nessun push automatico.

## 6. Come spiegare le cose

- Chi usa questo progetto **non è un programmatore**.
- Ogni modifica va spiegata **con parole semplici**: cosa è stato fatto,
  perché, e cosa bisogna fare adesso.
- Niente gergo tecnico non spiegato.

## 7. Privacy

- Il repository è **pubblico**: tutto quello che c'è dentro è visibile a chiunque,
  e con GitHub Pages lo è anche la pagina.
- **Nessun dato personale reale** (cognomi completi, email, classi,
  date di nascita, foto, numeri di telefono).
- Per le prove usare nomi di fantasia o sigle. I file di esempio in `dati/`
  finiscono sulla pagina pubblica: devono restare di fantasia.
- La pagina nel browser **non manda da nessuna parte** quello che ci si
  scrive dentro: i conti si fanno dentro il browser di chi la usa.
