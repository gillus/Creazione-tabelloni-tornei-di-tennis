# Regole del progetto — Tabelloni tornei di tennis

Questo è un **programma che funziona sul computer**, scritto in **Python**.
Non è più un sito da pubblicare su internet: **GitHub Pages non si usa più**.
Il repository su GitHub resta, ma serve solo come **copia di sicurezza**
e per tenere la storia delle modifiche.

Repository: https://github.com/daviderobrtoalovisi/Creazione-tabelloni-tornei-di-tennis

Queste regole vanno rispettate sempre, in ogni lavoro su questa cartella.

## 1. Programma locale e semplice

- Il programma è scritto in **Python 3** e si avvia sul computer, senza internet.
- **Solo la libreria standard di Python** (quella che arriva insieme a Python).
  **Niente `pip`**, niente pacchetti da scaricare, niente ambienti virtuali.
  Se serve una finestra grafica si usa `tkinter`, che è già dentro Python.
- **Nessun passaggio di build**: i file `.py` che stanno nella cartella sono
  esattamente quelli che vengono eseguiti. Niente compilazione, niente strumenti
  da installare.
- Su questo computer Python si avvia con il comando `py` (non `python`).

## 2. Struttura dei file

- Il file da avviare si chiama `tabelloni.py` e sta nella **cartella principale**.
- Usare **solo percorsi relativi** (per esempio `dati/giocatori.txt`),
  mai percorsi completi tipo `C:\Users\...`.
  Così la cartella si può copiare su un'altra chiavetta o un altro computer
  e il programma continua a funzionare.
- Il programma deve funzionare **anche senza collegamento a internet**.

## 3. Contenuti separati dal codice

- I contenuti (nomi dei tornei, elenchi di partecipanti, testi, impostazioni)
  stanno in **file di testo semplici**, separati dal codice.
- Devono essere leggibili e modificabili **da chi non sa programmare**:
  una riga per voce, con un commento in cima che spiega come si compila.
- Cambiare un contenuto non deve mai richiedere di toccare i file `.py`.

## 4. Risultati del programma

- I tabelloni prodotti vengono **salvati come file nella cartella**
  (per esempio in `risultati/`), così si possono riaprire e stampare.
- I file prodotti dal programma non vanno mai a sovrascrivere i file dei contenuti.

## 5. Come lavorare con git

- Usare **solo `git` da riga di comando**. **Mai `gh`** (la GitHub CLI non è installata).
- **Commit piccoli e frequenti**: un commit per ogni cosa che cambia,
  non un unico commit gigante.
- Messaggi di commit **in italiano**, che spiegano **cosa è cambiato**
  (esempio: `Aggiunto elenco partecipanti nel file dati/giocatori.txt`).
- **Prima di ogni `git push` va chiesta conferma**. Nessun push automatico.
- Il push serve solo come copia di sicurezza: **non pubblica nessuna pagina**.

## 6. Come spiegare le cose

- Chi usa questo progetto **non è un programmatore**.
- Ogni modifica va spiegata **con parole semplici**: cosa è stato fatto,
  perché, e cosa bisogna fare adesso.
- Niente gergo tecnico non spiegato.

## 7. Privacy

- Il repository è **pubblico**: tutto quello che c'è dentro è visibile a chiunque.
- **Nessun dato personale reale di studenti** (cognomi completi, email, classi,
  date di nascita, foto, numeri di telefono).
- Per le prove usare nomi di fantasia o sigle.
