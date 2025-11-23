import ffmpeg

(
    ffmpeg
    .input('../workspace/860924031381890_1763889207/tmp/video_chunk_1763889238904359_000002.webm')
    .output('output.wav', acodec='pcm_s16le', vn=None)
    .overwrite_output()
    .run()
)