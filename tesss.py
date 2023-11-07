# -*- coding:utf-8 -*-
# 享受雷霆感受雨露
# author xyy,time:2023/11/6
from configure.tools import baidutrans
if __name__ == '__main__':

    info = baidutrans(text="今天是个好日子呀",src="zh",dest="en")
    # info = baidutrans(text="开心",src="zh",dest="en")
    # info = get_baiducookie_token()

    # info = tes2("今天是个好日子呀")
    # info = get_baidu()
    print(info)