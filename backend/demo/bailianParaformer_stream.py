import pyaudio
from dashscope.audio.asr import (Recognition, RecognitionCallback,
                                 RecognitionResult)

# 若没有将API Key配置到环境变量中，需将下面这行代码注释放开，并将apiKey替换为自己的API Key
# import dashscope
# dashscope.api_key = "apiKey"

mic = None
stream = None


class Callback(RecognitionCallback):
    def on_open(self) -> None:
        global mic
        global stream
        print('RecognitionCallback open.')
        mic = pyaudio.PyAudio()
        stream = mic.open(format=pyaudio.paInt16,
                          channels=1,
                          rate=16000,
                          input=True)

    def on_close(self) -> None:
        global mic
        global stream
        print('RecognitionCallback close.')
        stream.stop_stream()
        stream.close()
        mic.terminate()
        stream = None
        mic = None

    def on_event(self, result: RecognitionResult) -> None:
        print('RecognitionCallback sentence: ', result.get_sentence())


callback = Callback()
recognition = Recognition(model='paraformer-realtime-v2',
                          format='pcm',
                          sample_rate=16000,
                          callback=callback)
recognition.start()

while True:
    if stream:
        data = stream.read(3200, exception_on_overflow=False)
        recognition.send_audio_frame(data)
    else:
        break

recognition.stop()