import requests
from typing import List, Tuple
from http import HTTPStatus
from dashscope.audio.asr import Recognition, Transcription
import json
from camera_surveillance.tools.workspace import log_with_timestamp


class SpeechProcessor:
    """语音处理器，集成百炼语音识别服务"""
    
    def __init__(self, model: str = 'paraformer-v2', sample_rate: int = 16000):
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
    
    def transcribe_url(self, oss_path: str) -> List[Tuple[float, str]]:
        """
        转录音频文件，返回带时间戳的文本列表
        
        Args:
            oss_path: oss上音频文件路径，有过期时间
            
        Returns:
            识别出的文本列表，每个元素为(时间戳, 文本)的元组
        """
        log_with_timestamp(f"开始识别音频文件: {oss_path}")

        try:
            task_response = Transcription.async_call(
                model='paraformer-v2',
                file_urls=[oss_path],
                language_hints=['zh', 'en']  # “language_hints”只支持paraformer-v2模型
            )

            transcribe_response = Transcription.wait(task=task_response.output.task_id)
            if transcribe_response.status_code == HTTPStatus.OK:
                log_with_timestamp(json.dumps(transcribe_response.output, indent=4, ensure_ascii=False))
                log_with_timestamp('transcription done!')
                
                # 获取transcription_url并下载内容
                transcription_url = transcribe_response.output.results[0].transcription_url
                log_with_timestamp(f"获取到transcription_url: {transcription_url}")
                
                # 下载transcription_url内容
                import requests
                response = requests.get(transcription_url)
                if response.status_code == 200:
                    transcription_data = response.json()
                    log_with_timestamp(f"下载transcription数据成功，内容长度: {len(transcription_data.get('transcripts', []))}")
                    
                    # 从transcripts中提取sentences的text和时间信息
                    transcriptions = []
                    for transcript in transcription_data.get('transcripts', []):
                        for sentence in transcript.get('sentences', []):
                            # 时间从毫秒转换为秒
                            begin_time = sentence['begin_time'] / 1000.0
                            text = sentence['text']
                            transcriptions.append((begin_time, text))
                    
                    log_with_timestamp(f"提取到 {len(transcriptions)} 条转录记录")
                    return transcriptions
                else:
                    log_with_timestamp(f"下载transcription_url失败，状态码: {response.status_code}")
                    return []
            else:
                log_with_timestamp(f"转录任务失败，状态码: {transcribe_response.status_code}")
                return []
                
        except Exception as e:
            log_with_timestamp(f"转录过程中发生错误: {e}")
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
    
    # 示例1: 转录本地文件
    # result = processor.transcribe_file('path/to/your/audio.wav')
    # print('本地文件识别结果：', result)
    
    # 示例2: 从URL转录
    # result = processor.transcribe_url(
    #     'https://dashscope.oss-cn-beijing.aliyuncs.com/samples/audio/paraformer/hello_world_female2.wav'
    # )
    # print('URL识别结果：', result)
    
    log_with_timestamp("SpeechProcessor模块已加载")