﻿# -*- coding: utf-8 -*-
"""
鎸囦护鍖归厤寮曟搸 - 涓ユ牸寮€澶?+ 鏍煎紡鏍￠獙 + 鍙嬪ソ鎻愮ず
"""

import re
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class MatchMethod(Enum):
    PREFIX = "prefix"
    FORMAT = "format"
    NONE = "none"


class CommandType(Enum):
    REPORT = "report"                     # 鎶ュ伐
    PROCESS_COMPLETE = "process_complete"  # 宸ュ簭瀹屾垚
    ORDER_COMPLETE = "order_complete"     # 璁㈠崟瀹屾垚
    INSPECTION_QUERY = "inspection_query"  # 妫€楠屾煡璇?    REPORT_FIRST_INSPECTION = "report_first_inspection"  # 鎶ラ妫€
    REPORT_PATROL_INSPECTION = "report_patrol_inspection"  # 鎶ュ贰妫€
    REPORT_FINAL_INSPECTION = "report_final_inspection"  # 鎶ョ粓妫€
    CONFIRM = "confirm"                   # 纭
    QUERY_ORDER = "query_order"           # 鏌ヨ宸ュ崟
    QUERY_ORDER_MATERIAL = "query_order_material"  # 鏌ヨ宸ュ崟鐗╂枡
    QUERY_PROCESS = "query_process"        # 鏌ヨ宸ュ簭
    CANCEL = "cancel"                     # 鍙栨秷
    REPORT_REPAIR = "report_repair"        # 鎶ヤ慨
    REPAIR_COMPLETE = "repair_complete"   # 缁翠慨瀹屾垚
    REPAIR_SUPPLY = "repair_supply"       # 缁翠慨琛ュ厖
    QUERY_REPAIR = "query_repair"         # 鏌ヨ缁翠慨
    APPLY_MATERIAL = "apply_material"     # 鐢宠鐗╂枡
    REPAIR_MATERIAL = "repair_material"    # 缁翠慨鐗╂枡
    OUTSOURCE_PROGRESS = "outsource_progress"  # 澶栧崗杩涘害
    OUTSOURCE_COMPLETE = "outsource_complete"  # 澶栧崗瀹屾垚
    OUTSOURCE_QC = "outsource_qc"         # 澶栧崗璐ㄦ
    QUERY_MATERIAL = "query_material"     # 鏌ヨ鐗╂枡
    PRODUCT_STOCK_IN = "product_stock_in"  # 鎴愬搧鍏ュ簱
    MATERIAL_SHIPMENT = "material_shipment"  # 鐗╂枡鍙戣揣
    MATERIAL_CREATE = "material_create"    # 鐗╂枡寤烘。
    MATERIAL_STOCK_IN = "material_stock_in"  # 鐗╂枡鍏ュ簱
    SCHEDULE_QUERY = "schedule_query"        # 鏌ヨ鎺掍骇
    SCHEDULE_NOTIFY = "schedule_notify"      # 鎺掍骇閫氱煡
    DO_SCHEDULE = "do_schedule"              # 杩涜鎺掍骇
    HELP_REQUEST = "help_request"         # 姹傚姪
    UNKNOWN = "unknown"


@dataclass
class MatchResult:
    command_type: CommandType
    params: Dict[str, Any]
    confidence: float
    match_method: MatchMethod
    original_content: str
    matched_keyword: str
    error_message: str = ""


class InstructionMatcher:
    """
    鎸囦护鍖归厤寮曟搸

    - 涓ユ牸鍖归厤鎸囦护寮€澶?    - 鏍煎紡鏍￠獙鍙傛暟
    - 宸窛澶ぇ杩斿洖鍙嬪ソ鎻愮ず
    """

    PREFIX_COMMANDS = {
        '鎶?: CommandType.REPORT,
        '宸ュ簭瀹屾垚': CommandType.PROCESS_COMPLETE,
        '璁㈠崟瀹屾垚': CommandType.ORDER_COMPLETE,
        '妫€楠屾煡璇?: CommandType.INSPECTION_QUERY,
        '鎶ラ妫€': CommandType.REPORT_FIRST_INSPECTION,
        '鎶ュ贰妫€': CommandType.REPORT_PATROL_INSPECTION,
        '鎶ョ粓妫€': CommandType.REPORT_FINAL_INSPECTION,
        '纭': CommandType.CONFIRM,
        '鏌ヨ宸ュ崟': CommandType.QUERY_ORDER,
        '鏌ヨ宸ュ崟鐗╂枡': CommandType.QUERY_ORDER_MATERIAL,
        '鏌ヨ宸ュ簭': CommandType.QUERY_PROCESS,
        '鏌ヨ缁翠慨': CommandType.QUERY_REPAIR,
        '缁翠慨鏌ヨ': CommandType.QUERY_REPAIR,
        '鍙栨秷': CommandType.CANCEL,
        '鎶ヤ慨': CommandType.REPORT_REPAIR,
        '缁翠慨瀹屾垚': CommandType.REPAIR_COMPLETE,
        '缁翠慨琛ュ厖': CommandType.REPAIR_SUPPLY,
        '鐢宠鐗╂枡': CommandType.APPLY_MATERIAL,
        '缁翠慨鐗╂枡': CommandType.REPAIR_MATERIAL,
        '澶栧崗杩涘害': CommandType.OUTSOURCE_PROGRESS,
        '澶栧崗瀹屾垚': CommandType.OUTSOURCE_COMPLETE,
        '澶栧崗璐ㄦ': CommandType.OUTSOURCE_QC,
        '鏌ヨ鐗╂枡': CommandType.QUERY_MATERIAL,
        '鎴愬搧鍏ュ簱': CommandType.PRODUCT_STOCK_IN,
        '鐗╂枡鍙戣揣': CommandType.MATERIAL_SHIPMENT,
        '鐗╂枡寤烘。': CommandType.MATERIAL_CREATE,
        '鐗╂枡鍏ュ簱': CommandType.MATERIAL_STOCK_IN,
        '鏌ヨ鎺掍骇': CommandType.SCHEDULE_QUERY,
        '鎺掍骇閫氱煡': CommandType.SCHEDULE_NOTIFY,
        '杩涜鎺掍骇': CommandType.DO_SCHEDULE,
        '姹傚姪': CommandType.HELP_REQUEST,
    }

    SORTED_PREFIXES = sorted(PREFIX_COMMANDS.keys(), key=len, reverse=True)

    FORMAT_HELP = {
        CommandType.REPORT: "鏍煎紡: 鎶?宸ュ崟鍙?宸ュ簭鍚嶇О+鏁伴噺+鍗曚綅\n绀轰緥: 鎶BC123+缂栫粐+100+浠?,
        CommandType.PROCESS_COMPLETE: "鏍煎紡: 宸ュ簭瀹屾垚+宸ュ崟鍙?宸ュ簭鍚嶇О\n绀轰緥: 宸ュ簭瀹屾垚+ABC123+缂栫粐",
        CommandType.ORDER_COMPLETE: "鏍煎紡: 璁㈠崟瀹屾垚+宸ュ崟鍙穃n绀轰緥: 璁㈠崟瀹屾垚+ABC123",
        CommandType.INSPECTION_QUERY: "鏍煎紡: 妫€楠屾煡璇?宸ュ崟鍙穃n绀轰緥: 妫€楠屾煡璇?ABC123",
        CommandType.REPORT_FIRST_INSPECTION: "鏍煎紡: 鎶ラ妫€+宸ュ崟鍙?妫€楠岄」+鍐呭+鍗曚綅\n绀轰緥: 鎶ラ妫€+ABC123+闀垮害+100+cm",
        CommandType.REPORT_PATROL_INSPECTION: "鏍煎紡: 鎶ュ贰妫€+宸ュ崟鍙?妫€楠岄」+鍐呭+鍗曚綅\n绀轰緥: 鎶ュ贰妫€+ABC123+瀹藉害+50+cm",
        CommandType.REPORT_FINAL_INSPECTION: "鏍煎紡: 鎶ョ粓妫€+宸ュ崟鍙?妫€楠岄」+鍐呭+鍗曚綅\n绀轰緥: 鎶ョ粓妫€+ABC123+鍘氬害+10+mm",
        CommandType.CONFIRM: "鏍煎紡: 纭+缂栧彿\n绀轰緥: 纭+001",
        CommandType.QUERY_ORDER: "鏍煎紡: 鏌ヨ宸ュ崟\n绀轰緥: 鏌ヨ宸ュ崟",
        CommandType.QUERY_ORDER_MATERIAL: "鏍煎紡: 鏌ヨ宸ュ崟鐗╂枡\n绀轰緥: 鏌ヨ宸ュ崟鐗╂枡",
        CommandType.QUERY_PROCESS: "鏍煎紡: 鏌ヨ宸ュ簭+宸ュ崟鍙穃n绀轰緥: 鏌ヨ宸ュ簭+ABC123",
        CommandType.CANCEL: "鏍煎紡: 鍙栨秷+宸ュ崟鍙?鍐呭\n绀轰緥: 鍙栨秷+ABC123+缂栫粐+100",
        CommandType.REPORT_REPAIR: "鏍煎紡: 鎶ヤ慨+鏁呴殰浣嶇疆+鏁呴殰鎻忚堪\n绀轰緥: 鎶ヤ慨+2鍙锋満+鍙橀鍣ㄦ姤璀?,
        CommandType.REPAIR_COMPLETE: "鏍煎紡: 缁翠慨瀹屾垚+缁翠慨宸ュ崟缂栧彿\n绀轰緥: 缁翠慨瀹屾垚+WX20260101001",
        CommandType.REPAIR_SUPPLY: "鏍煎紡: 缁翠慨琛ュ厖+缁翠慨宸ュ崟缂栧彿\n绀轰緥: 缁翠慨琛ュ厖+WX20260101001",
        CommandType.QUERY_REPAIR: "鏍煎紡: 鏌ヨ缁翠慨\n绀轰緥: 鏌ヨ缁翠慨",
        CommandType.APPLY_MATERIAL: "鏍煎紡: 鐢宠鐗╂枡+宸ュ崟鍙?鐗╂枡鍚嶇О+瑙勬牸\n绀轰緥: 鐢宠鐗╂枡+ABC123+閽㈢瓔+12mm",
        CommandType.REPAIR_MATERIAL: "鏍煎紡: 缁翠慨鐗╂枡+宸ュ崟鍙穃n绀轰緥: 缁翠慨鐗╂枡+ABC123",
        CommandType.OUTSOURCE_PROGRESS: "鏍煎紡: 澶栧崗杩涘害+宸ュ崟鍙?宸ュ簭/鐗╂枡+杩涘害+瀹屾垚鏃堕棿\n绀轰緥: 澶栧崗杩涘害+ABC123+鐒婃帴+80%+2026-01-15",
        CommandType.OUTSOURCE_COMPLETE: "鏍煎紡: 澶栧崗瀹屾垚+宸ュ崟鍙?宸ュ簭/鐗╂枡\n绀轰緥: 澶栧崗瀹屾垚+ABC123+鐒婃帴",
        CommandType.OUTSOURCE_QC: "鏍煎紡: 澶栧崗璐ㄦ+宸ュ崟鍙?宸ュ簭/鐗╂枡+缁撴灉\n绀轰緥: 澶栧崗璐ㄦ+ABC123+鐒婃帴+鍚堟牸",
        CommandType.QUERY_MATERIAL: "鏍煎紡: 鏌ヨ鐗╂枡+鍚嶇О\n绀轰緥: 鏌ヨ鐗╂枡+閽㈢瓔",
        CommandType.PRODUCT_STOCK_IN: "鏍煎紡: 鎴愬搧鍏ュ簱+宸ュ崟鍙穃n绀轰緥: 鎴愬搧鍏ュ簱+ABC123",
        CommandType.MATERIAL_SHIPMENT: "鏍煎紡: 鐗╂枡鍙戣揣+宸ュ崟鍙?鐗╂祦鍏徃+鐗╂祦鍙?鏁伴噺\n绀轰緥: 鐗╂枡鍙戣揣+ABC123+椤轰赴+SF123456789+100",
        CommandType.MATERIAL_CREATE: "鏍煎紡: 鐗╂枡寤烘。+鐗╁搧鍚嶇О+瑙勬牸+鍗曚綅+浠撳簱+鐢熶骇鍟?鑱旂郴鏂瑰紡\n绀轰緥: 鐗╂枡寤烘。+閽㈢瓔+12mm+鏍?A搴?瀹濋挗+13800138000",
        CommandType.MATERIAL_STOCK_IN: "鏍煎紡: 鐗╂枡鍏ュ簱+鐗╁搧鍚嶇О+瑙勬牸+鏁伴噺+鍗曚綅\n绀轰緥: 鐗╂枡鍏ュ簱+閽㈢瓔+12mm+100+鏍?,
        CommandType.SCHEDULE_QUERY: "鏍煎紡: 鏌ヨ鎺掍骇+宸ュ崟鍙穃n绀轰緥: 鏌ヨ鎺掍骇+ABC123",
        CommandType.SCHEDULE_NOTIFY: "鏍煎紡: 鎺掍骇閫氱煡\n绀轰緥: 鎺掍骇閫氱煡",
        CommandType.DO_SCHEDULE: "鏍煎紡: 杩涜鎺掍骇+宸ュ崟鍙?宸ユ湡澶╂暟\n绀轰緥: 杩涜鎺掍骇+WO001+15",
    }

    HELP_CATEGORY_KEYWORDS = {
        '鐗╂枡绫?: ['鐗╂枡', '鏉愭枡', '涓嶈冻', '缂哄皯', '闇€瑕佽ˉ鍏?, '娌℃枡', '缂鸿揣', '鍘熸枡', '寤烘。', '鍏ュ簱', '鍙戣揣'],
        '璁惧绫?: ['璁惧', '鏈哄櫒', '鏁呴殰', '鍧忎簡', '缁翠慨', '鍋滄満', '鏈哄彴', '鎹熷潖'],
        '璁㈠崟绫?: ['浜よ揣', '瀹㈡埛', '浜ゆ湡', '鎻愬墠', '寤惰繜', '璁㈠崟', '鍑鸿揣', '绱ф€?, '瀹屾垚'],
        '璐ㄩ噺绫?: ['璐ㄩ噺', '妫€楠?, '涓嶅悎鏍?, '杩斿伐', '鎶曡瘔', '涓嶈壇', '娆″搧', '閫€璐?, '棣栨', '宸℃', '缁堟'],
        '浜哄憳绫?: ['浜哄憳', '鍔犵彮', '璇峰亣', '浜烘墜涓嶈冻', '缂轰汉', '浜哄姏'],
        '澶栧崗绫?: ['澶栧崗', '渚涘簲鍟?, '澶栭潰鍔犲伐', '澶栧彂', '濮斿', '杩涘害', '璐ㄦ'],
        '鎺掍骇绫?: ['鎺掍骇', '璁″垝', '鎺掑崟', '鐢熶骇璁″垝', '鎺掔▼', '鎶曚骇'],
    }

    def get_help_text(self) -> str:
        """鑾峰彇瀹屾暣甯姪鏂囨湰"""
        helps = []
        for cmd_type, help_msg in self.FORMAT_HELP.items():
            helps.append(help_msg)
        return "\n\n".join(helps)

    def get_command_list(self) -> str:
        """鑾峰彇鎸囦护鍒楄〃"""
        commands = [
            "鎶?| 宸ュ簭瀹屾垚 | 璁㈠崟瀹屾垚",
            "妫€楠屾煡璇?| 鎶ラ妫€ | 鎶ュ贰妫€ | 鎶ョ粓妫€",
            "纭 | 鍙栨秷",
            "鏌ヨ宸ュ崟 | 鏌ヨ宸ュ崟鐗╂枡 | 鏌ヨ宸ュ簭",
            "鏌ヨ缁翠慨 | 缁翠慨鏌ヨ",
            "鎶ヤ慨 | 缁翠慨瀹屾垚 | 缁翠慨琛ュ厖",
            "鐢宠鐗╂枡 | 缁翠慨鐗╂枡",
            "澶栧崗杩涘害 | 澶栧崗瀹屾垚 | 澶栧崗璐ㄦ",
            "鏌ヨ鐗╂枡 | 鎴愬搧鍏ュ簱 | 鐗╂枡鍙戣揣 | 鐗╂枡寤烘。 | 鐗╂枡鍏ュ簱",
            "鏌ヨ鎺掍骇 | 鎺掍骇閫氱煡 | 杩涜鎺掍骇",
            "姹傚姪+鍐呭",
        ]
        return "鍙敤鎸囦护: " + " | ".join(commands)

    def match(self, content: str) -> MatchResult:
        """鎵ц鍖归厤"""
        content = content.strip()

        if not content:
            return self._error_result(content, "璇疯緭鍏ユ寚浠?, "")

        logger.info(f"[Matcher] 寮€濮嬪尮閰? {content}")

        for prefix in self.SORTED_PREFIXES:
            if content.startswith(prefix):
                cmd_type = self.PREFIX_COMMANDS[prefix]
                remainder = content[len(prefix):].strip().lstrip('+')

                result = self._validate_and_extract(cmd_type, remainder, content, prefix)
                if result:
                    return result

        return self._unknown_result(content)

    def _validate_and_extract(self, cmd_type: CommandType, remainder: str, original: str, prefix: str) -> Optional[MatchResult]:
        """楠岃瘉鏍煎紡骞舵彁鍙栧弬鏁?""
        params = {}

        if cmd_type == CommandType.REPORT:
            if not remainder:
                return self._format_error(cmd_type, original, prefix, "缂哄皯宸ュ崟鍙?)
            parts = self._split_params(remainder)
            if len(parts) < 1:
                return self._format_error(cmd_type, original, prefix, "缂哄皯宸ュ崟鍙?)
            params['order_no'] = parts[0]
            if len(parts) >= 2:
                params['process'] = parts[1]
            if len(parts) >= 3:
                try:
                    params['quantity'] = int(parts[2])
                except ValueError:
                    return self._format_error(cmd_type, original, prefix, f"鏁伴噺蹇呴』鏄暟瀛? {parts[2]}")
            if len(parts) >= 4:
                params['unit'] = parts[3]
            if len(parts) >= 5:
                params['extra'] = parts[4]

        elif cmd_type == CommandType.PROCESS_COMPLETE:
            if not remainder:
                return self._format_error(cmd_type, original, prefix, "缂哄皯宸ュ崟鍙?)
            parts = self._split_params(remainder)
            if len(parts) >= 1:
                params['order_no'] = parts[0]
            if len(parts) >= 2:
                params['process_name'] = parts[1]

        elif cmd_type == CommandType.ORDER_COMPLETE:
            if not remainder:
                return self._format_error(cmd_type, original, prefix, "缂哄皯宸ュ崟鍙?)
            params['order_no'] = remainder

        elif cmd_type == CommandType.INSPECTION_QUERY:
            if not remainder:
                return self._format_error(cmd_type, original, prefix, "缂哄皯宸ュ崟鍙?)
            params['order_no'] = remainder

        elif cmd_type in (CommandType.REPORT_FIRST_INSPECTION, CommandType.REPORT_PATROL_INSPECTION, CommandType.REPORT_FINAL_INSPECTION):
            if not remainder:
                return self._format_error(cmd_type, original, prefix, "缂哄皯宸ュ崟鍙?)
            parts = self._split_params(remainder)
            if len(parts) >= 1:
                params['order_no'] = parts[0]
            if len(parts) >= 2:
                params['inspection_item'] = parts[1]
            if len(parts) >= 3:
                params['content'] = parts[2]
            if len(parts) >= 4:
                params['unit'] = parts[3]

        elif cmd_type == CommandType.CONFIRM:
            if not remainder:
                return self._format_error(cmd_type, original, prefix, "缂哄皯缂栧彿")
            params['confirm_no'] = remainder

        elif cmd_type == CommandType.QUERY_ORDER:
            pass

        elif cmd_type == CommandType.QUERY_ORDER_MATERIAL:
            pass

        elif cmd_type == CommandType.QUERY_PROCESS:
            if not remainder:
                return self._format_error(cmd_type, original, prefix, "缂哄皯宸ュ崟鍙?)
            params['order_no'] = remainder

        elif cmd_type == CommandType.CANCEL:
            if not remainder:
                return self._format_error(cmd_type, original, prefix, "缂哄皯宸ュ崟鍙?)
            parts = self._split_params(remainder)
            if len(parts) >= 1:
                params['order_no'] = parts[0]
            if len(parts) >= 2:
                params['content'] = parts[1]

        elif cmd_type == CommandType.REPORT_REPAIR:
            if not remainder:
                return self._format_error(cmd_type, original, prefix, "缂哄皯鏁呴殰浣嶇疆")
            parts = self._split_params(remainder, maxsplit=1)
            if len(parts) >= 1:
                params['location'] = parts[0]
            if len(parts) >= 2:
                params['description'] = parts[1]

        elif cmd_type == CommandType.REPAIR_COMPLETE:
            if not remainder:
                return self._format_error(cmd_type, original, prefix, "缂哄皯缁翠慨宸ュ崟缂栧彿")
            params['repair_order_no'] = remainder

        elif cmd_type == CommandType.REPAIR_SUPPLY:
            if not remainder:
                return self._format_error(cmd_type, original, prefix, "缂哄皯缁翠慨宸ュ崟缂栧彿")
            params['repair_order_no'] = remainder

        elif cmd_type == CommandType.QUERY_REPAIR:
            pass

        elif cmd_type == CommandType.APPLY_MATERIAL:
            if not remainder:
                return self._format_error(cmd_type, original, prefix, "缂哄皯宸ュ崟鍙?)
            parts = self._split_params(remainder)
            if len(parts) >= 1:
                params['order_no'] = parts[0]
            if len(parts) >= 2:
                params['material_name'] = parts[1]
            if len(parts) >= 3:
                params['spec'] = parts[2]

        elif cmd_type == CommandType.REPAIR_MATERIAL:
            if not remainder:
                return self._format_error(cmd_type, original, prefix, "缂哄皯宸ュ崟鍙?)
            params['order_no'] = remainder

        elif cmd_type == CommandType.OUTSOURCE_PROGRESS:
            if not remainder:
                return self._format_error(cmd_type, original, prefix, "缂哄皯宸ュ崟鍙?)
            parts = self._split_params(remainder)
            if len(parts) >= 1:
                params['order_no'] = parts[0]
            if len(parts) >= 2:
                params['process_or_material'] = parts[1]
            if len(parts) >= 3:
                params['progress'] = parts[2]
            if len(parts) >= 4:
                params['complete_time'] = parts[3]

        elif cmd_type == CommandType.OUTSOURCE_COMPLETE:
            if not remainder:
                return self._format_error(cmd_type, original, prefix, "缂哄皯宸ュ崟鍙?)
            parts = self._split_params(remainder)
            if len(parts) >= 1:
                params['order_no'] = parts[0]
            if len(parts) >= 2:
                params['process_or_material'] = parts[1]

        elif cmd_type == CommandType.OUTSOURCE_QC:
            if not remainder:
                return self._format_error(cmd_type, original, prefix, "缂哄皯宸ュ崟鍙?)
            parts = self._split_params(remainder)
            if len(parts) >= 1:
                params['order_no'] = parts[0]
            if len(parts) >= 2:
                params['process_or_material'] = parts[1]
            if len(parts) >= 3:
                params['result'] = parts[2]

        elif cmd_type == CommandType.QUERY_MATERIAL:
            if not remainder:
                return self._format_error(cmd_type, original, prefix, "缂哄皯鐗╂枡鍚嶇О")
            params['material_name'] = remainder

        elif cmd_type == CommandType.PRODUCT_STOCK_IN:
            if not remainder:
                return self._format_error(cmd_type, original, prefix, "缂哄皯宸ュ崟鍙?)
            params['order_no'] = remainder

        elif cmd_type == CommandType.MATERIAL_SHIPMENT:
            if not remainder:
                return self._format_error(cmd_type, original, prefix, "缂哄皯宸ュ崟鍙?)
            parts = self._split_params(remainder)
            if len(parts) >= 1:
                params['order_no'] = parts[0]
            if len(parts) >= 2:
                params['logistics_company'] = parts[1]
            if len(parts) >= 3:
                params['logistics_no'] = parts[2]
            if len(parts) >= 4:
                params['quantity'] = parts[3]

        elif cmd_type == CommandType.MATERIAL_CREATE:
            if not remainder:
                return self._format_error(cmd_type, original, prefix, "缂哄皯鐗╂枡鍚嶇О")
            parts = self._split_params(remainder)
            if len(parts) >= 1:
                params['material_name'] = parts[0]
            if len(parts) >= 2:
                params['spec'] = parts[1]
            if len(parts) >= 3:
                params['unit'] = parts[2]
            if len(parts) >= 4:
                params['warehouse_location'] = parts[3]
            if len(parts) >= 5:
                params['manufacturer'] = parts[4]
            if len(parts) >= 6:
                params['contact'] = parts[5]

        elif cmd_type == CommandType.MATERIAL_STOCK_IN:
            if not remainder:
                return self._format_error(cmd_type, original, prefix, "缂哄皯鐗╂枡鍚嶇О")
            parts = self._split_params(remainder)
            if len(parts) >= 1:
                params['material_name'] = parts[0]
            if len(parts) >= 2:
                params['spec'] = parts[1]
            if len(parts) >= 3:
                params['quantity'] = parts[2]
            if len(parts) >= 4:
                params['unit'] = parts[3]

        elif cmd_type == CommandType.SCHEDULE_QUERY:
            if not remainder:
                return self._format_error(cmd_type, original, prefix, "缂哄皯宸ュ崟鍙?)
            params['order_no'] = remainder

        elif cmd_type == CommandType.SCHEDULE_NOTIFY:
            pass

        elif cmd_type == CommandType.DO_SCHEDULE:
            if not remainder:
                return self._format_error(cmd_type, original, prefix, "缂哄皯宸ュ崟鍙?)
            parts = self._split_params(remainder)
            if len(parts) >= 1:
                params['order_no'] = parts[0]
            if len(parts) >= 2:
                params['duration_days'] = parts[1]

        elif cmd_type == CommandType.HELP_REQUEST:
            params['content'] = remainder if remainder else ''

        logger.info(f"[Matcher] 鍖归厤鎴愬姛: {cmd_type.value}")

        return MatchResult(
            command_type=cmd_type,
            params=params,
            confidence=1.0,
            match_method=MatchMethod.PREFIX,
            original_content=original,
            matched_keyword=prefix
        )

    def _split_params(self, text: str, maxsplit: int = 0) -> List[str]:
        """鍒嗗壊鍙傛暟锛屾敮鎸?鍙锋垨绌烘牸鍒嗛殧"""
        text = text.strip()
        if not text:
            return []

        parts = []
        for part in re.split(r'[\s\+]+', text):
            if part:
                parts.append(part.strip())

        if maxsplit > 0 and len(parts) > maxsplit:
            first = parts[:maxsplit]
            remainder = '+'.join(parts[maxsplit:])
            if remainder:
                first.append(remainder)
            return first

        return parts

    def _classify_help(self, content: str) -> tuple:
        """鍒嗙被姹傚姪鍐呭"""
        scores = {}
        for category, keywords in self.HELP_CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in content)
            if score > 0:
                scores[category] = score

        if scores:
            best_category = max(scores.keys(), key=lambda x: scores[x])
            matched_kw = [kw for kw in self.HELP_CATEGORY_KEYWORDS[best_category] if kw in content]
            return best_category, matched_kw

        return '鍏朵粬', []

    def _format_error(self, cmd_type: CommandType, original: str, prefix: str, message: str) -> MatchResult:
        """鏍煎紡閿欒"""
        help_msg = self.FORMAT_HELP.get(cmd_type, "")
        error_msg = f"{message}\n\n{help_msg}"

        logger.info(f"[Matcher] 鏍煎紡閿欒: {message}")

        return MatchResult(
            command_type=cmd_type,
            params={'error': message, 'help': help_msg},
            confidence=0.8,
            match_method=MatchMethod.FORMAT,
            original_content=original,
            matched_keyword=prefix,
            error_message=error_msg
        )

    def _unknown_result(self, content: str) -> MatchResult:
        """鏈煡鎸囦护"""
        logger.info(f"[Matcher] 鏈瘑鍒寚浠? {content}")

        return MatchResult(
            command_type=CommandType.UNKNOWN,
            params={'help': self.get_command_list()},
            confidence=0.0,
            match_method=MatchMethod.NONE,
            original_content=content,
            matched_keyword='',
            error_message=f"鏈瘑鍒殑鎸囦护寮€澶碶n\n{self.get_command_list()}\n\n杈撳叆姹傚姪+鍐呭 鍙幏鍙栦汉宸ュ府鍔?
        )

    def _error_result(self, content: str, message: str, error_msg: str) -> MatchResult:
        """閿欒缁撴灉"""
        return MatchResult(
            command_type=CommandType.UNKNOWN,
            params={'help': self.get_command_list()},
            confidence=0.0,
            match_method=MatchMethod.NONE,
            original_content=content,
            matched_keyword='',
            error_message=error_msg or message
        )

    def normalize_content(self, content: str) -> str:
        """鏍囧噯鍖栧唴瀹?""
        content = content.strip()
        content = re.sub(r'\s+', ' ', content)
        return content


_matcher = InstructionMatcher()


def get_matcher() -> InstructionMatcher:
    """鑾峰彇鍖归厤鍣ㄥ疄渚?""
    return _matcher
