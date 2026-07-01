@echo off
chcp 65001 > nul
cd /d "d:\yuan\不锈钢网带跟单3.0\mobile_api_ai"
start "cloud_relay_5005" /B python cloud_relay.py
echo cloud_relay.py started
