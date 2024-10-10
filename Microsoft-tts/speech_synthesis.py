import os
import azure.cognitiveservices.speech as speechsdk
import tkinter as tk
from tkinter import filedialog, messagebox
import threading

# Azure Speech 配置
speech_config = speechsdk.SpeechConfig(subscription=os.environ.get('SPEECH_KEY'), region=os.environ.get('SPEECH_REGION'))
speech_config.speech_synthesis_voice_name='zh-CN-XiaoxiaoNeural'
speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3)

def synthesize_speech(text, output_file):
    audio_config = speechsdk.audio.AudioOutputConfig(filename=output_file)
    speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
    
    speech_synthesis_result = speech_synthesizer.speak_text_async(text).get()

    if speech_synthesis_result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        root.after(0, lambda: messagebox.showinfo("成功", f"已成功合成语音并保存为MP3：\n{output_file}"))
    elif speech_synthesis_result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = speech_synthesis_result.cancellation_details
        root.after(0, lambda: messagebox.showerror("错误", f"语音合成取消: {cancellation_details.reason}"))
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            if cancellation_details.error_details:
                root.after(0, lambda: messagebox.showerror("错误详情", f"错误详情: {cancellation_details.error_details}\n请检查是否正确设置了语音资源密钥和区域值。"))

def open_file():
    file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
    if file_path:
        with open(file_path, 'r', encoding='utf-8') as file:
            text = file.read()
            text_input.delete(1.0, tk.END)
            text_input.insert(tk.END, text)

def speak():
    text = text_input.get(1.0, tk.END).strip()
    if text:
        speak_button.config(state=tk.DISABLED)
        status_label.config(text="正在合成语音...")
        output_file = filedialog.asksaveasfilename(defaultextension=".mp3", filetypes=[("MP3 files", "*.mp3")])
        if output_file:
            threading.Thread(target=synthesize_speech_thread, args=(text, output_file), daemon=True).start()
        else:
            speak_button.config(state=tk.NORMAL)
            status_label.config(text="")
    else:
        messagebox.showwarning("警告", "请输入要合成的文本。")

def synthesize_speech_thread(text, output_file):
    synthesize_speech(text, output_file)
    root.after(0, lambda: speak_button.config(state=tk.NORMAL))
    root.after(0, lambda: status_label.config(text=""))

# 创建主窗口
root = tk.Tk()
root.title("语音合成")
root.geometry("400x350")

# 创建并布置控件
tk.Button(root, text="打开文本文件", command=open_file).pack(pady=10)

text_input = tk.Text(root, height=10)
text_input.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

speak_button = tk.Button(root, text="开始语音合成", command=speak)
speak_button.pack(pady=10)

status_label = tk.Label(root, text="")
status_label.pack(pady=5)

# 运行主循环
root.mainloop()
