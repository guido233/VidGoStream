import os
import openai
import sys

class TextTranslator:
    def __init__(self, api_key):
        self.api_key = api_key
        openai.api_key = self.api_key

    def translate_file(self, input_file, output_file, target_lang='zh'):
        try:
            # 读取输入文件
            with open(input_file, 'r', encoding='utf-8') as f:
                text = f.read()

            # 准备翻译提示
            prompt = f"""请将以下YouTube视频的文本翻译成{target_lang}。
            翻译时请注意以下几点：
            1. 保持原文的语气和风格，使其听起来自然流畅。
            2. 考虑到这个翻译将用于生成语音，请确保翻译后的文本适合朗读。
            3. 保留原文的段落结构和格式。
            4. 如果有任何特定于视频的术语或参考，请适当调整以适应目标语言的观众。
            5. 保持任何时间标记或字幕编号的格式不变。

            以下是需要翻译的文本：

            {text}"""

            # 调用 OpenAI API
            response = openai.ChatCompletion.create(
                model="gpt-4",  # 使用 GPT-4 模型
                messages=[
                    {"role": "system", "content": "你是一个专业的视频翻译助手，擅长将YouTube视频的文本翻译成其他语言，并确保翻译结果适合用于语音生成。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=4000,
                top_p=0.95,
                frequency_penalty=0,
                presence_penalty=0,
                stop=None
            )

            # 提取翻译结果
            translated_text = response.choices[0].message['content'].strip()

            # 将翻译结果写入输出文件
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(translated_text)

            print(f"翻译完成。结果已保存到 {output_file}")
            return True

        except Exception as e:
            print(f"翻译过程中出错: {str(e)}")
            return False

def translate_file(input_file, output_file, target_lang='zh'):
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY 环境变量未设置")
    translator = TextTranslator(api_key)
    return translator.translate_file(input_file, output_file, target_lang)

if __name__ == "__main__":
    input_file = "data/test.txt"  # 替换为您的输入文件名
    output_file = "data/test_translated.txt"  # 替换为您想要的输出文件名
    target_lang = '中文'  # 目标语言，这里设置为中文

    api_key = os.environ.get('OPENAI_API_KEY')
    translator = TextTranslator(api_key)
    success = translator.translate_file(input_file, output_file, target_lang)

    if success:
        print(f"翻译成功完成。结果已保存到 {output_file}")
    else:
        print("翻译失败")
