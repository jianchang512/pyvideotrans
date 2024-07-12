[English](./language.md#adding-language-packs)

# 添加语言包

1. 首先在控制台执行下面代码，查看系统当前语言代码

```
    import locale
    locale.getdefaultlocale()[0]
```
将输出内容的前2个字符小写，拼接上`.json`作为文件名创建json文件，比如输出的是`en_US`,就创建 `en.json` 到 videotrans/language 目录下，这个`en.json`就是语言文件。


> 
> 在软件启动时，会以该方式locale.getdefaultlocale()[0]的前2个字符小写，然后拼接`.json`，组成文件名，到 videotrans/language目录下搜寻,如果存在则使用，不存在则显示英文界面。
> 如果在 `videotrans/set.ini` 文件中  `lang=` 设置了值，则以该值为默认语言代码，否则以 `locale.getdefaultlocale()` 结果为准。
>  


已存在`en.json` `zh.json` 2种语言文件，可直接复制后修改名称，在此基础上制作新的语言文件

每个语言文件都是一个json对象，最外层有4个字段，分别是

```
{
"translate_language":{},
"ui_lang":{},
"toolbox_lang":{}, 
"language_code_list":{}
}
```

其中 `translate_language` 是用于进度显示、错误提示、各种交互状态的文本，`ui_lang` 软件界面各个部件的显示名称，`toolbox_lang` 是视频工具箱界面各个部件的显示名称, `language_code_list` 是支持的语言显示名称

## translate_language 修改

```
"translate_language": {
    "qianyiwenjian": "The video path or name contains non ASCII spaces. To avoid errors, it has been migrated to ",
    "mansuchucuo": "Video automatic slow error, please try to cancel the 'Video auto down' option",
}
```

如上，translate_language 是 `字段名:字段值` 组成的json对象，字段名不要动，字段值改为相应语言的文本即可。


## ui_lang 修改

"ui_lang": {
    "SP-video Translate Dubbing": "SP-video Translate Dubbing",
    "Multiple MP4 videos can be selected and automatically queued for processing": "Multiple MP4 videos can be selected and automatically queued for processing",
    "Select video..": "Select video..",
}
同 `translate_language` 的修改一样，字段名不要动，将字段值改为相应语言的文本即可。

## toolbox_lang 修改

"toolbox_lang": {
    "No voice video":"无声视频",
    "Open dir":"打开目录",
    "Audio Wav":"音频文件",
}
同 `translate_language` 的修改一样，字段名不要动，将字段值改为相应语言的文本即可。

## language_code_list 的修改

```
"language_code_list": {
    "zh-cn":"Simplified Chinese",
    "zh-tw":"Traditional Chinese",
    "en":"English",
    "fr":"French",
    "de":"German",
    "ja":"Japanese",
    "ko":"Korean",
    "ru":"Russian",
    "es":"Spanish",
    "th":"Thai",
    "it":"Italian",
    "pt":"Portuguese",
    "vi":"Vietnamese",
    "ar":"Arabic",
    "tr":"Turkish",
    "hi":"Hindi"
  }
```

和其他一样，该内容字段名不要动，字段值改为要显示的名称

**制作完成后，确认符合正确的 json 格式，然后放到 videotrans/language 目录下，重启软件就会自动应用该语言，如何你制作的语言包和默认语言不同，可通过设置 `set.ini`中 lang=语言代码和强制使用，比如 `lang=zh`将强制显示 zh.json 内容**



----


----



# Adding Language Packs



1. First, execute the following code in the console to check the system's current language code

```
    import locale
    locale.getdefaultlocale()[0]
```
Lowercase the first 2 characters of the output content and append `.json` to create a json file as the filename. For example, if the output is `en_US`, create `en.json` in the videotrans/language directory, where `en.json` is the language file.


> 
> When the software starts, the system will take the first 2 characters lowercase from locale.getdefaultlocale()[0] and append `.json` to form the filename, and then look for it under the videotrans/language directory. If it exists, it will be used; otherwise, the English interface will be displayed.
> If the `lang=` in the `videotrans/set.ini` file has a value set, then this value will be taken as the default language code, otherwise the result of `locale.getdefaultlocale()` will be used.
> 


There are already `en.json` and `zh.json` 2 language files. You can copy and modify the name directly to create new language files.

Each language file is a json object. The outermost layer has 4 fields, which are

```
{
"translate_language":{},
"ui_lang":{},
"toolbox_lang":{}, 
"language_code_list":{}
}
```

Here `translate_language` is used for progress display, error prompts, various interaction states of text, `ui_lang` software interface display name of each component, `toolbox_lang` video toolbox interface display name of each component, `language_code_list` is the supported language display name

## Modification of translate_language 

```
"translate_language": {
    "qianyiwenjian": "The video path or name contains non ASCII spaces. To avoid errors, it has been migrated to ",
    "mansuchucuo": "Video automatic slow error, please try to cancel the 'Video auto down' option",
}
```

As mentioned above, translate_language is a json object composed of `field name: field value`. Do not move the field name and change the field value to the corresponding language text.


## Modification of ui_lang 

"ui_lang": {
    "SP-video Translate Dubbing": "SP-video Translate Dubbing",
    "Multiple MP4 videos can be selected and automatically queued for processing": "Multiple MP4 videos can be selected and automatically queued for processing",
    "Select video..": "Select video..",
}
The same as the modification of `translate_language`, do not move the field name and change the field value to the corresponding language text.

## Modification of toolbox_lang 

"toolbox_lang": {
    "No voice video":"Silent video",
    "Open dir":"Open directory",
    "Audio Wav":"Audio file",
}
The same as the modification of `translate_language`, do not move the field name, and change the field value to the relevant language text.

## Modification of language_code_list 

```
"language_code_list": {
    "zh-cn":"Simplified Chinese",
    "zh-tw":"Traditional Chinese",
    "en":"English",
    "fr":"French",
    "de":"German",
    "ja":"Japanese",
    "ko":"Korean",
    "ru":"Russian",
    "es":"Spanish",
    "th":"Thai",
    "it":"Italian",
    "pt":"Portuguese",
    "vi":"Vietnamese",
    "ar":"Arabic",
    "tr":"Turkish",
    "hi":"Hindi"
  }
```

Like the others, do not modify the field name of this content, change the field value to the display name

**After the production is completed, make sure it meets the correct json format, put it into the videotrans/language directory, and the software will automatically apply the language when restarted. If the language pack you made is different from the default language, you can set `set.ini` in lang= language code and use it forcibly, such as `lang=zh` will forcibly display the content of zh.json**