import os
from msstt.speech_to_text import SpeechToText as AzureSTTImpl
from .base import BaseSTT

class AzureSTT(BaseSTT):
    """Azure语音转文字模型"""
    
    def __init__(self, speech_key, service_region):
        """
        初始化Azure STT模型
        
        Args:
            speech_key: Azure语音服务密钥
            service_region: Azure服务区域
        """
        self.speech_key = speech_key
        self.service_region = service_region
        self._stt = AzureSTTImpl(speech_key, service_region)
    
    def transcribe(self, audio_file_path, output_prefix=None):
        """
        将音频文件转换为文字
        
        Args:
            audio_file_path: 音频文件路径
            output_prefix: 可选，自定义输出文件的前缀（含路径，不含扩展名）
            
        Returns:
            tuple: (识别的文本, 检测到的语言)
        """
        return self._stt.transcribe(audio_file_path, output_prefix=output_prefix)
