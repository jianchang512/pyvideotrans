[English](./README_EN.md) / [Dona al proyecto](./about.md) / [Join Discord](https://discord.gg/TMCM2PfHzQ)

# Herramientas de traducción y doblaje de vídeo

[Descargue la versión precompilada de Windows del exe](https://github.com/jianchang512/pyvideotrans/releases)

>
> Es una herramienta de doblaje de traducción de video que traduce un video en un idioma a un video en un idioma específico, genera y agrega automáticamente subtítulos y doblaje en ese idioma.
>
> El reconocimiento de voz se basa en `faster-whisper` un modelo sin conexión
>
> Soporte de traducción de `google|baidu|tencent|chatGPT|Azure|Gemini|DeepL|DeepLX` textos,
>
> Compatibilidad con `Microsoft Edge tts` `Openai TTS-1`  texto a voz`Elevenlabs TTS`
>

# Usos y uso principales

【Traducir video y doblaje】 Configure cada opción según sea necesario, configure libremente la combinación y realice la traducción y el doblaje, la aceleración y desaceleración automáticas, la fusión, etc.

[Extraer subtítulos sin traducción] Seleccione un archivo de video y seleccione el idioma de origen del video, luego se reconocerá el texto del video y el archivo de subtítulos se exportará automáticamente a la carpeta de destino

【Extraer subtítulos y traducir】 Seleccione el archivo de video, seleccione el idioma de origen del video y configure el idioma de destino que se traducirá, luego se reconocerá el texto del video y se traducirá al idioma de destino, y luego el archivo de subtítulos bilingüe se exportará a la carpeta de destino

[Combinación de subtítulos y vídeo] Seleccione el vídeo, luego arrastre y suelte el archivo de subtítulos existente en el área de subtítulos de la derecha, establezca el idioma de origen y el idioma de destino en el idioma de los subtítulos y, a continuación, seleccione el tipo de doblaje y la función para iniciar la ejecución

【Crear doblaje para subtítulos】 Arrastre y suelte el archivo de subtítulos local en el editor de subtítulos a la derecha, luego seleccione el idioma de destino, el tipo de doblaje y el rol, y transfiera el archivo de audio doblado generado a la carpeta de destino

[Reconocimiento de texto de audio y vídeo] Arrastre el vídeo o audio a la ventana de reconocimiento y el texto se reconocerá y exportará al formato de subtítulos SRT

[Sintetizar texto en voz] Genere una voz en off a partir de un fragmento de texto o subtítulo utilizando una función de doblaje específica

Separar audio de video Separa archivos de video en archivos de audio y videos silenciosos

【Combinación de subtítulos de audio y video】 Combine archivos de audio, archivos de video y archivos de subtítulos en un solo archivo de video

【Conversión de formato de audio y video】 Conversión entre varios formatos

【Traducción de subtítulos】 Traduzca texto o archivos de subtítulos SRT a otros idiomas

----




https://github.com/jianchang512/pyvideotrans/assets/3378335/c3d193c8-f680-45e2-8019-3069aeb66e01



# Use win para precompilar la versión exe (otros sistemas usan código fuente para la implementación)

0. [Haga clic en Descargar para descargar la versión precompilada](https://github.com/jianchang512/pyvideotrans/releases)

1. Se recomienda descomprimir los datos a la ruta en inglés y la ruta no contiene espacios. Después de la descompresión, haga doble clic en sp.exe (si encuentra problemas de permisos, puede hacer clic con el botón derecho para abrirlo con permisos de administrador)

3. Si no se realiza ninguna eliminación, el software de eliminación doméstica puede tener falsos positivos, que se pueden ignorar o implementar mediante código fuente


# Implementación del código fuente

[![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1yDGPWRyXeZ1GWqkOpdJDv4nA_88HNm01?usp=sharing)


1. Configurar el entorno de Python 3.9->3.11
2. `git clone https://github.com/jianchang512/pyvideotrans`
3. `cd pyvideotrans`
4. `python -m venv venv`
5. Ejecute en Windows `%cd%/venv/scripts/activate`, Linux y Mac `source ./venv/bin/activate`
6. `pip install -r requirements.txt`Si encuentra un conflicto de versiones, use `pip install -r requirements.txt --no-deps` (CUDA no es compatible con MacOS, reemplace requirements.txt por requirements-mac.txt en Mac).
7. Extraiga ffmpeg .zip al directorio raíz (archivo ffmpeg .exe), Linux y Mac Instale ffmpeg usted mismo, el método específico puede ser "Baidu o Google"
8. `python sp.py` Abra la interfaz del software
9. Si necesita admitir la aceleración CUDA, debe tener una tarjeta gráfica NVIDIA en el dispositivo, consulte Compatibilidad con aceleración CUDA [ a continuación para conocer las precauciones de instalación específicas](https://github.com/jianchang512/pyvideotrans?tab=readme-ov-file#cuda-%E5%8A%A0%E9%80%9F%E6%94%AF%E6%8C%81)


# Modo de empleo:

1. Video original: seleccione video MP4 / AVI / MOV / MKV / MPEG, puede seleccionar varios videos;

2. Directorio de vídeo de salida: Si no selecciona esta opción, se generará en el mismo directorio de forma predeterminada y se crearán `_video_out` dos archivos de subtítulos en el idioma original y en el idioma de destino en la carpeta SRT de este directorio

3. Seleccione una traducción: Seleccione google|baidu|tencent|chatGPT|Azure|Géminis|DeepL|Canal de traducción de DeepLX

4. Dirección de proxy web: Si no puede acceder directamente a google/chatGPT en su región, debe configurar un proxy en la interfaz de software Web Proxy, por ejemplo, si usa v2ray`http://127.0.0.1:10809`, complete .  Si `http://127.0.0.1:7890`ha modificado el puerto predeterminado u otro software proxy que esté utilizando, complete la información según sea necesario

5. Idioma original: seleccione el idioma del video que desea traducir

6. Idioma de destino: seleccione el idioma al que desea traducir

7. Seleccionar doblaje: Después de seleccionar el idioma de destino para la traducción, puede seleccionar la función de doblaje en las opciones de doblaje.
   
   Subtítulos duros: Se refiere a mostrar siempre los subtítulos, que no se pueden ocultar, si desea tener subtítulos al reproducir en la página web, seleccione incrustación de subtítulos duros

   Subtítulos suaves: si el reproductor admite la administración de subtítulos, puede mostrar o cerrar subtítulos, pero los subtítulos no se mostrarán cuando se reproduzcan en la página web, es posible que algunos reproductores nacionales no lo admitan y debe colocar el video generado con el mismo nombre srt file y video en un directorio para que se muestre


8. Modelo de reconocimiento de voz: seleccione base/pequeño/mediano/grande-v3, el efecto de reconocimiento es cada vez mejor, pero la velocidad de reconocimiento es cada vez más lenta, y la memoria requerida es cada vez más grande, el modelo base incorporado, descargue otros modelos por separado, descomprímalos y colóquelos en el `/models` directorio

   Reconocimiento general/presegmentación: El reconocimiento integral se refiere al envío de todo el archivo de voz directamente al modelo, que es procesado por el modelo, y la segmentación puede ser más precisa, pero también puede crear un solo subtítulo con una duración de 30 segundos, que es adecuado para audio con silencio claro;  La segmentación previa significa que el audio se corta a una duración de unos 10 segundos y luego se envía al modelo para su procesamiento.

    [Todos los modelos están disponibles para su descarga](https://github.com/jianchang512/stt/releases/tag/0.0)
    
    Después de la descarga, descomprima y copie la carpeta models--systran--faster-whisper-xx en el paquete comprimido en el directorio models

    ![](https://github.com/jianchang512/stt/assets/3378335/5c972f7b-b0bf-4732-a6f1-253f42c45087)
 

    [Descarga de FFmepg (la versión compilada viene con él).](https://www.ffmpeg.org/)

9. Velocidad de habla de doblaje: complete el número entre -90 y +90, la misma oración en diferentes idiomas, el tiempo requerido es diferente, por lo que es posible que los subtítulos de sonido e imagen no se sincronicen después del doblaje, puede ajustar la velocidad de habla aquí, los números negativos representan una velocidad lenta, los números positivos representan una reproducción acelerada.

10. Alineación de audio y vídeo: "Aceleración automática de la voz en off" y "ralentización automática del vídeo" respectivamente

>
> Después de la traducción, los diferentes idiomas tienen diferentes duraciones de pronunciación, como una oración en chino 3s, traducida al inglés puede ser 5s, lo que resulta en una duración y un video inconsistentes.
> 
> Hay 2 formas de solucionarlo:
>
>     1. Forzar voces en off para acelerar la reproducción para acortar la duración de la voz en off y la alineación del vídeo
> 
>     2. Obligue a que el video se reproduzca lentamente para que la duración del video sea más larga y la voz en off esté alineada.
> 
> Puede elegir solo uno de los dos
>  
 
  
11. Silenciar clip: Introduzca un número de 100 a 2000, que represente milisegundos, y el valor predeterminado es 500, es decir, el segmento silenciado mayor o igual a 500 ms se utiliza como intervalo para dividir la voz

12. **Aceleración CUDA**: Confirme que la tarjeta gráfica de su computadora es una tarjeta N y que se han configurado el entorno y el controlador CUDA, luego habilite esta opción, la velocidad se puede mejorar considerablemente y el método de configuración específico se muestra en el soporte de[ aceleración CUDA a continuación](https://github.com/jianchang512/pyvideotrans?tab=readme-ov-file#cuda-%E5%8A%A0%E9%80%9F%E6%94%AF%E6%8C%81)

13. TTS: Puede usar los modelos edgeTTS y openai TTS para seleccionar los caracteres que desea sintetizar la voz, y openai necesita usar la interfaz oficial o abrir la interfaz de terceros del modelo TTS-1

14. Haga clic en el botón Inicio en la parte inferior para mostrar el progreso actual y los registros, y los subtítulos se mostrarán en el cuadro de texto de la derecha

15. Una vez completado el análisis de subtítulos, se detendrá y esperará a que se modifique el subtítulo, y si no hace nada, pasará automáticamente al siguiente paso después de 60 segundos. También puede editar los subtítulos en el área de subtítulos de la derecha y, a continuación, hacer clic manualmente para continuar con la composición

16. En el subdirectorio del vídeo con el mismo nombre en la carpeta de destino, se generará respectivamente el archivo SRT de subtítulos de los dos idiomas, la voz original y el archivo WAV doblado para facilitar su posterior procesamiento

17. Establecer el rol de línea: Puede establecer el rol de pronunciación para cada línea en los subtítulos, primero seleccione el tipo y el rol TTS a la izquierda, y luego haga clic en "Establecer rol de línea" en la parte inferior derecha del área de subtítulos, y complete el número de línea que desea usar el doblaje del rol en el texto detrás del nombre de cada personaje, como se muestra en la siguiente figura:![](./images/p2.png)
    
# Ajustes avanzados videotrans/set.ini

**No lo ajustes a menos que sepas lo que va a pasar**

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



# Compatibilidad con la aceleración CUDA

**Instale la herramienta**  CUDA [para obtener métodos de instalación detallados](https://juejin.cn/post/7318704408727519270)

Después de instalar CUDA, si hay un problema, realice `pip uninstall torch torchaudio torchvision` Desinstalar[, luego vaya a https://pytorch.org/get-started/locally/]() según el tipo de sistema operativo y la versión de CUDA, seleccione `pip3` el comando,  cambie  a y, `pip`a continuación, copie el comando para ejecutarlo. 
 
Una vez completada la instalación, ejecute Si el `python testcuda.py` resultado es True, está disponible  

A veces aparece el error "cublasxx .dll doesn't exist", o no recibe este error, y la configuración de CUDA es correcta, pero siempre aparece el error de reconocimiento, debe descargar cuBLAS y luego copiar el archivo dll en el directorio del sistema

[Haga clic para descargar cuBLAS, ](https://github.com/jianchang512/stt/releases/download/0.0/cuBLAS_win.7z)descomprimirlo y copiar el archivo dll en C:/Windows/System32


# Preguntas frecuentes

1. Usando Google Translate, dice error

   Para utilizar la interfaz oficial de google o chatGPT en China, es necesario colgar una escalera

2. Se ha utilizado un proxy global, pero no parece que vaya a ser un proxy

   Debe establecer una dirección proxy específica en la interfaz del software "Proxy de red", como http://127.0.0.1:7890

3. Consejo: FFmepg no existe

   Primero verifique para asegurarse de que hay ffmpeg .exe, ffprobe ..exe archivos en el directorio raíz del software, si no existen, descomprima ffmpeg .7z y coloque estos 2 archivos en el directorio raíz del software

4. CUDA está habilitado en Windows, pero se muestra un error

   R: [En primer lugar, verifique el método de instalación detallado, ](https://juejin.cn/post/7318704408727519270)asegúrese de haber instalado correctamente las herramientas relacionadas con cuda, si aún hay errores,[ haga clic para descargar cuBLAS, ](https://github.com/jianchang512/stt/releases/download/0.0/cuBLAS_win.7z)descomprima y copie el archivo dll dentro de C: / Windows / System32

   B: Si está seguro de que no tiene nada que ver con A, verifique si el video está codificado en H264 mp4, algunos videos HD están codificados en H265, esto no es compatible, puede intentar convertir a video H264 en la "Caja de herramientas de video".

   C: La decodificación de hardware y la codificación de video bajo GPU requieren una estricta corrección de datos, y la tasa de tolerancia a fallas es casi 0, cualquier pequeño error conducirá a fallas, además de que las diferencias entre las diferentes versiones del modelo de tarjeta gráfica, la versión del controlador, la versión CUDA, la versión ffmpeg, etc., lo que resulta en errores de compatibilidad son fáciles de ocurrir. En la actualidad, se agrega la reserva y el software de la CPU se usa automáticamente para codificar y decodificar después de una falla en la GPU. Cuando se produce un error, se registra un mensaje de error en el directorio de registros.

5. Indica que el modelo no existe

   Después de la versión 0.985, los modelos deben reinstalarse y el directorio models es una carpeta para cada modelo, no un archivo pt.
   Para usar el modelo base, asegúrese de que exista la carpeta models/models--Systran--faster-whisper-base, si no existe, debe descargarla y copiar la carpeta en los modelos.
   Si desea utilizar un modelo pequeño, debe asegurarse de que exista la carpeta models/models--Systran--faster-whisper-small, si no existe, debe descargarla y copiar la carpeta en models.
   Para usar el modelo medio, asegúrese de que exista la carpeta models/models--Systran--faster-whisper-medium, si no existe, debe descargarla y copiar la carpeta en los modelos.
   Para usar el modelo large-v3, asegúrese de que la carpeta models/models--Systran--faster-whisper-large-v3 existe, si no es así, debe descargarla y copiar la carpeta en los modelos.

   [Todos los modelos están disponibles para su descarga](https://github.com/jianchang512/stt/releases/tag/0.0)

6. El directorio no existe o el permiso es incorrecto

   Haga clic con el botón derecho en sp..exe para abrir con privilegios de administrador

7. Se solicita un error, pero no hay información detallada sobre el error

   Abra el directorio de registros, busque el archivo de registro más reciente y desplácese hasta la parte inferior para ver el mensaje de error.

8. El modelo v3 grande es muy lento

   Si no tiene una GPU de tarjeta N, o no tiene un entorno CUDA configurado, o la memoria de video es inferior a 4G, no use este modelo, de lo contrario será muy lento y tartamudeará

9. Falta el archivo .dll cublasxx

   A veces encuentra el error "cublasxx .dll no existe", debe descargar cuBLAS y copiar el archivo dll en el directorio del sistema

   [Haga clic para descargar cuBLAS, ](https://github.com/jianchang512/stt/releases/download/0.0/cuBLAS_win.7z)descomprimirlo y copiar el archivo dll en C:/Windows/System32


10. Falta la música de fondo

   只识别人声并保存人声，即配音后音频中不会存在原背景音乐，如果你需要保留，请使用[人声背景音乐分离项目](https://github.com/jianchang512/vocal-separate)，将背景音提取出来，然后再和配音文件合并。

11. Cómo usar sonidos personalizados
   
   目前暂不支持该功能，如果有需要，你可以先识别出字幕，然后使用另一个[声音克隆项目](https://github.com/jiangchang512/clone-voice),输入字幕srt文件，选择自定义的音色合成为音频文件，然后再生成新视频。
   
13. Los subtítulos no se pueden alinear en la voz

> Después de la traducción, los diferentes idiomas tienen diferentes duraciones de pronunciación, como una oración en chino 3s, traducida al inglés puede ser 5s, lo que resulta en una duración y un video inconsistentes.
> 
> Hay 2 formas de solucionarlo:
> 
>     1. Forzar voces en off para acelerar la reproducción para acortar la duración de la voz en off y la alineación del vídeo
> 
>     2. Obligue a que el video se reproduzca lentamente para que la duración del video sea más larga y la voz en off esté alineada.
> 
> Puede elegir solo uno de los dos
   

14. Los subtítulos no aparecen ni muestran caracteres ilegibles

> 
> Subtítulos compuestos suaves: los subtítulos se incrustan en el video como un archivo separado, que se puede extraer nuevamente y, si el reproductor lo admite, los subtítulos se pueden habilitar o deshabilitar en la administración de subtítulos del reproductor;
> 
> Tenga en cuenta que muchos reproductores nacionales deben poner el archivo de subtítulos srt y el video en el mismo directorio y el mismo nombre para cargar los subtítulos suaves, y es posible que deba convertir el archivo srt a la codificación GBK, de lo contrario, mostrará caracteres ilegibles.
> 

15. Cómo cambiar el idioma de la interfaz del software/chino o inglés

Si el archivo videotrans/set.ini no existe  , créelo primero, luego pegue el siguiente código en él, `lang=`luego complete el código de idioma, que `zh`representa el chino, que representa `en`el inglés y, a continuación, reinicie el software

```

[GUI]
;GUI show language ,set en or zh  eg.  lang=en
lang =

```

# Modo de línea de comandos de la CLI

[![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1yDGPWRyXeZ1GWqkOpdJDv4nA_88HNm01?usp=sharing)


cli.py es un script de ejecución de línea de comandos y`python cli.py` es la forma más fácil de ejecutarlo

Parámetros recibidos:

`-m mp4 `

Los parámetros de configuración específicos se pueden configurar en la CLI.ini ubicada en el mismo directorio que cli.py, y otras direcciones de video MP4 que se procesarán también se pueden configurar mediante parámetros de línea de comandos, `-m mp4 ` como `python cli.py -m D:/1.mp4`.

cli.ini son los parámetros completos, el primer parámetro `source_mp4`representa el video que se procesará, si la línea de comandos pasa parámetros a través de -m, use el argumento de la línea de comandos, de lo contrario use esto`source_mp4`

`-c cli.ini`

También puede copiar cli.ini a otra ubicación `-c cli.ini的绝对路径地址` y especificar el archivo de configuración a utilizar desde la línea de comandos,  por ejemplo, `python cli.py -c E:/conf/cli.ini` utilizará la información de configuración en el archivo e ignorará el archivo de configuración en el directorio del proyecto. 

`-cuda`No es necesario seguir el valor, simplemente agréguelo para habilitar la aceleración CUDA (si está disponible) `python cli.py -cuda`

Ejemplo:`python cli.py -cuda -m D:/1.mp4`

## Parámetros específicos y descripciones en cli.ini

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

# Captura de pantalla de la vista previa del software

![](./images/p1.png?c)

[Demostración de Youtube](https://youtu.be/-S7jptiDdtc)

# Tutoriales en video (de terceros)

[Implementar el código fuente en la estación Mac/B](https://b23.tv/RFiTmlA)

[Utilice la API de Gemini para configurar una estación de método/b para la traducción de vídeo](https://b23.tv/fED1dS3)


# Proyectos Relacionados

[Herramienta de clonación de voz: sintetiza voces con timbres arbitrarios](https://github.com/jianchang512/clone-voice)

[Herramienta de reconocimiento de voz: una herramienta local de reconocimiento de voz a texto sin conexión](https://github.com/jianchang512/stt)

[Separación de voces y música de fondo: una herramienta minimalista para separar voces y música de fondo, operaciones de páginas web localizadas](https://github.com/jianchang512/stt)

## Gracias

> Este programa se basa principalmente en algunos proyectos de código abierto

1. ffmpeg
2. PyQt5
3. Borde-TTS
4. Susurro más rápido


