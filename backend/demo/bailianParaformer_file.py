import requests
from http import HTTPStatus
from dashscope.audio.asr import Recognition

# 若没有将API Key配置到环境变量中，需将下面这行代码注释放开，并将apiKey替换为自己的API Key
# import dashscope
# dashscope.api_key = "apiKey"

# 用户可忽略从url下载文件这部分代码，直接使用本地文件进行识别
r = requests.get(
    'https://dashscope.oss-cn-beijing.aliyuncs.com/samples/audio/paraformer/hello_world_female2.wav'
)
with open('asr_example.wav', 'wb') as f:
    f.write(r.content)

recognition = Recognition(model='paraformer-realtime-v2',
                          format='wav',
                          sample_rate=16000,
                          # “language_hints”只支持paraformer-v2和paraformer-realtime-v2模型
                          language_hints=['zh', 'en'],
                          callback=None)
result = recognition.call('asr_example.wav')
if result.status_code == HTTPStatus.OK:
    print('识别结果：')
    print(result.get_sentence())
else:
    print('Error: ', result.message)