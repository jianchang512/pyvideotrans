[Leggi me in inglese](./README_EN.md) / [👑 Dona al progetto](./about.md) / [Link di invito a Discord](https://discord.gg/mTh5Cu5Bqm) / WeChat Official Account: cerca "pyvideotrans"

# Strumento di traduzione e doppiaggio video

>
> Questo è uno strumento di traduzione e doppiaggio video, che può tradurre un video da una lingua a una lingua desiderata, generando e aggiungendo automaticamente i sottotitoli e il doppiaggio in quella lingua.
>
> Il riconoscimento vocale supporta i modelli `faster-whisper`, `openai-whisper` e `GoogleSpeech`, `zh_recogn il modello di riconoscimento vocale cinese di Alibaba`.
>
> La traduzione del testo supporta `Microsoft Translator|Google Translate|Baidu Translate|Tencent Translate|ChatGPT|AzureAI|Gemini|DeepL|DeepLX|Offline Translation OTT`
>
> La sintesi vocale del testo supporta `Microsoft Edge tts`, `Google tts`, `Azure AI TTS`, `Openai TTS`, `Elevenlabs TTS`, `Custom TTS server api`, `GPT-SoVITS`, [clone-voice](https://github.com/jianchang512/clone-voice), `[ChatTTS-ui](https://github.com/jianchang512/ChatTTS-ui)`
>
> Permette di mantenere la musica di sottofondo e così via (basato su uvr5)
> 
> Lingue supportate: Cinese semplificato/tradizionale, Inglese, Coreano, Giapponese, Russo, Francese, Tedesco, Italiano, Spagnolo, Portoghese, Vietnamita, Tailandese, Arabo, Turco, Ungherese, Hindi, Ucraino, Kazako, Indonesiano, Malese, Ceco



# Principali usi e modalità di utilizzo

【Traduci e doppia il video】Traduci l'audio del video in un altro doppiaggio linguistico e incorpora i sottotitoli in quella lingua

【Converti audio o video in sottotitoli】Riconosci la voce umana nei file audio e video come testo ed esporta come file di sottotitoli srt

【Creazione in blocco di doppiaggio per i sottotitoli】Crea doppiaggio basandosi sui file di sottotitoli srt esistenti localmente, supporta singoli o sottotitoli in blocco

【Traduzione sottotitoli in blocco】Traduci uno o più file di sottotitoli srt in file di sottotitoli in altre lingue

【Unisci audio, video e sottotitoli】Unisci file audio, file video e file di sottotitoli in un unico file video

【Estrai l'audio dal video】Estrai il file audio dal video e il video senza suono


【Scarica video da YouTube】Puoi scaricare video da YouTube

----



https://github.com/jianchang512/pyvideotrans/assets/3378335/3811217a-26c8-4084-ba24-7a95d2e13d58


# Versioni preconfezionate (disponibili solo per win10/win11, sistemi MacOS/Linux usano la distribuzione del codice sorgente)

> Pacchettizzato usando pyinstaller, non è stato firmato né reso immune ai software antivirus, può essere segnalato come minaccia dai software antivirus, si prega di aggiungerlo all'elenco delle eccezioni o utilizzare la distribuzione del codice sorgente

0. [Clicca per scaricare la versione preconfezionata, estrai in una directory in inglese senza spazi, dopodiché fai doppio clic su sp.exe](https://github.com/jianchang512/pyvideotrans/releases)

1. Estrai in un percorso in inglese senza spazi e fai doppio clic su sp.exe (se incontri problemi di autorizzazione, puoi fare clic con il tasto destro per aprire come amministratore)

4. Nota: deve essere utilizzato dopo l'estrazione, non può essere utilizzato facendo doppio clic direttamente dal pacchetto compresso, né spostando il file sp.exe in un'altra posizione dopo l'estrazione


# Deployment del codice sorgente su MacOS

0. Apri una finestra del terminale e esegui i seguenti comandi
	
	> Assicurati di avere già installato Homebrew, se non hai installato Homebrew, devi installarlo prima
	>
	> Esegui il comando per installare Homebrew: `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`
	>
	> Dopo l'installazione, esegui: `eval $(brew --config)`
	>

    ```
    brew install libsndfile

    brew install ffmpeg

    brew install git

    brew install python@3.10

    ```

    Continua con

    ```
    export PATH="/usr/local/opt/python@3.10/bin:$PATH"

    source ~/.bash_profile 
	
	source ~/.zshrc

    ```



1. Crea una cartella senza spazi e caratteri cinesi e accedici dal terminale.
2. Esegui il comando `git clone https://github.com/jianchang512/pyvideotrans `
3. Esegui il comando `cd pyvideotrans`
4. Continua con `python -m venv venv`
5. Continua ad eseguire il comando `source ./venv/bin/activate`, dopo aver terminato controlla se la richiesta del terminale inizia con `(venv)`, i comandi successivi devono essere eseguiti solo dopo aver confermato che la richiesta del terminale inizia con `(venv)`
6. Esegui `pip install -r requirements.txt --no-deps`, se fallisce, esegui i seguenti due comandi per cambiare lo specchio pip in quello di Aliyun

    ```
    pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/
    pip config set install.trusted-host mirrors.aliyun.com
    ```

    Quindi prova a rieseguire.
    Se è stato cambiato allo specchio Aliyun e continua a fallire, prova a eseguire `pip install -r requirements.txt  --ignore-installed --no-deps `

7. `python sp.py` per avviare l'interfaccia del software


[Dettagliata soluzione di distribuzione per Mac](https://pyvideotrans.com/mac.html)





# Deployment del codice sorgente su Linux

0. Per CentOS/RHEL segui questi comandi per installare python3.10

```

sudo yum update

sudo yum groupinstall "Development Tools"

sudo yum install openssl-devel bzip2-devel libffi-devel

cd /tmp

wget https://www.python.org/ftp/python/3.10.4/Python-3.10.4.tgz

tar xzf Python-3.10.4.tgz

cd Python-3.10.4

./configure — enable-optimizations

sudo make && sudo make install

sudo alternatives — install /usr/bin/python3 python3 /usr/local/bin/python3.10

sudo yum install -y ffmpeg

```

1. Per Ubuntu/Debian segui questi comandi per installare python3.10

```

apt update && apt upgrade -y

apt install software-properties-common -y

add-apt-repository ppa:deadsnakes/ppa

apt update

sudo apt-get install libxcb-cursor0

apt install python3.10

curl -sS https://bootstrap.pypa.io/get-pip.py | python3.10

pip 23.2.1 from /usr/local/lib/python3.10/site-packages/pip (python 3.10)

sudo update-alternatives --install /usr/bin/python python /usr/local/bin/python3.10 

sudo update-alternatives --config python

apt-get install ffmpeg

```


**Apri qualsiasi terminale e esegui `python3 -V`, se mostra "3.10.4" significa che l'installazione è riuscita, altrimenti non è riuscita**


1. Crea una cartella senza spazi e caratteri cinesi e aprila da un terminale.
3. Esegui il comando `git clone https://github.com/jianchang512/pyvideotrans`
4. Continua con il comando `cd pyvideotrans`
5. Continua con `python -m venv venv`
6. Continua con il comando `source ./venv/bin/activate`, dopo aver finito controlla di confermare che la richiesta del terminale sia iniziata con `(venv)`, i comandi successivi devono essere eseguiti solo dopo aver confermato che la richiesta del terminale inizia con `(venv)`
7. Esegui `pip install -r requirements.txt --no-deps`, se fallisce, esegui i seguenti due comandi per cambiare lo specchio pip in quello di Aliyun

    ```

    pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/
    pip config set install.trusted-host mirrors.aliyun.com

    ```

    Quindi prova a rieseguire, se è stato cambiato allo specchio Aliyun e continua a fallire, prova `pip install -r requirements.txt  --ignore-installed --no-deps `
8. Se vuoi usare l'accelerazione CUDA, esegui separatamente

    `pip uninstall -y torch torchaudio`


    `pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118`

    `pip install nvidia-cublas-cu11 nvidia-cudnn-cu11`

9. Su linux se vuoi attivare l'accelerazione cuda, devi avere una scheda grafica Nvidia e un ambiente CUDA11.8+ configurato, cerca "Installazione Linux CUDA"


10. `python sp.py` per avviare l'interfaccia del software


# Deployment del codice sorgente su Window10/11

0. Apri https://www.python.org/downloads/ e scarica windows3.10, dopodiché fai doppio clic e fai clic su next, assicurandoti di selezionare "Add to PATH"

   **Apri un cmd e esegui `python -V`, se l'output non è `3.10.4`, significa che qualcosa è andato storto nell'installazione o nella procedura di "Add to PATH", si prega di reinstallare**

1. Apri https://github.com/git-for-windows/git/releases/download/v2.45.0.windows.1/Git-2.45.0-64-bit.exe, scarica git, poi fai doppio clic e prosegui con l'installazione.
2. Trova una cartella senza spazi e caratteri cinesi, scrivi `cmd` nella barra degli indirizzi e premi invio per aprire la console, i comandi successivi dovrebbero essere eseguiti in questa console
3. Esegui il comando `git clone https://github.com/jianchang512/pyvideotrans`
4. Continua con il comando `cd pyvideotrans`
5. Continua con `python -m venv venv`
6. Continua con il comando `.\venv\scripts\activate`, dopo verifica che la richiesta del terminale sia iniziata con `(venv)`, altrimenti c'è un errore
7. Esegui `pip install -r requirements.txt --no-deps`, se fallisce, esegui i seguenti due comandi per cambiare lo specchio pip in quello di Aliyun

    ```

    pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/
    pip config set install.trusted-host mirrors.aliyun.com

    ```

    Quindi prova a rieseguire, se è stato cambiato allo specchio Aliyun e continua a fallire, prova `pip install -r requirements.txt  --ignore-installed --no-deps `
8.  Se vuoi usare l'accelerazione CUDA, esegui separatamente

    `pip uninstall -y torch torchaudio`

    `pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118`


9. Su windows se vuoi attivare l'accelerazione cuda, devi avere una scheda grafica Nvidia e un ambiente CUDA11.8+ configurato, vedi [Supporto accelerazione CUDA](https://pyvideotrans.com/gpu.html)

10. Estrai ffmpeg.zip nella directory corrente del codice sorgente, se richiesto sovrascrivi, dopo assicurati di trovare ffmpeg.exe ffprobe.exe ytwin32.exe nella cartella ffmpeg del codice sorgente,

11. `python sp.py` per avviare l'interfaccia del software



# Spiegazione dei problemi relativi al deployment del codice sorgente

1. Di default si usa la versione 4.x di ctranslate2 che supporta solo CUDA versione 12.x, se la tua versione di CUDA è inferiore a 12 e non puoi aggiornare CUDA alla versione 12.x, esegui il seguente comando per disinstallare ctranslate2 e poi reinstallare

```

pip uninstall -y ctranslate2

pip install ctranslate2==3.24.0

```

2. Si può incontrare l'errore `xx module not found`, apri il file requirements.txt, cerca il modulo xx, poi rimuovi '==' e il numero della versione successivo




# Tutorial e Documenti di Uso

Si prega di controllare https://pyvideotrans.com/guide.html


# Modelli di riconoscimento vocale:

   Indirizzo di download: https://pyvideotrans.com/model.html

   Spiegazione e differenze dei modelli: https://pyvideotrans.com/02.html



# Tutorial video (terze parti)

[Deployment del codice sorgente su Mac/bilibili](https://www.bilibili.com/video/BV1tK421y7rd/)

[Metodo per impostare la traduzione video con Gemini Api/bilibili](https://b23.tv/fED1dS3)

[Come scaricare e installare](https://www.bilibili.com/video/BV1Gr421s7cN/)


# Anteprime dello schermo del software

![image](https://github.com/jianchang512/pyvideotrans/assets/3378335/c3abb561-1ab5-47f9-bfdc-609245445190)



# Progetti correlati

[OTT: strumento di traduzione del testo offline locale](https://github.com/jianchang512/ott)

[Strumento di clonazione della voce: utilizza qualsiasi timbro vocale per sintetizzare voce](https://github.com/jianchang512/clone-voice)

[Strumento di riconoscimento vocale: uno strumento locale offline per convertire il riconoscimento vocale in testo](https://github.com/jianchang512/stt)

[Separazione della voce dallo sfondo musicale: strumento per la separazione della voce dalla musica di sottofondo](https://github.com/jianchang512/vocal-separate)

[Versione migliorata di api.py di GPT-SoVITS](https://github.com/jianchang512/gptsovits-api)


## Ringraziamenti

> I principali progetti open source sui quali si basa questo programma

1. ffmpeg
2. PySide6
3. edge-tts
4. faster-whisper
5. openai-whisper
6. pydub