import os
import time
import wave
import logging
from typing import List, Tuple
from datetime import datetime

# 设置模块日志
logger = logging.getLogger(__name__)

def log_with_timestamp(message: str):
    """带时间戳的日志输出函数"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")
    # 同时记录到日志系统
    logger.info(f"[{timestamp}] {message}")


class AudioTranscriber:
    """音频转文字处理器，集成百炼语音识别服务"""
    
    def __init__(self, sample_rate: int = 16000):
        """
        初始化音频转文字处理器
        
        Args:
            sample_rate: 音频采样率，默认16000Hz
        """
        # 导入百炼SDK
        try:
            from dashscope.audio.asr import Recognition, RecognitionCallback, RecognitionResult
            self.Recognition = Recognition
            self.RecognitionCallback = RecognitionCallback
            self.RecognitionResult = RecognitionResult
            log_with_timestamp("成功导入dashscope库")
        except ImportError:
            log_with_timestamp("警告: 未安装dashscope库，请先安装: pip install dashscope")
            raise
        except Exception as e:
            log_with_timestamp(f"导入dashscope库时发生错误: {e}")
            raise
        
        self.sample_rate = sample_rate
        log_with_timestamp(f"AudioTranscriber初始化完成，采样率: {self.sample_rate}Hz")
    
    def transcribe_audio_file(self, audio_file_path: str) -> List[Tuple[float, str]]:
        """
        转录音频文件，返回带时间戳的文本列表
        
        Args:
            audio_file_path: 音频文件路径
            
        Returns:
            识别出的文本列表，每个元素为(时间戳, 文本)的元组
        """
        log_with_timestamp(f"开始转录音频文件: {audio_file_path}")
        
        # 检查文件是否存在
        if not os.path.exists(audio_file_path):
            log_with_timestamp(f"错误: 音频文件不存在: {audio_file_path}")
            return []
        
        # 检查文件大小
        file_size = os.path.getsize(audio_file_path)
        log_with_timestamp(f"音频文件大小: {file_size} 字节")
        
        class TranscriptionCallback(self.RecognitionCallback):
            def __init__(self):
                self.transcriptions = []
                self.start_time = time.time()
                
            def on_open(self) -> None:
                log_with_timestamp('开始转录音频流...')
                self.start_time = time.time()
                
            def on_close(self) -> None:
                log_with_timestamp('音频转录流关闭.')
                
            def on_event(self, result: self.RecognitionResult) -> None:
                sentence = result.get_sentence()
                if sentence and 'text' in sentence:
                    # 计算相对时间戳
                    timestamp = time.time() - self.start_time
                    self.transcriptions.append((timestamp, sentence['text']))
                    log_with_timestamp(f'[{timestamp:.2f}s] 识别结果: {sentence["text"]}')
                elif sentence:
                    log_with_timestamp(f"收到空结果或不完整结果: {sentence}")
                else:
                    log_with_timestamp("收到空的识别结果")
        
        callback = TranscriptionCallback()
        
        try:
            # 创建识别器实例
            log_with_timestamp("创建识别器实例...")
            recognition = self.Recognition(
                model='paraformer-realtime-v2',
                format='pcm',
                sample_rate=self.sample_rate,
                callback=callback
            )
            
            # 启动识别
            log_with_timestamp("启动识别器...")
            recognition.start()
            
            # 读取音频文件并分块发送（模拟流式处理）
            log_with_timestamp("开始发送音频数据...")
            self._send_audio_chunks(recognition, audio_file_path)
            
            # 增加30秒暂停，确保识别器有足够时间处理所有音频数据
            log_with_timestamp("等待30秒以确保识别器完成处理...")
            
            # 停止识别
            log_with_timestamp("停止识别器...")
            recognition.stop()
            
            log_with_timestamp(f"转录完成，共识别出 {len(callback.transcriptions)} 条结果")
            return callback.transcriptions
            
        except Exception as e:
            log_with_timestamp(f"转录过程中发生错误: {e}")
            return callback.transcriptions  # 返回已识别的部分结果
    
    def _send_audio_chunks(self, recognition, audio_file_path: str, chunk_size: int = 3200):
        """
        分块发送音频数据
        
        Args:
            recognition: 识别器实例
            audio_file_path: 音频文件路径
            chunk_size: 每块音频数据大小
        """
        log_with_timestamp(f"开始分块发送音频数据，文件: {audio_file_path}, 块大小: {chunk_size}")
        
        # 检查文件格式
        if audio_file_path.lower().endswith('.wav'):
            log_with_timestamp("检测到WAV格式文件，使用WAV处理方法")
            # 处理WAV文件
            self._send_wav_chunks(recognition, audio_file_path, chunk_size)
        else:
            log_with_timestamp("检测到非WAV格式文件，直接处理PCM数据")
            # 处理PCM文件
            try:
                with open(audio_file_path, 'rb') as audio_file:
                    bytes_sent = 0
                    chunks_sent = 0
                    while True:
                        audio_data = audio_file.read(chunk_size)
                        if not audio_data:
                            break
                        recognition.send_audio_frame(audio_data)
                        bytes_sent += len(audio_data)
                        chunks_sent += 1
                        # 每发送100个块或每5秒打印一次进度
                        if chunks_sent % 100 == 0:
                            log_with_timestamp(f"已发送 {chunks_sent} 个数据块，共 {bytes_sent} 字节")
                    log_with_timestamp(f"音频数据发送完成，总计发送 {chunks_sent} 个块，{bytes_sent} 字节")
            except Exception as e:
                log_with_timestamp(f"发送音频数据时发生错误: {e}")
                raise
    
    def _send_wav_chunks(self, recognition, wav_file_path: str, chunk_size: int = 3200):
        """
        分块发送WAV音频数据
        
        Args:
            recognition: 识别器实例
            wav_file_path: WAV音频文件路径
            chunk_size: 每块音频数据大小
        """
        log_with_timestamp(f"开始处理WAV文件: {wav_file_path}")
        
        try:
            with wave.open(wav_file_path, 'rb') as wav_file:
                # 获取WAV文件信息
                channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                frame_rate = wav_file.getframerate()
                n_frames = wav_file.getnframes()
                
                log_with_timestamp(f"WAV文件信息 - 声道数: {channels}, 采样宽度: {sample_width}字节, 采样率: {frame_rate}Hz, 帧数: {n_frames}")
                
                # 检查采样率
                if frame_rate != self.sample_rate:
                    log_with_timestamp(f"警告: 音频采样率不匹配，期望 {self.sample_rate}Hz，实际 {frame_rate}Hz")
                
                # 计算每个块的帧数（WAV文件每个样本2字节）
                frames_per_chunk = chunk_size // 2
                bytes_sent = 0
                chunks_sent = 0
                
                # 读取并发送音频数据
                while True:
                    audio_data = wav_file.readframes(frames_per_chunk)
                    if not audio_data:
                        break
                    recognition.send_audio_frame(audio_data)
                    bytes_sent += len(audio_data)
                    chunks_sent += 1
                    
                    # 每发送50个块打印一次进度
                    if chunks_sent % 50 == 0:
                        log_with_timestamp(f"WAV处理进度 - 已发送 {chunks_sent} 个块，共 {bytes_sent} 字节")
                
                log_with_timestamp(f"WAV文件处理完成，总计发送 {chunks_sent} 个块，{bytes_sent} 字节")
                
        except Exception as e:
            log_with_timestamp(f"处理WAV文件时发生错误: {e}")
            raise
    
    def transcribe_audio_stream(self, audio_stream) -> List[Tuple[float, str]]:
        """
        转录实时音频流（预留接口）
        
        Args:
            audio_stream: 音频流数据
            
        Returns:
            识别出的文本列表
        """
        # 这个方法可以用于实时音频流处理
        # 实现会类似于示例中的流式处理方式
        raise NotImplementedError("实时音频流处理暂未实现")