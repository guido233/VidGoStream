import tkinter as tk
from tkinter import filedialog, messagebox
import threading
from .speech_synthesis import configure_speech_synthesizer, synthesize_speech

class MTTSGUI:
    def __init__(self, master):
        self.master = master
        master.title("语音合成")
        master.geometry("400x350")

        self.subscription = ""
        self.region = ""

        tk.Button(master, text="打开文本文件", command=self.open_file).pack(pady=10)

        self.text_input = tk.Text(master, height=10)
        self.text_input.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        self.speak_button = tk.Button(master, text="开始语音合成", command=self.speak)
        self.speak_button.pack(pady=10)

        self.status_label = tk.Label(master, text="")
        self.status_label.pack(pady=5)

    def open_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if file_path:
            with open(file_path, 'r', encoding='utf-8') as file:
                text = file.read()
                self.text_input.delete(1.0, tk.END)
                self.text_input.insert(tk.END, text)

    def speak(self):
        text = self.text_input.get(1.0, tk.END).strip()
        if text:
            self.speak_button.config(state=tk.DISABLED)
            self.status_label.config(text="正在合成语音...")
            output_file = filedialog.asksaveasfilename(defaultextension=".mp3", filetypes=[("MP3 files", "*.mp3")])
            if output_file:
                threading.Thread(target=self.synthesize_speech_thread, args=(text, output_file), daemon=True).start()
            else:
                self.speak_button.config(state=tk.NORMAL)
                self.status_label.config(text="")
        else:
            messagebox.showwarning("警告", "请输入要合成的文本。")

    def synthesize_speech_thread(self, text, output_file):
        speech_config = configure_speech_synthesizer(self.subscription, self.region)
        success = synthesize_speech(text, output_file, speech_config)
        self.master.after(0, self.update_gui, success, output_file)

    def update_gui(self, success, output_file):
        self.speak_button.config(state=tk.NORMAL)
        if success:
            messagebox.showinfo("成功", f"已成功合成语音并保存为MP3：\n{output_file}")
        else:
            messagebox.showerror("错误", "语音合成失败")
        self.status_label.config(text="")

def run_gui(subscription, region):
    root = tk.Tk()
    gui = MTTSGUI(root)
    gui.subscription = subscription
    gui.region = region
    root.mainloop()
