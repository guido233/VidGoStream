import os
import datetime
import argparse
import subprocess
from models.factory import ModelFactory
from videomerger import VideoMerger
from audio_utils import separate_vocals_background
from utils.path_manager import PathManager



def _select_codec_args(output_path: str) -> list:
    ext = os.path.splitext(output_path)[1].lower()
    if ext == ".mp3":
        return ["-c:a", "libmp3lame", "-b:a", "192k"]
    if ext == ".aac":
        return ["-c:a", "aac", "-b:a", "192k"]
    return []

def _mix_background_and_tts(bg_audio_path: str, tts_audio_path: str, out_audio_path: str,
                            bg_volume: float = 0.35, tts_volume: float = 1.0) -> bool:
    filter_complex = (
        f"[0:a]volume={bg_volume}[bg];"
        f"[1:a]volume={tts_volume}[tts];"
        "[bg][tts]amix=inputs=2:normalize=0:dropout_transition=0[aout]"
    )
    cmd = [
        "ffmpeg", "-y",
        "-i", bg_audio_path,
        "-i", tts_audio_path,
        "-filter_complex", filter_complex,
        "-map", "[aout]",
        "-shortest",
    ]
    cmd += _select_codec_args(out_audio_path)
    cmd.append(out_audio_path)

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception as exc:
        print(f"背景声混音失败: {exc}")
        return False

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
    
    basename_audio_file = os.path.splitext(os.path.basename(input_audio_file))[0]
    
    # 初始化路径管理器
    pm = PathManager()
    
    # 获取目录（PathManager会自动创建目录）
    project_dir = pm.get_project_dir(basename_audio_file)
    intermediate_dir = pm.get_intermediate_dir(basename_audio_file)
    
    # 获取音频输出路径
    output_audio = pm.get_path('tts_audio', basename_audio_file)
    
    # 如果提供了视频文件，准备输出视频路径
    output_video = None
    if input_video_file:
        if not os.path.exists(input_video_file):
            print(f"警告: 视频文件不存在: {input_video_file}，将跳过视频合并步骤")
            input_video_file = None
        else:
            output_video = pm.get_path('final_video', basename_audio_file)
    
    # SRT文件路径
    srt_file = pm.get_path('srt', basename_audio_file)
    translated_srt_file = pm.get_path('translated_srt', basename_audio_file)

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
        _, detected_language = stt.transcribe(input_audio_file, output_dir=intermediate_dir)
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
        
        tmp_dir = pm.get_path('tmp_tts', basename_audio_file)
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
        
        # 5. 使用 spleeter 分离背景音并混合
        bg_audio_path = pm.get_path('bg_audio', basename_audio_file)
        vocals_audio_path = pm.get_path('vocals_audio', basename_audio_file)

        mix_audio = output_audio
        sep_success = separate_vocals_background(
            input_audio_path=input_audio_file,
            vocals_output_path=vocals_audio_path,
            background_output_path=bg_audio_path,
            mode="spleeter",
        )
        if sep_success:
            # 混合文件放到项目根目录
            mix_audio_path = pm.get_path('final_mix', basename_audio_file)
            mix_success = _mix_background_and_tts(bg_audio_path, output_audio, mix_audio_path)
            if mix_success:
                mix_audio = mix_audio_path
                print(f"✓ 背景声混合成功，保存为 {mix_audio}")
            else:
                print("⚠ 背景声混合失败，继续使用纯TTS音频")
        else:
            print("⚠ 背景声分离失败，继续使用纯TTS音频")
        print()

        # 6. 如果提供了视频文件，合并视频和音频
        if input_video_file and output_video:
            print("=" * 50)
            print("步骤6: 合并视频和音频")
            print("=" * 50)
            merger = VideoMerger()
            merge_success = merger.merge(input_video_file, mix_audio, output_video)
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
