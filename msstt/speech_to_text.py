import azure.cognitiveservices.speech as speechsdk
import os
from pydub import AudioSegment
import time
from datetime import timedelta

def convert_mp3_to_wav(mp3_path, wav_path):
    audio = AudioSegment.from_mp3(mp3_path)
    audio.export(wav_path, format="wav")

def format_timestamp(total_seconds):
    """
    将秒数转换为SRT格式的时间戳 (HH:MM:SS,mmm)
    
    Args:
        total_seconds: 总秒数（可以是浮点数）
        
    Returns:
        str: SRT格式的时间戳字符串
    """
    td = timedelta(seconds=total_seconds)
    total_seconds_int = int(total_seconds)
    milliseconds = int((total_seconds - total_seconds_int) * 1000)
    
    hours = total_seconds_int // 3600
    minutes = (total_seconds_int % 3600) // 60
    seconds = total_seconds_int % 60
    
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

def generate_srt(segments):
    """
    生成SRT格式的字幕内容
    
    Args:
        segments: 包含时间戳和文本的列表，每个元素为 (start_time, end_time, text)
        
    Returns:
        str: SRT格式的字幕内容
    """
    srt_content = []
    for index, (start_time, end_time, text) in enumerate(segments, 1):
        start_str = format_timestamp(start_time)
        end_str = format_timestamp(end_time)
        # SRT格式：序号、时间轴、文本，每个块之间用空行分隔
        srt_content.append(f"{index}\n{start_str} --> {end_str}\n{text}")
    
    return "\n\n".join(srt_content)

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
        recognized_segments = []  # 存储带时间戳的识别结果
        detected_language = None

        def stop_cb(evt):
            nonlocal done
            print('CLOSING on {}'.format(evt))
            done = True

        def recognized_cb(evt):
            nonlocal recognized_text, recognized_segments, detected_language
            result = evt.result
            
            # 获取时间信息（offset和duration以100纳秒为单位）
            offset_ticks = result.offset
            duration_ticks = result.duration
            
            # 转换为秒
            start_time = offset_ticks / 10000000.0  # 100纳秒 = 10^-7 秒
            end_time = (offset_ticks + duration_ticks) / 10000000.0
            
            text = result.text.strip()
            if text:  # 只保存非空文本
                recognized_text.append(text)
                recognized_segments.append((start_time, end_time, text))
                
                if not detected_language:
                    detected_language = result.properties.get(speechsdk.PropertyId.SpeechServiceConnection_AutoDetectSourceLanguageResult)
                
                print(f"Recognized [{format_timestamp(start_time)} --> {format_timestamp(end_time)}]: {text}")
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
        output_txt_path = os.path.join(file_dir, base_name + '.txt')
        with open(output_txt_path, 'w', encoding='utf-8') as f:
            f.write(full_text)
        
        print(f"识别的文本已保存到: {output_txt_path}")
        
        # 生成SRT格式的字幕文件
        if recognized_segments:
            output_srt_path = os.path.join(file_dir, base_name + '.srt')
            srt_content = generate_srt(recognized_segments)
            with open(output_srt_path, 'w', encoding='utf-8') as f:
                f.write(srt_content)
            print(f"SRT字幕文件已保存到: {output_srt_path}")
        else:
            print("警告: 没有识别到任何文本，无法生成SRT文件")

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
