#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import sys
import threading
from pathlib import Path

TIMEOUT_SECONDS = 180

def check_jar_already_decompiled(jar_file, output_dir):
    """
    检查JAR是否已经成功反编译
    
    :param jar_file: JAR文件路径
    :param output_dir: 输出目录
    :return: True如果已存在有效的反编译结果，False否则
    """
    jar_output_dir = output_dir / jar_file.stem
    
    if not jar_output_dir.exists():
        return False
    
    java_files = list(jar_output_dir.rglob("*.java"))
    return len(java_files) > 0


def decompile_with_timeout(jar_file, jd_cli_path, output_dir):
    """
    带超时机制的反编译函数
    
    :param jar_file: JAR文件路径
    :param jd_cli_path: jd-cli.jar路径
    :param output_dir: 输出目录
    :return: (success, error_message, timeout)
    """
    result = {
        'success': False,
        'error': None,
        'timeout': False,
        'process': None
    }
    
    def run_decompile():
        cmd = [
            "java", "-jar", jd_cli_path,
            str(jar_file),
            "-od", str(output_dir / jar_file.stem)
        ]
        
        result['process'] = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8'
        )
        
        stdout, stderr = result['process'].communicate()
        
        if result['process'].returncode == 0:
            result['success'] = True
        else:
            result['error'] = stderr
    
    thread = threading.Thread(target=run_decompile)
    thread.daemon = True
    thread.start()
    
    thread.join(TIMEOUT_SECONDS)
    
    if thread.is_alive():
        result['timeout'] = True
        if result['process']:
            result['process'].kill()
    
    return result['success'], result['error'], result['timeout']


def decompile_jars(jd_cli_path, lib_dir, output_dir):
    """
    使用jd-cli反编译lib目录中的所有JAR文件
    
    :param jd_cli_path: jd-cli.jar的完整路径
    :param lib_dir: 包含JAR文件的目录
    :param output_dir: 输出Java源代码的目录
    """
    lib_path = Path(lib_dir)
    output_path = Path(output_dir)
    
    if not lib_path.exists():
        print(f"错误: lib目录不存在: {lib_dir}")
        return
    
    if not Path(jd_cli_path).exists():
        print(f"错误: jd-cli.jar不存在: {jd_cli_path}")
        return
    
    output_path.mkdir(parents=True, exist_ok=True)
    
    jar_files = list(lib_path.glob("*.jar"))
    
    if not jar_files:
        print(f"警告: 在 {lib_dir} 中没有找到JAR文件")
        return
    
    print(f"找到 {len(jar_files)} 个JAR文件")
    print(f"输出目录: {output_dir}")
    print(f"超时设置: {TIMEOUT_SECONDS} 秒")
    print("-" * 50)
    
    success_count = 0
    failed_count = 0
    timeout_jars = []
    retry_count = 0
    skipped_count = 0
    
    for jar_file in jar_files:
        jar_name = jar_file.stem
        jar_output_dir = output_path / jar_name
        
        if check_jar_already_decompiled(jar_file, output_path):
            print(f"[跳过] {jar_file.name} - 已存在反编译结果")
            skipped_count += 1
            print()
            continue
        
        print(f"正在反编译: {jar_file.name}")
        
        success, error, timeout = decompile_with_timeout(jar_file, jd_cli_path, output_path)
        
        if timeout:
            print(f"[超时] {jar_file.name} - 超过 {TIMEOUT_SECONDS} 秒，稍后重试")
            timeout_jars.append(jar_file)
            failed_count += 1
        elif success:
            print(f"[成功] {jar_file.name}")
            success_count += 1
        else:
            print(f"[失败] {jar_file.name}")
            if error:
                print(f"  错误信息: {error}")
            failed_count += 1
        
        print()
    
    if timeout_jars:
        print("=" * 50)
        print(f"开始重试 {len(timeout_jars)} 个超时的JAR文件...")
        print("-" * 50)
        
        for jar_file in timeout_jars:
            print(f"重试反编译: {jar_file.name}")
            
            success, error, timeout = decompile_with_timeout(jar_file, jd_cli_path, output_path)
            
            if timeout:
                print(f"[超时] {jar_file.name} - 再次超时")
            elif success:
                print(f"[成功] {jar_file.name}")
                success_count += 1
                retry_count += 1
                failed_count -= 1
            else:
                print(f"[失败] {jar_file.name}")
                if error:
                    print(f"  错误信息: {error}")
            
            print()
    
    print("=" * 50)
    print(f"反编译完成: 成功 {success_count}, 失败 {failed_count}, 重试成功 {retry_count}, 跳过 {skipped_count}")
    if timeout_jars:
        print(f"超时JAR数量: {len(timeout_jars)}")
    print(f"所有源代码已输出到: {output_dir}")


def main():
    JD_CLI_PATH = r"C:\lib\jd-cli.jar"
    LIB_DIR = "./lib"
    OUTPUT_DIR = "./output"
    
    if len(sys.argv) >= 2:
        JD_CLI_PATH = sys.argv[1]
    if len(sys.argv) >= 3:
        LIB_DIR = sys.argv[2]
    if len(sys.argv) >= 4:
        OUTPUT_DIR = sys.argv[3]
    
    decompile_jars(JD_CLI_PATH, LIB_DIR, OUTPUT_DIR)


if __name__ == "__main__":
    main()
