import os
import datetime
from msstt.speech_to_text import SpeechToText
from mstts.text_to_speech import TextToSpeech
from texttranslator.translator import TextTranslator

def generate_output_filename(prefix, extension):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}.{extension}"

def main():
    # 设置环境变量和文件路径
    input_audio_file = "data/098f6bcd4621d373cade4e832627b4f6.mp3"
    basename_audio_file = os.path.splitext(os.path.basename(input_audio_file))[0]
    
    output_audio = os.path.join(os.path.dirname(input_audio_file), basename_audio_file + '_output.mp3')
    output_audio = generate_output_filename(output_audio, "mp3")

    # 设置API密钥（请替换为实际的密钥）
    azure_speech_key = os.environ.get('AZURE_SPEECH_KEY', 'your_azure_speech_key')
    azure_region = os.environ.get('AZURE_SPEECH_REGION', 'your_azure_region')
    openai_api_key = os.environ.get('OPENAI_API_KEY', 'your_openai_api_key')

    # 1. 语音转文字
    stt = SpeechToText(azure_speech_key, azure_region)

    _, detected_language = stt.transcribe(input_audio_file)
    text_file = os.path.join(os.path.dirname(input_audio_file), basename_audio_file + '.txt')
    translated_text_file = os.path.join(os.path.dirname(input_audio_file), basename_audio_file + '_translated.txt')

    # 2. 文字翻译
    translator = TextTranslator(openai_api_key)
    translation_success = translator.translate_file(text_file, translated_text_file, target_lang='中文')
    
    if not translation_success:
        print("翻译失败")
        return

    # 3. 文字转语音
    tts = TextToSpeech(azure_speech_key, azure_region)
    
    with open(translated_text_file, 'r', encoding='utf-8') as f:
        chinese_text = f.read()
    
    tts_success = tts.synthesize_speech(chinese_text, output_audio)
    
    if tts_success:
        print(f"中文音频生成成功，保存为 {output_audio}")
    else:
        print("中文音频生成失败")


if __name__ == "__main__":
    main()
