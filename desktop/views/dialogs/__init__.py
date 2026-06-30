# -*- coding: utf-8 -*-
"""
对话框模块
"""
from .base import alert, center_window, confirm, popup_form, show_detail, manage_custom_types_dialog, BaseDialog
from .widgets import PlaceholderEntry
from .quality_dialogs import QualityTaskCompileDialog, QualityRecordFormDialog, CompletionConfirmDialog
from .material_dialogs import (
    MaterialPrepHistoryDialog, MaterialTemplateManagerDialog, MaterialTemplatePreviewDialog,
    MaterialRulesContainerDialog, BatchCalcMaterialDialog, MaterialQueryLogDialog
)
from .rule_dialogs import (
    QualityRuleDialog, MaterialRuleDialog, AddProductTypeDialog,
    SaveRuleTemplateDialog, LoadRuleTemplateDialog, ManageRuleTemplatesDialog
)

__all__ = ['alert', 'center_window', 'confirm', 'popup_form', 'show_detail', 'PlaceholderEntry',
           'manage_custom_types_dialog', 'BaseDialog',
           'QualityTaskCompileDialog', 'QualityRecordFormDialog', 'CompletionConfirmDialog',
           'MaterialPrepHistoryDialog', 'MaterialTemplateManagerDialog', 'MaterialTemplatePreviewDialog',
           'MaterialRulesContainerDialog', 'BatchCalcMaterialDialog', 'MaterialQueryLogDialog',
           'QualityRuleDialog', 'MaterialRuleDialog', 'AddProductTypeDialog',
           'SaveRuleTemplateDialog', 'LoadRuleTemplateDialog', 'ManageRuleTemplatesDialog']
