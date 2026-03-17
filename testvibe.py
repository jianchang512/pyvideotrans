def api():
    from gradio_client import Client, handle_file
    import os

    # 1. 检查文件是否存在
    audio_file = "300.wav"
    if not os.path.exists(audio_file):
        print(f"❌ 错误: 找不到文件 {audio_file}")
        exit()

    # 2. 初始化客户端
    # 注意：如果你之前使用了 ngrok，请把这里换成 ngrok 的地址，否则阿里云这个链接可能会报 403 错误
    client = Client("https://dsw-gateway-cn-hangzhou.data.aliyun.com/dsw-1620000/proxy/7860/")

    print(f"🚀 正在上传并转录 {audio_file} ...")

    # 3. 发送请求
    try:
        result = client.predict(
            # 核心修改：使用 handle_file 处理本地路径
            audio_input=handle_file(audio_file),

            # 其他参数保持默认或根据需要修改
            audio_path_input=None,
            start_time_input=None,
            end_time_input=None,
            max_new_tokens=32768,  # 长音频务必设大
            temperature=0,
            top_p=1,
            do_sample=False,
            repetition_penalty=1,
            context_info="",       # 如果有热词（如人名）可以填在这里
            api_name="/transcribe_audio"
        )

        print("✅ 转录成功！")
        print("-" * 30)

        # 打印原始返回结果以便观察结构
        print("数据类型:", type(result))
        print("数据长度:", len(result))
        print("-" * 30)
        print("结果 [0] (部分预览):", result[0][:200])
        return clean(result[0])
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        print("提示：如果报错 403/Auth Required，请参考上一步使用 ngrok 获取公网地址。")
        raise


def clean(raw_text):
    import re
    import ast


    # 1. 使用正则表达式找到列表部分（从 '[' 开始，到 ']' 结束）
    match = re.search(r'(\[.*\])', raw_text, re.DOTALL)

    if match:
        list_str = match.group(1)
        try:
            # 2. 使用 ast.literal_eval 将字符串安全地转为 Python 列表
            segments = ast.literal_eval(list_str)

            # 3. 遍历结果
            for seg in segments:
                print(f"[{seg['start']:.2f}s -> {seg['end']:.2f}s] {seg['text']}")

        except Exception as e:
            print("解析列表出错:", e)
    else:
        print("未找到转录数据，可能转录失败或输出为空。")