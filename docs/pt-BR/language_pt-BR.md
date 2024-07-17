## Adicionando Pacotes de Idiomas

Execute o seguinte código no console para verificar o código de idioma atual do sistema:

```python
import locale
locale.getdefaultlocale()[0]
```

Pegue os 2 primeiros caracteres da saída, coloque-os em minúsculas e adicione `.json` para criar o arquivo de idioma. Por exemplo, se a saída for `en_US`, crie `en.json` no diretório `videotrans/language`.

> Quando o software inicia, ele utiliza os 2 primeiros caracteres em minúsculas de `locale.getdefaultlocale()[0]` e adiciona `.json` para formar o nome do arquivo, buscando-o no diretório `videotrans/language`. Se o arquivo existir, ele será usado; caso contrário, a interface em inglês será exibida.
> Se o `lang=` no arquivo `videotrans/set.ini` tiver um valor definido, esse valor será considerado como o código de idioma padrão. Caso contrário, o resultado de `locale.getdefaultlocale()` será utilizado.

Já existem dois arquivos de idioma: `en.json` e `zh.json`. Você pode copiá-los e modificar os nomes para criar novos arquivos de idioma.

Cada arquivo de idioma é um objeto JSON. A camada mais externa possui quatro campos:

```json
{
  "translate_language": {},
  "ui_lang": {},
  "toolbox_lang": {},
  "language_code_list": {}
}
```

- **translate_language:** Usado para exibição de progresso, prompts de erro e vários estados de interação de texto.
- **ui_lang:** Exibe o nome de cada componente da interface do software.
- **toolbox_lang:** Exibe o nome de cada componente da interface da caixa de ferramentas de vídeo.
- **language_code_list:** Nome de exibição dos idiomas suportados.

### Modificação de `translate_language`

```json
"translate_language": {
  "qianyiwenjian": "O caminho ou nome do vídeo contém espaços não ASCII. Para evitar erros, ele foi migrado para ",
  "mansuchucuo": "Erro de lentidão automática do vídeo, por favor, tente cancelar a opção 'Video auto down'"
}
```

Modifique apenas os valores dos campos para o texto do idioma correspondente. Não altere os nomes dos campos.

### Modificação de `ui_lang`

```json
"ui_lang": {
  "SP-video Translate Dubbing": "SP-video Tradução e Dublagem",
  "Multiple MP4 videos can be selected and automatically queued for processing": "Vários vídeos MP4 podem ser selecionados e automaticamente colocados em fila para processamento",
  "Select video..": "Selecionar vídeo.."
}
```

Siga o mesmo procedimento de `translate_language`, modificando apenas os valores dos campos.

### Modificação de `toolbox_lang`

```json
"toolbox_lang": {
  "No voice video": "Vídeo sem áudio",
  "Open dir": "Abrir diretório",
  "Audio Wav": "Arquivo de áudio"
}
```

Novamente, modifique apenas os valores dos campos para o texto relevante.

### Modificação de `language_code_list`

```json
"language_code_list": {
  "zh-cn": "Chinês Simplificado",
  "zh-tw": "Chinês Tradicional",
  "en": "Inglês",
  "fr": "Francês",
  "de": "Alemão",
  "ja": "Japonês",
  "ko": "Coreano",
  "ru": "Russo",
  "es": "Espanhol",
  "th": "Tailandês",
  "it": "Italiano",
  "pt": "Português",
  "vi": "Vietnamita",
  "ar": "Árabe",
  "tr": "Turco",
  "hi": "Hindi"
}
```

Altere apenas os valores dos campos para o nome de exibição correspondente.

**Após concluir, certifique-se de que o arquivo esteja no formato JSON correto. Coloque-o no diretório `videotrans/language` e o software aplicará automaticamente o idioma ao ser reiniciado. Se o pacote de idiomas que você criou for diferente do idioma padrão, você pode forçar o uso definindo `lang=` no `set.ini`, por exemplo, `lang=zh` exibirá o conteúdo de `zh.json`.**

---