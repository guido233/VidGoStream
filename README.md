# VidGoStream
VidGoStream automates the translation of YouTube videos, creating subtitles and making content accessible across multiple languages. It streamlines the process, allowing users to easily translate and distribute videos globally.

## 新功能：VTT文件翻译和文本输出

VidGoStream现在支持将VTT字幕文件从一种语言翻译成另一种语言，并同时输出翻译后的VTT文件和纯文本文件。这个新功能使用以下步骤：

1. 读取输入VTT文件
2. 自动检测源语言
3. 翻译文本内容为目标语言
4. 创建翻译后的VTT文件
5. 生成翻译后的纯文本文件

这个新功能具有以下特点：

- 自动语言检测：无需手动指定源语言，脚本会自动检测。
- 灵活的目标语言：可以指定任何目标语言，默认为中文（简体）。
- 智能翻译：只有当源语言和目标语言不同时才进行翻译，避免不必要的操作。
- 双重输出：同时生成VTT文件和纯文本文件，方便不同场景的使用。

使用这个功能，用户可以轻松地将字幕文件翻译成不同的语言，并获得易于阅读和编辑的纯文本版本，使视频内容更容易被全球观众理解和使用。
