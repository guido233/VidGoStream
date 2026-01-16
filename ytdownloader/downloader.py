import os
import csv
import glob
import yt_dlp
import subprocess
from typing import List, Dict
import sys

# Add project root to sys.path to import path_manager
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.path_manager import PathManager

class YouTubeDownloader:
    def __init__(self):
        # 使用相对路径，兼容性更好
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.cookies_file = os.path.join(base_dir, 'config', 'cookies.txt')
        self.pm = PathManager()
        
    def read_video_list(self, csv_path: str) -> List[Dict[str, str]]:
        """从CSV文件读取视频信息列表"""
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"CSV文件不存在: {csv_path}")

        videos = []
        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                # print(f"CSV表头: {reader.fieldnames}")
                for row in reader:
                    udi_key = next((k for k in row.keys() if k.lower().endswith('udi')), None)
                    if not udi_key or 'URL' not in row:
                        continue
                    
                    if row.get(udi_key) and row.get('URL'):
                        # 核心修复: 清洗URL中的转义反斜杠
                        raw_url = row['URL']
                        clean_url = raw_url.replace('\\', '')
                        
                        videos.append({
                            'udi': row[udi_key],
                            'url': clean_url
                        })
                        # print(f"读取视频: {row[udi_key]}")
        except Exception as e:
            print(f"读取CSV文件时出错: {str(e)}")
            return []
        
        print(f"总共读取到 {len(videos)} 个视频")
        return videos

    def _extract_audio(self, video_path: str, audio_path: str) -> bool:
        """调用 ffmpeg 本地提取音频，比重新下载快得多"""
        try:
            cmd = [
                "ffmpeg", "-y",
                "-i", video_path,
                "-vn",             # 禁用视频流
                "-acodec", "libmp3lame",
                "-q:a", "2",       # 高质量 VBR
                audio_path
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception as e:
            print(f"音频提取失败: {e}")
            return False

    def _remove_audio_track(self, video_path: str) -> bool:
        """移除视频文件中的音频轨，生成纯视频文件"""
        try:
            tmp_path = video_path + ".tmp.mp4"
            cmd = [
                "ffmpeg", "-y",
                "-i", video_path,
                "-c", "copy",
                "-an",             # 移除音频
                tmp_path
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # 覆盖原文件
            os.replace(tmp_path, video_path)
            return True
        except Exception as e:
            print(f"移除音频轨失败: {e}")
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            return False

    def _consolidate_subtitles(self, udi: str, detected_lang: str) -> None:
        """合并/清理字幕文件，只保留一份最佳字幕，重命名为 {udi}.srt (存放在 intermediate 目录)"""
        project_dir = self.pm.get_project_dir(udi)
        final_path = self.pm.get_path('srt', udi)
        
        # 查找所有相关字幕 (yt-dlp 默认下载在项目根目录)
        # 注意: yt-dlp 可能会生成 udi.Code.srt
        pattern = os.path.join(project_dir, f"{udi}.*.srt")
        candidates = glob.glob(pattern)
        
        # 如果final_path已存在，也纳入考量（为了重新评估或去重）
        if os.path.exists(final_path):
            candidates.append(final_path)
            
        candidates = list(set(candidates))
        if not candidates:
            return

        # 如果只有1个文件，且就是目标文件，无需操作
        if len(candidates) == 1 and candidates[0] == final_path:
            return

        # 选出最佳字幕
        best_candidate = None
        
        # 1. 优先找包含 'orig' 的
        orig_candidates = [f for f in candidates if 'orig' in os.path.basename(f).lower()]
        if orig_candidates:
            best_candidate = orig_candidates[0]
        
        # 2. 其次找匹配 detected_lang 的
        elif detected_lang:
            lang_candidates = [f for f in candidates if detected_lang in os.path.basename(f)]
            if lang_candidates:
                best_candidate = lang_candidates[0]
        
        # 3. 兜底：选文件名最短的（通常是 .ja.srt 优于 .ja-JP.srt）
        if not best_candidate:
            candidates.sort(key=lambda x: len(os.path.basename(x)))
            best_candidate = candidates[0]
            
        # 执行重命名和清理
        try:
            print(f"🧹 字幕合并: 保留 {os.path.basename(best_candidate)}")
            
            # 如果最佳候选不是目标文件，进行重命名
            if best_candidate != final_path:
                if os.path.exists(final_path):
                    os.remove(final_path) # 移除旧的目标文件以免冲突
                os.rename(best_candidate, final_path)
            
            # 删除其他多余文件
            for f in candidates:
                if f != best_candidate and f != final_path:
                    try:
                        os.remove(f)
                    except OSError:
                        pass
                        
        except Exception as e:
            print(f"⚠ 字幕合并出错: {e}")

    def download_video(self, video: Dict[str, str], need_audio: bool = True) -> bool:
        """下载单个视频（智能跳过、本地提取音频、生成纯视频、下载字幕）"""
        try:
            # 获取项目目录和路径
            project_dir = self.pm.get_project_dir(video['udi'])
            os.makedirs(project_dir, exist_ok=True)
            
            video_path = os.path.join(project_dir, f"{video['udi']}.mp4")
            audio_path = os.path.join(project_dir, f"{video['udi']}.mp3")
            # 最终期望的字幕文件 (在 intermediate 目录)
            final_sub_path = self.pm.get_path('srt', video['udi'])

            # 1. 检查是否存在 (Video & Audio & Subtitles)
            video_exists = os.path.exists(video_path)
            audio_exists = os.path.exists(audio_path)
            # 检查是否有标准命名的srt字幕
            subs_exists = os.path.exists(final_sub_path)
            
            # 如果没找到标准字幕，检查是否有任何相关字幕(可能是上次没合并成功)
            if not subs_exists:
                pattern = os.path.join(project_dir, f"{video['udi']}*.srt")
                if len(glob.glob(pattern)) > 0:
                     # 或者是未合并的状态，尝试合并一下
                     print(f"Found unmerged subtitles for {video['udi']}, consolidating...")
                     self._consolidate_subtitles(video['udi'], None)
                     # 再次检查
                     subs_exists = os.path.exists(final_sub_path)

            # 如果所有需要的文件都存在，则跳过
            if video_exists and (not need_audio or audio_exists) and subs_exists:
                print(f"✓ 所有文件已存在，跳过任务: {video['udi']}")
                return True

            # 2. 如果视频不存在，或者字幕缺失，我们需要获取信息来决定下载策略
            # 为了优先下载原语言字幕，先获取视频元数据
            detected_lang = None
            if not video_exists or not subs_exists:
                print(f"🔍 正在解析视频信息以确定字幕语言: {video['udi']} ...")
                temp_opts = {
                    'quiet': True, 
                    'no_warnings': True,
                    'noplaylist': True,
                }
                if os.path.exists(self.cookies_file):
                    temp_opts['cookiefile'] = self.cookies_file
                
                try:
                    with yt_dlp.YoutubeDL(temp_opts) as ydl_temp:
                        info = ydl_temp.extract_info(video['url'], download=False)
                        detected_lang = info.get('language')
                        if detected_lang:
                            print(f"✓ 检测到视频语言: {detected_lang}")
                        else:
                            print(f"⚠ 未能检测到语言元数据，将尝试下载所有字幕")
                except Exception as e:
                    print(f"获取元数据失败，将尝试默认下载: {e}")

            # 配置 yt-dlp 选项
            video_opts = {
                'format': 'bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4] / bv*+ba/b',
                'outtmpl': os.path.join(project_dir, f"{video['udi']}.%(ext)s"),
                'merge_output_format': 'mp4',
                'noplaylist': True,
                'geo_bypass': True,
                'quiet': False,
                'no_warnings': True,
                
                # 字幕相关配置
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitlesformat': 'srt',
                'postprocessors': [
                    {'key': 'FFmpegSubtitlesConvertor', 'format': 'srt'}
                ],
            }

            # 设置字幕语言优先级
            if detected_lang:
                # 优先下载检测到的语言，使用正则匹配 (例如 'en' 匹配 'en-US')
                video_opts['subtitleslangs'] = [f"{detected_lang}.*", 'orig'] 
            else:
                # 无法检测时，下载所有以确保包含原语言
                video_opts['subtitleslangs'] = ['all']
            
            if os.path.exists(self.cookies_file):
                video_opts['cookiefile'] = self.cookies_file

            # 3. 执行下载
            try:
                if not video_exists:
                    print(f"⬇️ 正在下载视频及字幕 ({detected_lang or 'ALL'}): {video['udi']} ...")
                    with yt_dlp.YoutubeDL(video_opts) as ydl:
                        ydl.download([video['url']])
                
                elif not subs_exists:
                    print(f"⬇️ 视频已存在，正在补充下载字幕 ({detected_lang or 'ALL'}): {video['udi']} ...")
                    # 开启 skip_download 只下字幕
                    opts_subs_only = video_opts.copy()
                    opts_subs_only['skip_download'] = True
                    with yt_dlp.YoutubeDL(opts_subs_only) as ydl:
                        ydl.download([video['url']])
                
                # 下载完成后，合并/清理字幕文件
                self._consolidate_subtitles(video['udi'], detected_lang)

            except Exception as dl_err:
                 print(f"下载过程出错: {dl_err}")
                 return False

            # 再次确认视频是否就位
            if not os.path.exists(video_path):
                 print(f"❌ 视频下载失败或文件未生成: {video['udi']}")
                 return False

            # 4. 如果需要音频且音频不存在，从本地视频提取
            if need_audio and not os.path.exists(audio_path):
                print(f"🎵 正在从本地提取音频: {video['udi']} ...")
                if self._extract_audio(video_path, audio_path):
                    print(f"✓ 音频提取成功")
                else:
                    return False
            
            # 5. 生成纯视频 (仅在刚刚下载了新视频时执行，或者强制检查？)
            # 由于 video_exists 是初始状态，如果是新下载(not video_exists)，肯定有声音
            if not video_exists: 
                print(f"✂️ 正在移除视频原声以生成纯视频...")
                if self._remove_audio_track(video_path):
                    print(f"✓ 纯视频生成成功")
                else:
                    print(f"⚠ 无法移除视频原声")

            return True
            
        except Exception as e:
            print(f"处理出错 {video['url']}: {str(e)}")
            return False

    def batch_download(self, csv_path: str, need_audio: bool = True) -> None:
        """批量下载视频"""
        videos = self.read_video_list(csv_path)
        if not videos:
            print("没有找到要下载的视频")
            return

        total = len(videos)
        success = 0
        failed = []

        print(f"开始处理 {total} 个任务...")
        
        for i, video in enumerate(videos, 1):
            print(f"\n--- 任务 {i}/{total} : {video['udi']} ---")
            if self.download_video(video, need_audio):
                success += 1
            else:
                failed.append(f"{video['udi']} ({video['url']})")

        print(f"\n==================================================")
        print(f"全部完成！成功: {success}/{total}")
        if failed:
            print("以下任务失败:")
            for item in failed:
                print(f" - {item}")
        print(f"==================================================")

def main():
    try:
        downloader = YouTubeDownloader()
        # 修正：使用相对路径查找 CSV
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        csv_path = os.path.join(base_dir, 'config', 'vdc.csv')
        
        downloader.batch_download(csv_path, need_audio=True)
    except Exception as e:
        print(f"发生错误: {str(e)}")

if __name__ == "__main__":
    main()