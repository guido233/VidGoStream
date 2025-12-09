from mstts.text_to_speech import TextToSpeech as AzureTTSImpl
from .base import BaseTTS

class AzureTTS(BaseTTS):
    """Azure文字转语音模型"""
    
    def __init__(self, subscription, region, voice_name='zh-CN-XiaoxiaoNeural'):
        """
        初始化Azure TTS模型
        
        Args:
            subscription: Azure订阅密钥
            region: Azure服务区域
            voice_name: 语音名称
        """
        self.subscription = subscription
        self.region = region
        self.voice_name = voice_name
        self._tts = AzureTTSImpl(subscription, region, voice_name)
    
    def synthesize_speech(self, text, output_file):
        """
        将文字转换为语音
        
        Args:
            text: 要转换的文字
            output_file: 输出音频文件路径
            
        Returns:
            bool: 是否成功
        """
        return self._tts.synthesize_speech(text, output_file)

