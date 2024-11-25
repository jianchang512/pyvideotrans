# 本代码复制自 https://github.com/OpenDocCN/python-code-anls/blob/master/docs/hf-tfm/models----clvp----number_normalizer.py.md
# 以下为原文件所附带版权声明
#
# coding=utf-8
# Copyright 2023 The HuggingFace Inc. team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""English Normalizer class for CLVP."""


import re

class EnglishNormalizer:
    def __init__(self):
        # List of (regular expression, replacement) pairs for abbreviations:
        self._abbreviations = [
            # Compile regular expressions for abbreviations and their replacements
            (re.compile("\\b%s\\." % x[0], re.IGNORECASE), x[1])
            for x in [
                ("mrs", "misess"),
                ("mr", "mister"),
                ("dr", "doctor"),
                ("st", "saint"),
                ("co", "company"),
                ("jr", "junior"),
                ("maj", "major"),
                ("gen", "general"),
                ("drs", "doctors"),
                ("rev", "reverend"),
                ("lt", "lieutenant"),
                ("hon", "honorable"),
                ("sgt", "sergeant"),
                ("capt", "captain"),
                ("esq", "esquire"),
                ("ltd", "limited"),
                ("col", "colonel"),
                ("ft", "fort"),
            ]
        ]

        # List of English words for numbers
        self.ones = ["", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
        self.teens = [
            "ten",
            "eleven",
            "twelve",
            "thirteen",
            "fourteen",
            "fifteen",
            "sixteen",
            "seventeen",
            "eighteen",
            "nineteen",
        ]
        self.tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
    def number_to_words(self, num: int) -> str:
        """
        Converts numbers(`int`) to words(`str`).

        Please note that it only supports up to - "'nine hundred ninety-nine quadrillion, nine hundred ninety-nine
        trillion, nine hundred ninety-nine billion, nine hundred ninety-nine million, nine hundred ninety-nine
        thousand, nine hundred ninety-nine'" or `number_to_words(999_999_999_999_999_999)`.
        """
        # 如果输入的数字为0，返回字符串 "zero"
        if num == 0:
            return "zero"
        # 如果输入的数字小于0，返回负数的英文表示，递归调用自身处理绝对值
        elif num < 0:
            return "minus " + self.number_to_words(abs(num))
        # 处理0到9之间的数字，直接返回对应的英文表示
        elif num < 10:
            return self.ones[num]
        # 处理10到19之间的数字，直接返回对应的英文表示
        elif num < 20:
            return self.teens[num - 10]
        # 处理20到99之间的数字，分解为十位和个位，递归调用自身处理个位
        elif num < 100:
            return self.tens[num // 10] + ("-" + self.number_to_words(num % 10) if num % 10 != 0 else "")
        # 处理100到999之间的数字，分解为百位和剩余部分，递归调用自身处理剩余部分
        elif num < 1000:
            return (
                self.ones[num // 100] + " hundred" + (" " + self.number_to_words(num % 100) if num % 100 != 0 else "")
            )
        # 处理1000到999999之间的数字，分解为千位和剩余部分，递归调用自身处理剩余部分
        elif num < 1_000_000:
            return (
                self.number_to_words(num // 1000)
                + " thousand"
                + (", " + self.number_to_words(num % 1000) if num % 1000 != 0 else "")
            )
        # 处理1000000到999999999之间的数字，分解为百万位和剩余部分，递归调用自身处理剩余部分
        elif num < 1_000_000_000:
            return (
                self.number_to_words(num // 1_000_000)
                + " million"
                + (", " + self.number_to_words(num % 1_000_000) if num % 1_000_000 != 0 else "")
            )
        # 处理1000000000到999999999999之间的数字，分解为十亿位和剩余部分，递归调用自身处理剩余部分
        elif num < 1_000_000_000_000:
            return (
                self.number_to_words(num // 1_000_000_000)
                + " billion"
                + (", " + self.number_to_words(num % 1_000_000_000) if num % 1_000_000_000 != 0 else "")
            )
        # 处理1000000000000到999999999999999之间的数字，分解为万亿位和剩余部分，递归调用自身处理剩余部分
        elif num < 1_000_000_000_000_000:
            return (
                self.number_to_words(num // 1_000_000_000_000)
                + " trillion"
                + (", " + self.number_to_words(num % 1_000_000_000_000) if num % 1_000_000_000_000 != 0 else "")
            )
        # 处理1000000000000000到999999999999999999之间的数字，分解为千万亿位和剩余部分，递归调用自身处理剩余部分
        elif num < 1_000_000_000_000_000_000:
            return (
                self.number_to_words(num // 1_000_000_000_000_000)
                + " quadrillion"
                + (
                    ", " + self.number_to_words(num % 1_000_000_000_000_000)
                    if num % 1_000_000_000_000_000 != 0
                    else ""
                )
            )
        # 处理超出范围的数字，返回字符串 "number out of range"
        else:
            return "number out of range"

    def convert_to_ascii(self, text: str) -> str:
        """
        Converts unicode to ascii
        """
        # 将Unicode文本转换为ASCII编码，忽略非ASCII字符
        return text.encode("ascii", "ignore").decode("utf-8")
    def _expand_dollars(self, m: str) -> str:
        """
        This method is used to expand numerical dollar values into spoken words.
        """
        # 匹配到的数字字符串，即货币值
        match = m.group(1)
        # 将货币值按小数点分割为整数部分和小数部分
        parts = match.split(".")
        if len(parts) > 2:
            return match + " dollars"  # 如果小数点超过一个，返回原始字符串加上 " dollars" 表示异常格式

        # 解析整数部分和小数部分
        dollars = int(parts[0]) if parts[0] else 0
        cents = int(parts[1]) if len(parts) > 1 and parts[1] else 0
        # 根据货币值的整数部分和小数部分，构造成对应的英文表达形式
        if dollars and cents:
            dollar_unit = "dollar" if dollars == 1 else "dollars"
            cent_unit = "cent" if cents == 1 else "cents"
            return "%s %s, %s %s" % (dollars, dollar_unit, cents, cent_unit)
        elif dollars:
            dollar_unit = "dollar" if dollars == 1 else "dollars"
            return "%s %s" % (dollars, dollar_unit)
        elif cents:
            cent_unit = "cent" if cents == 1 else "cents"
            return "%s %s" % (cents, cent_unit)
        else:
            return "zero dollars"

    def _remove_commas(self, m: str) -> str:
        """
        This method is used to remove commas from sentences.
        """
        # 去除输入字符串中的逗号
        return m.group(1).replace(",", "")

    def _expand_decimal_point(self, m: str) -> str:
        """
        This method is used to expand '.' into spoken word ' point '.
        """
        # 将输入字符串中的点号 '.' 替换为单词 " point "
        return m.group(1).replace(".", " point ")

    def _expand_ordinal(self, num: str) -> str:
        """
        This method is used to expand ordinals such as '1st', '2nd' into spoken words.
        """
        # 定义英文序数词的后缀映射表
        ordinal_suffixes = {1: "st", 2: "nd", 3: "rd"}

        # 提取序数词的数字部分并转换为整数
        num = int(num.group(0)[:-2])
        # 根据序数的不同情况选择正确的后缀
        if 10 <= num % 100 and num % 100 <= 20:
            suffix = "th"
        else:
            suffix = ordinal_suffixes.get(num % 10, "th")
        # 将整数转换为对应的英文序数词形式并添加后缀
        return self.number_to_words(num) + suffix

    def _expand_number(self, m: str) -> str:
        """
        This method acts as a preprocessing step for numbers between 1000 and 3000 (same as the original repository,
        link :
        https://github.com/neonbjb/tortoise-tts/blob/4003544b6ff4b68c09856e04d3eff9da26d023c2/tortoise/utils/tokenizer.py#L86)
        """
        # 提取匹配到的数字字符串并转换为整数
        num = int(m.group(0))

        # 如果数字在 1000 到 3000 之间，按特定规则进行英文数字的扩展
        if num > 1000 and num < 3000:
            if num == 2000:
                return "two thousand"
            elif num > 2000 and num < 2010:
                return "two thousand " + self.number_to_words(num % 100)
            elif num % 100 == 0:
                return self.number_to_words(num // 100) + " hundred"
            else:
                return self.number_to_words(num)
        else:
            return self.number_to_words(num)


    # 此方法用于规范化文本中的数字，如将数字转换为单词，移除逗号等操作。
    def normalize_numbers(self, text: str) -> str:
        # 使用正则表达式替换匹配的数字和逗号，调用 self._remove_commas 方法
        text = re.sub(re.compile(r"([0-9][0-9\,]+[0-9])"), self._remove_commas, text)
        # 替换匹配的英镑金额为其单词表示形式
        text = re.sub(re.compile(r"£([0-9\,]*[0-9]+)"), r"\1 pounds", text)
        # 替换匹配的美元金额为其完整的金额表达形式，调用 self._expand_dollars 方法
        text = re.sub(re.compile(r"\$([0-9\.\,]*[0-9]+)"), self._expand_dollars, text)
        # 替换匹配的小数形式为其完整的数值表达形式，调用 self._expand_decimal_point 方法
        text = re.sub(re.compile(r"([0-9]+\.[0-9]+)"), self._expand_decimal_point, text)
        # 替换匹配的序数词（如1st、2nd）为其完整的序数词形式，调用 self._expand_ordinal 方法
        text = re.sub(re.compile(r"[0-9]+(st|nd|rd|th)"), self._expand_ordinal, text)
        # 替换匹配的数字为其完整的数值表达形式，调用 self._expand_number 方法
        text = re.sub(re.compile(r"[0-9]+"), self._expand_number, text)
        # 返回规范化后的文本
        return text

    # 扩展缩写词
    def expand_abbreviations(self, text: str) -> str:
        # 遍历缩写词及其对应的替换规则，使用正则表达式进行替换
        for regex, replacement in self._abbreviations:
            text = re.sub(regex, replacement, text)
        # 返回扩展后的文本
        return text

    # 去除多余的空白字符
    def collapse_whitespace(self, text: str) -> str:
        # 使用正则表达式将多个连续的空白字符替换为一个空格
        return re.sub(re.compile(r"\s+"), " ", text)

    # 对象可调用方法，将文本转换为 ASCII 码，将数字转换为完整形式，并扩展缩写词
    def __call__(self, text):
        # 将文本转换为 ASCII 码表示形式
        text = self.convert_to_ascii(text)
        # 将文本转换为小写形式
        text = text.lower()
        # 规范化文本中的数字
        text = self.normalize_numbers(text)
        # 扩展文本中的缩写词
        text = self.expand_abbreviations(text)
        # 去除文本中的多余空白字符
        text = self.collapse_whitespace(text)
        # 移除文本中的双引号
        text = text.replace('"', "")

        # 返回处理后的文本
        return text