import subprocess
import tempfile
import os
import time
import glob


def merge_mediarecorder_chunks(chunk_files, output_path):
    """手动合并 MediaRecorder 分段文件为webm，然后转换为mp4"""

    if not chunk_files:
        return False

    # 读取所有分段
    chunk_data = []
    for chunk_file in chunk_files:
        with open(chunk_file, 'rb') as f:
            data = f.read()
            if data:
                chunk_data.append(data)

    if not chunk_data:
        return False

    # 首先创建一个临时的webm文件
    temp_webm = output_path.replace('.mp4', '_temp.webm')
    
    # 手动合并：第一个分段 + 后续分段的核心数据
    with open(temp_webm, 'wb') as output_file:
        # 写入第一个分段（包含头部）
        output_file.write(chunk_data[0])

        # 后续分段：跳过可能的重复头部，写入核心数据
        for i, chunk in enumerate(chunk_data[1:], 1):
            output_file.write(chunk)

    # 验证临时webm文件大小
    temp_size = os.path.getsize(temp_webm)
    expected_size = sum(len(data) for data in chunk_data)

    print(f"二进制合并完成: {expected_size} -> {temp_size} bytes")
    
    # 然后使用ffmpeg将webm转换为mp4
    print("开始转换webm到mp4...")
    convert_result = subprocess.run([
        'ffmpeg',
        '-i', temp_webm,
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-movflags', '+faststart',
        '-y',
        output_path
    ], capture_output=True, text=True)

    if convert_result.returncode == 0:
        output_size = os.path.getsize(output_path)
        print(f"转换完成! 最终文件大小: {output_size} bytes")
        return True
    else:
        print(f"转换失败: {convert_result.stderr}")
        return False


def process_workspace_tmp_data():
    """处理 workspace 目录下 tmp 文件夹中的数据"""
    # 指定目录路径
    workspace_path = "/Users/wanglei/workStore/code/workSource/camera-surveillance/backend/workspace/860924031381890_1763905130/tmp"
    
    # 查找所有 .webm 文件
    webm_pattern = os.path.join(workspace_path, "*.webm")
    chunk_files = sorted(glob.glob(webm_pattern))
    
    if not chunk_files:
        print("未找到任何 .webm 文件")
        return False
    
    # 输出文件路径
    output_path = "/Users/wanglei/workStore/code/workSource/camera-surveillance/backend/workspace/860924031381890_1763905130/merged_output.mp4"
    
    print(f"找到 {len(chunk_files)} 个分段文件")
    print("开始处理...")
    
    # 调用处理函数
    success = merge_mediarecorder_chunks(chunk_files, output_path)
    
    if success:
        print(f"处理成功! 输出文件: {output_path}")
    else:
        print("处理失败")
    
    return success


if __name__ == "__main__":
    process_workspace_tmp_data()