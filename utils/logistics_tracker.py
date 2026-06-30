# -*- coding: utf-8 -*-
"""
物流追踪核心模块
支持快递100和快递鸟两个API平台
提供实时查询和订阅推送两种模式
"""
import json
import time
import hashlib
import hmac
import base64
import urllib.parse
import threading
import logging
from datetime import datetime

import requests

logger = logging.getLogger(__name__)

LOGISTICS_COMPANY_CODES = {
    "顺丰速运": {"kuaidi100": "shunfeng", "kdniao": "SF"},
    "中通快递": {"kuaidi100": "zhongtong", "kdniao": "ZTO"},
    "圆通速递": {"kuaidi100": "yuantong", "kdniao": "YTO"},
    "韵达快递": {"kuaidi100": "yunda", "kdniao": "YD"},
    "德邦物流": {"kuaidi100": "debangwuliu", "kdniao": "DBL"},
    "安能物流": {"kuaidi100": "annengwuliu", "kdniao": "ANE"},
    "申通快递": {"kuaidi100": "shentong", "kdniao": "STO"},
    "极兔速递": {"kuaidi100": "jtexpress", "kdniao": "JTSD"},
    "京东物流": {"kuaidi100": "jd", "kdniao": "JD"},
    "邮政EMS": {"kuaidi100": "ems", "kdniao": "EMS"},
    "天地华宇": {"kuaidi100": "tiandihuayu", "kdniao": "HOAU"},
    "佳吉快运": {"kuaidi100": "jiajiwuliu", "kdniao": "JJKY"},
    "货拉拉": {"kuaidi100": "huolala", "kdniao": "HLL"},
}

TRACKING_STATE_MAP = {
    "0": "暂无轨迹",
    "1": "已揽收",
    "2": "运输中",
    "3": "已签收",
    "4": "问题件",
    "5": "转投",
    "6": "清关中",
    "7": "妥投",
    "10": "待取件",
    "14": "拒签",
}


def get_company_code(company_name, platform="kuaidi100"):
    """根据物流公司名称获取对应平台的编码"""
    codes = LOGISTICS_COMPANY_CODES.get(company_name)
    if codes:
        return codes.get(platform, "")
    return ""


def get_company_name_by_code(code, platform="kuaidi100"):
    """根据平台编码反查物流公司名称"""
    for name, codes in LOGISTICS_COMPANY_CODES.items():
        if codes.get(platform) == code:
            return name
    return ""


def state_text(state_code):
    """将物流状态码转为中文描述"""
    return TRACKING_STATE_MAP.get(str(state_code), f"未知状态({state_code})")


class TrackingConfig:
    """物流追踪API配置管理"""

    _instance = None
    _config_file = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._data = {}
        return cls._instance

    @classmethod
    def set_config_file(cls, filepath):
        cls._config_file = filepath

    def _load_env_file(self, env_path):
        """从.env文件加载配置"""
        import os
        if not os.path.exists(env_path):
            return
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" not in line:
                        continue
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip()
                    if not value:
                        continue
                    env_map = {
                        "LOGISTICS_PLATFORM": "platform",
                        "LOGISTICS_KD100_CUSTOMER": "kuaidi100_customer",
                        "LOGISTICS_KD100_KEY": "kuaidi100_key",
                        "LOGISTICS_KD100_CALLBACK_URL": "kuaidi100_callback_url",
                        "LOGISTICS_KDNIAO_EBUSINESS_ID": "kdniao_ebusiness_id",
                        "LOGISTICS_KDNIAO_API_KEY": "kdniao_api_key",
                        "LOGISTICS_KDNIAO_CALLBACK_URL": "kdniao_callback_url",
                    }
                    mapped_key = env_map.get(key)
                    if mapped_key and mapped_key not in self._data:
                        self._data[mapped_key] = value
        except Exception:
            pass

    def load(self):
        """从配置文件加载API密钥（优先级: .env > json配置文件）"""
        import os
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        if self._config_file:
            try:
                with open(self._config_file, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except Exception:
                self._data = {}

        json_path = self._config_file or os.path.join(base_dir, "logistics_api_config.json")
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._data.update(data)
            except Exception:
                pass

        env_path = os.path.join(base_dir, ".env")
        self._load_env_file(env_path)

    def save(self):
        """保存配置到文件"""
        if not self._config_file:
            import os
            self._config_file = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "logistics_api_config.json"
            )
        with open(self._config_file, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    @property
    def platform(self):
        return self._data.get("platform", "kuaidi100")

    @platform.setter
    def platform(self, value):
        self._data["platform"] = value

    @property
    def kuaidi100_customer(self):
        return self._data.get("kuaidi100_customer", "")

    @kuaidi100_customer.setter
    def kuaidi100_customer(self, value):
        self._data["kuaidi100_customer"] = value

    @property
    def kuaidi100_key(self):
        return self._data.get("kuaidi100_key", "")

    @kuaidi100_key.setter
    def kuaidi100_key(self, value):
        self._data["kuaidi100_key"] = value

    @property
    def kuaidi100_callback_url(self):
        return self._data.get("kuaidi100_callback_url", "")

    @kuaidi100_callback_url.setter
    def kuaidi100_callback_url(self, value):
        self._data["kuaidi100_callback_url"] = value

    @property
    def kdniao_ebusiness_id(self):
        return self._data.get("kdniao_ebusiness_id", "")

    @kdniao_ebusiness_id.setter
    def kdniao_ebusiness_id(self, value):
        self._data["kdniao_ebusiness_id"] = value

    @property
    def kdniao_api_key(self):
        return self._data.get("kdniao_api_key", "")

    @kdniao_api_key.setter
    def kdniao_api_key(self, value):
        self._data["kdniao_api_key"] = value

    @property
    def kdniao_callback_url(self):
        return self._data.get("kdniao_callback_url", "")

    @kdniao_callback_url.setter
    def kdniao_callback_url(self, value):
        self._data["kdniao_callback_url"] = value

    def is_configured(self):
        """检查当前平台是否已配置API密钥"""
        if self.platform == "kuaidi100":
            return bool(self.kuaidi100_customer and self.kuaidi100_key)
        elif self.platform == "kdniao":
            return bool(self.kdniao_ebusiness_id and self.kdniao_api_key)
        return False

    def get_config_info(self):
        """获取当前配置摘要（隐藏敏感信息）"""
        info = {"platform": self.platform}
        if self.platform == "kuaidi100":
            info["customer"] = self.kuaidi100_customer[:4] + "****" if self.kuaidi100_customer else "未配置"
            info["key"] = "已配置" if self.kuaidi100_key else "未配置"
        elif self.platform == "kdniao":
            info["ebusiness_id"] = self.kdniao_ebusiness_id[:4] + "****" if self.kdniao_ebusiness_id else "未配置"
            info["api_key"] = "已配置" if self.kdniao_api_key else "未配置"
        return info


class Kuaidi100Tracker:
    """快递100物流追踪"""

    QUERY_URL = "https://poll.kuaidi100.com/poll/query.do"
    SUBSCRIBE_URL = "https://poll.kuaidi100.com/poll"
    AUTO_DETECT_URL = "https://www.kuaidi100.com/autonumber/autoComNum"

    def __init__(self, config: TrackingConfig):
        self.config = config

    def _generate_sign(self, param_json_str):
        """生成签名 (HMAC-SHA256)"""
        key = self.config.kuaidi100_key.encode("utf-8")
        msg = (param_json_str + self.config.kuaidi100_key).encode("utf-8")
        sign = hmac.new(key, msg, hashlib.sha256).hexdigest()
        return sign

    def query(self, tracking_no, company_name="", phone=""):
        """实时查询物流轨迹

        Args:
            tracking_no: 运单号
            company_name: 物流公司名称（可选，为空时自动识别）
            phone: 收/寄件人手机号（顺丰必填后4位）

        Returns:
            dict: {"success": bool, "state": str, "traces": [...], "message": str}
        """
        if not self.config.is_configured():
            return {"success": False, "state": "", "traces": [], "message": "API未配置，请先在设置中配置快递100密钥"}

        company_code = get_company_code(company_name, "kuaidi100") if company_name else ""

        if not company_code:
            auto_result = self.auto_detect(tracking_no)
            if auto_result:
                company_code = auto_result

        param = {
            "num": tracking_no,
        }
        if company_code:
            param["com"] = company_code
        if phone:
            param["phone"] = phone

        param_str = json.dumps(param, ensure_ascii=False)
        sign = self._generate_sign(param_str)

        data = {
            "customer": self.config.kuaidi100_customer,
            "sign": sign,
            "param": param_str,
        }

        try:
            resp = requests.post(self.QUERY_URL, data=data, timeout=15)
            result = resp.json()

            if result.get("status") == "200" or result.get("data"):
                traces = result.get("data", [])
                state = result.get("state", "0")
                return {
                    "success": True,
                    "state": state,
                    "state_text": state_text(state),
                    "traces": traces,
                    "company": result.get("com", company_code),
                    "tracking_no": tracking_no,
                    "message": "查询成功",
                }
            else:
                return_code = result.get("returnCode", "500")
                return_msg = result.get("message", "查询失败")
                return {
                    "success": False,
                    "state": "0",
                    "traces": [],
                    "message": f"查询失败({return_code}): {return_msg}",
                }
        except requests.Timeout:
            return {"success": False, "state": "", "traces": [], "message": "查询超时，请检查网络连接"}
        except Exception as e:
            logger.error(f"快递100查询异常: {e}")
            return {"success": False, "state": "", "traces": [], "message": f"查询异常: {str(e)}"}

    def subscribe(self, tracking_no, company_name="", callback_url="", phone=""):
        """订阅物流推送

        Args:
            tracking_no: 运单号
            company_name: 物流公司名称
            callback_url: 回调地址
            phone: 手机号（顺丰必填）

        Returns:
            dict: {"success": bool, "message": str}
        """
        if not self.config.is_configured():
            return {"success": False, "message": "API未配置"}

        company_code = get_company_code(company_name, "kuaidi100") if company_name else ""
        if not company_code:
            auto_result = self.auto_detect(tracking_no)
            if auto_result:
                company_code = auto_result

        cb_url = callback_url or self.config.kuaidi100_callback_url
        if not cb_url:
            return {"success": False, "message": "订阅推送需要配置回调地址"}

        param = {
            "company": company_code,
            "number": tracking_no,
            "key": self.config.kuaidi100_key,
            "parameters": {
                "callbackurl": cb_url,
                "resultv2": "4",
            },
        }
        if phone:
            param["parameters"]["phone"] = phone

        param_str = json.dumps(param, ensure_ascii=False)

        data = {
            "schema": "json",
            "param": param_str,
        }

        try:
            resp = requests.post(self.SUBSCRIBE_URL, data=data, timeout=15)
            result = resp.json()

            if result.get("result"):
                return {"success": True, "message": result.get("message", "订阅成功")}
            else:
                return_code = result.get("returnCode", 500)
                return_msg = result.get("message", "订阅失败")
                return {"success": False, "message": f"订阅失败({return_code}): {return_msg}"}
        except Exception as e:
            logger.error(f"快递100订阅异常: {e}")
            return {"success": False, "message": f"订阅异常: {str(e)}"}

    def auto_detect(self, tracking_no):
        """自动识别运单号所属快递公司"""
        try:
            resp = requests.post(
                self.AUTO_DETECT_URL,
                data={"logisticCode": tracking_no},
                timeout=10,
            )
            result = resp.json()
            auto_list = result.get("auto", [])
            if auto_list:
                return auto_list[0].get("comCode", "")
        except Exception:
            pass
        return ""


class KdniaoTracker:
    """快递鸟物流追踪"""

    QUERY_URL = "https://api.kdniao.com/Ebusiness/EbusinessOrderHandle.aspx"
    SUBSCRIBE_URL = "https://api.kdniao.com/Ebusiness/EbusinessOrderHandle.aspx"

    QUERY_TYPE = "1002"
    SUBSCRIBE_TYPE = "1008"

    def __init__(self, config: TrackingConfig):
        self.config = config

    def _generate_sign(self, data_str):
        """生成签名 (MD5 + Base64)"""
        h = hashlib.md5((data_str + self.config.kdniao_api_key).encode("utf-8")).digest()
        return base64.b64encode(h).decode("utf-8").strip()

    def query(self, tracking_no, company_name=""):
        """实时查询物流轨迹

        Args:
            tracking_no: 运单号
            company_name: 物流公司名称

        Returns:
            dict: {"success": bool, "state": str, "traces": [...], "message": str}
        """
        if not self.config.is_configured():
            return {"success": False, "state": "", "traces": [], "message": "API未配置，请先在设置中配置快递鸟密钥"}

        company_code = get_company_code(company_name, "kdniao") if company_name else ""
        if not company_code:
            return {"success": False, "state": "", "traces": [], "message": "请指定物流公司名称"}

        req_data = json.dumps({
            "OrderCode": "",
            "ShipperCode": company_code,
            "LogisticCode": tracking_no,
        }, ensure_ascii=False)

        data_sign = self._generate_sign(req_data)

        payload = {
            "RequestData": urllib.parse.quote(req_data),
            "EBusinessID": self.config.kdniao_ebusiness_id,
            "RequestType": self.QUERY_TYPE,
            "DataSign": urllib.parse.quote(data_sign),
            "DataType": "2",
        }

        try:
            resp = requests.post(self.QUERY_URL, data=payload, timeout=15)
            result = resp.json()

            if result.get("Success"):
                traces = result.get("Traces", [])
                state = result.get("State", "0")
                formatted_traces = []
                for t in traces:
                    formatted_traces.append({
                        "time": t.get("AcceptTime", ""),
                        "ftime": t.get("AcceptTime", ""),
                        "context": t.get("AcceptStation", ""),
                        "location": "",
                    })
                return {
                    "success": True,
                    "state": state,
                    "state_text": state_text(state),
                    "traces": formatted_traces,
                    "company": company_code,
                    "tracking_no": tracking_no,
                    "message": "查询成功",
                    "ebusiness_id": result.get("EBusinessID", ""),
                }
            else:
                reason = result.get("Reason", "查询失败")
                return {
                    "success": False,
                    "state": "0",
                    "traces": [],
                    "message": f"查询失败: {reason}",
                }
        except requests.Timeout:
            return {"success": False, "state": "", "traces": [], "message": "查询超时，请检查网络连接"}
        except Exception as e:
            logger.error(f"快递鸟查询异常: {e}")
            return {"success": False, "state": "", "traces": [], "message": f"查询异常: {str(e)}"}

    def subscribe(self, tracking_no, company_name="", callback_url=""):
        """订阅物流推送

        Args:
            tracking_no: 运单号
            company_name: 物流公司名称
            callback_url: 回调地址

        Returns:
            dict: {"success": bool, "message": str}
        """
        if not self.config.is_configured():
            return {"success": False, "message": "API未配置"}

        company_code = get_company_code(company_name, "kdniao") if company_name else ""
        if not company_code:
            return {"success": False, "message": "请指定物流公司名称"}

        cb_url = callback_url or self.config.kdniao_callback_url
        if not cb_url:
            return {"success": False, "message": "订阅推送需要配置回调地址"}

        req_data = json.dumps({
            "OrderCode": "",
            "ShipperCode": company_code,
            "LogisticCode": tracking_no,
            "PayMode": "1",
        }, ensure_ascii=False)

        data_sign = self._generate_sign(req_data)

        payload = {
            "RequestData": urllib.parse.quote(req_data),
            "EBusinessID": self.config.kdniao_ebusiness_id,
            "RequestType": self.SUBSCRIBE_TYPE,
            "DataSign": urllib.parse.quote(data_sign),
            "DataType": "2",
        }

        try:
            resp = requests.post(self.SUBSCRIBE_URL, data=payload, timeout=15)
            result = resp.json()

            if result.get("Success"):
                return {"success": True, "message": "订阅成功"}
            else:
                reason = result.get("Reason", "订阅失败")
                return {"success": False, "message": f"订阅失败: {reason}"}
        except Exception as e:
            logger.error(f"快递鸟订阅异常: {e}")
            return {"success": False, "message": f"订阅异常: {str(e)}"}


class LogisticsTracker:
    """物流追踪统一入口"""

    def __init__(self):
        self.config = TrackingConfig()
        self.config.load()
        self._kuaidi100 = Kuaidi100Tracker(self.config)
        self._kdniao = KdniaoTracker(self.config)

    @property
    def current_tracker(self):
        """获取当前平台的追踪器"""
        if self.config.platform == "kdniao":
            return self._kdniao
        return self._kuaidi100

    def query(self, tracking_no, company_name="", phone="", callback=None):
        """实时查询物流轨迹（后台线程执行）

        Args:
            tracking_no: 运单号
            company_name: 物流公司名称
            phone: 手机号
            callback: 查询完成回调 callback(result_dict)
        """
        if not tracking_no:
            result = {"success": False, "state": "", "traces": [], "message": "运单号不能为空"}
            if callback:
                callback(result)
            return result

        def _do_query():
            result = self.current_tracker.query(tracking_no, company_name, phone)
            if callback:
                callback(result)

        thread = threading.Thread(target=_do_query, daemon=True)
        thread.start()
        return {"success": True, "state": "", "traces": [], "message": "正在查询中..."}

    def query_sync(self, tracking_no, company_name="", phone=""):
        """同步查询物流轨迹（阻塞调用）

        Args:
            tracking_no: 运单号
            company_name: 物流公司名称
            phone: 手机号

        Returns:
            dict: 查询结果
        """
        if not tracking_no:
            return {"success": False, "state": "", "traces": [], "message": "运单号不能为空"}
        return self.current_tracker.query(tracking_no, company_name, phone)

    def subscribe(self, tracking_no, company_name="", callback_url="", phone=""):
        """订阅物流推送

        Args:
            tracking_no: 运单号
            company_name: 物流公司名称
            callback_url: 回调地址
            phone: 手机号

        Returns:
            dict: {"success": bool, "message": str}
        """
        if not tracking_no:
            return {"success": False, "message": "运单号不能为空"}
        return self.current_tracker.subscribe(tracking_no, company_name, callback_url, phone)

    def is_configured(self):
        """检查API是否已配置"""
        return self.config.is_configured()

    def get_config_info(self):
        """获取当前配置摘要"""
        return self.config.get_config_info()

    def save_tracking_result(self, shipment_id, result):
        """保存查询结果到数据库

        Args:
            shipment_id: 发货单ID
            result: 查询结果dict
        """
        try:
            from models.database import get_connection
            conn = get_connection()
            cursor = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            traces_json = json.dumps(result.get("traces", []), ensure_ascii=False)
            cursor.execute("""
                INSERT INTO shipment_tracks
                (shipment_id, tracking_no, state, state_text, traces, company_code, query_time)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                shipment_id,
                result.get("tracking_no", ""),
                result.get("state", "0"),
                result.get("state_text", ""),
                traces_json,
                result.get("company", ""),
                now,
            ))
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            logger.error(f"保存追踪结果失败: {e}")

    def get_tracking_history(self, shipment_id, limit=5):
        """获取发货单的追踪历史

        Args:
            shipment_id: 发货单ID
            limit: 返回条数

        Returns:
            list: 追踪记录列表
        """
        try:
            from models.database import get_connection
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, shipment_id, tracking_no, state, state_text,
                       traces, company_code, query_time
                FROM shipment_tracks
                WHERE shipment_id = %s
                ORDER BY query_time DESC
                LIMIT %s
            """, (shipment_id, limit))
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            results = []
            for row in rows:
                if isinstance(row, dict):
                    r = row
                else:
                    r = {
                        "id": row[0],
                        "shipment_id": row[1],
                        "tracking_no": row[2],
                        "state": row[3],
                        "state_text": row[4],
                        "traces": json.loads(row[5]) if row[5] else [],
                        "company_code": row[6],
                        "query_time": row[7],
                    }
                    try:
                        r["traces"] = json.loads(row[5]) if row[5] else []
                    except (json.JSONDecodeError, TypeError):
                        r["traces"] = []
                results.append(r)
            return results
        except Exception as e:
            logger.error(f"获取追踪历史失败: {e}")
            return []


_tracker_instance = None


def get_tracker():
    """获取物流追踪器单例"""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = LogisticsTracker()
    return _tracker_instance
