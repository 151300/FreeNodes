@echo off
:: hb/start_hb.bat

echo 🚀 启动节点处理系统
echo 当前时间: %date% %time%
echo.

echo 📦 检查Python依赖...
python -c "import yaml" 2>nul || pip install pyyaml

echo 📁 检查目录结构...
mkdir nodes 2>nul
mkdir hb\output 2>nul
mkdir hb\backup 2>nul
mkdir hb\logs 2>nul

echo 🔄 运行节点处理...
cd /d "%~dp0.."
python hb\runner.py --force

echo.
echo ✅ 启动完成
echo 输出文件在: hb\output\
echo 日志文件在: hb\logs\
pause
