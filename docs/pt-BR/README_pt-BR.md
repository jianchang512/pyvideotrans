[简体中文](../../README.md) | [English](../EN/README_EN.md) | pt-BR | [Italian](../IT/README_IT.md) | [Spanish](../ES/README_ES.md)

---

[👑 Doe para este projeto](About_pt-BR.md) | [Link de convite para o Discord](https://discord.gg/y9gUweVCCJ) | Canal do WeChat: Procure por "pyvideotrans"

---

## Ferramenta de Tradução e Dublagem de Vídeos

Traduza e duble seus vídeos com facilidade! Esta ferramenta converte vídeos de um idioma para outro, adicionando automaticamente legendas e dublagem no idioma de destino.

**Principais recursos:**

* **Reconhecimento de fala:** Suporta diversos modelos, incluindo `faster-whisper`, `openai-whisper`, `GoogleSpeech` e o modelo chinês `zh_recogn` do Alibaba.
* **Tradução de texto:** Ampla gama de opções, como `Microsoft Translator`, `Google Translate`, `Baidu Translate`, `Tencent Translate`, `ChatGPT`, `AzureAI`, `Gemini`, `DeepL`, `DeepLX`, `ByteDance Volcano`, além da tradução offline com `OTT`.
* **Síntese de texto em fala (TTS):** Diversas vozes disponíveis, incluindo `Microsoft Edge tts`, `Google tts`, `Azure AI TTS`, `Openai TTS`, `Elevenlabs TTS`, APIs personalizadas, `GPT-SoVITS`, e ferramentas como [clone-voice](https://github.com/jianchang512/clone-voice), [ChatTTS-ui](https://github.com/jianchang512/ChatTTS-ui), [Fish TTS](https://github.com/fishaudio/fish-speech) e [CosyVoice](https://github.com/FunAudioLLM/CosyVoice).
* **Preservação da música de fundo:** Mantém a trilha sonora original do vídeo (baseado em uvr5).
* **Amplo suporte a idiomas:** Traduza para e a partir de Chinês (simplificado e tradicional), Inglês, Coreano, Japonês, Russo, Francês, Alemão, Italiano, Espanhol, Português, Vietnamita, Tailandês, Árabe, Turco, Húngaro, Hindi, Ucraniano, Cazaque, Indonésio, Malaio, Tcheco e Polonês ,nl,sw


> **[Patrocinadores]**
>
> [![](https://github.com/user-attachments/assets/48f4ac8f-e321-4bd3-ab2e-d6053d932f49)](https://302.ai/)
>[302.AI](https://302.ai) é uma plataforma self-service que reúne as melhores IAs do mundo, com pagamento sob demanda, sem mensalidades e sem barreiras para usar vários tipos de IA.
>
> [Clique para se registrar](https://302.ai): Ganhe 1 PTC (1 PTC = 1 dólar americano, cerca de R$ 7) instantaneamente. Experimente através do link com um limite diário de 5 PTC.
>
> **Funcionalidades completas:** Integra as melhores IAs na plataforma, incluindo, mas não limitado a, chat de IA, geração de imagens, processamento de imagens, geração de vídeos e cobertura completa.
>
> **Fácil de usar:** Oferece várias formas de uso, como robôs, ferramentas e APIs, atendendo às necessidades de iniciantes a desenvolvedores.
>
> **Pagamento sob demanda, sem barreiras:** Não oferece planos mensais, não impõe barreiras aos produtos, pagamento sob demanda, acesso total. O saldo recarregado é válido para sempre.
>
> **Separação de administradores e usuários:** Os administradores compartilham com um clique, os usuários não precisam fazer login. Os usuários não precisam se preocupar com configurações complexas de IA, permitindo que especialistas em IA configurem e simplifiquem o processo de uso.


# Principais Funcionalidades e Usos

**Tradução e Dublagem de Vídeo:** Traduz o áudio de um vídeo para outro idioma, adicionando dublagem e legendas no novo idioma.

**Transcrição de Áudio/Vídeo para Legendas:** Converte a fala de arquivos de áudio ou vídeo em legendas no formato SRT.

**Dublagem em Lote a Partir de Legendas:** Cria dublagens a partir de arquivos SRT, individualmente ou em lote.

**Tradução de Legendas em Lote:** Traduz um ou mais arquivos SRT para outros idiomas.

**Mesclagem de Áudio, Vídeo e Legendas:** Combina arquivos de áudio, vídeo e legendas em um único vídeo.

**Extração de Áudio de Vídeo:** Separa o áudio de um vídeo, criando um arquivo de áudio e outro de vídeo sem som.

**Download de Vídeos do YouTube:** Baixa vídeos do YouTube.

----



https://github.com/jianchang512/pyvideotrans/assets/3378335/3811217a-26c8-4084-ba24-7a95d2e13d58


# Versões Pré-Compiladas (Windows 10/11)

> **Atenção:** Versões pré-compiladas são exclusivas para Windows 10/11. Para macOS/Linux, utilize a instalação via código fonte.

> **Importante:** As versões pré-compiladas são empacotadas com PyInstaller e podem ser sinalizadas por antivírus. Adicione à lista de permissões ou use o código fonte.

**Baixe e extraia**

1. Baixe a versão desejada em: [https://github.com/jianchang512/pyvideotrans/releases](https://github.com/jianchang512/pyvideotrans/releases)
2. Extraia o conteúdo para um diretório **sem espaços** no nome.

**Execute**

1. **Não execute diretamente do arquivo compactado!**
2. Acesse a pasta onde você extraiu os arquivos.
3. Clique duas vezes em `sp.exe`.
4. Se houver problemas de permissão, clique com o botão direito em `sp.exe` e execute como administrador.

**Observação:** Não mova o arquivo `sp.exe` após a extração.


# Instalação no MacOS (Código Fonte)

**Instale as dependências**

1. Abra o terminal e execute os seguintes comandos:

   ```bash
   # Instale o Homebrew, se necessário:
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   # Configure o Homebrew:
   eval $(brew --config)

   # Instale as dependências:
   brew install libsndfile ffmpeg git python@3.10
   export PATH="/usr/local/opt/python@3.10/bin:$PATH"
   source ~/.bash_profile 
   source ~/.zshrc
   ```

**Prepare o ambiente**

1. Crie uma pasta (sem espaços ou caracteres especiais) e acesse-a pelo terminal.
2. Clone o repositório: `git clone https://github.com/jianchang512/pyvideotrans`
3. Entre na pasta: `cd pyvideotrans`
4. Crie um ambiente virtual: `python -m venv venv`
5. Ative o ambiente: `source ./venv/bin/activate` (seu prompt deve iniciar com `(venv)`).

**Instale as dependências**

1. Instale: `pip install -r requirements.txt `. Se falhar, configure o espelho do pip para o Alibaba:

   ```bash
   pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/
   pip config set install.trusted-host mirrors.aliyun.com
   ```

   Tente instalar novamente. Se persistir, use: `pip install -r requirements.txt `.

**Inicie o software**

1. Execute: `python sp.py`



# Instalação no Linux (Código Fonte)

**Instale o Python 3.10**

* **CentOS/RHEL:**

  ```bash
  sudo yum update
  sudo yum groupinstall "Development Tools"
  sudo yum install openssl-devel bzip2-devel libffi-devel
  cd /tmp
  wget https://www.python.org/ftp/python/3.10.4/Python-3.10.4.tgz
  tar xzf Python-3.10.4.tgz
  cd Python-3.10.4
  ./configure --enable-optimizations
  sudo make && sudo make install
  sudo alternatives --install /usr/bin/python3 python3 /usr/local/bin/python3.10 1
  sudo yum install -y ffmpeg
  ```

* **Ubuntu/Debian:**

  ```bash
  apt update && apt upgrade -y
  apt install software-properties-common -y
  add-apt-repository ppa:deadsnakes/ppa
  apt update
  sudo apt-get install libxcb-cursor0
  apt install python3.10
  curl -sS https://bootstrap.pypa.io/get-pip.py | python3.10
  sudo update-alternatives --install /usr/bin/python python /usr/local/bin/python3.10  1
  sudo update-alternatives --config python
  apt-get install ffmpeg
  ```

Verifique a instalação: `python3 -V` (deve retornar "3.10.4").

**Prepare o ambiente**

1. Crie uma pasta (sem espaços ou caracteres especiais) e acesse-a pelo terminal.
2. Clone o repositório: `git clone https://github.com/jianchang512/pyvideotrans`
3. Entre na pasta: `cd pyvideotrans`
4. Crie um ambiente virtual: `python -m venv venv`
5. Ative o ambiente: `source ./venv/bin/activate` (seu prompt deve iniciar com `(venv)`).

**Instale as dependências**

1. Instale: `pip install -r requirements.txt `. Se falhar, configure o espelho do pip para o Alibaba:

   ```bash
   pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/
   pip config set install.trusted-host mirrors.aliyun.com
   ```

   Tente instalar novamente. Se persistir, use: `pip install -r requirements.txt `.

**Aceleração CUDA (Opcional)**

1. Se desejar usar aceleração CUDA (requer placa NVIDIA e CUDA 11.8+), execute:

   ```bash
   pip uninstall -y torch torchaudio
   pip install torch==2.2.0 torchaudio==2.2.0 --index-url https://download.pytorch.org/whl/cu118
   pip install nvidia-cublas-cu11 nvidia-cudnn-cu11
   ```

   Para configurar o CUDA no Linux, pesquise por "Instalação CUDA Linux".

**Inicie o software**

1. Execute: `python sp.py`


## Instalação do pyvideotrans no Windows 10/11

**Instale o Python 3.10**

1. Baixe o instalador na [página oficial do Python](https://www.python.org/downloads/)
2. Execute o instalador e marque a opção "Add to PATH".
3. Verifique a instalação: `python -V` (deve retornar "3.10.4").

**Instale o Git**

1. Baixe o instalador no site do [Git for Windows](https://github.com/git-for-windows/git/releases/download/v2.45.0.windows.1/Git-2.45.0-64-bit.exe)
2. Execute o instalador e siga as instruções.

**Prepare o ambiente**

1. Crie uma pasta (sem espaços ou caracteres especiais).
2. Abra a pasta no terminal (digite `cmd` na barra de endereços).
3. Clone o repositório: `git clone https://github.com/jianchang512/pyvideotrans`
4. Entre na pasta: `cd pyvideotrans`
5. Crie um ambiente virtual: `python -m venv venv`
6. Ative o ambiente: `.\venv\scripts\activate` (seu prompt deve iniciar com `(venv)`).

**Instale as dependências**

1. Instale: `pip install -r requirements.txt `. Se falhar, configure o espelho do pip para o Alibaba:

   ```bash
   pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/
   pip config set install.trusted-host mirrors.aliyun.com
   ```

   Tente instalar novamente. Se persistir, use: `pip install -r requirements.txt `.

**Aceleração CUDA (Opcional)**

1. Se desejar usar aceleração CUDA (requer placa NVIDIA e CUDA 11.8+), execute:

   ```bash
   pip uninstall -y torch torchaudio
   pip install torch==2.2.0 torchaudio==2.2.0 --index-url https://download.pytorch.org/whl/cu118
   ```

   Para configurar o CUDA no Windows, consulte: [https://pyvideotrans.com/gpu.html](https://pyvideotrans.com/gpu.html)

**Extraia o FFmpeg**

1. Extraia ou baixe (ver seção Solução de Problemas abaixo) o arquivo `ffmpeg.zip` para a pasta do código fonte (substitua se necessário).
2. Verifique se os arquivos `ffmpeg.exe`, `ffprobe.exe` e `ytwin32.exe` estão na pasta `ffmpeg`.

**Inicie o software**

1. Execute: `python sp.py`


## Solução de Problemas na Instalação via Código Fonte

1. **Incompatibilidade com CUDA:** Se sua versão do CUDA for inferior a 12.x e você encontrar problemas com o ctranslate2 (que, por padrão, usa a versão 4.x, compatível apenas com CUDA 12.x), execute:

   ```bash
   pip uninstall -y ctranslate2
   pip install ctranslate2==3.24.0
   ```

2. **Módulo não encontrado:** Caso encontre erros do tipo `[nome do módulo] module not found`, abra o arquivo `requirements.txt`, localize o módulo em questão e remova a parte que especifica a versão (ex: `NomeDoMódulo==1.2.3`).

3. **ytwin32.exe ausente na pasta ffmpeg:** Se o arquivo `ytwin32.exe` estiver ausente, baixe-o em https://github.com/yt-dlp/yt-dlp/releases/download/2024.07.16/yt-dlp.exe, renomeie para `ytwin32.exe` e coloque na pasta `ffmpeg`.

Obs.: Se preferir, você pode baixar a versão mais recente do yt-dlp.exe na página de releases do projeto: [yt-dlp](https://github.com/yt-dlp/yt-dlp/releases), e seguir as instruções acima.

4. **ffmpeg.exe/ffprobe.exe ausentes na pasta ffmpeg:** Veja como baixa-los em [Instalação do FFmpeg no Windows](ffmpeg-download_pt-br.md)


## Tutoriais e Documentação

Para aprender a usar o pyvideotrans, consulte o guia completo em: [https://pyvideotrans.com/guide.html](https://pyvideotrans.com/guide.html)

## Modelos de Reconhecimento de Fala

* **Download:** [https://pyvideotrans.com/model.html](https://pyvideotrans.com/model.html) ou  [Download dos Modelos](Download-do-Modelo.md) (Em pt-BR)
* **Descrição e Comparação:** [https://pyvideotrans.com/02.html](https://pyvideotrans.com/02.html)

## Vídeo Tutoriais (Terceiros)

* Instalação no Mac: [https://www.bilibili.com/video/BV1tK421y7rd/](https://www.bilibili.com/video/BV1tK421y7rd/)
* Tradução com API Gemini: [https://b23.tv/fED1dS3](https://b23.tv/fED1dS3)
* Download e Instalação: [https://www.bilibili.com/video/BV1Gr421s7cN/](https://www.bilibili.com/video/BV1Gr421s7cN/)

## Interface do Software

![imagem](https://github.com/jianchang512/pyvideotrans/assets/3378335/55faecd9-5ac6-4962-b0f3-ef2283000c64)

## Projetos Relacionados

* **ChatTTS-ui:** Interface para sintetizar voz com ChatTTS: [https://github.com/jianchang512/ChatTTS-ui](https://github.com/jianchang512/ChatTTS-ui)
* **OTT:** Ferramenta de tradução de texto offline: [https://github.com/jianchang512/ott](https://github.com/jianchang512/ott)
* **Ferramenta de Clonagem de Voz:** Sintetize voz com qualquer timbre: [https://github.com/jianchang512/clone-voice](https://github.com/jianchang512/clone-voice)
* **Ferramenta de Reconhecimento de Fala:** Conversor offline de fala para texto: [https://github.com/jianchang512/stt](https://github.com/jianchang512/stt)
* **Separador de Voz e Música de Fundo:** Ferramenta para separar voz e música: [https://github.com/jianchang512/vocal-separate](https://github.com/jianchang512/vocal-separate)
* **Versão Aprimorada do api.py do GPT-SoVITS:** [https://github.com/jianchang512/gptsovits-api](https://github.com/jianchang512/gptsovits-api)
* **api.py Adaptado para CosyVoice:** [https://github.com/jianchang512/cosyvoice-api](https://github.com/jianchang512/cosyvoice-api)

## Agradecimentos

> Este programa depende principalmente dos seguintes projetos de código aberto:

1. [ffmpeg](https://github.com/FFmpeg/FFmpeg)
2. [PySide6](https://pypi.org/project/PySide6/)
3. [edge-tts](https://github.com/rany2/edge-tts)
4. [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
5. [openai-whisper](https://github.com/openai/whisper)
6. [pydub](https://github.com/jiaaro/pydub)