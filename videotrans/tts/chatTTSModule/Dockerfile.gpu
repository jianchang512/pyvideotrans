FROM pytorch/torchserve:0.11.0-gpu as builder

WORKDIR /app

COPY . ./

RUN pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple