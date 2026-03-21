#!/bin/bash
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$APP_DIR"

if [ -f app.pid ]; then
    PID=$(cat app.pid)
    kill "$PID" 2>/dev/null && echo "✓ 已停止 (PID: $PID)" || echo "进程不存在"
    rm -f app.pid
else
    echo "没有找到 PID 文件"
fi
pkill -f "python.*app.py" 2>/dev/null
