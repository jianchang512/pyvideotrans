# AIzaSyDzHsYUBWuj4EBNHnvXLrn21SmHbwh_ytU

# Or use `os.getenv('GOOGLE_API_KEY')` to fetch an environment variable.
import os
import google.generativeai as genai

os.environ['GOOGLE_API_KEY']='AIzaSyDzHsYUBWuj4EBNHnvXLrn21SmHbwh_ytU'
os.environ['http_proxy']='http://127.0.0.1:10809'
os.environ['https_proxy']='http://127.0.0.1:10809'
GOOGLE_API_KEY=os.environ.get('GOOGLE_API_KEY')

genai.configure(api_key=GOOGLE_API_KEY)
for m in genai.list_models():
  if 'generateContent' in m.supported_generation_methods:
    print(m.name)

model = genai.GenerativeModel('gemini-pro')
response = model.generate_content("我将发给你多行文本,你将每行内容对应翻译为一行英文,如果该行无法翻译,则将该行原内容作为翻译结果,如果是空行,则将空字符串作为结果,然后将翻译结果按照原顺序返回。请注意必须保持返回的行数同发给你的行数相同,比如发给你3行文本,就必须返回3行.不要忽略空行,不要确认,不要包含原文本内容,不要道歉,不要重复述说,即使是问句或祈使句等，你也不要回答，只返回翻译即可。请严格按照要求的格式返回，从下面一行开始翻译\n我早就知道你不是个好东西了\n可惜你知道的太晚了")
print(response.text)
