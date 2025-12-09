import os
import csv
import yt_dlp
from typing import List, Dict

class YouTubeDownloader:
    def __init__(self):
        self.cookies_file = os.path.join('config', 'cookies.txt')
        if not os.path.exists(self.cookies_file):
            raise FileNotFoundError(f"Cookie文件不存在: {self.cookies_file}")

    def read_video_list(self, csv_path: str) -> List[Dict[str, str]]:
        """从CSV文件读取视频信息列表"""
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"CSV文件不存在: {csv_path}")

        videos = []
        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                print(f"CSV表头: {reader.fieldnames}")
                for row in reader:
                    print(f"读取行: {row}")
                    udi_key = next((k for k in row.keys() if k.lower().endswith('udi')), None)
                    if not udi_key or 'URL' not in row:
                        print(f"警告: 缺少必要的列 (UDI 或 URL)，跳过行: {row}")
                        continue
                    
                    if row.get(udi_key) and row.get('URL'):
                        videos.append({
                            'udi': row[udi_key],
                            'url': row['URL']
                        })
                        print(f"添加视频: UDI={row[udi_key]}, URL={row['URL']}")
        except Exception as e:
            print(f"读取CSV文件时出错: {str(e)}")
            return []
        
        print(f"总共读取到 {len(videos)} 个视频")
        return videos

    def download_video(self, video: Dict[str, str], need_audio: bool = True) -> bool:
        """下载单个视频"""
        try:
            output_dir = os.path.join('data')
            os.makedirs(output_dir, exist_ok=True)
            
            # 下载视频
            video_opts = {
                'format': 'bv*+ba/b',  # 优先分离轨合并，回退为单一最佳文件
                'outtmpl': os.path.join(output_dir, f"{video['udi']}.%(ext)s"),
                'cookiefile': self.cookies_file,
                'merge_output_format': 'mp4',
                'noplaylist': True,
                'geo_bypass': True,
                'ignoreerrors': True,
                'quiet': False,
                'no_warnings': False,
                'extract_flat': False,
            }

            with yt_dlp.YoutubeDL(video_opts) as ydl:
                ydl.download([video['url']])

            # 如果需要音频版本，单独下载音频
            if need_audio:
                audio_opts = {
                    'format': 'bestaudio/best',
                    'outtmpl': os.path.join(output_dir, f"{video['udi']}.%(ext)s"),
                    'cookiefile': self.cookies_file,
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                    'noplaylist': True,
                    'geo_bypass': True,
                    'ignoreerrors': True,
                    'quiet': False,
                    'no_warnings': False,
                    'extract_flat': False,
                }

                with yt_dlp.YoutubeDL(audio_opts) as ydl:
                    ydl.download([video['url']])

            return True
            
        except Exception as e:
            print(f"下载视频时出错 {video['url']}: {str(e)}")
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

        for i, video in enumerate(videos, 1):
            print(f"正在下载 {i}/{total}: {video['udi']} ({video['url']})")
            if self.download_video(video, need_audio):
                success += 1
            else:
                failed.append(f"{video['udi']} - {video['url']}")

        print(f"\n下载完成！成功: {success}/{total}")
        if failed:
            print("以下视频��载失败:")
            for item in failed:
                print(item)

def main():
    try:
        downloader = YouTubeDownloader()
        csv_path = os.path.join('config', 'vdc.csv')
        downloader.batch_download(csv_path, need_audio=True)
    except FileNotFoundError as e:
        print(f"错误: {str(e)}")
    except Exception as e:
        print(f"发生错误: {str(e)}")

if __name__ == "__main__":
    main() 