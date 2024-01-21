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

每个语言文件都是一个json对象，最外层有3个字段，分别是

```
{
"translate_language":{},
"ui_lang":{},
"language_code_list":{}
}
```

其中 `translate_language` 是用于进度显示、错误提示、各种交互状态的文本，`ui_lang` 软件界面各个部件的显示名称，`language_code_list` 是支持的语言代码

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

## language_code_list 的修改

```
"language_code_list": {
    "Simplified_Chinese": [
      "zh-cn",
      "chi",
      "zh",
      "ZH",
      "zh"
    ],
    "Traditional_Chinese": [
      "zh-tw",
      "chi",
      "cht",
      "ZH",
      "zh-TW"
    ]
}
```

和其他2个不同，该内容只需要将字段名改为相应语言文本，字段值不要动，即 [] 数组内的元素不要修改，比如上方内容，可以修改 Simplified_Chinese 和  Traditional_Chinese 为其他语言文本，但 [] 内的保持原样不要动

## 制作完成后，确认符合正确的 json 格式，然后放到 videotrans/language 目录下，重启软件就会自动应用该语言，如何你制作的语言包和默认语言不同，可通过设置 `set.ini`中 lang=语言代码和强制使用，比如 `lang=zh`将强制显示 zh.json 内容