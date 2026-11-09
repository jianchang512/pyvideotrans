# WorldRouter 字幕翻译

WorldRouter 渠道通过 OpenAI 兼容接口提供文本与 SRT 字幕翻译。
此渠道仅用于翻译；视频流程中的语音识别和配音仍在各自的渠道中配置。

## 配置

1. 在 [WorldRouter](https://router.worldclaw.ai) 创建 API Key。
2. 打开 pyVideoTrans 顶部的「翻译设置 → WorldRouter」。
3. 填入 API Key，选择模型，点击「测试」。测试会调用真实接口并消耗账户额度。
4. 测试成功后点击「保存」，在主界面或「字幕翻译」工具中选择 **WorldRouter**。

接口地址固定为 `https://inference-api.worldrouter.ai/v1`，请求发送至
`POST /chat/completions`。使用 WorldRouter 的 API Key，不需要单独填写各模型供应商的密钥。

沿用项目其他供应商的「预设模型 + 手动编辑列表」方式，不在打开窗口时自动访问模型接口。
预设覆盖 2026-11-09 公开模型目录中的 46 个文本模型，包括 GPT、Claude、DeepSeek、GLM、
Kimi、MiniMax 和 ERNIE，默认仍为 `deepseek-v4-flash`。
可在下方模型列表中添加其他模型 ID，以英文逗号分隔，之后在上方下拉框中选择。
实际可用模型以 [WorldRouter 模型目录](https://router.worldclaw.ai/models) 和账户权限为准。
列入预设表示已核对模型目录，并不表示所有模型均完成实际翻译测试。

最大输出 token 默认为 `16384`。遇到输出截断时，提高此值或在高级设置中减少每批字幕行数；
模型自身的输出上限仍然适用。完整 SRT 模式会检查字幕块数量和时间戳，逐行文本模式会检查行数，
不一致时提示错误，避免把错位字幕继续用于配音。

提示词文件：

- `videotrans/prompts/srt/worldrouter.txt`：发送完整字幕模式。
- `videotrans/prompts/text/worldrouter.txt`：逐行文本模式。

修改时保留 `{lang}`、`{batch_input}` 等占位符。

## 本地验证

在已按项目 README 安装依赖的源码环境中，运行：

```bash
QT_QPA_PLATFORM=offscreen uv run --group dev pytest tests/test_worldrouter.py tests/test_worldrouter_ui.py -q
```

自动测试使用模拟 HTTP 响应与真实 OpenAI SDK、Qt 控件，不需要 API Key，不产生 API 费用。
它验证渠道注册、配置保存、请求路径与认证、文本/SRT 翻译、时间戳检查、错误处理和配置窗口。

真实接口与人工检查：

1. 运行 `uv run sp.py`，打开「翻译设置 → WorldRouter」并点击「测试」。
2. 用下面的内容保存为 UTF-8 的 `worldrouter-test.srt`，在「字幕翻译」工具中选择
   WorldRouter，源语言中文，目标语言英语。
3. 分别开启、关闭高级设置中的「发送完整字幕」，确认两种模式都返回两条英文字幕，
   且时间戳保持不变。
4. 切换到另一个账户可用模型后重复测试，关闭并重新打开设置窗口，确认模型选择保留。

```srt
1
00:00:01,000 --> 00:00:03,000
你好，欢迎使用视频翻译。

2
00:00:04,000 --> 00:00:06,000
这是一段字幕翻译测试。
```

接口文档：[WorldRouter API reference](https://router.worldclaw.ai/docs/api)。

## English quick start

Open **Translation settings → WorldRouter**, enter a WorldRouter API key, choose a model,
and click **Test**, then **Save**. Select **WorldRouter** in the translation channel list.
Both line-by-line text and full-SRT modes are supported. The endpoint is
`https://inference-api.worldrouter.ai/v1/chat/completions`.
The Test button makes a billable API request; the automated tests above use mock responses.
Speech recognition and text-to-speech use their separately selected providers.
