window.LABELS = (function () {

  var STATUS = {
    pending: '待处理',
    dispatched: '已分配',
    distributed: '已派发',
    in_progress: '进行中',
    completed: '已完成',
    overdue: '已超时',
    cancelled: '已取消',
    published: '已发布',
    scheduled: '已排产',
    confirmed: '已排产',
    in_production: '生产中',
    reported: '已报工',
    qc_passed: '质检通过',
    created: '已创建',
    received: '已收货',
    processing: '处理中',
    active: '进行中'
  };

  var TYPE = {
    process_report: '工序报工',
    flow_step: '流程步骤',
    flow_production: '排产发布',
    material_request: '物料申请',
    material_pickup: '领料出库',
    material_buy: '物料采购',
    quality_task: '质检任务',
    equipment_repair: '设备报修',
    outsource_task: '外协任务',
    config: '系统配置',
    // 旧值兼容(v1.0 过渡期保留)
    report: '报工',
    quality: '质检',
    material: '物料',
    approval: '审批',
    work_order: '工单',
    unknown: '未知',
    task_assign: '派单',
    task_reassign: '转派',
    batch_assign: '批量派单'
  };

  var FLOW = {
    production: '生产流程',
    material_purchase: '物料采购',
    quality: '质检流程',
    repair: '维修流程',
    outsource: '外协流程'
  };

  var REPAIR_STATUS_MAP = {
    pending: '待处理',
    completed: '已完成'
  };

  function label(map, key) {
    return (map && map[key]) || key;
  }

  return {
    STATUS: STATUS,
    TYPE: TYPE,
    FLOW: FLOW,
    REPAIR_STATUS: REPAIR_STATUS_MAP,
    s: function (key) { return label(STATUS, key); },
    t: function (key) { return label(TYPE, key); },
    f: function (key) { return label(FLOW, key); },
    r: function (key) { return label(REPAIR_STATUS_MAP, key); },
    repairBadgeClass: function (status) {
      return status === 'completed' ? 'success' : 'warning';
    },
    outsourceStatusMap: {
      pending: '待处理',
      processing: '处理中',
      completed: '已完成',
      received: '已收货',
      overdue: '已超时'
    },
    outsourceBadgeClass: function (status) {
      var m = { pending: 'warning', processing: 'info', completed: 'success', received: 'success', overdue: 'danger' };
      return m[status] || 'warning';
    }
  };
})();
