import os
import datetime
import argparse
from models.factory import ModelFactory

def generate_output_filename(prefix, extension):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}.{extension}"

def main(stt_model='azure', tts_model='azure', translator_model='zhipu', 
         input_audio_file=None, target_lang='中文'):
    """
    主函数：处理音频转文字、翻译、文字转语音的完整流程
    
    Args:
        stt_model: 语音转文字模型名称（默认: 'azure'）
        tts_model: 文字转语音模型名称（默认: 'azure'）
        translator_model: 翻译模型名称（默认: 'zhipu'）
        input_audio_file: 输入音频文件路径（如果为None，使用默认路径）
        target_lang: 目标翻译语言（默认: '中文'）
    """
    # 设置文件路径
    if input_audio_file is None:
        input_audio_file = "data/098f6bcd4621d373cade4e832627b4f6.mp3"
    
    if not os.path.exists(input_audio_file):
        print(f"错误: 输入音频文件不存在: {input_audio_file}")
        return
    
    basename_audio_file = os.path.splitext(os.path.basename(input_audio_file))[0]
    output_audio = os.path.join(os.path.dirname(input_audio_file), basename_audio_file + '_output.mp3')
    output_audio = generate_output_filename(output_audio, "mp3")
    
    text_file = os.path.join(os.path.dirname(input_audio_file), basename_audio_file + '.txt')
    translated_text_file = os.path.join(os.path.dirname(input_audio_file), basename_audio_file + '_translated.txt')

    try:
        # 创建模型工厂
        factory = ModelFactory()
        
        # 显示可用模型
        available_models = factory.get_available_models()
        print(f"可用模型:")
        print(f"  STT: {available_models['stt']}")
        print(f"  TTS: {available_models['tts']}")
        print(f"  Translator: {available_models['translator']}")
        print()
        
        # 1. 创建并使用语音转文字模型
        print(f"使用STT模型: {stt_model}")
        stt = factory.create_stt(stt_model)
        _, detected_language = stt.transcribe(input_audio_file)
        print(f"检测到的语言: {detected_language}")
        print()
        
        # 2. 创建并使用翻译模型
        print(f"使用翻译模型: {translator_model}")
        translator = factory.create_translator(translator_model)
        translation_success = translator.translate_file(text_file, translated_text_file, target_lang=target_lang)
        
        if not translation_success:
            print("翻译失败")
            return
        print()
        
        # 3. 创建并使用文字转语音模型
        print(f"使用TTS模型: {tts_model}")
        tts = factory.create_tts(tts_model)
        
        with open(translated_text_file, 'r', encoding='utf-8') as f:
            chinese_text = f.read()
        
        tts_success = tts.synthesize_speech(chinese_text, output_audio)
        
        if tts_success:
            print(f"中文音频生成成功，保存为 {output_audio}")
        else:
            print("中文音频生成失败")
            
    except ValueError as e:
        print(f"错误: {e}")
    except Exception as e:
        print(f"发生错误: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='VidGoStream: 视频音频处理工具')
    parser.add_argument('--stt-model', type=str, default='azure', 
                       help='语音转文字模型名称 (默认: azure)')
    parser.add_argument('--tts-model', type=str, default='azure', 
                       help='文字转语音模型名称 (默认: azure)')
    parser.add_argument('--translator-model', type=str, default='zhipu', 
                       help='翻译模型名称 (默认: zhipu)')
    parser.add_argument('--input', type=str, default=None, 
                       help='输入音频文件路径')
    parser.add_argument('--target-lang', type=str, default='中文', 
                       help='目标翻译语言 (默认: 中文)')
    
    args = parser.parse_args()
    
    main(
        stt_model=args.stt_model,
        tts_model=args.tts_model,
        translator_model=args.translator_model,
        input_audio_file=args.input,
        target_lang=args.target_lang
    )
