#!/bin/bash
cd /root/findyou
if [ -f app.pid ]; then
    kill $(cat app.pid) 2>/dev/null && echo "已停止" || echo "进程不存在"
    rm -f app.pid
fi
pkill -f "python.*findyou/app.py" 2>/dev/null
