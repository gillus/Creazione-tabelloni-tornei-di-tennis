# Creazione tabelloni tornei di tennis

Programma che prepara i tabelloni dei tornei FITP seguendo i manuali FIT dei
tabelloni (Volume I e II): calcoli preliminari, teste di serie, posti liberi,
sorteggio, tabelloni di selezione e tabelloni collegati, controllo di un
tabellone fatto a mano, pagina pronta da stampare.

## Provarlo nel browser (niente da installare)

Aprire https://gillus.github.io/Creazione-tabelloni-tornei-di-tennis/

1. Compilare il torneo con la maschera (nome, date, quanti tabelloni, teste di
   serie, qualificati) e caricare il file Excel degli iscritti nel riquadro
   "Giocatori" (oppure scriverli a mano: dentro c'è un torneo di fantasia da
   cui partire).
2. Premere **Fai il tabellone**: compaiono i calcoli, gli avvisi e il
   tabellone da stampare.
3. Se qualcosa non va, premere **Copia tutto per segnalare un problema** e
   mandare il testo a chi segue il programma.

Tutto si fa dentro il browser: i dati non vengono mandati da nessuna parte.

## Usarlo sul computer

Serve solo Python 3 (niente altro da installare). Nella cartella del programma:

    py tabelloni.py

si apre la finestra con i pulsanti. Con "Carica dall'Excel..." si prende
l'elenco degli iscritti, con "Compila con la maschera..." si scrive il torneo:
tutti e due finiscono nella cartella `dati-veri/`, che resta sul computer (non
va su internet). Gli esempi di fantasia sono nella cartella `dati/`, i
risultati finiscono in `risultati/`.

Le prove si avviano con `py -m unittest discover prove`.
