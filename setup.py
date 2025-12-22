from setuptools import find_packages, setup

setup(
    name="vidgostream",
    version="0.1.0",
    description="VidGoStream: video/audio translation pipeline",
    packages=find_packages(exclude=("tests", "data", "tmp_srt_tts")),
    install_requires=[
        "azure-cognitiveservices-speech",
        "pydub",
        "openai",
        "webvtt-py",
        "googletrans==4.0.0-rc1",
        "yt-dlp",
    ],
    python_requires=">=3.9",
)
