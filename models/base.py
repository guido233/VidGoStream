from abc import ABC, abstractmethod

class BaseSTT(ABC):
    """语音转文字基类"""
    
    @abstractmethod
    def transcribe(self, audio_file_path, output_dir=None):
        """
        将音频文件转换为文字
        
        Args:
            audio_file_path: 音频文件路径
            output_dir: 输出目录（可选）
            
        Returns:
            tuple: (识别的文本, 检测到的语言)
        """
        pass

class BaseTTS(ABC):
    """文字转语音基类"""
    
    @abstractmethod
    def synthesize_speech(self, text, output_file):
        """
        将文字转换为语音
        
        Args:
            text: 要转换的文字
            output_file: 输出音频文件路径
            
        Returns:
            bool: 是否成功
        """
        pass

class BaseTranslator(ABC):
    """翻译基类"""
    
    @abstractmethod
    def translate_file(self, input_file, output_file, target_lang='zh'):
        """
        翻译文件
        
        Args:
            input_file: 输入文件路径
            output_file: 输出文件路径
            target_lang: 目标语言
            
        Returns:
            bool: 是否成功
        """
        pass

