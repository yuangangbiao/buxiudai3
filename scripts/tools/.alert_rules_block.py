# ═══════════════════════════════════════════════════════════════════════════════
# Part 20: 配置接口 (硬迁移 2026-06-20)
# 背景：原 container_center/api/configs.py 中的 /configs/alert_rules 路由随死代码包删除而消失。
#       ContainerCenterClient.get_alert_rules / update_alert_rules 原本调用 5002 /api/v4/configs/alert_rules，
#       硬迁移后必须由 5003 端口接管。存储复用 AlertEngine 已有的 ConfigStore 实例。
# ═══════════════════════════════════════════════════════════════════════════════

@dispatch_center_bp.route('/configs/alert_rules', methods=['GET'])
def api_get_alert_rules():
    """[硬迁移 2026-06-20] 获取告警规则

    替代原 5002 /api/v4/configs/alert_rules (container_center/api/configs.py 已删除)。
    存储：复用 DispatchContext.alert_engine.config_store (ConfigStore，SQLite)。
    """
    from flask import request
    try:
        ctx = DispatchContext.get_instance()
        alert_engine = ctx.alert_engine
        if alert_engine is None or alert_engine.config_store is None:
            logger.warning('[DispatchCenter] AlertEngine 未初始化，alert_rules 返回空')
            return jsonify({'code': 0, 'message': 'success', 'data': {}})
        rules = alert_engine.config_store.get('alert_rules')
        if rules is None:
            return jsonify({'code': 0, 'message': 'success', 'data': {}})
        return jsonify({'code': 0, 'message': 'success', 'data': rules})
    except Exception as e:
        logger.error('[DispatchCenter] get_alert_rules 失败: %s', e)
        return jsonify({'code': 500, 'message': str(e)}), 500


@dispatch_center_bp.route('/configs/alert_rules', methods=['PUT'])
def api_update_alert_rules():
    """[硬迁移 2026-06-20] 更新告警规则

    替代原 5002 /api/v4/configs/alert_rules (container_center/api/configs.py 已删除)。
    存储：复用 DispatchContext.alert_engine.config_store (ConfigStore，SQLite)。
    """
    from flask import request
    try:
        ctx = DispatchContext.get_instance()
        alert_engine = ctx.alert_engine
        if alert_engine is None or alert_engine.config_store is None:
            return jsonify({'code': 503, 'message': 'AlertEngine 未初始化'}), 503
        body = request.get_json(silent=True) or {}
        ok = alert_engine.config_store.set('alert_rules', body)
        if not ok:
            return jsonify({'code': 500, 'message': '保存失败'}), 500
        logger.info('[DispatchCenter] alert_rules 更新成功: keys=%s', list(body.keys()))
        return jsonify({'code': 0, 'message': 'success', 'data': {'updated': True}})
    except Exception as e:
        logger.error('[DispatchCenter] update_alert_rules 失败: %s', e)
        return jsonify({'code': 500, 'message': str(e)}), 500

