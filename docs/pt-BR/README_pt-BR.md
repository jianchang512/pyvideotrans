[简体中文](../../README.md) | [English](../EN/README_EN.md) | pt-BR | [Italian](../IT/README_IT.md) | [Spanish](../ES/README_ES.md)

---

[👑 Doe para este projeto](About_pt-BR.md) | [Link de convite para o Discord](https://discord.gg/y9gUweVCCJ) | Canal do WeChat: Pesquise por "pyvideotrans"

---

## Ferramenta de Tradução e Dublagem de Vídeos Pyvideotrans

O Pyvideotrans permite traduzir e dublar vídeos de um idioma para outro, gerando e adicionando legendas e dublagens automaticamente no idioma desejado.

### Funcionalidades Principais
- **Reconhecimento de Voz:** `faster-whisper`, `openai-whisper`, `GoogleSpeech`, `zh_recogn` da Ali.
- **Tradução de Texto:** `Microsoft Translator`, `Google Translate`, `Baidu Translate`, `Tencent Translate`, `ChatGPT`, `AzureAI`, `Gemini`, `DeepL`, `DeepLX`, `Offline Translation OTT`.
- **Síntese de Texto para Fala:** `Microsoft Edge tts`, `Google tts`, `Azure AI TTS`, `Openai TTS`, `Elevenlabs TTS`, API de servidor TTS personalizado, `GPT-SoVITS`, [clone-voice](https://github.com/jianchang512/clone-voice), [ChatTTS-ui](https://github.com/jianchang512/ChatTTS-ui), [Fish TTS](https://github.com/fishaudio/fish-speech).
- **Recursos Adicionais:** Retenção de música de fundo (baseado em uvr5).
- **Idiomas Suportados:** Chinês Simplificado e Tradicional, Inglês, Coreano, Japonês, Russo, Francês, Alemão, Italiano, Espanhol, Português, Vietnamita, Tailandês, Árabe, Turco, Húngaro, Hindi, Ucraniano, Cazaque, Indonésio, Malaio e Tcheco.

### Principais Funcionalidades
- **Traduzir Vídeo e Dublar:** Tradução e dublagem de vídeos para outro idioma com incorporação de legendas.
- **Áudio ou Vídeo para Legendas:** Conversão de fala em texto e exportação como arquivos de legenda SRT.
- **Criação e Dublagem de Legendas em Lote:** Dublagem a partir de arquivos SRT, com suporte a processamento em lote.
- **Tradução de Legendas em Lote:** Tradução de arquivos SRT para outros idiomas.
- **Mesclar Áudio, Vídeo e Legendas:** Combinação de arquivos de áudio, vídeo e legendas em um único vídeo.
- **Extrair Áudio de Vídeo:** Separação de um vídeo em arquivos de áudio e vídeo silencioso.
- **Baixar Vídeos do YouTube:** Download de vídeos do YouTube.

---

https://github.com/jianchang512/pyvideotrans/assets/3378335/3811217a-26c8-4084-ba24-7a95d2e13d58

## Versão Pré-compilada (Somente para Windows 10/11, MacOS/Linux use a implantação do código-fonte)

> O PyVideoTrans é empacotado usando pyinstaller e não é assinado, portanto, seu antivírus pode gerar alertas. Para evitar isso, adicione o programa à lista de permissões do antivírus ou opte pela implantação usando o código-fonte.

1. [Clique aqui](https://github.com/jianchang512/pyvideotrans/releases) para baixar a versão pré-compilada.
2. Extraia o arquivo para um diretório sem espaços e com nome em inglês. Após a extração, execute `sp.exe` (Se houver problemas de permissão, execute como administrador).

**Obs:** Execute o programa após descompactá-lo. Não execute diretamente do arquivo compactado e não mova `sp.exe` para outro local após a descompactação.

## Implantação do Código-Fonte

### MacOS
1. Certifique-se de ter o `Homebrew` instalado. Se não, instale-o com:
    ```bash
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    ```
2. Abra uma janela de terminal e execute os seguintes comandos:
    ```bash
    brew install libsndfile
    brew install ffmpeg
    brew install git
    brew install python@3.10
    export PATH="/usr/local/opt/python@3.10/bin:$PATH"
    source ~/.bash_profile
    source ~/.zshrc
    ```
3. Crie uma pasta sem espaços ou caracteres chineses e navegue até essa pasta no terminal.
4. Clone o repositório e entre no diretório:
    ```bash
    git clone https://github.com/jianchang512/pyvideotrans
    cd pyvideotrans
    ```
5. Crie e ative um ambiente virtual:
    ```bash
    python -m venv venv
    source ./venv/bin/activate
    ```
6. Instale as dependências:
    ```bash
    pip install -r mac-requirements.txt --no-deps
    # Se falhar, tente:
    pip install -r requirements.txt --ignore-installed --no-deps
    ```
7. Execute o software:
    ```bash
    python sp.py
    ```

### Linux
1. Instale o Python 3.10 e outras dependências, dependendo da sua distribuição:
- **CentOS/RHEL**
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
    sudo alternatives --install /usr/bin/python3 python3 /usr/local/bin/python3.10
    sudo yum install -y ffmpeg
    ```

- **Ubuntu/Debian**
    ```bash
    sudo apt update && sudo apt upgrade -y
    sudo apt install software-properties-common -y
    sudo add-apt-repository ppa:deadsnakes/ppa
    sudo apt update
    sudo apt install python3.10
    curl -sS https://bootstrap.pypa.io/get-pip.py | python3.10
    sudo apt-get install ffmpeg
    ```
2. Verifique a instalação do Python:
    ```bash
    python3 -V
    # Deve retornar "3.10.4"
    ```
3. Clone o repositório e entre no diretório:
    ```bash
    git clone https://github.com/jianchang512/pyvideotrans
    cd pyvideotrans
    ```
4. Crie e ative um ambiente virtual:
    ```bash
    python -m venv venv
    source ./venv/bin/activate
    ```
5. Instale as dependências:
    ```bash
    pip install -r requirements.txt --no-deps
    # Se falhar, mude para o espelho Alibaba:
    pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/
    pip config set install.trusted-host mirrors.aliyun.com
    pip install -r requirements.txt --ignore-installed --no-deps
    ```
6. Para usar a aceleração CUDA, execute:
    ```bash
    pip uninstall -y torch torchaudio
    pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
    pip install nvidia-cublas-cu11 nvidia-cudnn-cu11
    ```
7. Execute o software:
    ```bash
    python sp.py
    ```

### Windows 10/11
1. Instale o Python 3.10 de [python.org](https://www.python.org/downloads/), certificando-se de selecionar "Adicionar ao PATH".
2. Instale o Git de [git-for-windows](https://github.com/git-for-windows/git/releases/download/v2.45.0.windows.1/Git-2.45.0-64-bit.exe).
3. Crie uma pasta com um nome simples (sem espaços ou caracteres especiais) e abra um terminal nela.
4. Clone o repositório e entre no diretório:
    ```cmd
    git clone https://github.com/jianchang512/pyvideotrans
    cd pyvideotrans
    ```
5. Crie e ative um ambiente virtual:
    ```cmd
    python -m venv venv
    .\venv\scripts\activate
    ```
6. Instale as dependências:
    ```cmd
    pip install -r requirements.txt --no-deps
    # Se falhar, mude para o espelho Alibaba:
    pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/
    pip config set install.trusted-host mirrors.aliyun.com
    pip install -r requirements.txt --ignore-installed --no-deps
    ```
7. Para usar a aceleração CUDA, execute:
    ```cmd
    pip uninstall -y torch torchaudio
    pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
    ```
8. Descompacte `ffmpeg.zip` no diretório do código-fonte, substituindo se solicitado.
9. Execute o software:
    ```cmd
    python sp.py
    ```

## Explicação de Problemas na Implantação do Código-Fonte

Por padrão, a versão 4.x do ctranslate2 é usada, suportando apenas a versão CUDA12.x. Se a sua versão do CUDA for inferior a 12 e você não puder atualizar para o CUDA12.x, execute:
```bash
pip uninstall -y ctranslate2
pip install ctranslate2==3.24.0
```
**Nota:** Para erros como `xx module not found`, remova o `==` e o número da versão no `requirements.txt`.

---

## Links Úteis
- **Docs:**
    [Guia do Usuário e Documentação](https://pyvideotrans.com/guide.html)
    [Como adicionar pacotes de idioma](language_pt-BR.md)
    [Como baixar e instalar o FFmpeg](ffmpeg-download_pt-br.md)
- **Modelos de Reconhecimento de Fala:**
    [Download dos Modelos](Download-do-Modelo.md) **(Em pt-BR)**
    [Download dos Modelos](https://pyvideotrans.com/model.html)
    [Descrições e Diferenças dos Modelos](https://pyvideotrans.com/02.html)
- **Tutoriais em Vídeo (Terceiros):**
    [Implantação do Código-Fonte no Mac/Bilibili](https://www.bilibili.com/video/BV1tK421y7rd/)
    [Método de Configuração da Tradução de Vídeo com Gemini Api/Bilibili](https://b23.tv/fED1dS3)
    [Como Baixar e Instalar](https://www.bilibili.com/video/BV1Gr421s7cN/)
- **Projetos Relacionados:**
    [OTT: Ferramenta de Tradução de Texto Offline Local](https://github.com/jianchang512/ott)
    [Ferramenta de Clonagem de Voz: Sintetizando Fala com Qualquer Voz](https://github.com/jianchang512/clone-voice)
    [Ferramenta de Reconhecimento de Fala: Ferramenta de Fala para Texto Offline Local](https://github.com/jianchang512/stt)
    [Ferramenta de Separação de Voz e Música de Fundo](https://github.com/jianchang512/vocal-separate)
    [Versão Melhorada do api.py para GPT-SoVITS](https://github.com/jianchang512/gptsovits-api)

## Interface do Pyvideotrans
![Interface](https://github.com/jianchang512/pyvideotrans/assets/3378335/c3abb561-1ab5-47f9-bfdc-609245445190)

## Agradecimentos
Este programa depende de vários projetos de código aberto, principalmente:
1. ffmpeg
2. PySide6
3. edge-tts
4. faster-whisper
5. openai-whisper
6. pydub

---
