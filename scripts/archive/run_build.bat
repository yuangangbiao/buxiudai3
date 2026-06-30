@echo off
cd /d "d:\yuan\不锈钢网带跟单3.0"
echo Starting build...
python full_build_client.py > build_log.txt 2>&1
echo Build completed. Check build_log.txt
type build_log.txt
