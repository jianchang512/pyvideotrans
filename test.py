import re

file="C:/Users/c1/Videos/1.srt"


content=[]
try:
    with open(file,'r',encoding='utf-8') as f:
        content=f.read().strip().splitlines()
except:
    with open(file,'r',encoding='gbk') as f:
        content=f.read().strip().splitlines()
content=[i for i in content if i.strip()]

result=[]
# 最大索引
maxlen=len(content)-1
# 时间格式
timepat = r'\d+:\d+:\d+\,?\d*?\s*?-->\s*?\d+:\d+:\d+\,?\d*'
i=0
while i<maxlen-1:
    tmp=content[i].strip()
    #第一行匹配数字行
    if re.match(r'^\d+$',tmp):
        nextmp=content[i+1].strip()
        #再判断第二行匹配时间戳，则视为有效字幕
        if re.match(timepat,nextmp):
            res={"line":tmp,"text":"","time":nextmp}
            j=i+2
            #大于最大索引，超出退出
            if j>maxlen:
                break
            t0=content[j].strip()
            #如果下一行是空行，即没有文字内容，则跳过
            if re.match(r'^\d+$',t0):
                i=j
                continue
            res['text']+=t0
            #已是最后一行，直接退出
            if j==maxlen:
                result.append(res)
                break

            #继续判断下一行是否还是内容行
            while 1:
                #再继续判断下一行是否是内容行
                t1=content[j+1]
                if j<maxlen-1:
                    t2=content[j+2]
                    # 后边2行都符合行数规则，则第一行视为内容
                    if re.match(r'^\d+$',t1) and  re.match(r'^\d+$',t2):
                        res['text']+=t1
                        j+=1
                        i=j+1+1
                        continue
                    elif not re.match(r'^\d+$',t1):
                        res['text']+=t1
                        j+=1
                        i=j+1+1
                        continue
                    else:
                        i=j+1
                        break
                elif j>=maxlen-1:
                    if not re.match(r'^\d+$',t1):
                        res['text']+=t1
                    i=maxlen
                    break
            result.append(res)

print(result)
