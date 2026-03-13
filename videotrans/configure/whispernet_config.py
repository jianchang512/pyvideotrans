"""
Whisper.NET 配置管理
"""

from pathlib import Path
from typing import Optional

from videotrans.configure.config import ROOT_DIR


class WhisperNetConfig:
    """Whisper.NET 配置类"""
    
    def __init__(self):
        self.deps_dir = Path(ROOT_DIR) / "deps"
        self.native_dir = self.deps_dir / "native"
        self.models_dir = Path(ROOT_DIR) / "models"
        
        # 默认设置
        self.default_use_gpu = True
        self.default_gpu_device = 0
        self.default_no_context = True
        self.default_no_speech_threshold = -0.8
        self.default_logprob_threshold = -1.0
        
    def get_runtime_files(self):
        """获取Whisper.NET运行时文件"""
        runtime_files = {}
        
        # 检查主要DLL文件
        whisper_dll = self.deps_dir / "Whisper.net.dll"
        runtime_files['whisper_dll'] = whisper_dll if whisper_dll.exists() else None
        
        # 检查native DLL文件
        if self.native_dir.exists():
            native_dlls = []
            for dll_file in self.native_dir.glob("*.dll"):
                native_dlls.append(dll_file)
            runtime_files['native_dlls'] = native_dlls
        else:
            runtime_files['native_dlls'] = []
            
        return runtime_files
        
    def validate_setup(self) -> tuple[bool, str]:
        """验证Whisper.NET设置是否完整"""
        errors = []
        
        # 检查DLL文件
        whisper_dll = self.deps_dir / "Whisper.net.dll"
        if not whisper_dll.exists():
            errors.append(f"Whisper.net.dll not found: {whisper_dll}")
            
        # 检查native目录
        if not self.native_dir.exists():
            errors.append(f"Native directory not found: {self.native_dir}")
        else:
            native_dlls = list(self.native_dir.glob("*.dll"))
            if not native_dlls:
                errors.append(f"No native DLLs found in: {self.native_dir}")
        
        if errors:
            return False, "; ".join(errors)
        
        return True, "Setup is valid"
        
    def get_available_models(self) -> list[str]:
        """获取可用的模型列表"""
        models = []
        if self.models_dir.exists():
            # 查找ggml格式的模型文件
            for model_file in self.models_dir.glob("*.bin"):
                if "ggml" in model_file.name.lower():
                    models.append(model_file.name)
        
        return sorted(models)
        
    def get_model_path(self, model_name: str) -> Optional[Path]:
        """获取模型文件的完整路径"""
        # 首先检查是否是绝对路径
        if Path(model_name).is_absolute() and Path(model_name).exists():
            return Path(model_name)
            
        # 然后检查相对路径
        model_path = self.models_dir / model_name
        if model_path.exists():
            return model_path
            
        # 检查是否只提供文件名，在models目录下查找
        for model_file in self.models_dir.rglob(model_name):
            if model_file.is_file():
                return model_file
                
        return None


# 创建全局配置实例
whispernet_config = WhisperNetConfig()