import requests
import re
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


def getlist():
  result=[]
  for i in range(1,1536):
    # print(i)
    # continue
    url=f'https://manhua.idmzj.com/api/v1/comic2/filter?channel=pc&app_name=comic&version=1.0.0&timestamp=1695350855804&uid=17383259&status=0&cate=0&zone=0&firstLetter&theme=0&sortType=1&page={i}&size=30'
    res=requests.get(url)
    if res.status_code!=200:
      print(f'{url=}')
      exit()
    print(res.status_code)
    j=res.json()
    for it in j['data']['comicList']:
      result.append(it['comic_py'])

  with open('./mh.txt','w') as f:
    f.write("\n".join(result))

def isno(html):
  return re.search(r'<div class=\Wcartoon_online_border\W>\s*?<img src=\W/_nuxt/4004.c3e0d2a7.gif\W',html,re.I) is not None

# 第一个号判断是否无法阅读
def oneis(by):
  global result,error

  url=f"https://manhua.idmzj.com/api/v1/comic2/comic/detail?channel=pc&app_name=comic&version=1.0.0&timestamp=1695350856666&uid=17383259&comic_py={by}&page=1&size=50"

  headers = {
      'authority': 'manhua.idmzj.com',
      'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
      'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7,zh-HK;q=0.6,ja;q=0.5',
      'cache-control': 'no-cache',
      'cookie': '_ga=GA1.1.848007520.1704372727; Hm_lvt_64c730018cadfc05d349cd34e80fa7ba=1704372727; my=17383259%7C%25E9%25AA%2591%25E5%25A3%25AB%25E7%258E%258Bsa%7C1402259419%40qq.com%7Ccbd95266151e7f7e91fe5ad285eecea6%7Cd41c22db1e378307ae849ae2c98e855a; love=fde1afd5f236745bc272f06e489dea49; tpNavClass=0; Hm_lpvt_64c730018cadfc05d349cd34e80fa7ba=1704373957; _ga_JEZCSW6TY5=GS1.1.1704372726.1.1.1704373956.0.0.0',
      'dnt': '1',
      'pragma': 'no-cache',
      'referer': 'https://manhua.idmzj.com/tags/category_search/0-0-0-2304-0-0-0-1.shtml',
      'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
      'sec-ch-ua-mobile': '?0',
      'sec-ch-ua-platform': '"Windows"',
      'sec-fetch-dest': 'document',
      'sec-fetch-mode': 'navigate',
      'sec-fetch-site': 'same-origin',
      'sec-fetch-user': '?1',
      'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  }

  res = requests.get(url, headers=headers, verify=False)
  if res.status_code != 200:
    print(f'{url=}')
    exit()

  j=res.json()

  if j and j['data']['comicInfo'] and j['data']['comicInfo']['chapterList'] and len(j['data']['comicInfo']['chapterList'])>0:
    #可读
    print(f'{by} 可读')
  elif j and j['data']['comicInfo']:
    print(f'{by} 不可读')
    with open('./one.txt','a') as f:
      f.write(f"{j['data']['comicInfo']['title']} -> {j['data']['comicInfo']['comicPy']}\n")
  else:
    #不可读
    # error.append(f"{by} 出错")
    print(f'{by} 出错')
    with open('./error.txt','a') as f:
      f.write(f"{by} 出错\n")


def twois(by):
  global result,error

  url=f"https://manhua.idmzj.com/api/v1/comic2/comic/detail?channel=pc&app_name=comic&version=1.0.0&timestamp=1695350855804&uid=34761237&comic_py={by}&page=1&size=50"

  headers = {
      'authority': 'manhua.idmzj.com',
      'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
      'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7,zh-HK;q=0.6,ja;q=0.5',
      'cache-control': 'no-cache',
      'cookie': 'Hm_lvt_64c730018cadfc05d349cd34e80fa7ba=1704382608; _ga=GA1.1.376786074.1704382608; my=34761237%7C%25E6%259C%259B%25E6%2598%259F%25E8%25AE%25B8%25E6%2584%25BF%7Cwww.1418071894%40foxmail.com%7C8700e96a5d342618454fe71c1bab71e9%7C88228748ad1413a54612b5f834ccc15f; love=e0dbede3c1edd41adb3ce6c8cf2abce4; tpNavClass=0; Hm_lpvt_64c730018cadfc05d349cd34e80fa7ba=1704382673; _ga_JEZCSW6TY5=GS1.1.1704382607.1.1.1704382673.0.0.0',
      'dnt': '1',
      'pragma': 'no-cache',
      'referer': 'https://manhua.idmzj.com/tags/category_search/0-0-0-2304-0-0-0-1.shtml',
      'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
      'sec-ch-ua-mobile': '?0',
      'sec-ch-ua-platform': '"Windows"',
      'sec-fetch-dest': 'document',
      'sec-fetch-mode': 'navigate',
      'sec-fetch-site': 'same-origin',
      'sec-fetch-user': '?1',
      'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  }

  res = requests.get(url, headers=headers, verify=False)
  if res.status_code != 200:
    print(f'{url=}')
    exit()

  j=res.json()

  if j and j['data']['comicInfo'] and j['data']['comicInfo']['chapterList'] and len(j['data']['comicInfo']['chapterList'])>0:
    #可读
    print(f'{by} 可读')
  elif j and j['data']['comicInfo']:
    print(f'{by} 不可读')
    with open('./two.txt','a') as f:
      f.write(f"{j['data']['comicInfo']['title']} -> {j['data']['comicInfo']['comicPy']}\n")
  else:
    #不可读
    # error.append(f"{by} 出错")
    print(f'{by} 出错')
    with open('./error.txt','a') as f:
      f.write(f"{by} 出错\n")

def panduan1():
    with open("./mh.txt",'r') as f:
      for it in f.readlines():
        try:
            oneis(it.strip())
        except:
            with open('./error.txt', 'a') as f:
                f.write(f"{it} 出错\n")




def panduan2():
    with open("./mh.txt",'r') as f:
      for it in f.readlines():
        try:
            twois(it.strip())
        except:
            with open('./error.txt', 'a') as f:
                f.write(f"{it} 出错\n")


twos=[]
with open("./two.txt",'r') as f:
      for it in f.readlines():
          cmp=it.split(' -> ')[-1].strip()
          if cmp:
            twos.append(it.split(' -> ')[-1].strip())
print(twos)

with open("./one.txt",'r') as f:
      for it in f.readlines():
          cmp=it.split(' -> ')[-1].strip()
          if  cmp and cmp not in twos:
              with open('./onenottwois.txt','a') as f:
                  f.write(f"{it}")