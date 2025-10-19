import torch,os

# 检查 CUDA 是否可用
print(f"\nCUDA是否可用: {'是 Yes' if torch.cuda.is_available() else '否 No'}")

# 如果 CUDA 可用，再检查 CUDNN
if torch.cuda.is_available():
    print(f"\ncuDNN 是否可用: {'是 Yes' if torch.backends.cudnn.is_available() else '否 No'}")
    print(f"\ncuDNN 版本号: {torch.backends.cudnn.version()}\n\n")
    
os.system('pause')    