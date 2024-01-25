[English](./README_EN.md) / [Fai una donazione al progetto](./about.md) / [Discord](https://discord.gg/TMCM2PfHzQ)

# Strumenti di traduzione e doppiaggio video

[Scarica la versione precompilata per Windows del file exe](https://github.com/jianchang512/pyvideotrans/releases)

>
> È uno strumento di doppiaggio per la traduzione di video che traduce un video in una lingua in un video in una lingua specificata, genera e aggiunge automaticamente sottotitoli e doppiaggio in quella lingua.
>
> Il riconoscimento vocale si basa su `faster-whisper` un modello offline
>
> Supporto per la traduzione di testi `google|baidu|tencent|chatGPT|Azure|Gemini|DeepL|DeepLX` ,
>
> Supporto  `Microsoft Edge tts`  `Openai TTS-1`per la sintesi vocale `Elevenlabs TTS`
>

# Usi principali e utilizzo

【Traduci video e doppiaggio】 Imposta ogni opzione secondo necessità, configura liberamente la combinazione e realizza traduzione e doppiaggio, accelerazione e decelerazione automatiche, fusione, ecc

[Estrai sottotitoli senza traduzione] Seleziona un file video e seleziona la lingua di origine del video, quindi il testo verrà riconosciuto dal video e il file dei sottotitoli verrà automaticamente esportato nella cartella di destinazione

【Estrai sottotitoli e traduci】 Seleziona il file video, seleziona la lingua di origine del video e imposta la lingua di destinazione da tradurre, quindi il testo verrà riconosciuto dal video e tradotto nella lingua di destinazione, quindi il file dei sottotitoli bilingue verrà esportato nella cartella di destinazione

[Unione sottotitoli e video] Seleziona il video, quindi trascina e rilascia il file dei sottotitoli esistente nell'area dei sottotitoli a destra, imposta la lingua di origine e la lingua di destinazione sulla lingua dei sottotitoli, quindi seleziona il tipo di doppiaggio e il ruolo per avviare l'esecuzione

【Crea doppiaggio per i sottotitoli】 Trascina e rilascia il file dei sottotitoli locali nell'editor dei sottotitoli a destra, quindi seleziona la lingua di destinazione, il tipo di doppiaggio e il ruolo e trasferisci il file audio doppiato generato nella cartella di destinazione

[Riconoscimento testo audio e video] Trascina il video o l'audio nella finestra di riconoscimento e il testo verrà riconosciuto ed esportato in formato sottotitoli SRT

[Sintetizza testo in voce] Genera una voce fuori campo da un testo o da un sottotitolo utilizzando un ruolo di doppiaggio specifico

Separa audio da video Separa i file video in file audio e video silenziosi

【Unione di sottotitoli audio e video】 Unisci file audio, file video e file di sottotitoli in un unico file video

【Conversione di formati audio e video】 Conversione tra vari formati

【Traduzione dei sottotitoli】 Traduci file di testo o sottotitoli SRT in altre lingue

----




https://github.com/jianchang512/pyvideotrans/assets/3378335/c3d193c8-f680-45e2-8019-3069aeb66e01



# Utilizzare win per precompilare la versione exe (altri sistemi utilizzano il codice sorgente per la distribuzione)

0. [Fare clic su Download per scaricare la versione precompilata](https://github.com/jianchang512/pyvideotrans/releases)

1. Si consiglia di decomprimere i dati nel percorso inglese e il percorso non contiene spazi. Dopo la decompressione, fare doppio clic su sp.exe (se si verificano problemi di autorizzazione, è possibile fare clic con il pulsante destro del mouse per aprirlo con autorizzazioni di amministratore)

3. Se non viene eseguita alcuna uccisione, il software di uccisione domestica può avere falsi positivi, che possono essere ignorati o distribuiti utilizzando il codice sorgente


# Distribuzione del codice sorgente

[![Apri in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1yDGPWRyXeZ1GWqkOpdJDv4nA_88HNm01?usp=sharing)


1. Configurare l'ambiente Python 3.9->3.11
2. `git clone https://github.com/jianchang512/pyvideotrans`
3. `cd pyvideotrans`
4. `python -m venv venv`
5. Corri sotto win `%cd%/venv/scripts/activate`, Linux e Mac `source ./venv/bin/activate`
6. `pip install -r requirements.txt`Se riscontri un conflitto di versione, utilizza `pip install -r requirements.txt --no-deps` (CUDA non è supportato su MacOS, sostituisci requirements.txt con requirements-mac.txt su Mac).
7. Estrai ffmpeg.zip nella directory principale (file .exe ffmpeg), Linux e Mac Si prega di installare ffmpeg da soli, il metodo specifico può essere "Baidu o Google"
8. `python sp.py` Aprire l'interfaccia del software
9. Se è necessario supportare l'accelerazione CUDA, è necessario disporre di una scheda grafica NVIDIA sul dispositivo, vedere Supporto per l'accelerazione CUDA di [ seguito per precauzioni specifiche per l'installazione](https://github.com/jianchang512/pyvideotrans?tab=readme-ov-file#cuda-%E5%8A%A0%E9%80%9F%E6%94%AF%E6%8C%81)


# Modo d'uso:

1. Video originale: seleziona video MP4 / AVI / MOV / MKV / MPEG, puoi selezionare più video;

2. Directory video di output: se non si seleziona questa opzione, verrà generata nella stessa directory per impostazione predefinita `_video_out` e verranno creati due file di sottotitoli nella lingua originale e nella lingua di destinazione nella cartella SRT in questa directory

3. Seleziona una traduzione: Seleziona google|baidu|tencent|chatGPT|Azzurro|Gemelli|DeepL|Canale di traduzione DeepLX

4. Indirizzo proxy web: se non riesci ad accedere direttamente a google/chatGPT nella tua regione, devi impostare un proxy nell'interfaccia del software Web Proxy, ad esempio, se utilizzi v2ray, compila `http://127.0.0.1:10809` .  Se `http://127.0.0.1:7890`hai modificato la porta predefinita o un altro software proxy che stai utilizzando, inserisci le informazioni necessarie

5. Lingua originale: seleziona la lingua del video da tradurre

6. Lingua di destinazione: seleziona la lingua in cui desideri tradurre

7. Seleziona Doppiaggio: Dopo aver selezionato la lingua di destinazione per la traduzione, è possibile selezionare il ruolo di doppiaggio dalle opzioni di Doppiaggio.
   
   Sottotitoli rigidi: si riferisce alla visualizzazione sempre dei sottotitoli, che non possono essere nascosti, se si desidera avere i sottotitoli durante la riproduzione nella pagina Web, selezionare l'incorporamento dei sottotitoli rigidi

   Sottotitoli soft: se il lettore supporta la gestione dei sottotitoli, è possibile visualizzare o chiudere i sottotitoli, ma i sottotitoli non verranno visualizzati durante la riproduzione nella pagina Web, alcuni lettori nazionali potrebbero non supportarlo ed è necessario inserire il video generato con lo stesso nome file srt e video in una directory da visualizzare


8. Modello di riconoscimento vocale: selezionare base/piccolo/medio/grande-v3, l'effetto di riconoscimento sta migliorando sempre di più, ma la velocità di riconoscimento sta diventando sempre più lenta e la memoria richiesta sta diventando sempre più grande, il modello di base integrato, scaricare altri modelli separatamente, decomprimerli e inserirli nella `当前软件目录/models`directory

   Riconoscimento/pre-segmentazione complessiva: il riconoscimento integrale si riferisce all'invio dell'intero file vocale direttamente al modello, che viene elaborato dal modello, e la segmentazione può essere più accurata, ma può anche creare un singolo sottotitolo con una lunghezza di 30 secondi, adatto per l'audio con silenziamento chiaro;  La presegmentazione significa che l'audio viene tagliato a una lunghezza di circa 10 secondi e quindi inviato al modello per l'elaborazione.

    [Tutti i modelli sono disponibili per il download](https://github.com/jianchang512/stt/releases/tag/0.0)
    
    Dopo il download, decomprimere e copiare la cartella models--systran--faster-whisper-xx nel pacchetto compresso nella directory models

    ![](https://github.com/jianchang512/stt/assets/3378335/5c972f7b-b0bf-4732-a6f1-253f42c45087)
 

    [Download di FFmepg (la versione compilata viene fornita con esso).](https://www.ffmpeg.org/)

9. Velocità di doppiaggio: inserisci il numero compreso tra -90 e +90, la stessa frase in lingue diverse, il tempo richiesto è diverso, quindi i sottotitoli audio e immagine potrebbero non essere sincronizzati dopo il doppiaggio, puoi regolare la velocità di conversazione qui, i numeri negativi rappresentano la bassa velocità, i numeri positivi rappresentano la riproduzione accelerata.

10. Allineamento audio e video: rispettivamente "Accelerazione automatica della voce fuori campo" e "Rallentamento automatico del video"

>
> Dopo la traduzione, lingue diverse hanno durate di pronuncia diverse, ad esempio una frase in cinese 3 secondi, tradotta in inglese può essere 5 secondi, con conseguente durata e video incoerenti.
> 
> Ci sono 2 modi per risolverlo:
>
>     1. Forzare le voci fuori campo per velocizzare la riproduzione per ridurre la durata della voce fuori campo e l'allineamento del video
> 
>     2. Forza la riproduzione lenta del video in modo che la lunghezza del video sia maggiore e la voce fuori campo sia allineata.
> 
> Puoi scegliere solo uno dei due
>  
 
  
11. Clip muto: immettere un numero compreso tra 100 e 2000, che rappresenta i millisecondi, e il valore predefinito è 500, ovvero il segmento silenziato maggiore o uguale a 500 ms viene utilizzato come intervallo per dividere la voce

12. **Accelerazione CUDA: verifica che la scheda **grafica del tuo computer sia una scheda N e che l'ambiente CUDA e il driver siano stati configurati, quindi abilita questa opzione, la velocità può essere notevolmente migliorata e il metodo di configurazione specifico è mostrato nel supporto per l['accelerazione CUDA di seguito](https://github.com/jianchang512/pyvideotrans?tab=readme-ov-file#cuda-%E5%8A%A0%E9%80%9F%E6%94%AF%E6%8C%81)

13. TTS: è possibile utilizzare i modelli edgeTTS e openai TTS per selezionare i caratteri che si desidera sintetizzare vocalmente e openai deve utilizzare l'interfaccia ufficiale o aprire l'interfaccia di terze parti del modello TTS-1

14. Fai clic sul pulsante Start in basso per visualizzare l'avanzamento e i registri correnti e i sottotitoli verranno visualizzati nella casella di testo a destra

15. Al termine dell'analisi dei sottotitoli, si fermerà e aspetterà che il sottotitolo venga modificato e, se non fai nulla, passerà automaticamente al passaggio successivo dopo 60 secondi. Puoi anche modificare i sottotitoli nell'area dei sottotitoli a destra, quindi fare clic manualmente per continuare la composizione

16. Nella sottodirectory del video con lo stesso nome nella cartella di destinazione, verranno generati rispettivamente il file SRT dei sottotitoli delle due lingue, la voce originale e il file WAV doppiato per facilitare l'ulteriore elaborazione

17. Imposta il ruolo della linea: è possibile impostare il ruolo di pronuncia per ogni riga nei sottotitoli, selezionare prima il tipo e il ruolo TTS a sinistra, quindi fare clic su "Imposta ruolo di linea" in basso a destra nell'area dei sottotitoli e inserire il numero di riga in cui si desidera utilizzare il doppiaggio del ruolo nel testo dietro il nome di ciascun personaggio, come mostrato nella figura seguente:![](./images/p2.png)
    
# Impostazioni avanzate videotrans/set.ini

**Non regolarlo a meno che tu non sappia cosa accadrà**

```
;设置软件界面语言，en代表英文，zh代表中文
lang =
;同时配音线程数量
dubbing_thread=5
;同时翻译行数
trans_thread=10
;软件等待修改字幕倒计时
countdown_sec=60
;加速设备 cuvid 或 cuda
hwaccel=cuvid
; 加速设备输出格式，nv12 或 cuda 
hwaccel_output_format=nv12
;是否使用硬件解码 -c:v h264_cuvid  true代表是，false代表否
no_decode=false
;语音识别时，数据格式，int8 或 float16 或 float32
cuda_com_type=int8
; 语音识别线程数量，0代表和cpu核数一致，如果占用cpu太多，此处可设为4
whisper_threads=4
;语音识别工作进程数量
whisper_worker=1
;如果显存不足，下面2个值可以改为 1
beam_size=5
best_of=5
;预分割模式同时工作线程
split_threads=4
```



# Supporto per l'accelerazione CUDA

**Installare lo strumento**  CUDA [per i metodi di installazione dettagliati](https://juejin.cn/post/7318704408727519270)

Dopo aver installato CUDA, se si verifica un problema, eseguire `pip uninstall torch torchaudio torchvision` Disinstalla[, quindi passare a https://pytorch.org/get-started/locally/]() in base al tipo di sistema operativo e alla versione di CUDA, selezionare `pip3` il comando,  passare  `pip`a , quindi copiare il comando da eseguire. 
 
Al termine dell'installazione, eseguire Se l' `python testcuda.py` output è True, è disponibile  

A volte viene visualizzato l'errore "cublasxx .dll non esiste", oppure non si ottiene questo errore e la configurazione CUDA è corretta, ma viene sempre visualizzato l'errore di riconoscimento, è necessario scaricare cuBLAS e quindi copiare il file dll nella directory di sistema

[Fare clic per scaricare cuBLAS, ](https://github.com/jianchang512/stt/releases/download/0.0/cuBLAS_win.7z)decomprimerlo e copiare il file dll in C:/Windows/System32


# Domande frequenti

1. Utilizzando Google Translate, dice errore

   Per utilizzare l'interfaccia ufficiale di Google o ChatGPT in Cina, è necessario appendere una scala

2. È stato utilizzato un proxy globale, ma non sembra che sarà un proxy

   È necessario impostare un indirizzo proxy specifico nell'interfaccia software "Network Proxy", ad esempio http://127.0.0.1:7890

3. Suggerimento: FFmepg non esiste

   Per prima cosa controlla che ci siano file ffmpeg.exe, ffprobe.exe nella directory principale del software, se non esistono, decomprimere ffmpeg.7z e mettere questi 2 file nella directory principale del software

4. CUDA è abilitato su Windows, ma viene visualizzato un errore

   R: [Prima di tutto, controlla il metodo di installazione dettagliato, ](https://juejin.cn/post/7318704408727519270)assicurati di aver installato correttamente gli strumenti relativi a cuda, se ci sono ancora errori,[ fai clic per scaricare cuBLAS, ](https://github.com/jianchang512/stt/releases/download/0.0/cuBLAS_win.7z)decomprimi e copia il file dll all'interno di C:/Windows/System32

   B: Se sei sicuro che non abbia nulla a che fare con A, controlla se il video è mp4 codificato H264, alcuni video HD sono codificati H265, questo non è supportato, puoi provare a convertire in video H264 nella "Casella degli strumenti video".

   C: La decodifica hardware e la codifica del video sotto GPU richiedono una rigorosa correttezza dei dati e il tasso di tolleranza ai guasti è quasi 0, qualsiasi piccolo errore porterà al guasto, oltre alle differenze tra le diverse versioni del modello della scheda grafica, della versione del driver, della versione CUDA, della versione ffmpeg, ecc., Con conseguente facilità di verificarsi errori di compatibilità. Al momento, viene aggiunto il fallback e il software della CPU viene utilizzato automaticamente per codificare e decodificare dopo un errore sulla GPU. Quando si verifica un errore, viene registrato un messaggio di errore nella directory dei log.

5. Indica che il modello non esiste

   Dopo la versione 0.985, i modelli devono essere reinstallati e la directory dei modelli è una cartella per ogni modello, non un file pt.
   Per utilizzare il modello di base, assicurarsi che la cartella models/models--Systran--faster-whisper-base esista, se non esiste, è necessario scaricarla e copiare la cartella nei modelli.
   Se si desidera utilizzare un modello di piccole dimensioni, è necessario assicurarsi che la cartella models/models--Systran--faster-whisper-small esista, se non esiste, è necessario scaricarla e copiare la cartella nei modelli.
   Per utilizzare il modello medio, assicurarsi che la cartella models/models--Systran--faster-whisper-medium esista, se non esiste, è necessario scaricarla e copiare la cartella nei modelli.
   Per utilizzare il modello large-v3, assicurarsi che la cartella models/models--Systran--faster-whisper-large-v3 esista, in caso contrario, è necessario scaricarla e copiare la cartella nei modelli.

   [Tutti i modelli sono disponibili per il download](https://github.com/jianchang512/stt/releases/tag/0.0)

6. La directory non esiste o l'autorizzazione non è corretta

   Fare clic con il pulsante destro del mouse su sp..exe per aprire con privilegi di amministratore

7. Viene visualizzato un messaggio di errore, ma non sono disponibili informazioni dettagliate sull'errore

   Apri la directory dei registri, trova il file di registro più recente e scorri fino in fondo per visualizzare il messaggio di errore.

8. Il modello v3 di grandi dimensioni è molto lento

   Se non si dispone di una GPU N-card, o non si dispone di un ambiente CUDA configurato, o la memoria video è inferiore a 4G, si prega di non utilizzare questo modello, altrimenti sarà molto lento e balbuziente

9. Il file .dll cublasxx è mancante

   A volte si verifica l'errore "cublasxx .dll non esiste", è necessario scaricare cuBLAS e copiare il file dll nella directory di sistema

   [Fare clic per scaricare cuBLAS, ](https://github.com/jianchang512/stt/releases/download/0.0/cuBLAS_win.7z)decomprimerlo e copiare il file dll in C:/Windows/System32


10. Manca la musica di sottofondo

   只识别人声并保存人声，即配音后音频中不会存在原背景音乐，如果你需要保留，请使用[人声背景音乐分离项目](https://github.com/jianchang512/vocal-separate)，将背景音提取出来，然后再和配音文件合并。

11. Come utilizzare i suoni personalizzati
   
   目前暂不支持该功能，如果有需要，你可以先识别出字幕，然后使用另一个[声音克隆项目](https://github.com/jiangchang512/clone-voice),输入字幕srt文件，选择自定义的音色合成为音频文件，然后再生成新视频。
   
13. Le didascalie non possono essere allineate nel parlato

> Dopo la traduzione, lingue diverse hanno durate di pronuncia diverse, ad esempio una frase in cinese 3 secondi, tradotta in inglese può essere 5 secondi, con conseguente durata e video incoerenti.
> 
> Ci sono 2 modi per risolverlo:
> 
>     1. Forzare le voci fuori campo per velocizzare la riproduzione per ridurre la durata della voce fuori campo e l'allineamento del video
> 
>     2. Forza la riproduzione lenta del video in modo che la lunghezza del video sia maggiore e la voce fuori campo sia allineata.
> 
> Puoi scegliere solo uno dei due
   

14. I sottotitoli non vengono visualizzati o mostrano caratteri confusi

> 
> Sottotitoli compositi soft: i sottotitoli sono incorporati nel video come file separato, che può essere estratto di nuovo, e se il lettore lo supporta, i sottotitoli possono essere abilitati o disabilitati nella gestione dei sottotitoli del lettore;
> 
> Si noti che molti lettori nazionali devono mettere il file dei sottotitoli srt e il video nella stessa directory e con lo stesso nome per caricare i sottotitoli soft, e potrebbe essere necessario convertire il file srt nella codifica GBK, altrimenti visualizzerà caratteri confusi.
> 

15. Come cambiare la lingua dell'interfaccia software/cinese o inglese

Se il file set.ini non esiste nella directory del software, crearlo prima, quindi incollare il codice seguente al suo interno, quindi `lang=`compilare il codice della lingua`zh`, che rappresenta il cinese, che rappresenta`en` l'inglese e quindi riavviare il software

```

[GUI]
;GUI show language ,set en or zh  eg.  lang=en
lang =

```

# Modalità della riga di comando dell'interfaccia della riga di comando

[![Apri in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1yDGPWRyXeZ1GWqkOpdJDv4nA_88HNm01?usp=sharing)


cli.py è uno script di esecuzione da riga di comando ed è`python cli.py` il modo più semplice per eseguirlo

Parametri ricevuti:

`-m mp4视频的绝对地址`

I parametri di configurazione specifici possono essere configurati nella CLI.ini che si trova nella stessa directory di cli.py, e altri indirizzi video MP4 da elaborare possono essere configurati anche tramite parametri della riga di comando, `-m mp4视频绝对地址` ad esempio `python cli.py -m D:/1.mp4`.

cli.ini è il parametro completo, il primo parametro `source_mp4`rappresenta il video da elaborare, se la riga di comando passa i parametri attraverso -m, quindi usa l'argomento della riga di comando, altrimenti usa questo`source_mp4`

`-c 配置文件地址`

È inoltre possibile copiare cli.ini in un'altra posizione `-c cli.ini的绝对路径地址` e specificare il file di configurazione da utilizzare dalla riga di comando  , ad esempio, `python cli.py -c E:/conf/cli.ini` utilizzerà le informazioni di configurazione nel file e ignorerà il file di configurazione nella directory del progetto. 

`-cuda`Non è necessario seguire il valore, basta aggiungerlo per abilitare l'accelerazione CUDA (se disponibile) `python cli.py -cuda`

Esempio:`python cli.py -cuda -m D:/1.mp4`

## Parametri specifici e descrizioni in cli.ini

```
;命令行参数
;待处理的视频绝对地址，正斜杠做路径分隔符，也可在命令行参数中 -m 后传递
source_mp4=
;网络代理地址，google  chatGPT官方china必填
proxy=http://127.0.0.1:10809
;输出结果文件到目录
target_dir=
;视频发音语言，从这里选择 zh-cn zh-tw en fr de ja ko ru es th it pt vi ar tr
source_language=zh-cn
;语音识别语言 无需填写
detect_language=
;翻译到的语言 zh-cn zh-tw en fr de ja ko ru es th it pt vi ar tr
target_language=en
;软字幕嵌入时的语言，不填写
subtitle_language=
;true=启用CUDA
cuda=false
;角色名称，openaiTTS角色名称“alloy,echo,fable,onyx,nova,shimmer”，edgeTTS角色名称从 voice_list.json 中对应语言的角色中寻找。elevenlabsTTS 的角色名称从 elevenlabs.json 中寻找
voice_role=en-CA-ClaraNeural
; 配音加速值，必须以 + 号或 - 号开头，+代表加速，-代表减速，以%结尾
voice_rate=+0%
;可选 edgetTTS  openaiTTS elevenlabsTTS
tts_type=edgeTTS
;静音片段，单位ms
voice_silence=500
;all=整体识别，split=预先分割声音片段后识别
whisper_type=all
;语音识别模型可选，base small medium large-v3
whisper_model=base
;翻译渠道，可选 google baidu  chatGPT Azure  Gemini  tencent DeepL DeepLX
translate_type=google
;0=不嵌入字幕，1=嵌入硬字幕，2=嵌入软字幕
subtitle_type=1
;true=配音自动加速
voice_autorate=false
;true=视频自动慢速
video_autorate=false
;deepl翻译的接口地址
deepl_authkey=asdgasg
;自己配置的deeplx服务的接口地址
deeplx_address=http://127.0.0.1:1188
;腾讯翻译id
tencent_SecretId=
;腾讯翻译key
tencent_SecretKey=
;百度翻译id
baidu_appid=
;百度翻译密钥
baidu_miyue=
; elevenlabstts的key
elevenlabstts_key=
;chatGPT 接口地址，以 /v1 结尾，可填写第三方接口地址
chatgpt_api=
;chatGPT的key
chatgpt_key=
;chatGPT模型，可选 gpt-3.5-turbo gpt-4
chatgpt_model=gpt-3.5-turbo
; Azure 的api接口地址
azure_api=
;Azure的key
azure_key=
; Azure的模型名，可选 gpt-3.5-turbo gpt-4
azure_model=gpt-3.5-turbo
;google Gemini 的key
gemini_key=

```

# Screenshot dell'anteprima del software

![](./images/p1.png?c)

[Demo di Youtube](https://youtu.be/-S7jptiDdtc)

# Tutorial video (di terze parti)

[Distribuisci il codice sorgente su Mac/B station](https://b23.tv/RFiTmlA)

[Usa l'API Gemini per impostare un metodo/stazione b per la traduzione video](https://b23.tv/fED1dS3)


# Progetti correlati

[Strumento di clonazione vocale: sintetizza voci con timbri arbitrari](https://github.com/jianchang512/clone-voice)

[Strumento di riconoscimento vocale: uno strumento locale offline per il riconoscimento vocale in testo](https://github.com/jianchang512/stt)

[Separazione della voce e della musica di sottofondo: uno strumento minimalista per separare la voce e la musica di sottofondo, operazioni localizzate della pagina Web](https://github.com/jianchang512/stt)

## Grazie

> Questo programma si basa principalmente su alcuni progetti open source

1. ffmpeg
2. PyQt5
3. bordo-tts
4. sussurro più veloce


