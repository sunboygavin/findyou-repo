#!/bin/bash
APP_DIR="/root/findyou"
cd $APP_DIR

# 创建虚拟环境
if [ ! -d "venv" ]; then
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# 停止旧进程
if [ -f app.pid ]; then
    kill $(cat app.pid) 2>/dev/null
    rm -f app.pid
fi
pkill -f "python.*findyou/app.py" 2>/dev/null
sleep 1

# 启动
nohup python3 app.py > app.log 2>&1 &
echo $! > app.pid
sleep 2

if ps -p $(cat app.pid) > /dev/null 2>&1; then
    echo "✓ Findyou 已启动 → http://0.0.0.0:5001"
else
    echo "✗ 启动失败，查看 app.log"
    exit 1
fi
