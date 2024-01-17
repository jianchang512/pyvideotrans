import re

from videotrans.configure.config import rootdir, defaulelang
import configparser
import os

def parse_init(file,*,default={}):
    settings = default
    if os.path.exists(file):
        # 创建配置解析器
        iniconfig = configparser.ConfigParser()
        # 读取.ini文件
        iniconfig.read(file)
        # return
        # 遍历.ini文件中的每个section
        for section in iniconfig.sections():
            # 遍历每个section中的每个option
            for key, value in iniconfig.items(section):
                value=value.strip()
                if re.match(r'^\d+$',value):
                    settings[key] = int(value)
                elif re.match(r'^true|false$',value):
                    settings[key] = bool(value)
                else:
                    settings[key] = str(value)

    return settings

print(parse_init("./set.ini"))