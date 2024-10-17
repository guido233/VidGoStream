import os
import azure.cognitiveservices.speech as speechsdk

class TextToSpeech:
    def __init__(self, subscription, region, voice_name='zh-CN-XiaoxiaoNeural'):
        self.speech_config = self._configure_speech_synthesizer(subscription, region, voice_name)

    def _configure_speech_synthesizer(self, subscription, region, voice_name):
        speech_config = speechsdk.SpeechConfig(subscription=subscription, region=region)
        speech_config.speech_synthesis_voice_name = voice_name
        speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3)
        return speech_config

    def synthesize_speech(self, text, output_file):
        audio_config = speechsdk.audio.AudioOutputConfig(filename=output_file)
        speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=self.speech_config, audio_config=audio_config)
        
        speech_synthesis_result = speech_synthesizer.speak_text_async(text).get()

        if speech_synthesis_result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            print(f"语音合成成功，音频已保存为MP3：{output_file}")
            return True
        elif speech_synthesis_result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = speech_synthesis_result.cancellation_details
            print(f"语音合成取消: {cancellation_details.reason}")
            if cancellation_details.reason == speechsdk.CancellationReason.Error:
                if cancellation_details.error_details:
                    print(f"错误详情: {cancellation_details.error_details}")
            return False

# 使用示例：
# tts = TextToSpeech("your_subscription_key", "your_region")
# tts.synthesize_speech("你好，世界！", "output.mp3")
