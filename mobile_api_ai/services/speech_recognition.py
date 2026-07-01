# -*- coding: utf-8 -*-
"""
语音识别服务 - 企业微信 media/get 接口 + 第三方 ASR
支持格式：amr/silk/opus/mp3
"""
import os
import io
import requests
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class SpeechRecognitionService:
    """
    语音识别服务
    使用企业微信自带接口下载语音，再转发第三方 ASR 识别
    """

    def __init__(self):
        self.mode = os.getenv('AI_MODE', 'mock')
        self.asr_api_url = os.getenv('ASR_API_URL', '')
        self.asr_api_key = os.getenv('ASR_API_KEY', '')

    def recognize(self, media_id: str, bot=None) -> Dict[str, Any]:
        """
        通过 media_id 识别语音

        Args:
            media_id: 企业微信语音消息的 media_id
            bot: WeChatAppBot 实例，用于下载语音文件

        Returns:
            {
                'success': bool,
                'text': str,
                'confidence': float,
                'mode': str
            }
        """
        if self.mode == 'mock' or not bot:
            return self._mock_recognize()

        audio_data, filename = self._download_voice(media_id, bot)
        if not audio_data:
            return {
                'success': False,
                'text': '',
                'confidence': 0.0,
                'mode': 'wechat',
                'error': '下载语音文件失败'
            }

        if self.asr_api_url and self.asr_api_key:
            return self._call_asr_api(audio_data, filename)
        else:
            return self._mock_recognize()

    def _download_voice(self, media_id: str, bot) -> tuple:
        """
        通过企业微信应用机器人下载语音文件

        Args:
            media_id: 媒体文件ID
            bot: WeChatAppBot 实例

        Returns:
            (bytes, filename)
        """
        try:
            data, filename = bot.get_media(media_id)
            if data:
                logger.info(f"[SpeechRecognition] 下载语音成功: {filename}, 大小: {len(data)} bytes")
            return data, filename
        except Exception as e:
            logger.error(f"[SpeechRecognition] 下载语音异常: {e}")
            return None, None

    def _call_asr_api(self, audio_data: bytes, filename: str) -> Dict[str, Any]:
        """
        调用第三方 ASR 接口识别语音

        Args:
            audio_data: 语音文件内容
            filename: 文件名

        Returns:
            ASR 识别结果
        """
        try:
            files = {'file': (filename, io.BytesIO(audio_data), 'audio/amr')}
            headers = {'Authorization': f'Bearer {self.asr_api_key}'}
            resp = requests.post(self.asr_api_url, files=files, headers=headers, timeout=int(os.environ.get('REQUEST_TIMEOUT_LONG', '15')))
            if resp.status_code == 200:
                result = resp.json()
                return {
                    'success': True,
                    'text': result.get('text', ''),
                    'confidence': result.get('confidence', 0.9),
                    'mode': 'asr_api'
                }
            else:
                logger.error(f"[SpeechRecognition] ASR 接口返回错误: {resp.status_code}")
                return {
                    'success': False,
                    'text': '',
                    'confidence': 0.0,
                    'mode': 'asr_api',
                    'error': f'HTTP {resp.status_code}'
                }
        except requests.exceptions.Timeout:
            logger.error("[SpeechRecognition] ASR 接口请求超时")
            return {
                'success': False,
                'text': '',
                'confidence': 0.0,
                'mode': 'asr_api',
                'error': 'ASR 请求超时'
            }
        except Exception as e:
            logger.error(f"[SpeechRecognition] ASR 接口调用异常: {e}")
            return {
                'success': False,
                'text': '',
                'confidence': 0.0,
                'mode': 'asr_api',
                'error': str(e)
            }

    def _mock_recognize(self) -> Dict[str, Any]:
        """
        模拟识别（开发测试用）
        实际生产中配置 ASR_API_URL 和 ASR_API_KEY 即可启用真实识别
        """
        return {
            'success': True,
            'text': '裁剪200米完成了',
            'confidence': 0.92,
            'mode': 'mock',
            'note': '模拟模式，请配置 ASR_API_URL + ASR_API_KEY 启用真实识别'
        }


speech_service = SpeechRecognitionService()
