import os
import tempfile
import subprocess
from pathlib import Path
import time

def find_segment_start(data):
    """在 WebM/EBML 数据中找到 Segment 的开始位置"""
    if isinstance(data, str):
        with open(data, 'rb') as f:
            data = f.read()

    # WebM Segment 的 EBML ID: 0x18 0x53 0x80 0x67
    segment_marker = b'\x18\x53\x80\x67'
    segment_pos = data.find(segment_marker)

    if segment_pos != -1:
        return segment_pos

    # 如果没找到 Segment，返回 0
    return 0

def simple_convert_range_chunks(chunk_files, start_index, end_index, output_path):
    """
    简单方案：将指定范围的分段重新用 FFmpeg 处理
    """

    # 创建一个临时的"完整" WebM 文件
    temp_complete = f"temp_complete_{int(time.time())}.webm"

    try:
        with open(temp_complete, 'wb') as output:
            if start_index == 0:
                # 从第一个分段开始
                for i in range(end_index + 1):
                    with open(chunk_files[i], 'rb') as f:
                        data = f.read()

                    if i == 0:
                        output.write(data)  # 第一个分段包含头部
                    else:
                        # 后续分段：尝试找到 Segment 数据并写入
                        segment_pos = find_segment_start(data)
                        if segment_pos > 0:
                            output.write(data[segment_pos:])
                        else:
                            output.write(data)
            else:
                # 从中间分段开始：需要第一个分段的头部
                # 读取第一个分段获取头部
                with open(chunk_files[0], 'rb') as f:
                    first_data = f.read()

                # 找到 Segment 开始位置（这就是头部的结束位置）
                segment_pos = find_segment_start(first_data)
                if segment_pos > 0:
                    print(f"segment_pos: {segment_pos}, webm head: {first_data[:segment_pos]}")
                    print(f"segment_pos: {segment_pos}, webm head+8: {first_data[:segment_pos+16]}")
                    # 读取 Segment 的长度信息（EBML VL-INT 格式）
                    segment_len, len_bytes = read_vl_int_correct(first_data, segment_pos + 4)

                    if segment_len is not None:
                        # 写入：EBML Header + 完整的 Segment Header（包含长度）
                        # 这样就有一个完整的、可解析的 Segment 结构
                        segment_header_end = segment_pos + 4 + len_bytes
                        complete_header = first_data[:segment_header_end]
                        output.write(complete_header)
                        print(f"写入完整头部: {complete_header}")
                    else:
                        # 如果无法解析长度，至少写入 EBML Header + Segment ID
                        output.write(first_data[:segment_pos + 4])  # 包含 \x18\x53\x80\x67
                        print(f"写入基本头部: {segment_pos + 4} bytes")

                # 写入目标范围的数据
                for i in range(start_index, end_index + 1):
                    with open(chunk_files[i], 'rb') as f:
                        data = f.read()

                    # 尝试跳过重复头部，写入核心数据
                    core_pos = find_segment_start(data)
                    if core_pos > 0:
                        output.write(data[core_pos:])
                    else:
                        output.write(data)

        # 现在转换这个"完整"的临时文件
        result = subprocess.run([
            'ffmpeg',
            '-i', temp_complete,
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-movflags', '+faststart',
            '-avoid_negative_ts', 'make_zero',
            '-fflags', '+igndts',
            '-y',
            output_path
        ], capture_output=True, text=True)

        success = result.returncode == 0
        if success:
            print(f"✅ 转换成功:  bytes")
        else:
            print(f"❌ 转换失败: {result.stderr}")

        return success

    finally:
        import os
        if os.path.exists(temp_complete):
            os.unlink(temp_complete)


def read_vl_int_correct(data, start):
    """
    正确读取 EBML 变长整数
    \x01\xff\xff\xff 的含义：
    - \x01: 长度字节（1个字节的值）
    - \xff\xff\xff: 实际值（0xFFFFFF）
    """
    if start >= len(data):
        return None, 0

    first_byte = data[start]

    # 计算前导零的数量来确定总字节数
    total_bytes = 0
    temp = first_byte
    while temp & 0x80 == 0:
        temp <<= 1
        total_bytes += 1
    total_bytes += 1  # 加上第一个字节

    if total_bytes > 8 or start + total_bytes > len(data):
        return None, 0

    # 读取完整的长度字段
    length_value = 0
    for i in range(total_bytes):
        if i == 0:
            # 第一个字节，清除标记位
            length_value = data[start + i] & ((1 << (8 - total_bytes)) - 1)
        else:
            length_value = (length_value << 8) | data[start + i]

    return length_value, total_bytes


def convert_range_with_ffmpeg_concat(chunk_files, start_index, end_index, output_path):
    """
    直接用 FFmpeg concat 处理原始分段
    """
    import tempfile

    target_chunks = chunk_files[start_index:end_index + 1]

    # 创建临时列表文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as list_file:
        for chunk in target_chunks:
            import os
            list_file.write(f"file '{os.path.abspath(chunk)}'\n")
        list_path = list_file.name

    try:
        # 使用 FFmpeg concat 协议
        cmd = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-protocol_whitelist', 'file,pipe,data',
            '-i', list_path,
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-movflags', '+faststart',
            '-avoid_negative_ts', 'make_zero',
            '-fflags', '+igndts+genpts+nofillin',
            '-y',
            output_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            import os
            print(f"✅ FFmpeg concat 转换成功: {os.path.getsize(output_path)} bytes")
            return True
        else:
            print(f"❌ FFmpeg concat 失败: {result.stderr}")
            return False

    finally:
        import os
        os.unlink(list_path)


def get_latest_tmp_dir(workspace_path):
    """获取workspace下时间戳最新的目录中的tmp目录"""
    workspace = Path(workspace_path)
    
    # 查找符合 "name_timestamp" 格式的子目录（包含下划线和时间戳）
    timestamp_dirs = []
    for item in workspace.iterdir():
        if item.is_dir():
            parts = item.name.rsplit('_', 1)  # 从右边分割一次
            if len(parts) == 2:
                try:
                    # 尝试将后半部分解析为时间戳
                    timestamp = int(parts[1])
                    timestamp_dirs.append((timestamp, item))
                except ValueError:
                    continue  # 如果无法解析时间戳，则跳过
    
    # 按时间戳降序排列，获取最新的目录
    timestamp_dirs.sort(key=lambda x: x[0], reverse=True)
    
    if not timestamp_dirs:
        return None
    
    latest_dir = timestamp_dirs[0][1]
    tmp_dir = latest_dir / "tmp"
    
    if tmp_dir.exists():
        return tmp_dir
    else:
        return None


def get_chunk_files_from_workspace(workspace_path):
    """从工作空间获取所有视频块文件"""
    chunk_files = []
    
    # 从workspace下时间戳最新的目录的tmp文件夹获取视频块
    tmp_dir = get_latest_tmp_dir(workspace_path)
    if tmp_dir:
        # 查找tmp目录下的所有视频块文件（按名称排序以确保正确的顺序）
        for file_path in sorted(tmp_dir.glob("video_chunk_*.webm")):
            chunk_files.append(str(file_path))
    else:
        print(f"⚠️ 未找到workspace下时间戳最新的tmp目录")
        return []
    
    # 按文件名排序
    chunk_files.sort()
    
    return chunk_files


def merge_middle_chunks(workspace_path, output_path, start_index=0, end_index=None):
    """合并工作空间中的视频块"""
    # 从工作空间获取视频块文件列表
    chunk_files = get_chunk_files_from_workspace(workspace_path)
    
    if not chunk_files:
        print("❌ 没有找到视频块文件")
        return False
    
    # 如果未指定结束索引，则使用所有可用的文件
    if end_index is None:
        end_index = len(chunk_files) - 1
    
    print(f"📦 准备合并视频块: {len(chunk_files)} 个文件")
    print(f"📋 起始索引: {start_index}, 结束索引: {end_index}")
    print(f"🎬 输出路径: {output_path}")
    
    # 调用处理函数
    success = convert_range_with_ffmpeg_concat(chunk_files, start_index, end_index, output_path)
    
    if success:
        print("🎉 合并完成!")
        return True
    else:
        print("❌ 合并失败!")
        return False


def main():
    """入口函数"""
    # 直接使用实际路径和参数
    success = merge_middle_chunks(
        workspace_path="../workspace",  # 实际工作空间路径
        output_path="../workspace/merged_video.mp4",  # 输出文件路径
        start_index=2,
        end_index=4
    )
    
    if not success:
        exit(1)


if __name__ == "__main__":
    main()