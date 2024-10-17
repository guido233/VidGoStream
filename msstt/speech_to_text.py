import azure.cognitiveservices.speech as speechsdk
import os
from pydub import AudioSegment
import time

def convert_mp3_to_wav(mp3_path, wav_path):
    audio = AudioSegment.from_mp3(mp3_path)
    audio.export(wav_path, format="wav")

class SpeechToText:
    def __init__(self, speech_key, service_region):
        self.speech_key = speech_key
        self.service_region = service_region

    def transcribe(self, audio_file_path):
        # 获取文件的完整路径和文件名
        file_dir, file_name = os.path.split(audio_file_path)
        base_name, file_extension = os.path.splitext(file_name)

        # 检查文件是否为MP3格式，如果是，则转换为WAV
        temp_wav_path = None
        if file_extension.lower() == '.mp3':
            temp_wav_path = os.path.join(file_dir, base_name + '.wav')
            convert_mp3_to_wav(audio_file_path, temp_wav_path)
            audio_file_path = temp_wav_path

        speech_config = speechsdk.SpeechConfig(subscription=self.speech_key, region=self.service_region)
        auto_detect_source_language_config = speechsdk.languageconfig.AutoDetectSourceLanguageConfig(languages=["en-US", "zh-CN", "ja-JP", "ko-KR"])
        audio_config = speechsdk.audio.AudioConfig(filename=audio_file_path)

        speech_recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config, 
            auto_detect_source_language_config=auto_detect_source_language_config,
            audio_config=audio_config
        )

        done = False
        recognized_text = []
        detected_language = None

        def stop_cb(evt):
            nonlocal done
            print('CLOSING on {}'.format(evt))
            done = True

        def recognized_cb(evt):
            nonlocal recognized_text, detected_language
            recognized_text.append(evt.result.text)
            if not detected_language:
                detected_language = evt.result.properties.get(speechsdk.PropertyId.SpeechServiceConnection_AutoDetectSourceLanguageResult)
            print(f"Recognized: {evt.result.text}")
            print(f"Detected language: {detected_language}")

        speech_recognizer.recognized.connect(recognized_cb)
        speech_recognizer.session_stopped.connect(stop_cb)
        speech_recognizer.canceled.connect(stop_cb)

        speech_recognizer.start_continuous_recognition()

        while not done:
            time.sleep(.5)

        speech_recognizer.stop_continuous_recognition()

        full_text = " ".join(recognized_text)
        
        # 创建与音频文件同名的文本文件，保存在原始音频文件的相同位置
        output_file_path = os.path.join(file_dir, base_name + '.txt')
        with open(output_file_path, 'w', encoding='utf-8') as f:
            f.write(full_text)
        
        print(f"识别的文本已保存到: {output_file_path}")

        # 如果创建了临时WAV文件，在这里删除它
        if temp_wav_path and os.path.exists(temp_wav_path):
            os.remove(temp_wav_path)
            print(f"临时WAV文件已删除: {temp_wav_path}")

        return full_text, detected_language

if __name__ == "__main__":
    speech_key = "fe4416eeec3945279cf0201142f5a486"
    service_region = "japaneast"
    
    stt = SpeechToText(speech_key, service_region)
    
    audio_file_path = "data/test.mp3"
    recognized_text, detected_language = stt.transcribe(audio_file_path)
    print(f"完整识别的文本: {recognized_text}")
    print(f"检测到的语言: {detected_language}")
