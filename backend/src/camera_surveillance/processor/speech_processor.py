import requests
import os
import time
import logging
from typing import List, Tuple
from pathlib import Path
from datetime import datetime
from http import HTTPStatus
from dashscope.audio.asr import Recognition, Transcription
import json

def log_with_timestamp(message: str):
    """带时间戳的日志输出函数"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")
    # 同时记录到日志系统
    logging.getLogger(__name__).info(f"[{timestamp}] {message}")


class SpeechProcessor:
    """语音处理器，集成百炼语音识别服务"""
    
    def __init__(self, model: str = 'paraformer-realtime-v2', sample_rate: int = 16000):
        """
        初始化语音处理器
        
        Args:
            model: 语音识别模型名称
            sample_rate: 音频采样率，默认16000Hz
        """
        # 导入百炼SDK
        try:
            import dashscope
            dashscope.api_key = 'sk-75d99280f5db4b65b5eaa46525a35177'
        except ImportError:
            log_with_timestamp("警告: 未安装dashscope库，请先安装: pip install dashscope")
            raise
        except Exception as e:
            log_with_timestamp(f"配置dashscope时发生错误: {e}")
            raise
        
        self.model = model
        self.sample_rate = sample_rate
        log_with_timestamp(f"SpeechProcessor初始化完成，模型: {self.model}，采样率: {self.sample_rate}Hz")
    
    def transcribe_file(self, audio_file_path: str) -> List[Tuple[float, str]]:
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
        
        try:
            task_response = Transcription.async_call(
                model='paraformer-v2',
                file_urls=[
                    'https://test-workspace-wl.oss-cn-hangzhou.aliyuncs.com/voice/extracted_audio.wav?Expires=1763206898&OSSAccessKeyId=TMP.3Krxew4PmqeU7DxGWAouXnxb77PyfgXcmfXBYAvFLvMST3eEoNiH9ysUA9AFtu5NGkuCLYQJGUeBsjSH7aZn6bGq8rLpkZ&Signature=9BMIP6bSzqY7lq86ifbNaceD448%3D'],
                language_hints=['zh', 'en']  # “language_hints”只支持paraformer-v2模型
            )

            transcribe_response = Transcription.wait(task=task_response.output.task_id)
            if transcribe_response.status_code == HTTPStatus.OK:
                log_with_timestamp(json.dumps(transcribe_response.output, indent=4, ensure_ascii=False))
                log_with_timestamp('transcription done!')

            # 创建识别器实例
            recognition = Recognition(
                model=self.model,
                format='wav',  # 根据实际文件格式调整
                sample_rate=self.sample_rate,
                language_hints=['zh', 'en'],  # 支持中英文混合识别
                callback=None
            )
            
            result = recognition.call(audio_file_path)
            
            if result.status_code == HTTPStatus.OK:
                log_with_timestamp('识别成功')
                # 获取完整的句子结果
                full_result = result.get_sentence()
                log_with_timestamp(f'speech_result: {result}')
                log_with_timestamp(f'full_result: {full_result}')
                if full_result and 'text' in full_result:
                    # 模拟时间戳，实际应用中可以从result中获取更精确的时间戳
                    timestamp = 0.0
                    return [(timestamp, full_result['text'])]
                else:
                    log_with_timestamp('未找到识别结果')
                    return []
            else:
                log_with_timestamp(f'识别失败: {result.message}')
                return []
                
        except Exception as e:
            log_with_timestamp(f"转录过程中发生错误: {e}")
            return []
    
    def transcribe_url(self, audio_url: str, temp_filename: str = 'temp_audio.wav') -> List[Tuple[float, str]]:
        """
        从URL转录音频，支持在线音频处理
        
        Args:
            audio_url: 音频URL
            temp_filename: 临时文件名
            
        Returns:
            识别出的文本列表
        """
        log_with_timestamp(f"从URL转录音频: {audio_url}")
        
        try:
            # 下载音频文件到临时位置
            r = requests.get(audio_url)
            with open(temp_filename, 'wb') as f:
                f.write(r.content)
            
            log_with_timestamp(f"音频文件已下载到: {temp_filename}")
            
            # 转录音频文件
            result = self.transcribe_file(temp_filename)
            
            # 清理临时文件
            if os.path.exists(temp_filename):
                os.remove(temp_filename)
                log_with_timestamp(f"临时文件已清理: {temp_filename}")
            
            return result
            
        except Exception as e:
            log_with_timestamp(f"从URL转录音频时发生错误: {e}")
            # 确保清理临时文件
            if os.path.exists(temp_filename):
                os.remove(temp_filename)
            return []
    
    def transcribe_stream(self, audio_stream) -> List[Tuple[float, str]]:
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


# 示例使用
if __name__ == "__main__":
    # 创建语音处理器实例
    processor = SpeechProcessor()

    r = requests.get(
        'https://dashscope.oss-cn-beijing.aliyuncs.com/samples/audio/paraformer/hello_world_female2.wav'
    )
    with open('asr_example.wav', 'wb') as f:
        f.write(r.content)

    processor.transcribe_file(
        'asr_example.wav' )
    
    # 示例1: 转录本地文件
    # result = processor.transcribe_file('path/to/your/audio.wav')
    # print('本地文件识别结果：', result)
    
    # 示例2: 从URL转录
    # result = processor.transcribe_url(
    #     'https://dashscope.oss-cn-beijing.aliyuncs.com/samples/audio/paraformer/hello_world_female2.wav'
    # )
    # print('URL识别结果：', result)
    
    log_with_timestamp("SpeechProcessor模块已加载")