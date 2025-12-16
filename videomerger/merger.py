import os
import subprocess
from typing import Optional


class VideoMerger:
    """视频和音频合并器"""
    
    def __init__(self):
        """初始化视频合并器"""
        self._check_ffmpeg()
    
    def _check_ffmpeg(self) -> bool:
        """
        检查ffmpeg是否可用
        
        Returns:
            bool: ffmpeg是否可用
        """
        try:
            subprocess.run(
                ["ffmpeg", "-version"],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            return False
    
    def merge(self, video_path: str, audio_path: str, output_path: str, 
              video_codec: str = "copy", audio_codec: str = "aac",
              use_shortest: bool = True) -> bool:
        """
        使用ffmpeg将视频和音频合并，生成新的视频文件
        
        Args:
            video_path: 输入视频文件路径
            audio_path: 输入音频文件路径
            output_path: 输出视频文件路径
            video_codec: 视频编码方式，默认"copy"（直接复制，不重新编码）
            audio_codec: 音频编码方式，默认"aac"
            use_shortest: 是否以最短的流为准，默认True
            
        Returns:
            bool: 是否成功
        """
        # 验证输入文件
        if not os.path.exists(video_path):
            print(f"错误: 视频文件不存在: {video_path}")
            return False
        
        if not os.path.exists(audio_path):
            print(f"错误: 音频文件不存在: {audio_path}")
            return False
        
        # 检查ffmpeg是否可用
        if not self._check_ffmpeg():
            print("错误: 未找到ffmpeg，请确保已安装ffmpeg")
            return False
        
        try:
            # 构建ffmpeg命令
            cmd = [
                "ffmpeg", "-y",  # -y 表示覆盖输出文件
                "-i", video_path,
                "-i", audio_path,
                "-c:v", video_codec,  # 视频编码
                "-c:a", audio_codec,   # 音频编码
                "-map", "0:v:0",       # 使用视频文件的视频流
                "-map", "1:a:0",       # 使用音频文件的音频流
            ]
            
            if use_shortest:
                cmd.append("-shortest")  # 以最短的流为准
            
            cmd.append(output_path)
            
            print(f"正在合并视频和音频...")
            print(f"  视频: {video_path}")
            print(f"  音频: {audio_path}")
            print(f"  输出: {output_path}")
            
            result = subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            print(f"✓ 视频和音频合并成功: {output_path}")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"✗ 合并失败: {e}")
            if e.stderr:
                # 只显示关键错误信息，避免输出过多
                error_lines = e.stderr.split('\n')
                for line in error_lines[-10:]:  # 只显示最后10行
                    if line.strip() and ('error' in line.lower() or 'failed' in line.lower()):
                        print(f"  错误详情: {line}")
            return False
        except Exception as e:
            print(f"✗ 合并过程中出错: {str(e)}")
            return False
    
    def merge_with_options(self, video_path: str, audio_path: str, output_path: str,
                          options: Optional[dict] = None) -> bool:
        """
        使用自定义选项合并视频和音频
        
        Args:
            video_path: 输入视频文件路径
            audio_path: 输入音频文件路径
            output_path: 输出视频文件路径
            options: 自定义选项字典，可包含：
                - video_codec: 视频编码（默认: "copy"）
                - audio_codec: 音频编码（默认: "aac"）
                - use_shortest: 是否以最短流为准（默认: True）
                - extra_args: 额外的ffmpeg参数列表
        
        Returns:
            bool: 是否成功
        """
        if options is None:
            options = {}
        
        video_codec = options.get("video_codec", "copy")
        audio_codec = options.get("audio_codec", "aac")
        use_shortest = options.get("use_shortest", True)
        extra_args = options.get("extra_args", [])
        
        # 验证输入文件
        if not os.path.exists(video_path):
            print(f"错误: 视频文件不存在: {video_path}")
            return False
        
        if not os.path.exists(audio_path):
            print(f"错误: 音频文件不存在: {audio_path}")
            return False
        
        # 检查ffmpeg是否可用
        if not self._check_ffmpeg():
            print("错误: 未找到ffmpeg，请确保已安装ffmpeg")
            return False
        
        try:
            # 构建ffmpeg命令
            cmd = [
                "ffmpeg", "-y",
                "-i", video_path,
                "-i", audio_path,
                "-c:v", video_codec,
                "-c:a", audio_codec,
                "-map", "0:v:0",
                "-map", "1:a:0",
            ]
            
            if use_shortest:
                cmd.append("-shortest")
            
            # 添加额外参数
            if extra_args:
                cmd.extend(extra_args)
            
            cmd.append(output_path)
            
            print(f"正在合并视频和音频（使用自定义选项）...")
            print(f"  视频: {video_path}")
            print(f"  音频: {audio_path}")
            print(f"  输出: {output_path}")
            
            result = subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            print(f"✓ 视频和音频合并成功: {output_path}")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"✗ 合并失败: {e}")
            if e.stderr:
                error_lines = e.stderr.split('\n')
                for line in error_lines[-10:]:
                    if line.strip() and ('error' in line.lower() or 'failed' in line.lower()):
                        print(f"  错误详情: {line}")
            return False
        except Exception as e:
            print(f"✗ 合并过程中出错: {str(e)}")
            return False

