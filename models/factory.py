import os
import json
import importlib
from typing import Optional

class ModelFactory:
    """模型工厂类，根据配置创建模型实例"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化模型工厂
        
        Args:
            config_path: 配置文件路径，默认为 config/models_config.json
        """
        if config_path is None:
            config_path = os.path.join('config', 'models_config.json')
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self) -> dict:
        """加载配置文件"""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        return config
    
    def _resolve_env_vars(self, params: dict) -> dict:
        """
        解析环境变量
        
        Args:
            params: 参数字典，可能包含 ${VAR_NAME} 格式的环境变量
            
        Returns:
            解析后的参数字典
        """
        resolved = {}
        for key, value in params.items():
            if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                # 提取环境变量名
                env_var = value[2:-1]
                resolved[key] = os.environ.get(env_var, value)
            else:
                resolved[key] = value
        return resolved
    
    def _create_model_instance(self, model_config: dict):
        """
        根据配置创建模型实例
        
        Args:
            model_config: 模型配置字典
            
        Returns:
            模型实例
        """
        class_name = model_config['class']
        module_path = model_config['module']
        params = self._resolve_env_vars(model_config['params'])
        
        # 动态导入模块
        module = importlib.import_module(module_path)
        model_class = getattr(module, class_name)
        
        # 创建实例
        return model_class(**params)
    
    def create_stt(self, model_name: str):
        """
        创建语音转文字模型
        
        Args:
            model_name: 模型名称（如 'azure'）
            
        Returns:
            BaseSTT实例
        """
        if model_name not in self.config['stt_models']:
            raise ValueError(f"不支持的STT模型: {model_name}. 可用模型: {list(self.config['stt_models'].keys())}")
        
        model_config = self.config['stt_models'][model_name]
        return self._create_model_instance(model_config)
    
    def create_tts(self, model_name: str):
        """
        创建文字转语音模型
        
        Args:
            model_name: 模型名称（如 'azure'）
            
        Returns:
            BaseTTS实例
        """
        if model_name not in self.config['tts_models']:
            raise ValueError(f"不支持的TTS模型: {model_name}. 可用模型: {list(self.config['tts_models'].keys())}")
        
        model_config = self.config['tts_models'][model_name]
        return self._create_model_instance(model_config)
    
    def create_translator(self, model_name: str):
        """
        创建翻译模型
        
        Args:
            model_name: 模型名称（如 'zhipu'）
            
        Returns:
            BaseTranslator实例
        """
        if model_name not in self.config['translator_models']:
            raise ValueError(f"不支持的翻译模型: {model_name}. 可用模型: {list(self.config['translator_models'].keys())}")
        
        model_config = self.config['translator_models'][model_name]
        return self._create_model_instance(model_config)
    
    def get_available_models(self) -> dict:
        """
        获取所有可用的模型名称
        
        Returns:
            包含所有可用模型名称的字典
        """
        return {
            'stt': list(self.config['stt_models'].keys()),
            'tts': list(self.config['tts_models'].keys()),
            'translator': list(self.config['translator_models'].keys())
        }

