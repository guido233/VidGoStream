import os
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from mstts.text_to_speech import TextToSpeech

def test_speech_synthesis():
    # 请替换为您的 Azure 语音服务密钥和区域
    subscription = os.environ.get('AZURE_SPEECH_KEY', 'fe4416eeec3945279cf0201142f5a486')
    region = os.environ.get('AZURE_SPEECH_REGION', 'japaneast')
    
    # 测试文本
    test_text = "这是一个测试文本，用于验证语音合成功能。"
    
    # 创建 TextToSpeech 实例
    tts = TextToSpeech(subscription, region)
    
    # 设置输出文件
    output_file = os.path.join(os.path.dirname(__file__), "test_output.mp3")
    
    # 合成语音
    success = tts.synthesize_speech(test_text, output_file)
    
    if success:
        print(f"语音合成测试成功。输出文件: {output_file}")
        # 检查文件是否存在
        if os.path.exists(output_file):
            print(f"文件 {output_file} 已成功创建。")
        else:
            print(f"错误：文件 {output_file} 未创建。")
    else:
        print("语音合成测试失败。")

if __name__ == "__main__":
    test_speech_synthesis()
