#!/usr/bin/env python
import sys
import os

print("=" * 50)
print("DIAGNOSTIC INFORMATION")
print("=" * 50)

print(f"Current working directory: {os.getcwd()}")
print(f"Python executable: {sys.executable}")
print(f"Virtual environment: {os.environ.get('VIRTUAL_ENV', 'Not set')}")

print(f"\nPython path:")
for i, path in enumerate(sys.path):
    marker = " ← VENV" if "venv" in path else ""
    print(f"  {i}: {path}{marker}")

print(f"\nChecking camera_surveillance package:")
try:
    import camera_surveillance

    print(f"✅ SUCCESS: camera_surveillance imported from {camera_surveillance.__file__}")

    # 检查子模块
    print(f"Checking processor module:")
    try:
        from camera_surveillance import processor

        print(f"✅ SUCCESS: processor module imported from {processor.__file__}")
    except ImportError as e:
        print(f"❌ FAILED: processor import failed: {e}")

    print(f"Checking local_models:")
    try:
        from camera_surveillance.processor import AntiRollingModel

        print(f"✅ SUCCESS: AntiRollingModel imported successfully")
    except ImportError as e:
        print(f"❌ FAILED: local_models import failed: {e}")
        import traceback

        traceback.print_exc()

except ImportError as e:
    print(f"❌ FAILED: camera_surveillance import failed: {e}")
    import traceback

    traceback.print_exc()

print(f"\nChecking source directories:")
src_path = os.path.join(os.getcwd(), 'src')
print(f"src directory exists: {os.path.exists(src_path)}")

if os.path.exists(src_path):
    print(f"src contents: {os.listdir(src_path)}")

    camera_surv_path = os.path.join(src_path, 'camera_surveillance')
    print(f"camera_surveillance directory exists: {os.path.exists(camera_surv_path)}")

    if os.path.exists(camera_surv_path):
        print(f"camera_surveillance contents: {os.listdir(camera_surv_path)}")