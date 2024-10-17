import os
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from mstts import run_gui

def test_gui():
    # 请替换为您的 Azure 语音服务密钥和区域
    subscription = os.environ.get('AZURE_SPEECH_KEY', 'your_azure_speech_key')
    region = os.environ.get('AZURE_SPEECH_REGION', 'your_azure_region')
    
    print("启动 MSTTS GUI...")
    print(f"使用的订阅密钥: {subscription[:5]}...（已隐藏部分）")
    print(f"使用的区域: {region}")
    
    run_gui(subscription, region)

if __name__ == "__main__":
    test_gui()
