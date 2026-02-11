#!/bin/bash
# hb/start_hb.sh

echo "🚀 启动节点处理系统"
echo "当前时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# 检查依赖
echo "📦 检查Python依赖..."
python3 -c "import yaml" 2>/dev/null || pip3 install pyyaml

# 检查目录结构
echo "📁 检查目录结构..."
mkdir -p nodes hb/output hb/backup hb/logs

# 运行处理器
echo "🔄 运行节点处理..."
cd "$(dirname "$0")/.."
python3 hb/runner.py --force

echo ""
echo "✅ 启动完成"
echo "输出文件在: hb/output/"
echo "日志文件在: hb/logs/"
