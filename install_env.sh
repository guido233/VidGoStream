#!/bin/bash
set -e

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

echo "=================================================="
echo "   VidGoStream 一键环境部署脚本 (macOS/Linux)"
echo "=================================================="

# 检查 Conda 是否安装
if ! command -v conda &> /dev/null; then
    echo "❌ 错误: 未检测到 Conda。"
    echo "请先安装 Anaconda 或 Miniconda: https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

# 初始化 Conda (使其在脚本中可用)
CONDA_BASE=$(conda info --base)
source "$CONDA_BASE/etc/profile.d/conda.sh"

# ------------------------------------------------
# 1. 部署 tts 环境 (主逻辑环境)
# ------------------------------------------------
echo ""
echo "[1/2] 正在配置 'tts' 环境..."

if conda info --envs | grep -q "^tts "; then
    echo " -> 检测到 'tts' 环境已存在，正在更新..."
else
    echo " -> 创建 'tts' 环境 (Python 3.9)..."
    conda create -n tts python=3.9 -y
fi

echo " -> 安装依赖..."
conda activate tts
# 安装 ffmpeg (conda 源通常比较方便)
conda install -c conda-forge ffmpeg -y
# 安装 Python 依赖
pip install --upgrade pip
pip install azure-cognitiveservices-speech pydub openai webvtt-py "googletrans==4.0.0-rc1"
pip install -U "yt-dlp[default]"

echo " -> 'tts' 环境配置完毕。"
conda deactivate

# ------------------------------------------------
# 2. 部署 spleeter 环境 (音频分离环境)
# ------------------------------------------------
echo ""
echo "[2/2] 正在配置 'spleeter' 环境..."
echo "注意: Spleeter 依赖较多，对 Python 版本敏感，独立使用 Python 3.8。"

if conda info --envs | grep -q "^spleeter "; then
    echo " -> 检测到 'spleeter' 环境已存在，正在更新..."
else
    echo " -> 创建 'spleeter' 环境 (Python 3.8)..."
    conda create -n spleeter python=3.8 -y
fi

echo " -> 安装依赖..."
conda activate spleeter
conda install -c conda-forge ffmpeg -y
pip install --upgrade pip
pip install spleeter

echo " -> 'spleeter' 环境配置完毕。"
conda deactivate

# ------------------------------------------------
# 3. 结束指引
# ------------------------------------------------
echo ""
echo "=================================================="
echo "✅ 环境部署成功！"
echo "=================================================="
echo "下一步操作:"
echo "1. 配置环境变量: 请复制 env.example 为 .env 并填入 API Key"
echo "   cp env.example .env"
echo "2. 运行程序:"
echo "   conda activate tts"
echo "   python main.py --video your_video.mp4"
echo "=================================================="
