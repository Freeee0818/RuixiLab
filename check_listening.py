#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查服务监听地址脚本
在服务器上运行，检查服务是否监听在 0.0.0.0
"""

import socket
import subprocess
import sys

def check_listening_address(port):
    """检查端口监听地址"""
    print(f"\n检查端口 {port} 的监听情况:")
    print("-" * 60)
    
    try:
        # 使用 netstat 或 ss 命令
        try:
            result = subprocess.run(
                ['netstat', '-tlnp'],
                capture_output=True,
                text=True,
                timeout=5
            )
            lines = result.stdout.split('\n')
        except:
            result = subprocess.run(
                ['ss', '-tlnp'],
                capture_output=True,
                text=True,
                timeout=5
            )
            lines = result.stdout.split('\n')
        
        found = False
        for line in lines:
            if f':{port}' in line and 'LISTEN' in line:
                found = True
                print(f"  ✅ 找到监听: {line.strip()}")
                
                # 检查监听地址
                if '0.0.0.0' in line or '*:' in line:
                    print(f"  ✅ 监听地址: 0.0.0.0 (允许外部访问)")
                elif '127.0.0.1' in line or '::1' in line:
                    print(f"  ❌ 监听地址: 127.0.0.1 (只允许本地访问)")
                    print(f"  ⚠️  问题: 服务只监听本地，外部无法访问！")
                    print(f"  💡 解决: 确保服务启动时使用 host=0.0.0.0")
                else:
                    print(f"  ⚠️  监听地址: {line}")
        
        if not found:
            print(f"  ❌ 端口 {port} 未监听")
            print(f"  ⚠️  服务可能未运行")
        
        return found
        
    except Exception as e:
        print(f"  ❌ 检查失败: {e}")
        return False

def test_local_connection(port):
    """测试本地连接"""
    print(f"\n测试本地连接 (localhost:{port}):")
    print("-" * 60)
    
    try:
        import requests
        response = requests.get(f'http://localhost:{port}/', timeout=3)
        print(f"  ✅ 连接成功")
        print(f"  状态码: {response.status_code}")
        print(f"  响应: {response.text[:100]}")
        return True
    except Exception as e:
        print(f"  ❌ 连接失败: {e}")
        return False

def test_external_connection(ip, port):
    """测试外部连接"""
    print(f"\n测试外部连接 ({ip}:{port}):")
    print("-" * 60)
    
    try:
        import requests
        response = requests.get(f'http://{ip}:{port}/', timeout=5)
        print(f"  ✅ 连接成功")
        print(f"  状态码: {response.status_code}")
        return True
    except requests.exceptions.ConnectionError:
        print(f"  ❌ 连接被拒绝或超时")
        print(f"  ⚠️  可能原因:")
        print(f"     1. 防火墙阻止")
        print(f"     2. 阿里云安全组未开放")
        print(f"     3. 服务只监听 127.0.0.1")
        return False
    except Exception as e:
        print(f"  ❌ 连接失败: {e}")
        return False

def main():
    print("=" * 60)
    print("  服务监听地址检查工具")
    print("=" * 60)
    
    # 检查端口
    ports = [8000, 8001]
    server_ip = "47.94.229.183"
    
    for port in ports:
        service_name = "PySR 服务" if port == 8000 else "数据分析服务"
        print(f"\n{'='*60}")
        print(f"  {service_name} (端口 {port})")
        print(f"{'='*60}")
        
        # 检查监听
        is_listening = check_listening_address(port)
        
        if is_listening:
            # 测试本地连接
            local_ok = test_local_connection(port)
            
            # 测试外部连接
            external_ok = test_external_connection(server_ip, port)
            
            # 诊断
            if local_ok and not external_ok:
                print(f"\n  🔍 诊断:")
                print(f"     ✅ 服务运行正常（本地可访问）")
                print(f"     ❌ 外部无法访问")
                print(f"     💡 解决方案:")
                print(f"        1. 检查服务是否监听 0.0.0.0（不是 127.0.0.1）")
                print(f"        2. 检查宝塔防火墙是否开放端口 {port}")
                print(f"        3. 检查阿里云安全组是否开放端口 {port}")
    
    print("\n" + "=" * 60)
    print("检查完成")
    print("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 检查过程出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

