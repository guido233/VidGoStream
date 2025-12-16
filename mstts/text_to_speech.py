import os
import re
import math
import shutil
import subprocess
from dataclasses import dataclass
from typing import List, Optional

import azure.cognitiveservices.speech as speechsdk
from pydub import AudioSegment


@dataclass
class SrtCue:
    idx: int
    start_ms: int
    end_ms: int
    text: str


def srt_time_to_ms(t: str) -> int:
    # "HH:MM:SS,mmm"
    hh, mm, rest = t.split(":")
    ss, mmm = rest.split(",")
    return (int(hh) * 3600 + int(mm) * 60 + int(ss)) * 1000 + int(mmm)


def build_atempo_chain(factor: float) -> str:
    """
    ffmpeg atempo 支持范围 0.5~2.0
    超出时用多个 atempo 串起来（等价乘积）
    """
    if factor <= 0:
        raise ValueError("factor must be > 0")

    parts = []
    f = factor
    while f > 2.0:
        parts.append(2.0)
        f /= 2.0
    while f < 0.5:
        parts.append(0.5)
        f /= 0.5
    parts.append(f)

    # 避免显示成科学计数法
    parts = [f"{p:.6f}".rstrip("0").rstrip(".") for p in parts]
    return ",".join([f"atempo={p}" for p in parts])


def ffmpeg_time_stretch(in_wav: str, out_wav: str, tempo_factor: float):
    """
    tempo_factor > 1: 变快（时长变短）
    tempo_factor < 1: 变慢（时长变长）
    """
    chain = build_atempo_chain(tempo_factor)
    cmd = [
        "ffmpeg", "-y",
        "-i", in_wav,
        "-filter:a", chain,
        out_wav
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class TextToSpeech:
    def __init__(self, subscription, region, voice_name='zh-CN-XiaoxiaoNeural'):
        self.speech_config = self._configure_speech_synthesizer(subscription, region, voice_name)

    def _configure_speech_synthesizer(self, subscription, region, voice_name):
        speech_config = speechsdk.SpeechConfig(subscription=subscription, region=region)
        speech_config.speech_synthesis_voice_name = voice_name

        # 强烈建议用 WAV 输出（好测时长、好做变速）
        speech_config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Riff16Khz16BitMonoPcm
        )
        return speech_config

    def synthesize_speech_to_wav(self, text: str, output_wav: str) -> bool:
        audio_config = speechsdk.audio.AudioOutputConfig(filename=output_wav)
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=self.speech_config, audio_config=audio_config)

        result = synthesizer.speak_text_async(text).get()

        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            return True
        if result.reason == speechsdk.ResultReason.Canceled:
            cd = result.cancellation_details
            print(f"TTS取消: {cd.reason}")
            if cd.reason == speechsdk.CancellationReason.Error and cd.error_details:
                print(f"错误详情: {cd.error_details}")
        return False

    # -------------------------------
    # 解析 SRT
    # -------------------------------
    def parse_srt(self, srt_path: str) -> List[SrtCue]:
        with open(srt_path, "r", encoding="utf-8") as f:
            content = f.read().strip()

        blocks = re.split(r"\n\s*\n", content)
        cues: List[SrtCue] = []

        for block in blocks:
            lines = [ln.rstrip("\r") for ln in block.splitlines() if ln.strip() != ""]
            if len(lines) < 3:
                continue
            if not lines[0].strip().isdigit():
                continue

            idx = int(lines[0].strip())
            timecode = lines[1].strip()
            if "-->" not in timecode:
                continue

            start_s, end_s = [x.strip() for x in timecode.split("-->")]
            start_ms = srt_time_to_ms(start_s)
            end_ms = srt_time_to_ms(end_s)
            text = "\n".join(lines[2:]).strip()

            cues.append(SrtCue(idx=idx, start_ms=start_ms, end_ms=end_ms, text=text))

        cues.sort(key=lambda x: x.start_ms)
        return cues

    def _should_skip_cue(self, text: str) -> bool:
        t = text.strip()
        if not t:
            return True
        # 纯舞台提示可跳过：你也可以改成 False 让它读出来
        if re.fullmatch(r'[\[\(].*?[\]\)]', t) and len(t) <= 40:
            return True
        if re.fullmatch(r'[♪♫\s]+', t):
            return True
        return False

    # -------------------------------
    # SRT -> 严格时间对齐音频
    # -------------------------------
    def synthesize_srt_aligned(
        self,
        srt_path: str,
        out_audio_path: str,
        tmp_dir: str = "tmp_srt_tts",
        export_format: str = "mp3",
        speedup_cap: float = 3.0,
        slowdown_cap: float = 0.7,
        pad_when_short: bool = True,
        tail_silence_ms: int = 300
    ) -> bool:
        """
        - speedup_cap: 需要加速时，最大加速倍数（>1）。例如 3.0 表示最多加速到 3 倍。
        - slowdown_cap: 需要慢放时，最慢放到多少（<1）。例如 0.7 表示最多慢放到 0.7 倍（时长变长到约 1/0.7）。
        - pad_when_short: 若 TTS 实际时长 < 目标时长，优先“补静音”而不是大幅慢放（更自然）
        """
        if not os.path.exists(srt_path):
            raise FileNotFoundError(f"SRT文件不存在: {srt_path}")

        os.makedirs(tmp_dir, exist_ok=True)

        cues = self.parse_srt(srt_path)
        if not cues:
            print("SRT解析失败或为空")
            return False

        total_ms = max(c.end_ms for c in cues) + tail_silence_ms
        timeline = AudioSegment.silent(duration=total_ms)

        for cue in cues:
            target_ms = max(0, cue.end_ms - cue.start_ms)
            if target_ms == 0:
                continue

            if self._should_skip_cue(cue.text):
                continue

            raw_wav = os.path.join(tmp_dir, f"{cue.idx:06d}_raw.wav")
            adj_wav = os.path.join(tmp_dir, f"{cue.idx:06d}_adj.wav")

            ok = self.synthesize_speech_to_wav(cue.text, raw_wav)
            if not ok:
                print(f"第{cue.idx}条TTS失败，跳过")
                continue

            seg = AudioSegment.from_wav(raw_wav)
            actual_ms = len(seg)

            # 计算需要的 tempo_factor
            # tempo_factor = actual / target
            # 例：actual=1200ms target=1000ms -> factor=1.2 -> 加速（时长变短）
            tempo_factor = actual_ms / target_ms

            # 情况A：太长，需要加速缩短到 target
            if actual_ms > target_ms:
                tempo_factor = min(tempo_factor, speedup_cap)
                try:
                    ffmpeg_time_stretch(raw_wav, adj_wav, tempo_factor)
                except Exception as e:
                    print(f"第{cue.idx}条变速失败({e})，使用原音频硬截断")
                    seg2 = seg[:target_ms]
                    seg2.export(adj_wav, format="wav")

                seg_adj = AudioSegment.from_wav(adj_wav)
                # 若仍超出，硬截断保证严格对齐
                if len(seg_adj) > target_ms:
                    seg_adj = seg_adj[:target_ms]

            # 情况B：太短，需要拉长（慢放或补静音）
            else:
                if pad_when_short:
                    # 先不慢放，直接补静音到 target（最自然，字不会被拖慢）
                    seg_adj = seg + AudioSegment.silent(duration=(target_ms - actual_ms))
                else:
                    # 真慢放：tempo_factor < 1
                    tempo_factor = max(tempo_factor, slowdown_cap)  # 防止过慢
                    try:
                        ffmpeg_time_stretch(raw_wav, adj_wav, tempo_factor)
                        seg_adj = AudioSegment.from_wav(adj_wav)
                    except Exception as e:
                        print(f"第{cue.idx}条慢放失败({e})，改为补静音")
                        seg_adj = seg + AudioSegment.silent(duration=(target_ms - actual_ms))

                # 若慢放后仍不足，补静音兜底；若超出，截断兜底
                if len(seg_adj) < target_ms:
                    seg_adj += AudioSegment.silent(duration=(target_ms - len(seg_adj)))
                if len(seg_adj) > target_ms:
                    seg_adj = seg_adj[:target_ms]

            # 放入时间轴：严格以 start_ms 为起点，长度严格 target_ms
            start = cue.start_ms
            end = start + target_ms
            if end > len(timeline):
                # 扩展时间轴
                timeline += AudioSegment.silent(duration=(end - len(timeline)))

            # “替换式拼接”，避免 overlay 混音
            timeline = timeline[:start] + seg_adj + timeline[end:]

            print(f"[{cue.idx}] target={target_ms}ms actual={actual_ms}ms tempo={actual_ms/target_ms:.3f}")

        # 导出
        if export_format.lower() == "mp3":
            timeline.export(out_audio_path, format="mp3", bitrate="192k")
        else:
            timeline.export(out_audio_path, format=export_format.lower())

        print(f"完成：严格对齐音频已导出 -> {out_audio_path}")
        return True

    def cleanup_tmp(self, tmp_dir: str = "tmp_srt_tts"):
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    subscription = os.environ["AZURE_SPEECH_KEY"]
    region = os.environ["AZURE_SPEECH_REGION"]

    tts = TextToSpeech(subscription, region, voice_name="zh-CN-XiaoxiaoNeural")

    tts.synthesize_srt_aligned(
        srt_path="data/test_translated.srt",
        out_audio_path="data/test_aligned.mp3",
        tmp_dir="tmp_srt_tts",
        export_format="mp3",
        pad_when_short=True,   # 推荐：短了就补静音，更自然
        speedup_cap=3.0,       # 太长时最多加速 3x（再长就会截断兜底）
        slowdown_cap=0.7       # 如果你关掉 pad_when_short 才会用到
    )
