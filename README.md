# Creazione tabelloni tornei di tennis

Programma che prepara i tabelloni dei tornei FITP seguendo i manuali FIT dei
tabelloni (Volume I e II): calcoli preliminari, teste di serie, posti liberi,
sorteggio, tabelloni di selezione e tabelloni collegati, controllo di un
tabellone fatto a mano, pagina pronta da stampare.

## Provarlo nel browser (niente da installare)

Aprire https://gillus.github.io/Creazione-tabelloni-tornei-di-tennis/

1. Scrivere i giocatori e le impostazioni del torneo nei riquadri (dentro c'è
   un torneo di fantasia da cui partire), oppure caricare i propri file.
2. Premere **Fai il tabellone**: compaiono i calcoli, gli avvisi e il
   tabellone da stampare.
3. Se qualcosa non va, premere **Copia tutto per segnalare un problema** e
   mandare il testo a chi segue il programma.

Tutto si fa dentro il browser: i dati non vengono mandati da nessuna parte.

## Usarlo sul computer

Serve solo Python 3 (niente altro da installare). Nella cartella del programma:

    py tabelloni.py

si apre la finestra con i pulsanti. I dati si scrivono nei file della cartella
`dati/`, i risultati finiscono in `risultati/`.

Le prove si avviano con `py -m unittest discover prove`.
