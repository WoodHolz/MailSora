import os
import hashlib
from collections import defaultdict
import shutil

def calculate_mail_hash(mail_dir):
    """计算邮件文件夹内容的哈希值"""
    hash_md5 = hashlib.md5()
    
    # 按文件名排序以确保一致性
    files = sorted(os.listdir(mail_dir))
    
    for filename in files:
        filepath = os.path.join(mail_dir, filename)
        if os.path.isfile(filepath):
            try:
                with open(filepath, "rb") as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        hash_md5.update(chunk)
            except (IOError, OSError):
                continue
    
    return hash_md5.hexdigest()

def find_duplicate_mails(base_dir):
    """查找重复的邮件文件夹"""
    mail_hashes = defaultdict(list)
    
    # 遍历所有邮件文件夹
    for mail_dir in os.listdir(base_dir):
        full_path = os.path.join(base_dir, mail_dir)
        if os.path.isdir(full_path):
            try:
                mail_hash = calculate_mail_hash(full_path)
                mail_hashes[mail_hash].append(full_path)
            except Exception as e:
                print(f"Error processing {mail_dir}: {e}")
                continue
    
    # 返回有重复的邮件文件夹
    return {h: paths for h, paths in mail_hashes.items() if len(paths) > 1}

def delete_duplicate_mails(base_dir):
    """删除重复的邮件文件夹"""
    duplicates = find_duplicate_mails(base_dir)
    
    for mail_hash, mail_dirs in duplicates.items():
        # 保留第一个文件夹，删除其他重复的
        for mail_dir in mail_dirs[1:]:
            try:
                print(f"Deleting duplicate mail folder: {mail_dir}")
                shutil.rmtree(mail_dir)
            except OSError as e:
                print(f"Error deleting {mail_dir}: {e}")

if __name__ == "__main__":
    from email_fetcher.email_fetcher_api import fetcher_temp_path
    
    if os.path.exists(fetcher_temp_path):
        print(f"Cleaning duplicate mails in: {fetcher_temp_path}")
        delete_duplicate_mails(fetcher_temp_path)
        print("Duplicate mail cleaning completed.")
    else:
        print(f"Temp directory not found: {fetcher_temp_path}") 