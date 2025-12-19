import os
import shutil
import subprocess
from typing import Optional, Tuple

from pydub import AudioSegment


class AudioSeparator:
    """使用可用的工具拆分人声与伴奏"""

    def __init__(self):
        self.ffmpeg_available = self._check_ffmpeg()

    def _check_ffmpeg(self) -> bool:
        try:
            subprocess.run(
                ["ffmpeg", "-version"],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except Exception:
            return False

    def _try_spleeter(
        self, input_audio: str, output_dir: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """优先使用 spleeter（若已安装）做二分离"""
        if shutil.which("spleeter") is None:
            return None, None

        base = os.path.splitext(os.path.basename(input_audio))[0]
        work_dir = os.path.join(output_dir, base)
        os.makedirs(output_dir, exist_ok=True)

        try:
            subprocess.run(
                [
                    "spleeter",
                    "separate",
                    "-p",
                    "spleeter:2stems",
                    "-o",
                    output_dir,
                    input_audio,
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError as e:
            print(f"警告: spleeter 分离失败 ({e}), 将退回简单分离")
            return None, None

        vocal_path = os.path.join(work_dir, "vocals.wav")
        background_path = os.path.join(work_dir, "accompaniment.wav")
        if os.path.exists(vocal_path) and os.path.exists(background_path):
            return vocal_path, background_path

        return None, None

    def _simple_center_split(
        self, input_audio: str, output_dir: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        使用 ffmpeg 的中心声道抵消做一个近似分离：
        - vocals: 混合左右声道，突出人声
        - background: 左减右，尽量抵消居中的人声
        """
        if not self.ffmpeg_available:
            print("警告: 未检测到 ffmpeg，无法进行简单声道分离")
            return None, None

        os.makedirs(output_dir, exist_ok=True)
        base = os.path.splitext(os.path.basename(input_audio))[0]
        vocal_path = os.path.join(output_dir, f"{base}_vocals.wav")
        background_path = os.path.join(output_dir, f"{base}_background.wav")

        # vocals：取左右声道平均，得到居中声源
        vocal_cmd = [
            "ffmpeg",
            "-y",
            "-i",
            input_audio,
            "-af",
            "pan=mono|c0=0.5*c0+0.5*c1",
            vocal_path,
        ]

        # background：左右声道相消，压制中心人声
        background_cmd = [
            "ffmpeg",
            "-y",
            "-i",
            input_audio,
            "-af",
            "pan=stereo|c0=0.5*c0-0.5*c1|c1=0.5*c1-0.5*c0,highpass=f=90,lowpass=f=14000",
            background_path,
        ]

        try:
            subprocess.run(
                vocal_cmd,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            subprocess.run(
                background_cmd,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return vocal_path, background_path
        except subprocess.CalledProcessError as e:
            print(f"警告: ffmpeg 分离失败 ({e}), 将退回原始音频")
            return None, None

    def separate(
        self, input_audio: str, output_dir: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        返回 (vocals_path, background_path)，失败则为 (None, None)
        """
        if not os.path.exists(input_audio):
            print(f"警告: 输入音频不存在: {input_audio}")
            return None, None

        try:
            probe_audio = AudioSegment.from_file(input_audio)
            if probe_audio.channels == 1:
                print("提示: 单声道音频无法可靠分离，将直接使用原音频")
                return None, None
        except Exception:
            print("警告: 读取音频通道信息失败，将尝试直接分离")

        if output_dir is None:
            output_dir = os.path.join(
                os.path.dirname(input_audio),
                f"{os.path.splitext(os.path.basename(input_audio))[0]}_stems",
            )

        # 先尝试高质量的 spleeter（若可用），否则使用简单中心声道分离
        vocals, background = self._try_spleeter(input_audio, output_dir)
        if vocals and background:
            return vocals, background

        return self._simple_center_split(input_audio, output_dir)


class AudioMixer:
    """将翻译后的人声与背景音重新混合"""

    def __init__(self, background_gain_db: float = -4.0, voice_gain_db: float = 2.0):
        self.background_gain_db = background_gain_db
        self.voice_gain_db = voice_gain_db

    def mix(
        self,
        background_path: str,
        voice_path: str,
        output_path: str,
        background_gain_db: Optional[float] = None,
        voice_gain_db: Optional[float] = None,
    ) -> bool:
        if not os.path.exists(background_path):
            print(f"警告: 背景音不存在: {background_path}")
            return False
        if not os.path.exists(voice_path):
            print(f"警告: 人声音频不存在: {voice_path}")
            return False

        bg = AudioSegment.from_file(background_path)
        voice = AudioSegment.from_file(voice_path)

        target_ms = max(len(bg), len(voice))
        if len(bg) < target_ms:
            bg += AudioSegment.silent(duration=target_ms - len(bg))
        if len(voice) < target_ms:
            voice += AudioSegment.silent(duration=target_ms - len(voice))

        bg_gain = self.background_gain_db if background_gain_db is None else background_gain_db
        v_gain = self.voice_gain_db if voice_gain_db is None else voice_gain_db

        mixed = bg.apply_gain(bg_gain).overlay(voice.apply_gain(v_gain))

        export_fmt = os.path.splitext(output_path)[1].lstrip(".") or "mp3"
        mixed.export(output_path, format=export_fmt)
        print(f"✓ 混合完成: {output_path}")
        return True
