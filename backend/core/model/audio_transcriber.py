import os
import time
import wave
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import asyncio

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
        except ImportError:
            print("警告: 未安装dashscope库，请先安装: pip install dashscope")
            raise
        
        self.sample_rate = sample_rate
    
    def transcribe_audio_file(self, audio_file_path: str) -> List[Tuple[float, str]]:
        """
        转录音频文件，返回带时间戳的文本列表
        
        Args:
            audio_file_path: 音频文件路径
            
        Returns:
            识别出的文本列表，每个元素为(时间戳, 文本)的元组
        """
        class TranscriptionCallback(self.RecognitionCallback):
            def __init__(self):
                self.transcriptions = []
                self.start_time = time.time()
                
            def on_open(self) -> None:
                print('开始转录音频...')
                self.start_time = time.time()
                
            def on_close(self) -> None:
                print('音频转录完成.')
                
            def on_event(self, result: self.RecognitionResult) -> None:
                sentence = result.get_sentence()
                if sentence and 'text' in sentence:
                    # 计算相对时间戳
                    timestamp = time.time() - self.start_time
                    self.transcriptions.append((timestamp, sentence['text']))
                    print(f'[{timestamp:.2f}s] 识别结果: {sentence["text"]}')
        
        callback = TranscriptionCallback()
        
        # 创建识别器实例
        recognition = self.Recognition(
            model='paraformer-realtime-v2',
            format='pcm',
            sample_rate=self.sample_rate,
            callback=callback
        )
        
        # 启动识别
        recognition.start()
        
        # 读取音频文件并分块发送（模拟流式处理）
        self._send_audio_chunks(recognition, audio_file_path)
        
        # 停止识别
        recognition.stop()
        
        return callback.transcriptions
    
    def _send_audio_chunks(self, recognition, audio_file_path: str, chunk_size: int = 3200):
        """
        分块发送音频数据
        
        Args:
            recognition: 识别器实例
            audio_file_path: 音频文件路径
            chunk_size: 每块音频数据大小
        """
        # 检查文件格式
        if audio_file_path.lower().endswith('.wav'):
            # 处理WAV文件
            self._send_wav_chunks(recognition, audio_file_path, chunk_size)
        else:
            # 处理PCM文件
            with open(audio_file_path, 'rb') as audio_file:
                while True:
                    audio_data = audio_file.read(chunk_size)
                    if not audio_data:
                        break
                    recognition.send_audio_frame(audio_data)
    
    def _send_wav_chunks(self, recognition, wav_file_path: str, chunk_size: int = 3200):
        """
        分块发送WAV音频数据
        
        Args:
            recognition: 识别器实例
            wav_file_path: WAV音频文件路径
            chunk_size: 每块音频数据大小
        """
        with wave.open(wav_file_path, 'rb') as wav_file:
            # 检查采样率
            if wav_file.getframerate() != self.sample_rate:
                print(f"警告: 音频采样率不匹配，期望 {self.sample_rate}Hz，实际 {wav_file.getframerate()}Hz")
            
            # 读取并发送音频数据
            while True:
                audio_data = wav_file.readframes(chunk_size // 2)  # WAV文件每个样本2字节
                if not audio_data:
                    break
                recognition.send_audio_frame(audio_data)
    
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