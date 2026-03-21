#!/bin/bash
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$APP_DIR"

# Load .env if exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
    echo "✓ 已加载 .env"
fi

# Create virtual environment if needed
if [ ! -d "venv" ]; then
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Stop old process
if [ -f app.pid ]; then
    kill $(cat app.pid) 2>/dev/null
    rm -f app.pid
fi
pkill -f "python.*app.py" 2>/dev/null
sleep 1

# Start
nohup python3 app.py > app.log 2>&1 &
echo $! > app.pid
sleep 2

if ps -p $(cat app.pid) > /dev/null 2>&1; then
    echo "✓ Findyou 已启动 → http://0.0.0.0:5001"
    echo "  PID: $(cat app.pid)"
    echo "  日志: tail -f app.log"
else
    echo "✗ 启动失败，查看 app.log"
    exit 1
fi
