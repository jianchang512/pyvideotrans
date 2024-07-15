# Download de Modelos para o PyVideoTrans

O PyVideoTrans oferece suporte a uma variedade de modelos de reconhecimento de voz (Automatic Speech Recognition - ASR) para transcrição. Abaixo estão as instruções e links para download dos modelos disponíveis.

## Links para Download dos Modelos

Para sua conveniência, você pode baixar todos os modelos de reconhecimento de voz em um único arquivo:

- **Baixar todos os modelos de reconhecimento de voz:** [https://github.com/jianchang512/stt/releases/tag/0.0](https://github.com/jianchang512/stt/releases/tag/0.0)

## Modelos Faster Whisper

Os modelos Faster Whisper são otimizados para velocidade e desempenho.

### Instruções de Download

1. Baixe o modelo desejado da lista abaixo.
2. Extraia o arquivo baixado.
3. Copie a pasta extraída, para o diretório `models` do PyVideoTrans.

### Modelos Disponíveis

| Nome do Modelo | Tamanho | Link para Download | Mirrors |
| :------------- | :------ | :----------------- | :---------- |
| tiny | 64MB | [GitHub Link](https://github.com/jianchang512/stt/releases/download/0.0/faster-tiny.7z)
| tiny.en | 64MB | [GitHub Link](https://github.com/jianchang512/stt/releases/download/0.0/faster-tiny.en.7z)
| base | 124MB | [GitHub Link](https://github.com/jianchang512/stt/releases/download/0.0/faster-base.7z)
| base.en | 124MB | [GitHub Link](https://github.com/jianchang512/stt/releases/download/0.0/faster-base.en.7z)
| small | 415MB | [GitHub Link](https://github.com/jianchang512/stt/releases/download/0.0/faster-small.7z) | [Baidu Netdisk](https://pan.baidu.com/s/1ROjy-UOjz_2a7I_cyzUj2g?pwd=frth) |
| small.en | 415MB | [GitHub Link](https://github.com/jianchang512/stt/releases/download/0.0/faster-small.en.7z)
| medium | 1.27G | [GitHub Link](https://github.com/jianchang512/stt/releases/download/0.0/faster-medium.7z)
| medium.en | 1.27G | [GitHub Link](https://github.com/jianchang512/stt/releases/download/0.0/faster-medium.en.7z)
| large-v1 | - | [Hugging Face Link](https://huggingface.co/spaces/mortimerme/s4/resolve/main/faster-large-v1.7z?download=true) | [Baidu Netdisk](https://pan.baidu.com/s/1IS5y0Pyo1okPQOW2uNaLbw?pwd=428z) | Baidu Netdisk |
| large-v2 | - | [Hugging Face Link](https://huggingface.co/spaces/mortimerme/s4/blob/main/largev2-jieyao-dao-models.7z) | [Baidu Netdisk](https://pan.baidu.com/s/1pQiexsXSCtdN5yBeFAtwLw?pwd=yjmg) | Baidu Netdisk |
| large-v3 | - | [Hugging Face Link](https://huggingface.co/spaces/mortimerme/s4/resolve/main/largeV3Model-extract-models-folder-%E8%A7%A3%E5%8E%8B%E5%88%B0models%E7%9B%AE%E5%BD%95%E4%B8%8B.7z?download=true) | [Baidu Netdisk](https://pan.baidu.com/s/11a5NYCdRSW6VBOlGmeZdhg?pwd=he2w)
| distil-whisper-small.en | 282MB | [GitHub Link](https://github.com/jianchang512/stt/releases/download/0.0/distil-whisper-small.en.7z)
| distil-whisper-medium.en | 671MB | [GitHub Link](https://github.com/jianchang512/stt/releases/download/0.0/distil-whisper-medium.en.7z)
| distil-medium | - | [Baidu Netdisk](https://pan.baidu.com/s/1HXbf8lYBhlxkvX5ZTEtafA?pwd=443i)
| distil-whisper-large-v2 | 1.27G | [GitHub Link](https://github.com/jianchang512/stt/releases/download/0.0/distil-whisper-large-v2.7z)
| distil-large-v2 | - | [Baidu Netdisk](https://pan.baidu.com/s/1HXbf8lYBhlxkvX5ZTEtafA?pwd=443i)
| distil-whisper-large-v3 | 1.3G | [GitHub Link](https://github.com/jianchang512/stt/releases/download/0.0/distil-whisper-large-v3.7z) | [Baidu Netdisk](https://pan.baidu.com/s/1bEeZg584tOvEXlIOx5QQGg?pwd=958n)


### Estrutura de Pastas Esperada

Após copiar os modelos para o diretório `models`, você deverá ter as seguintes pastas:

```
models
├── models--Systran--faster-whisper-base
├── models--Systran--faster-whisper-small
├── models--Systran--faster-whisper-medium
├── models--Systran--faster-whisper-large-v2
└── models--Systran--faster-whisper-large-v3
```

## Whisper (OpenAI)

Os modelos OpenAI Whisper são conhecidos por sua precisão e qualidade de transcrição.

### Instruções de Download

1. Baixe o arquivo `.pt` do modelo desejado da lista abaixo.
2. Copie o arquivo `.pt` diretamente para o diretório `models`.

### Modelos Disponíveis

| Nome do Modelo | Tamanho | Link para Download |
| :-------------- | :----------- | :------------------------------------------------------------------------------------------------- |
| tiny | 66 MB | [Download Link](https://openaipublic.azureedge.net/main/whisper/models/65147644a518d12f04e32d6f3b26facc3f8dd46e5390956a9424a650c0ce22b9/tiny.pt) |
| tiny.en | 74 MB | [Download Link](https://openaipublic.azureedge.net/main/whisper/models/d3dd57d32accea0b295c96e26691aa14d8822fac7d9d27d5dc00b4ca2826dd03/tiny.en.pt) |
| base | 142 MB | [Download Link](https://openaipublic.azureedge.net/main/whisper/models/ed3a0b6b1c0edf879ad9b11b1af5a0e6ab5db9205f891f668f8b0e6c6326e34e/base.pt) |
| base.en | 155 MB | [Download Link](https://openaipublic.azureedge.net/main/whisper/models/25a8566e1d0c1e2231d1c762132cd20e0f96a85d16145c3a00adf5d1ac670ead/base.en.pt) |
| small | 500 MB | [Download Link](https://openaipublic.azureedge.net/main/whisper/models/9ecf779972d90ba49c06d968637d720dd632c55bbf19d441fb42bf17a411e794/small.pt) |
| small.en | 518 MB | [Download Link](https://openaipublic.azureedge.net/main/whisper/models/f953ad0fd29cacd07d5a9eda5624af0f6bcf2258be67c92b79389873d91e0872/small.en.pt) |
| medium | 1.5 GB | [Download Link](https://openaipublic.azureedge.net/main/whisper/models/345ae4da62f9b3d59415adc60127b97c714f32e89e936602e85993674d08dcb1/medium.pt) |
| medium.en | 1.6 GB | [Download Link](https://openaipublic.azureedge.net/main/whisper/models/d7440d1dc186f76616474e0ff0b3b6b879abc9d1a4926b7adfa41db2d497ab4f/medium.en.pt) |
| large-v1 | 2.9 GB | [Download Link](https://openaipublic.azureedge.net/main/whisper/models/e4b87e7e0bf463eb8e6956e646f1e277e901512310def2c24bf0e11bd3c28e9a/large-v1.pt) |
| large-v2 | 2.9 GB | [Download Link](https://openaipublic.azureedge.net/main/whisper/models/81f7c96c852ee8fc832187b0132e569d6c3065a3252ed18e56effd0b6a73e524/large-v2.pt) |
| large-v3 | 3 GB | [Download Link](https://openaipublic.azureedge.net/main/whisper/models/e5b1a55b89c1367dacf97e3e19bfd829a01529dbfdeefa8caeb59b3f1b81dadb/large-v3.pt) |

Obs: Se ao invés de um arquivo `.pt` você baixar um arquivo `.zip`, basta renomear o arquivo `.zip` para `.pt`.

### Estrutura de Arquivos Esperada

Após copiar os modelos para o diretório `models`, você deverá ter os seguintes arquivos:

```
models
├── tiny.pt
├── tiny.en.pt
├── base.pt
├── base.en.pt
├── small.pt
├── small.en.pt
├── medium.pt
├── medium.en.pt
├── large-v1.pt
├── large-v2.pt
└── large-v3.pt
```

## Modelo UVR5

O modelo UVR5 é um modelo de reconhecimento de voz específico para o idioma chinês.

### Instruções de Download

1. Baixe o modelo UVR5: [https://github.com/jianchang512/stt/releases/download/0.0/uvr5-model.7z](https://github.com/jianchang512/stt/releases/download/0.0/uvr5-model.7z)
2. Extraia o arquivo baixado.
3. Copie a pasta `uvr5_weights` para o diretório raiz da instalação do PyVideoTrans (onde está localizado o arquivo `pyvideotrans.exe`).

## Bibliotecas cuBLAS e cuDNN para Aceleração CUDA

Se você possui uma placa de vídeo NVIDIA compatível com CUDA e deseja habilitar a aceleração por GPU no PyVideoTrans, precisará baixar as bibliotecas cuBLAS e cuDNN.

### Instruções de Download

1. Verifique a versão do seu CUDA executando o comando `nvcc -V` no terminal.
2. Baixe as bibliotecas correspondentes à sua versão do CUDA:
   - **CUDA 11.x:** [cuBLAS e cuDNN](https://github.com/jianchang512/stt/releases/download/0.0/cuBLAS.and.cuDNN_CUDA11_win_v4.7z)
   - **CUDA 12.x:** [cuBLAS e cuDNN](https://github.com/jianchang512/stt/releases/download/0.0/cuBLAS.and.cuDNN_CUDA12_win_v1.7z)
3. Extraia os arquivos baixados.
4. Copie os arquivos `.dll` para o diretório `C:/Windows/System32` ou para o diretório raiz do PyVideoTrans.

## Resolução de Problemas com cuBLAS e cuDNN

Se você encontrar erros como "cublasxxx.dll não existe" ou o software travar após habilitar a aceleração CUDA, siga estas etapas:

1. Verifique se você baixou as bibliotecas cuBLAS e cuDNN corretas para a sua versão do CUDA.
2. Certifique-se de que os arquivos `.dll` foram copiados para o local correto (`C:/Windows/System32` ou o diretório raiz do PyVideoTrans).
3. Reinicie o computador e tente executar o PyVideoTrans novamente.

Se o problema persistir, consulte a documentação do PyVideoTrans ou busque ajuda nos fóruns de suporte.