# VidGoStream - AI 视频多语言自动化工具

VidGoStream 是一个全自动化的 AI 视频本地化工具，旨在打破语言障碍。它能够一键完成从下载、语音转文字 (STT)、多语言翻译、语音合成 (TTS) 到最终视频合成的完整流程，保留背景音乐并生成高质量的配音视频。

## ✨ 核心亮点

- **🎞️ 智能下载体系**：
  - 基于 `yt-dlp` 的高效下载器。
  - **智能字幕获取**：自动检测即使下载原语言字幕，支持断点续传。
  - **UDI 唯一标识**：使用统一的 UDI (Unique Document Identifier) 管理全流程文件。

- **🤖 强大的 AI 引擎**：
  - **ASR/STT**：集成 Azure Speech Service，提供高精度语音转写。
  - **Translation**：接入智谱 AI (GLM-4)，实现更自然的上下文翻译。
  - **TTS**：使用 Azure Neural TTS，生成拟人化的高质量配音。

- **🎵 专业级音频处理**：
  - **人声分离**：内置 Spleeter 引擎，自动剥离人声与背景音乐。
  - **智能混音**：自动调节背景音与 AI 配音的比例，确保听感舒适。
  - **时间轴对齐**：通过 SRT 精确控制 TTS 语速，保持画面与声音同步。

## 🛠️ 环境部署

本项目采用双 Conda 环境架构 (`tts` 和 `spleeter`) 以解决 Python 依赖冲突问题。

### 1. 前置要求
- **OS**: macOS / Linux
- **Conda**: 安装 [Anaconda](https://www.anaconda.com/) 或 [Miniconda](https://docs.conda.io/en/latest/miniconda.html)
- **FFmpeg**: 需预先安装 (如 `brew install ffmpeg`)

### 2. 一键安装
运行根目录下的安装脚本，自动配置所有环境：

```bash
chmod +x install_env.sh
./install_env.sh
```

### 3. 配置 API 密钥
项目依赖第三方 AI 服务，请配置 `.env` 文件：

```bash
cp env.example .env
```

编辑 `.env` 文件填入密钥：
```ini
# 智谱 AI (用于翻译)
ZHIPU_API_KEY=your_key_here

# Azure Speech (用于 STT/TTS)
AZURE_SPEECH_KEY=your_key_here
AZURE_SPEECH_REGION=japaneast
```

## 🚀 使用指南

### 1. 视频下载 (Downloader)
使用 `ytdownloader` 模块批量下载视频。编辑 `config/vdc.csv` 填入 YouTube 链接。

```bash
conda activate tts
python ytdownloader/downloader.py
```
> 下载内容将保存在 `data/` 目录下，包含 mp4, mp3 及 srt 字幕。

### 2. 完整转换流程 (Main Pipeline)
使用 `main.py` 执行核心转换任务。支持自动人声分离、翻译和配音合成。

**基本用法：**
```bash
conda activate tts
python main.py --input data/{UDI}.mp3 --video data/{UDI}.mp4 --target-lang "中文"
```

**参数说明：**
- `--input`: 输入音频文件路径 (必须)
- `--video`: 输入视频文件路径 (可选，用于最终合成)
- `--target-lang`: 目标语言，默认 "中文"
- `--stt-model`: STT 模型 (默认 azure)
- `--tts-model`: TTS 模型 (默认 azure)
- `--translator-model`: 翻译模型 (默认 zhipu)

### 3. 音频分离工具 (Audio Utils)
如果只需分离人声和背景音：

```python
from audio_utils import separate_vocals_background

separate_vocals_background(
    input_audio_path="input.mp3",
    vocals_output_path="vocals.mp3",
    background_output_path="bg.mp3"
)
```

## 📂 项目结构

```
VidGoStream/
├── audio_utils/       # 音频处理/分离工具 (Spleeter 集成)
├── config/            # 配置文件 (vdc.csv, cookies)
├── data/              # 数据存储目录 (视频/音频/字幕)
├── models/            # AI 模型接口 (Factory 模式)
├── msstt/             # STT 相关代码
├── videomerger/       # 视频合成模块
├── ytdownloader/      # YouTube 下载器
├── install_env.sh     # 环境安装脚本
├── main.py            # 主程序入口
├── requirements.txt   # 依赖清单
└── README.md          # 项目文档
```

## 📝 许可证

[MIT License](LICENSE)