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
        print(f"DEBUG: Initializing Azure TTS with region: {region}, voice: {voice_name}")
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
    
    def synthesize_srt_aligned(self, srt_path, out_audio_path, tmp_dir="tmp_srt_tts", 
                               export_format="mp3", speedup_cap=3.0, slowdown_cap=0.7, 
                               pad_when_short=True, tail_silence_ms=300):
        """
        根据SRT文件生成严格时间对齐的音频
        
        Args:
            srt_path: 输入SRT文件路径
            out_audio_path: 输出音频文件路径
            tmp_dir: 临时文件目录
            export_format: 导出格式（默认: mp3）
            speedup_cap: 最大加速倍数（默认: 3.0）
            slowdown_cap: 最慢慢放倍数（默认: 0.7）
            pad_when_short: 是否在时长不足时补静音（默认: True）
            tail_silence_ms: 尾部静音时长（毫秒，默认: 300）
            
        Returns:
            bool: 是否成功
        """
        return self._tts.synthesize_srt_aligned(
            srt_path=srt_path,
            out_audio_path=out_audio_path,
            tmp_dir=tmp_dir,
            export_format=export_format,
            speedup_cap=speedup_cap,
            slowdown_cap=slowdown_cap,
            pad_when_short=pad_when_short,
            tail_silence_ms=tail_silence_ms
        )
    
    def cleanup_tmp(self, tmp_dir="tmp_srt_tts"):
        """
        清理临时目录
        
        Args:
            tmp_dir: 临时目录路径
        """
        return self._tts.cleanup_tmp(tmp_dir)

