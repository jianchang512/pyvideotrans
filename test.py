import pathlib,json,os,sys




def find_unused_keys(directory_path, large_dict):
    """
    递归遍历指定目录下的所有 .py 文件，检查字典中的 key 是否未被 tr('key') 或 tr("key") 引用。
    
    :param directory_path: 目标目录路径，例如 'F:/python/pyvideo/videotrans'
    :param large_dict: 待检查的大字典
    :return: 所有未被引用的 key 列表
    """
    dir_path = pathlib.Path(directory_path)
    
    usejson={}
    
    # 1. 递归获取所有 .py 文件
    py_files = list(dir_path.rglob('*.py'))
    
    # 提前将所有文件内容读取到内存中，避免在嵌套循环中重复读取磁盘，提升运行效率
    file_contents = []
    for py_file in py_files:
        try:
            # 使用 utf-8 读取，并忽略可能存在的编码错误
            content = py_file.read_text(encoding='utf-8', errors='ignore')
            file_contents.append(content)
        except Exception as e:
            print(f"读取文件失败 {py_file}: {e}")

    unused_keys = []

    # 2. 第一层循环：遍历字典的所有 key
    for key,value in large_dict.items():
        # 构造需要匹配的字符串格式
        target_single = f"tr('{key}')"
        target_double = f'tr("{key}")'
        
        found = False
        
        # 3. 第二层循环：遍历所有读取到的文件内容
        for content in file_contents:
            if target_single in content or target_double in content:
                found = True
                usejson[key]=value
                break  # 找到匹配项，直接跳出第二层循环，继续处理下一个 key
        
        # 4. 如果所有文件都遍历完仍未找到该 key，则输出
        if not found:
            print(f"未被引用的 Key: {key}")
            unused_keys.append(key)
    with open("en.json","w",encoding="utf-8")  as f:
        f.write(json.dumps(usejson,ensure_ascii=False,indent=4))
    print(f'file_contents={len(file_contents)}')
    return unused_keys

# ================= 示例用法 =================
if __name__ == "__main__":
    # 替换为您的实际目录路径
    target_directory = r"F:/python/pyvideo/videotrans"
    import json,sys
    # 模拟您的大字典
    my_dict = json.load(open("./videotrans/language/en.json",'r',encoding='utf=8'))
    
    print("开始检测...")
    unused = find_unused_keys(target_directory, my_dict)
    print(f"\n检测完成，共找到 {len(unused)} 个未使用的 Key。")