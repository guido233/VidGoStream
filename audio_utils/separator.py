import os
import shutil
import subprocess
from typing import Optional

DEFAULT_SPLEETER_PYTHON = "/home/liumeng/miniconda3/envs/spleeter/bin/python"


def _probe_channels(audio_path: str) -> Optional[int]:
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "a:0",
        "-show_entries", "stream=channels",
        "-of", "default=nw=1:nk=1",
        audio_path,
    ]
    try:
        res = subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except Exception:
        return None

    value = res.stdout.strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _select_codec_args(output_path: str) -> list:
    ext = os.path.splitext(output_path)[1].lower()
    if ext == ".mp3":
        return ["-c:a", "libmp3lame", "-b:a", "192k"]
    if ext == ".aac":
        return ["-c:a", "aac", "-b:a", "192k"]
    return []


def _separate_with_spleeter(
    input_audio_path: str,
    vocals_output_path: str,
    background_output_path: str,
    spleeter_python: Optional[str] = None,
) -> bool:
    cmd_base = None
    if spleeter_python:
        cmd_base = [spleeter_python, "-m", "spleeter"]
    else:
        spleeter_bin = shutil.which("spleeter")
        if spleeter_bin:
            cmd_base = [spleeter_bin]

    if cmd_base is None:
        conda_bin = shutil.which("conda")
        if conda_bin:
            cmd_base = [conda_bin, "run", "-n", "spleeter", "spleeter"]

    if cmd_base is None:
        print("提示: 未找到 spleeter")
        print("提示: 可设置环境变量 SPLEETER_PYTHON 指向含 spleeter 的 python")
        print("提示: 或确保 conda 环境名为 spleeter 并可用 `conda run -n spleeter`")
        return False

    tmp_root = os.path.join(
        os.path.dirname(os.path.abspath(input_audio_path)),
        "_spleeter_tmp",
    )
    try:
        os.makedirs(tmp_root, exist_ok=True)
        cmd = cmd_base + [
            "separate",
            "-p", "spleeter:2stems",
            "-o", tmp_root,
            input_audio_path,
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        base = os.path.splitext(os.path.basename(input_audio_path))[0]
        out_dir = os.path.join(tmp_root, base)
        vocals_src = os.path.join(out_dir, "vocals.wav")
        bg_src = os.path.join(out_dir, "accompaniment.wav")
        if not os.path.exists(vocals_src) or not os.path.exists(bg_src):
            print("spleeter 输出文件缺失")
            return False

        subprocess.run(
            ["ffmpeg", "-y", "-i", vocals_src] + _select_codec_args(vocals_output_path) + [vocals_output_path],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            ["ffmpeg", "-y", "-i", bg_src] + _select_codec_args(background_output_path) + [background_output_path],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except Exception as exc:
        print(f"spleeter 分离失败: {exc}")
        return False
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)


def separate_vocals_background(
    input_audio_path: str,
    vocals_output_path: str,
    background_output_path: str,
    mode: str = "spleeter",
    spleeter_python: Optional[str] = None,
) -> bool:
    if not os.path.exists(input_audio_path):
        print(f"错误: 输入音频不存在: {input_audio_path}")
        return False

    if mode == "spleeter":
        return _separate_with_spleeter(
            input_audio_path=input_audio_path,
            vocals_output_path=vocals_output_path,
            background_output_path=background_output_path,
            spleeter_python=spleeter_python
            or os.environ.get("SPLEETER_PYTHON")
            or DEFAULT_SPLEETER_PYTHON,
        )

    if mode != "center_cancel":
        print(f"不支持的分离模式: {mode}")
        return False

    channels = _probe_channels(input_audio_path)
    if not channels or channels < 2:
        print("提示: 需要立体声才能做 center_cancel")
        return False

    # Vocal approx: (L+R)/2. Background approx: (L-R)/2.
    filter_complex = (
        "[0:a]aformat=channel_layouts=stereo,pan=stereo|"
        "c0=0.5*c0+0.5*c1|c1=0.5*c0+0.5*c1[voc];"
        "[0:a]aformat=channel_layouts=stereo,pan=stereo|"
        "c0=0.5*c0-0.5*c1|c1=0.5*c1-0.5*c0[bg]"
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-i", input_audio_path,
        "-filter_complex", filter_complex,
        "-map", "[voc]",
    ]
    cmd += _select_codec_args(vocals_output_path)
    cmd.append(vocals_output_path)
    cmd += ["-map", "[bg]"]
    cmd += _select_codec_args(background_output_path)
    cmd.append(background_output_path)

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception as exc:
        print(f"分离失败: {exc}")
        return False


if __name__ == "__main__":
    input_path = "data/test2.mp3"
    ok = separate_vocals_background(
        input_audio_path=input_path,
        vocals_output_path="data/test2_vocals.mp3",
        background_output_path="data/test2_bg.mp3",
        mode="spleeter",
    )
    if ok:
        print("✓ 分离完成")
