import subprocess
import os


def validate_webm_file(file_path):
    """验证 WebM 文件是否完整"""
    try:
        # 使用 ffprobe 检查文件
        result = subprocess.run([
            'ffprobe',
            '-v', 'quiet',
            '-show_format',
            '-show_streams',
            file_path
        ], capture_output=True, text=True)

        if result.returncode != 0:
            print(f"❌ 文件无效: {file_path}")
            print(f"   FFprobe error: {result.stderr}")
            return False

        # 检查输出中是否包含有效信息
        output = result.stdout
        if 'streams' not in output and 'format' not in output:
            print(f"❌ 文件格式异常: {file_path}")
            return False

        print(f"✅ 文件有效: {file_path}")
        return True

    except Exception as e:
        print(f"❌ 验证失败 {file_path}: {e}")
        return False


def check_file_integrity(chunk_files):
    """检查所有分段文件的完整性"""
    valid_files = []
    invalid_files = []

    for file_path in chunk_files:
        if validate_webm_file(file_path):
            valid_files.append(file_path)
        else:
            invalid_files.append(file_path)

    print(f"有效文件: {len(valid_files)}, 无效文件: {len(invalid_files)}")
    return valid_files, invalid_files


def main():
    """入口函数，测试指定目录下的webm文件完整性"""
    target_dir = "/Users/wanglei/workStore/code/workSource/camera-surveillance/backend/workspace/860924031381890_1763288465/tmp/"
    
    if not os.path.exists(target_dir):
        print(f"目录不存在: {target_dir}")
        return
    
    # 获取目录下所有webm文件
    webm_files = [os.path.join(target_dir, f) for f in os.listdir(target_dir) if f.lower().endswith('.webm')]
    
    if not webm_files:
        print(f"目录中没有找到webm文件: {target_dir}")
        return
    
    print(f"找到 {len(webm_files)} 个webm文件")
    for file in webm_files:
        print(f"  - {file}")
    
    print("\n开始验证文件完整性...")
    valid_files, invalid_files = check_file_integrity(webm_files)
    
    print(f"\n验证完成:")
    print(f"  有效文件: {len(valid_files)}")
    for file in valid_files:
        print(f"    - {file}")
    
    print(f"  无效文件: {len(invalid_files)}")
    for file in invalid_files:
        print(f"    - {file}")


if __name__ == "__main__":
    main()