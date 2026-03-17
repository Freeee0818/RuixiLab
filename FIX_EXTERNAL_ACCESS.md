# 🔧 修复外部无法访问问题

## 🎯 问题诊断

**现象**：
- ✅ `curl http://localhost:8000/` 成功（服务器本地）
- ❌ `curl http://47.94.229.183:8000/` 失败（外部访问）

**结论**：服务在运行，但外部无法访问。

---

## 🔍 可能原因（按优先级）

### 1. 服务只监听 127.0.0.1（最可能）

**检查方法**：

在服务器上运行：
```bash
netstat -tlnp | grep :8000
# 或
ss -tlnp | grep :8000
```

**应该看到**：
```
tcp  0  0  0.0.0.0:8000  LISTEN  python  ✅ 正确
```

**如果看到**：
```
tcp  0  0  127.0.0.1:8000  LISTEN  python  ❌ 错误！
```

**解决方法**：

检查启动命令或 Supervisor 配置，确保使用 `0.0.0.0`：

```bash
# ✅ 正确
python3 main.py --host 0.0.0.0 --port 8000

# ❌ 错误
python3 main.py --host 127.0.0.1 --port 8000
```

### 2. 宝塔防火墙未开放端口

**解决方法**：
1. 宝塔面板 → 安全 → 系统防火墙
2. 添加端口规则：
   - 端口：`8000`
   - 协议：`TCP`
   - 策略：`放行`
   - 方向：`入站`
   - 来源：`0.0.0.0`

### 3. 阿里云安全组未开放端口

**解决方法**：
1. 阿里云控制台 → ECS → 你的服务器
2. 安全组 → 配置规则
3. 添加入方向规则：
   - 端口：`8000/8000`
   - 授权对象：`0.0.0.0/0`

### 4. 系统防火墙（iptables/firewalld）

**检查方法**：
```bash
# CentOS/RHEL
firewall-cmd --list-ports
firewall-cmd --list-all

# Ubuntu/Debian
ufw status
```

**解决方法**：
```bash
# CentOS
firewall-cmd --permanent --add-port=8000/tcp
firewall-cmd --reload

# Ubuntu
ufw allow 8000/tcp
```

---

## 🚀 快速修复步骤

### 步骤 1: 检查监听地址

在服务器上运行：
```bash
python3 check_listening.py
```

或手动检查：
```bash
netstat -tlnp | grep :8000
```

### 步骤 2: 如果只监听 127.0.0.1

**修改 Supervisor 配置**：

1. 宝塔面板 → Supervisor → 找到 `guidelab-pysr`
2. 编辑启动命令：
   ```bash
   # 修改前（可能）
   /usr/bin/python3 /www/wwwroot/physics_center/pysr_module/main.py --port 8000
   
   # 修改后（确保有 --host 0.0.0.0）
   /usr/bin/python3 /www/wwwroot/physics_center/pysr_module/main.py --host 0.0.0.0 --port 8000
   ```
3. 保存并重启

**或修改 `main.py` 默认值**（如果 Supervisor 没指定 host）：

```python
# 在 main.py 中
parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to run the service on")
```

### 步骤 3: 开放防火墙端口

**宝塔面板**：
- 安全 → 系统防火墙 → 添加端口规则
- 端口：`8000`，协议：`TCP`，策略：`放行`，方向：`入站`

**阿里云安全组**：
- ECS → 安全组 → 添加入方向规则
- 端口：`8000/8000`，授权对象：`0.0.0.0/0`

### 步骤 4: 重启服务

```bash
# Supervisor 重启
supervisorctl restart guidelab-pysr

# 或手动
pkill -f "main.py"
cd /www/wwwroot/physics_center/pysr_module
python3 main.py --host 0.0.0.0 --port 8000
```

### 步骤 5: 验证

```bash
# 在服务器上测试外部 IP
curl http://47.94.229.183:8000/

# 应该返回 JSON 响应
```

---

## 📋 完整检查清单

- [ ] 服务监听在 `0.0.0.0:8000`（不是 `127.0.0.1:8000`）
- [ ] 宝塔防火墙已开放 8000 端口
- [ ] 阿里云安全组已开放 8000 端口
- [ ] 系统防火墙已开放 8000 端口（如果有）
- [ ] 服务已重启
- [ ] 外部 curl 测试成功

---

## 🧪 测试命令

```bash
# 1. 检查监听地址
netstat -tlnp | grep :8000

# 2. 测试本地
curl http://localhost:8000/

# 3. 测试外部（在服务器上）
curl http://47.94.229.183:8000/

# 4. 检查防火墙
firewall-cmd --list-ports  # CentOS
ufw status  # Ubuntu
```

---

**按照这个顺序检查，一定能找到问题！** 🔍

