import os
import datetime
import argparse
from models.factory import ModelFactory
from videomerger import VideoMerger

def generate_output_filename(prefix, extension):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}.{extension}"

def main(stt_model='azure', tts_model='azure', translator_model='zhipu', 
         input_audio_file=None, input_video_file=None, target_lang='中文'):
    """
    主函数：处理音频转文字、翻译、文字转语音的完整流程
    
    Args:
        stt_model: 语音转文字模型名称（默认: 'azure'）
        tts_model: 文字转语音模型名称（默认: 'azure'）
        translator_model: 翻译模型名称（默认: 'zhipu'）
        input_audio_file: 输入音频文件路径（如果为None，使用默认路径）
        input_video_file: 输入视频文件路径（可选，如果提供则会在最后合并视频和音频）
        target_lang: 目标翻译语言（默认: '中文'）
    """
    # 设置文件路径
    if input_audio_file is None:
        input_audio_file = "data/test2.mp3"
    
    if not os.path.exists(input_audio_file):
        print(f"错误: 输入音频文件不存在: {input_audio_file}")
        return
    
    basename_audio_file = os.path.splitext(os.path.basename(input_audio_file))[0]
    output_audio_base = os.path.join(os.path.dirname(input_audio_file), basename_audio_file + '_output')
    output_audio = generate_output_filename(output_audio_base, "mp3")
    
    # 如果提供了视频文件，准备输出视频路径
    output_video = None
    if input_video_file:
        if not os.path.exists(input_video_file):
            print(f"警告: 视频文件不存在: {input_video_file}，将跳过视频合并步骤")
            input_video_file = None
        else:
            basename_video_file = os.path.splitext(os.path.basename(input_video_file))[0]
            output_video = os.path.join(os.path.dirname(input_video_file), basename_video_file + '_translated.mp4')
            output_video = generate_output_filename(output_video, "mp4")
    
    # 使用SRT文件进行翻译
    srt_file = os.path.join(os.path.dirname(input_audio_file), basename_audio_file + '.srt')
    translated_srt_file = os.path.join(os.path.dirname(input_audio_file), basename_audio_file + '_translated.srt')

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
        
        # 2. 检查SRT文件是否存在
        if not os.path.exists(srt_file):
            print(f"错误: SRT文件不存在: {srt_file}")
            print("请确保STT步骤已成功生成SRT文件")
            return
        
        # 3. 创建并使用翻译模型翻译SRT文件
        print(f"使用翻译模型: {translator_model}")
        translator = factory.create_translator(translator_model)
        translation_success = translator.translate_file(srt_file, translated_srt_file, target_lang=target_lang)
        
        if not translation_success:
            print("翻译失败")
            return
        print()
        
        # 4. 创建并使用文字转语音模型（严格按SRT时间轴对齐）
        print(f"使用TTS模型: {tts_model}")
        tts = factory.create_tts(tts_model)
        
        tmp_dir = f"tmp_srt_tts_{basename_audio_file}"
        try:
            tts_success = tts.synthesize_srt_aligned(
                srt_path=translated_srt_file,
                out_audio_path=output_audio,
                tmp_dir=tmp_dir,
                export_format="mp3",
                pad_when_short=True,
                speedup_cap=3.0,
                slowdown_cap=0.7
            )
        finally:
            # 清理中间目录（可根据需要关闭清理便于调试）
            try:
                tts.cleanup_tmp(tmp_dir)
            except Exception:
                pass
        
        if tts_success:
            print(f"✓ 中文音频生成成功，保存为 {output_audio}")
        else:
            print("✗ 中文音频生成失败")
            return
        print()
        
        # 5. 如果提供了视频文件，合并视频和音频
        if input_video_file and output_video:
            print("=" * 50)
            print("步骤5: 合并视频和音频")
            print("=" * 50)
            merger = VideoMerger()
            merge_success = merger.merge(input_video_file, output_audio, output_video)
            if merge_success:
                print(f"✓ 最终视频已生成: {output_video}")
            else:
                print("✗ 视频合并失败")
        elif input_video_file:
            print("⚠ 视频文件路径无效，跳过合并步骤")
            
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
    parser.add_argument('--video', type=str, default=None, 
                       help='输入视频文件路径（可选，如果提供则会在最后合并视频和音频）')
    parser.add_argument('--target-lang', type=str, default='中文', 
                       help='目标翻译语言 (默认: 中文)')
    
    args = parser.parse_args()
    
    main(
        stt_model=args.stt_model,
        tts_model=args.tts_model,
        translator_model=args.translator_model,
        input_audio_file=args.input,
        input_video_file=args.video,
        target_lang=args.target_lang
    )
