# 服务器启动状态

> 更新时间: 2026-01-12

## 🚀 服务已启动

### 后端服务器
- **地址**: http://localhost:8090
- **API 文档**: http://localhost:8090/docs
- **健康检查**: http://localhost:8090/health
- **状态**: ✅ 运行中

### 前端开发服务器
- **地址**: http://localhost:5173
- **后端代理**: http://localhost:8090/api
- **状态**: ✅ 运行中

## 📋 启动命令

### 方法 1: 使用启动脚本（推荐）

```bash
# 启动后端
./start_backend.sh

# 启动前端（新终端）
./start_frontend.sh

# 或同时启动（新终端）
./start_all.sh
```

### 方法 2: 手动启动

```bash
# 终端 1: 启动后端
cd /home/lz/repo/PageIndex
source .venv/bin/activate
python -m md2tree.openindex.app

# 终端 2: 启动前端
cd /home/lz/repo/PageIndex/md2tree/openindex/frontend
npm run dev
```

## 🔍 测试端点

### 健康检查
```bash
curl http://localhost:8090/health
```

### API 文档
打开浏览器访问: http://localhost:8090/docs

### 系统指标
```bash
curl http://localhost:8090/api/stats
```

## 🛑 停止服务

按 `Ctrl+C` 停止当前终端中的服务，或使用：

```bash
# 查找进程
ps aux | grep -E "(uvicorn|vite)"

# 停止进程（替换 PID）
kill <PID>
```

---

*服务已启动，可以开始测试！*
