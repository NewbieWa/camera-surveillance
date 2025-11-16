import cv2
import os
from pathlib import Path
from typing import List, Tuple

class FrameExtractor:
    """图像帧提取器，用于从视频中提取特定时间点的帧"""
    
    def __init__(self, video_path: str):
        """
        初始化帧提取器
        
        Args:
            video_path: 视频文件路径
        """
        self.video_path = video_path
        self.cap = cv2.VideoCapture(video_path)
        self.fps = int(self.cap.get(cv2.CAP_PROP_FPS))
        
    def extract_frames_around_timestamp(self, timestamp: float, 
                                       before_seconds: float = 2.0, 
                                       after_seconds: float = 4.0, 
                                       interval_seconds: float = 1.0) -> List[Tuple[float, str]]:
        """
        在指定时间戳前后提取帧
        
        Args:
            timestamp: 中心时间戳
            before_seconds: 之前秒数
            after_seconds: 之后秒数
            interval_seconds: 间隔秒数
            
        Returns:
            帧时间戳和文件路径的列表
        """
        frame_paths = []
        
        # 计算开始和结束帧
        start_time = max(0, timestamp - before_seconds)
        end_time = timestamp + after_seconds
        
        # 计算帧索引范围
        start_frame = int(start_time * self.fps)
        end_frame = int(end_time * self.fps)
        interval_frames = int(interval_seconds * self.fps)
        
        # 提取帧
        for frame_idx in range(start_frame, end_frame + 1, interval_frames):
            # 设置视频位置
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            
            # 读取帧
            ret, frame = self.cap.read()
            if ret:
                # 计算实际时间戳
                actual_timestamp = frame_idx / self.fps
                
                # 保存帧到文件
                frame_filename = f"frame_{actual_timestamp:.2f}.jpg"
                frame_path = os.path.join(os.path.dirname(self.video_path), frame_filename)
                cv2.imwrite(frame_path, frame)
                
                frame_paths.append((actual_timestamp, frame_path))
        
        return frame_paths
    
    def extract_frames_for_audio_segment(self, segment_start: float, segment_end: float,
                                       before_seconds: float = 2.0, 
                                       after_seconds: float = 4.0, 
                                       interval_seconds: float = 1.0) -> List[Tuple[float, str]]:
        """
        为音频片段提取帧（解决时间点问题的关键方法）
        根据音频片段的时间范围，在片段结束后提取帧
        
        Args:
            segment_start: 音频片段开始时间
            segment_end: 音频片段结束时间
            before_seconds: 之前秒数（相对于片段结束时间）
            after_seconds: 之后秒数（相对于片段结束时间）
            interval_seconds: 间隔秒数
            
        Returns:
            帧时间戳和文件路径的列表
        """
        # 使用音频片段的结束时间作为中心时间点
        center_timestamp = segment_end
        
        # 调用原有的提取方法
        return self.extract_frames_around_timestamp(
            center_timestamp, 
            before_seconds, 
            after_seconds, 
            interval_seconds
        )
    
    def release(self):
        """释放视频资源"""
        if self.cap:
            self.cap.release()