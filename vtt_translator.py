import webvtt
from googletrans import Translator

def merge_captions(captions):
    merged = []
    current_text = ""
    current_start = None
    current_end = None

    for caption in captions:
        if not caption.text.strip():
            continue
        
        if current_text and caption.text not in current_text:
            merged.append((current_start, current_end, current_text))
            current_text = caption.text
            current_start = caption.start
            current_end = caption.end
        else:
            if not current_text:
                current_start = caption.start
            current_text += " " + caption.text.strip()
            current_end = caption.end

    if current_text:
        merged.append((current_start, current_end, current_text))

    return merged

def translate_vtt(input_file, output_vtt_file, output_txt_file, target_lang='zh-cn'):
    translator = Translator()
    captions = webvtt.read(input_file)
    translated_captions = webvtt.WebVTT()
    source_lang = None
    full_text = []

    merged_captions = merge_captions(captions)

    for start, end, text in merged_captions:
        if source_lang is None:
            source_lang = translator.detect(text).lang
            print(f"检测到源语言: {source_lang}")

        if source_lang != target_lang:
            translated_text = translator.translate(text, src=source_lang, dest=target_lang).text
        else:
            translated_text = text
        
        translated_captions.captions.append(webvtt.Caption(
            start=start,
            end=end,
            text=translated_text
        ))

        full_text.append(translated_text)

    translated_captions.save(output_vtt_file)

    with open(output_txt_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(full_text))

    print(f"处理完成。翻译后的VTT文件已保存为 {output_vtt_file}")
    print(f"翻译后的文本文件已保存为 {output_txt_file}")

if __name__ == "__main__":
    input_file = "input_jp.vtt"
    output_vtt_file = "output_translated.vtt"
    output_txt_file = "output_translated.txt"
    target_lang = 'zh-cn'
    translate_vtt(input_file, output_vtt_file, output_txt_file, target_lang)
