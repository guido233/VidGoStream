import os
import sys
import re
import json
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
from openai import OpenAI


@dataclass
class SrtItem:
    id: int
    timecode: str
    text: str


class TextTranslator:
    def __init__(self, api_key, model='glm-4', base_url='https://open.bigmodel.cn/api/paas/v4/'):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    # ---------------------------
    # 通用翻译（TXT）
    # ---------------------------
    def translate_file(self, input_file, output_file, target_lang='zh') -> bool:
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                text = f.read()

            prompt = f"""请将以下文本翻译成{target_lang}。
要求：
1) 保持原文语气风格，自然流畅。
2) 适合朗读（将用于TTS）。
3) 保留原文段落结构与格式（换行尽量保留）。
只输出译文，不要解释。

文本如下：
{text}
"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system",
                     "content": "你是专业翻译助手，输出应自然、适合朗读，且严格按要求只输出译文。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                top_p=0.95,
                max_tokens=4000,
            )

            translated_text = response.choices[0].message.content.strip()
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(translated_text)

            print(f"翻译完成。结果已保存到 {output_file}")
            return True

        except Exception as e:
            print(f"翻译过程中出错: {str(e)}")
            return False

    # ---------------------------
    # SRT 翻译：核心实现
    # ---------------------------
    def translate_srt_file(self, input_file, output_file, target_lang='zh') -> bool:
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                srt_content = f.read()

            items = self._parse_srt(srt_content)
            if not items:
                print("警告: 无法解析SRT文件格式，尝试简单文本翻译")
                return self.translate_file(input_file, output_file, target_lang)

            # 预处理：保护标签/控制符
            protected_texts: Dict[int, Tuple[str, Dict[str, str]]] = {}
            for it in items:
                protected, mapping = self._protect_markup(it.text)
                protected_texts[it.id] = (protected, mapping)

            # 按批翻译（只翻译需要翻译的条目）
            id2translation: Dict[int, str] = {}

            translatable = []
            for it in items:
                protected, _ = protected_texts[it.id]
                if self._should_translate(protected):
                    translatable.append({"id": it.id, "text": protected})
                else:
                    # 不翻译的直接原样回填（后面仍会 restore_tags）
                    id2translation[it.id] = protected

            for batch in self._batch_items(translatable, max_chars=6500, max_n=60):
                batch_map = self._translate_batch_with_retry(batch, target_lang=target_lang)
                id2translation.update(batch_map)

            # 回填并恢复标签
            out_lines: List[str] = []
            for it in items:
                protected, mapping = protected_texts[it.id]
                translated_protected = id2translation.get(it.id, protected)
                restored = self._restore_markup(translated_protected, mapping)

                # 可选：这里做一层“字幕友好后处理”（断行/标点等）
                restored = self._postprocess_subtitle(restored)

                out_lines.append(str(it.id))
                out_lines.append(it.timecode)
                out_lines.append(restored)
                out_lines.append("")

            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("\n".join(out_lines).rstrip() + "\n")

            print(f"SRT翻译完成。结果已保存到 {output_file}")
            return True

        except Exception as e:
            print(f"翻译SRT文件过程中出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    # ---------------------------
    # SRT 解析（稳健）
    # ---------------------------
    def _parse_srt(self, content: str) -> List[SrtItem]:
        blocks = re.split(r'\n\s*\n', content.strip())
        items: List[SrtItem] = []

        for block in blocks:
            lines = [ln.rstrip("\r") for ln in block.strip().splitlines()]
            if len(lines) < 3:
                continue

            idx = lines[0].strip()
            if not idx.isdigit():
                continue

            timecode = lines[1].strip()
            if '-->' not in timecode:
                continue

            text = "\n".join(lines[2:]).strip()
            items.append(SrtItem(id=int(idx), timecode=timecode, text=text))

        return items

    # ---------------------------
    # 是否需要翻译：纯提示/空白等不翻译
    # ---------------------------
    def _should_translate(self, text: str) -> bool:
        t = text.strip()
        if not t:
            return False

        # 只包含提示符号/舞台提示：如 [Music], (laughs), [Applause]
        # 你如果想把它们也翻译掉，可以把这里改成 return True
        if re.fullmatch(r'[\[\(].*?[\]\)]', t) and len(t) <= 40:
            return False

        # 只有音乐符号等
        if re.fullmatch(r'[♪♫\s]+', t):
            return False

        return True

    # ---------------------------
    # 保护/恢复标签：避免模型改掉 <i>...</i>、{\an8} 之类
    # ---------------------------
    def _protect_markup(self, text: str) -> Tuple[str, Dict[str, str]]:
        mapping: Dict[str, str] = {}
        counter = 0

        def repl(m: re.Match) -> str:
            nonlocal counter
            token = f"__TAG{counter}__"
            mapping[token] = m.group(0)
            counter += 1
            return token

        # HTML tags: <i> </i> <b> <font ...> 等
        text = re.sub(r'</?[^>]+?>', repl, text)

        # 常见 ASS/样式控制：{\an8} 这种
        text = re.sub(r'\{\\.*?\}', repl, text)

        # 你如果还有别的需要保护的模式，可以继续加
        return text, mapping

    def _restore_markup(self, text: str, mapping: Dict[str, str]) -> str:
        # 先按 token 长度倒序替换，避免 __TAG1__ 被 __TAG10__ 误伤
        for token in sorted(mapping.keys(), key=len, reverse=True):
            text = text.replace(token, mapping[token])
        return text

    # ---------------------------
    # 批处理
    # ---------------------------
    def _batch_items(self, items: List[Dict], max_chars: int = 6500, max_n: int = 60):
        batch = []
        total = 0
        for it in items:
            tlen = len(it["text"])
            if batch and (len(batch) >= max_n or total + tlen > max_chars):
                yield batch
                batch, total = [], 0
            batch.append(it)
            total += tlen
        if batch:
            yield batch

    # ---------------------------
    # 批量翻译（JSON 映射 + 缺失重试）
    # ---------------------------
    def _translate_batch_with_retry(self, batch: List[Dict], target_lang: str) -> Dict[int, str]:
        # 先批量一次
        result = self._translate_batch(batch, target_lang)

        need_ids = {x["id"] for x in batch}
        got_ids = set(result.keys())
        missing = list(need_ids - got_ids)

        # 缺失的：单条重试，最大重试 1 次（你也可以加大）
        for mid in missing:
            single = next(x for x in batch if x["id"] == mid)
            single_res = self._translate_batch([single], target_lang)
            if mid in single_res:
                result[mid] = single_res[mid]
            else:
                # 仍失败：降级为原文
                result[mid] = single["text"]

        return result

    def _translate_batch(self, batch: List[Dict], target_lang: str) -> Dict[int, str]:
        # 构造 JSON 输入（给模型看清结构）
        payload = {
            "target_lang": target_lang,
            "items": batch
        }
        payload_json = json.dumps(payload, ensure_ascii=False)

        system = (
            "你是专业字幕翻译器。"
            "你必须严格按输入 items 的 id 一一返回翻译结果。"
            "不要新增、删除、合并、拆分条目；不要改变 id。"
            "保留 __TAG0__ 这类占位符原样不变。"
            "输出必须是严格 JSON 数组："
            '[{"id": 1, "translation": "..."}, ...]。'
            "不要输出任何额外文字。"
        )

        user = f"""请把 items[].text 翻译成 {target_lang}。
要求：
- 译文自然口语化，适合朗读（TTS）。
- 不要改动任何 __TAGn__ 占位符。
- 只输出 JSON 数组，不要解释。

输入JSON如下：
{payload_json}
"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            temperature=0.2,
            top_p=0.95,
            max_tokens=4000,
        )

        raw = response.choices[0].message.content.strip()
        arr = self._safe_parse_json_array(raw)

        out: Dict[int, str] = {}
        if isinstance(arr, list):
            for obj in arr:
                if not isinstance(obj, dict):
                    continue
                if "id" not in obj or "translation" not in obj:
                    continue
                try:
                    sid = int(obj["id"])
                except Exception:
                    continue
                out[sid] = str(obj["translation"]).strip()

        return out

    # ---------------------------
    # JSON 解析容错：从模型输出里抠出 [...] 并 loads
    # ---------------------------
    def _safe_parse_json_array(self, text: str):
        # 直接尝试
        try:
            return json.loads(text)
        except Exception:
            pass

        # 尝试截取第一个 [...] 块
        m = re.search(r'\[\s*\{.*\}\s*\]', text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass

        # 再退一步：常见是 ```json ... ``` 包裹
        m = re.search(r'```(?:json)?\s*(\[[\s\S]*?\])\s*```', text, re.IGNORECASE)
        if m:
            try:
                return json.loads(m.group(1))
            except Exception:
                pass

        return None

    # ---------------------------
    # 字幕后处理（可选）
    # ---------------------------
    def _postprocess_subtitle(self, text: str) -> str:
        # 这里先做最小干预：去掉多余空白
        # 你想做“每行最多N字、最多两行”的断行，也可以在这里扩展
        lines = [ln.strip() for ln in text.splitlines()]
        lines = [ln for ln in lines if ln != ""]
        return "\n".join(lines).strip()


def translate_file(input_file, output_file, target_lang='zh'):
    api_key = os.environ.get('ZHIPU_API_KEY')
    if not api_key:
        raise ValueError("ZHIPU_API_KEY 环境变量未设置")
    translator = TextTranslator(api_key)
    return translator.translate_file(input_file, output_file, target_lang)


if __name__ == "__main__":
    api_key = os.environ.get('ZHIPU_API_KEY')
    if not api_key:
        print("请设置ZHIPU_API_KEY环境变量")
        sys.exit(1)

    translator = TextTranslator(api_key)

    print("=" * 50)
    print("测试1: 翻译TXT文件")
    print("=" * 50)
    input_txt_file = "data/test.txt"
    output_txt_file = "data/test_translated.txt"
    target_lang = '中文'

    if os.path.exists(input_txt_file):
        success = translator.translate_file(input_txt_file, output_txt_file, target_lang=target_lang)
        print("✓ TXT翻译成功完成。\n" if success else "✗ TXT翻译失败\n")
    else:
        print(f"⚠ 输入文件不存在: {input_txt_file}\n")

    print("=" * 50)
    print("测试2: 翻译SRT文件")
    print("=" * 50)
    input_srt_file = "data/test.srt"
    output_srt_file = "data/test_translated.srt"

    if os.path.exists(input_srt_file):
        success = translator.translate_srt_file(input_srt_file, output_srt_file, target_lang=target_lang)
        print("✓ SRT翻译成功完成。\n" if success else "✗ SRT翻译失败\n")
    else:
        print(f"⚠ 输入文件不存在: {input_srt_file}\n")

    print("=" * 50)
    print("测试完成")
    print("=" * 50)
