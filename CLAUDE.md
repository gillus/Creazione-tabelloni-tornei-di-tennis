# Regole del progetto — Tabelloni tornei di tennis

Questo è un piccolo sito pubblicato con **GitHub Pages**.
Repository: https://github.com/daviderobrtoalovisi/Creazione-tabelloni-tornei-di-tennis

Queste regole vanno rispettate sempre, in ogni lavoro su questa cartella.

## 1. Sito statico e semplice

- Solo **HTML, CSS e JavaScript**.
- **Nessuna libreria esterna** (niente React, jQuery, Bootstrap, CDN, font esterni...).
- **Nessun passaggio di build**: i file che stanno nella cartella sono esattamente quelli
  che il browser apre. Niente npm, niente compilazione, niente strumenti da installare.

## 2. Struttura dei file

- `index.html` deve stare nella **cartella principale** del repository.
- Usare **solo percorsi relativi** (per esempio `stile.css`, `dati/giocatori.txt`),
  mai percorsi che iniziano con `/` e mai indirizzi completi `http://...`.
  Questo serve perché su GitHub Pages il sito non sta nella radice del dominio.
- Il sito deve funzionare anche aprendo `index.html` direttamente dal computer.

## 3. Contenuti separati dal codice

- I contenuti (nomi dei tornei, elenchi di partecipanti, testi, impostazioni)
  stanno in **file di testo semplici**, separati dal codice.
- Devono essere leggibili e modificabili **da chi non sa programmare**:
  una riga per voce, con un commento in cima che spiega come si compila.
- Cambiare un contenuto non deve mai richiedere di toccare i file `.html`, `.css` o `.js`.

## 4. Come lavorare con git

- Usare **solo `git` da riga di comando**. **Mai `gh`** (la GitHub CLI non è installata).
- **Commit piccoli e frequenti**: un commit per ogni cosa che cambia,
  non un unico commit gigante.
- Messaggi di commit **in italiano**, che spiegano **cosa è cambiato**
  (esempio: `Aggiunto elenco partecipanti nel file dati/giocatori.txt`).
- **Prima di ogni `git push` va chiesta conferma**. Nessun push automatico.

## 5. Come spiegare le cose

- Chi usa questo progetto **non è un programmatore**.
- Ogni modifica va spiegata **con parole semplici**: cosa è stato fatto,
  perché, e cosa bisogna fare adesso.
- Niente gergo tecnico non spiegato.

## 6. Privacy

- Il repository è **pubblico**: tutto quello che c'è dentro è visibile a chiunque.
- **Nessun dato personale reale di studenti** (cognomi completi, email, classi,
  date di nascita, foto, numeri di telefono).
- Per le prove usare nomi di fantasia o sigle.
