import asyncio
import cv2
import queue
import time
from typing import Generator
import os
from pathlib import Path
from datetime import datetime
import base64
import tempfile

def log_with_timestamp(message: str):
    """带时间戳的日志输出函数"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

class VideoStreamProcessor:
    """视频流处理器，负责处理视频流并提取音频"""
    
    def __init__(self, workspace_path: str):
        """
        初始化视频流处理器
        
        Args:
            workspace_path: 工作空间路径
        """
        self.workspace_path = Path(workspace_path)
        self.video_writer = None
        self.audio_queue = queue.Queue()
        self.is_processing = False
        self.fps = 30  # 默认帧率
        self.frame_count = 0
        self.width = 640  # 默认宽度
        self.height = 480  # 默认高度
        self.output_video_path = None
        
    def start_video_recording(self, output_path: str = None) -> str:
        """
        开始视频录制
        
        Args:
            output_path: 输出文件路径，如果为None则自动生成
            
        Returns:
            录制文件路径
        """
        # 如果已有视频写入器，则先释放它
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None
        
        if not output_path:
            timestamp = int(time.time())
            output_path = str(self.workspace_path / f"video_{timestamp}.mp4")
        
        self.output_video_path = output_path
        
        log_with_timestamp(f"开始视频录制，输出路径: {self.output_video_path}, 尺寸: {self.width}x{self.height}, FPS: {self.fps}")
        
        # 尝试多种编码器
        codecs_to_try = ['mp4v', 'XVID', 'MJPG', 'X264']
        self.video_writer = None
        
        for codec in codecs_to_try:
            fourcc = cv2.VideoWriter_fourcc(*codec)
            try:
                self.video_writer = cv2.VideoWriter(
                    self.output_video_path, 
                    fourcc, 
                    self.fps, 
                    (self.width, self.height)
                )
                
                if self.video_writer.isOpened():
                    log_with_timestamp(f"使用编码器 {codec} 创建视频写入器成功: {self.output_video_path}")
                    break
                else:
                    log_with_timestamp(f"使用编码器 {codec} 创建视频写入器失败")
                    if self.video_writer:
                        self.video_writer.release()
                    self.video_writer = None
            except Exception as e:
                log_with_timestamp(f"使用编码器 {codec} 时出错: {e}")
                self.video_writer = None
        
        # 如果所有编码器都失败，尝试使用H264
        if not self.video_writer or not self.video_writer.isOpened():
            try:
                fourcc = cv2.VideoWriter_fourcc(*'H264')
                self.video_writer = cv2.VideoWriter(
                    self.output_video_path, 
                    fourcc, 
                    self.fps, 
                    (self.width, self.height)
                )
                
                if self.video_writer.isOpened():
                    log_with_timestamp(f"使用编码器 H264 创建视频写入器成功: {self.output_video_path}")
                else:
                    log_with_timestamp(f"使用编码器 H264 也失败了")
            except Exception as e:
                log_with_timestamp(f"使用编码器 H264 时出错: {e}")
        
        if not self.video_writer or not self.video_writer.isOpened():
            log_with_timestamp(f"所有编码器都失败，视频写入器创建失败: {self.output_video_path}")
            # 创建一个基本的写入器作为回退
            try:
                self.video_writer = cv2.VideoWriter(
                    self.output_video_path,
                    cv2.VideoWriter_fourcc(*'mp4v'),
                    1,  # 使用1fps作为回退
                    (self.width, self.height)
                )
            except:
                log_with_timestamp(f"无法创建视频写入器")
        
        return output_path
    
    def add_frame_to_video(self, image_path: str, video_path: str = None):
        """
        将单个图像帧添加到视频中
        
        Args:
            image_path: 图像文件路径
            video_path: 视频文件路径（可选）
        """
        # 如果指定了视频路径，则更新输出路径
        if video_path:
            self.output_video_path = video_path
            
        # 确保视频写入器已初始化
        if self.video_writer is None:
            log_with_timestamp(f"初始化视频写入器，输出路径: {self.output_video_path}")
            self.start_video_recording(self.output_video_path)
            
        # 读取图像
        frame = cv2.imread(image_path)
        if frame is not None:
            log_with_timestamp(f"读取图像文件成功: {image_path}, 尺寸: {frame.shape}")
            # 调整图像大小以匹配视频尺寸
            frame_resized = cv2.resize(frame, (self.width, self.height))
            log_with_timestamp(f"调整图像尺寸为: {self.width}x{self.height}")
            
            # 写入视频帧
            if self.video_writer and self.video_writer.isOpened():
                self.video_writer.write(frame_resized)
                self.frame_count += 1
                log_with_timestamp(f"写入视频帧成功，当前帧数: {self.frame_count}")
            else:
                log_with_timestamp(f"视频写入器未打开，无法写入帧")
        else:
            log_with_timestamp(f"无法读取图像文件: {image_path}")
    
    def process_video_stream(self, video_stream):
        """
        处理视频流并同时保存到本地
        
        Args:
            video_stream: 视频流数据（URL、文件路径或OpenCV VideoCapture对象）
        """
        # 如果是URL或文件路径，使用OpenCV读取
        if isinstance(video_stream, str):
            cap = cv2.VideoCapture(video_stream)
        else:
            # 如果是OpenCV VideoCapture对象，直接使用
            cap = video_stream
        
        # 获取视频参数
        self.fps = int(cap.get(cv2.CAP_PROP_FPS)) or self.fps
        self.width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or self.width
        self.height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or self.height
        
        # 重新初始化视频写入器（如果已有输出路径）
        if self.output_video_path and self.video_writer:
            self.video_writer.release()
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            self.video_writer = cv2.VideoWriter(
                self.output_video_path, 
                fourcc, 
                self.fps, 
                (self.width, self.height)
            )
        
        self.is_processing = True
        
        # 读取并处理每一帧
        while self.is_processing:
            ret, frame = cap.read()
            if not ret:
                break
                
            # 写入视频帧
            self.video_writer.write(frame)
            self.frame_count += 1
            
            # 每隔一定帧数提取音频特征（模拟）
            if self.frame_count % self.fps == 0:  # 每秒处理一次
                # 这里应该是音频处理逻辑
                pass
        
        # 释放资源
        cap.release()
        if self.video_writer:
            self.video_writer.release()
    
    def process_video_stream_from_bytes(self, video_data: bytes, output_path: str):
        """
        处理从字节数据传入的视频流并保存到本地
        保留原始视频的音频部分
        
        Args:
            video_data: 视频流的字节数据
            output_path: 输出视频文件路径
        """
        # 将字节数据写入临时文件
        temp_video_path = str(self.workspace_path / "temp_video_stream.mp4")
        with open(temp_video_path, "wb") as f:
            f.write(video_data)
        
        # 使用ffmpeg直接复制原始视频和音频到输出文件
        # 这样可以保留原始视频中的音频信息
        import subprocess
        cmd = [
            'ffmpeg',
            '-i', temp_video_path,  # 输入临时文件
            '-c', 'copy',           # 复制所有流（视频+音频）
            output_path,             # 输出文件
            '-y'                    # 覆盖输出文件
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                log_with_timestamp(f"ffmpeg处理失败: {result.stderr}")
                # 如果ffmpeg失败，回退到原来的方法（仅视频）
                self.process_video_stream_from_bytes_fallback(temp_video_path, output_path)
        except Exception as e:
            log_with_timestamp(f"ffmpeg处理视频时出错: {e}")
            # 如果ffmpeg不可用，回退到原来的方法（仅视频）
            self.process_video_stream_from_bytes_fallback(temp_video_path, output_path)
        
        # 删除临时文件
        try:
            os.remove(temp_video_path)
        except:
            pass
    
    def process_video_stream_from_bytes_fallback(self, temp_video_path: str, output_path: str):
        """
        回退方法：处理从字节数据传入的视频流并保存到本地（仅视频）
        当ffmpeg不可用时使用此方法
        
        Args:
            temp_video_path: 临时视频文件路径
            output_path: 输出视频文件路径
        """
        # 使用OpenCV处理临时视频文件
        cap = cv2.VideoCapture(temp_video_path)
        
        # 获取视频参数
        self.fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30  # 默认30fps
        self.width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640  # 默认640
        self.height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480  # 默认480
        
        # 重新初始化视频写入器
        if self.video_writer:
            self.video_writer.release()
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.video_writer = cv2.VideoWriter(
            output_path, 
            fourcc, 
            self.fps, 
            (self.width, self.height)
        )
        
        self.is_processing = True
        self.frame_count = 0
        
        # 读取并处理每一帧
        while self.is_processing:
            ret, frame = cap.read()
            if not ret:
                break
                
            # 写入视频帧
            self.video_writer.write(frame)
            self.frame_count += 1
            
            # 每隔一定帧数提取音频特征（模拟）
            if self.frame_count % self.fps == 0:  # 每秒处理一次
                # 这里应该是音频处理逻辑
                pass
        
        # 释放资源
        cap.release()
        if self.video_writer:
            self.video_writer.release()
    
    def extract_audio_from_video(self, video_path: str, audio_path: str) -> bool:
        """
        从视频文件中提取音频
        
        Args:
            video_path: 视频文件路径
            audio_path: 音频输出文件路径
            
        Returns:
            是否成功提取音频
        """
        log_with_timestamp(f"开始提取音频，输入视频: {video_path}, 输出音频: {audio_path}")
        
        try:
            # 检查输入视频文件是否存在
            if not os.path.exists(video_path):
                log_with_timestamp(f"输入视频文件不存在: {video_path}")
                return False
            
            # 使用ffmpeg从视频中提取音频
            import subprocess
            cmd = [
                'ffmpeg', 
                '-i', video_path,
                '-q:a', '0',
                '-map', 'a',
                audio_path,
                '-y'  # 覆盖输出文件
            ]
            
            log_with_timestamp(f"执行ffmpeg命令: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                log_with_timestamp(f"音频提取成功，输出文件: {audio_path}")
                
                # 检查输出音频文件是否存在以及大小
                if os.path.exists(audio_path):
                    file_size = os.path.getsize(audio_path)
                    log_with_timestamp(f"输出音频文件大小: {file_size} 字节")
                    return True
                else:
                    log_with_timestamp(f"警告：ffmpeg执行成功但输出音频文件不存在: {audio_path}")
                    return False
            else:
                log_with_timestamp(f"ffmpeg执行失败，返回码: {result.returncode}")
                log_with_timestamp(f"ffmpeg错误输出: {result.stderr}")
                log_with_timestamp(f"ffmpeg标准输出: {result.stdout}")
                return False
        except Exception as e:
            log_with_timestamp(f"提取音频时出错: {e}")
            return False
    
    def extract_audio_frames(self, audio_path: str, chunk_duration: float = 1.0) -> Generator[bytes, None, None]:
        """
        从音频文件中提取音频帧
        
        Args:
            audio_path: 音频文件路径
            chunk_duration: 每个音频块的持续时间（秒）
            
        Yields:
            音频数据块
        """
        try:
            import wave
            with wave.open(audio_path, 'rb') as wav_file:
                # 获取音频参数
                framerate = wav_file.getframerate()
                channels = wav_file.getnchannels()
                sampwidth = wav_file.getsampwidth()
                
                # 计算每个块的帧数
                chunk_frames = int(framerate * chunk_duration)
                
                while True:
                    frames = wav_file.readframes(chunk_frames)
                    if not frames:
                        break
                    yield frames
        except Exception as e:
            log_with_timestamp(f"提取音频帧时出错: {e}")
            return
    
    def stop_processing(self):
        """停止处理并释放资源"""
        log_with_timestamp(f"停止视频处理，当前帧数: {self.frame_count}")
        self.is_processing = False
        if self.video_writer:
            # 确保所有帧都已写入
            self.video_writer.release()
            self.video_writer = None
            log_with_timestamp(f"视频写入器已释放，输出文件: {self.output_video_path}")
            
            # 检查输出文件是否存在以及大小
            if self.output_video_path and os.path.exists(self.output_video_path):
                file_size = os.path.getsize(self.output_video_path)
                log_with_timestamp(f"输出文件大小: {file_size} 字节")
                
                # 如果文件太小，可能是没有写入数据
                if file_size < 1000:  # 小于1KB
                    log_with_timestamp("警告：输出文件非常小，可能没有正确写入视频数据")
            else:
                log_with_timestamp("输出文件不存在")