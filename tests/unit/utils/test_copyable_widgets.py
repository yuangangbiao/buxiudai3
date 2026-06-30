# -*- coding: utf-8 -*-
"""utils/copyable_widgets.py 全覆盖测试——CopyableLabel 和 ReadonlyEntry

策略：patch 整个 utils.copyable_widgets.tk → 纯 mock 环境，不创建真实窗口。
- tk.TclError → RuntimeError（真实异常才能被 except 捕获）
- mock_frame_instance 上附加 clipboard_clear/clipboard_append 等 Frame 方法
- configure/config 方法名前加 _mock_ 避免与 super().config 冲突
"""
import pytest
from unittest.mock import patch, MagicMock


def _build_tk_mock():
    """构造一个完整的 tkinter mock 模块"""
    mock_tk = MagicMock(name='tk')

    # ---- 常量 ----
    mock_tk.SUNKEN = 'sunken'
    mock_tk.END = 'end'
    mock_tk.SEL = 'sel'
    mock_tk.BOTH = 'both'

    # ---- TclError 必须是真实异常类 ----
    class _TclError(RuntimeError):
        pass
    mock_tk.TclError = _TclError

    # ---- StringVar ----
    sv = MagicMock(name='stringvar')
    mock_tk.StringVar = MagicMock(return_value=sv)

    # ---- Frame 实例 ----
    frame = MagicMock(name='frame')
    # Frame 继承自 Widget，提供 clipboard/config 等方法
    frame.clipboard_clear = MagicMock(name='clipboard_clear')
    frame.clipboard_append = MagicMock(name='clipboard_append')
    mock_tk.Frame = MagicMock(return_value=frame)

    # ---- Text 实例 ----
    text = MagicMock(name='text')
    text.delete = MagicMock(name='text.delete')
    text.insert = MagicMock(name='text.insert')
    text.tag_configure = MagicMock(name='text.tag_configure')
    text.tag_add = MagicMock(name='text.tag_add')
    text.tag_ranges = MagicMock(name='text.tag_ranges', return_value=())
    text.tag_names = MagicMock(name='text.tag_names', return_value=[])
    text.pack = MagicMock(name='text.pack')
    text.config = MagicMock(name='text.config')
    text.cget = MagicMock(name='text.cget', return_value=None)
    text.bind = MagicMock(name='text.bind')
    mock_tk.Text = MagicMock(return_value=text)

    # ---- Entry 实例 ----
    entry = MagicMock(name='entry')
    entry.insert = MagicMock(name='entry.insert')
    entry.config = MagicMock(name='entry.config')
    entry.pack = MagicMock(name='entry.pack')
    entry.get = MagicMock(name='entry.get', return_value='')
    entry.bind = MagicMock(name='entry.bind')
    entry.cget = MagicMock(name='entry.cget', return_value=None)
    mock_tk.Entry = MagicMock(return_value=entry)

    # ---- Menu 实例 ----
    menu = MagicMock(name='menu')
    menu.add_command = MagicMock(name='menu.add_command')
    menu.add_separator = MagicMock(name='menu.add_separator')
    menu.post = MagicMock(name='menu.post')
    mock_tk.Menu = MagicMock(return_value=menu)

    return mock_tk


@pytest.fixture(autouse=True)
def _full_tk_patch():
    """patch utils.copyable_widgets.tk → mock 模块"""
    mock_tk = _build_tk_mock()
    with patch('utils.copyable_widgets.tk', mock_tk):
        yield mock_tk


class TestCopyableLabel:
    """CopyableLabel 全覆盖"""

    # ---------- __init__ ----------
    def test_init_defaults(self, _full_tk_patch):
        from utils.copyable_widgets import CopyableLabel
        parent = MagicMock()
        label = CopyableLabel(parent, "Hello")
        # super().__init__(parent, ...) 在 mock 中走 MagicMock.__init__，不会触发 tk.Frame()
        # 所以这里不测 Frame 构造调用，改用 StringVar 验证
        _full_tk_patch.StringVar.assert_called_once_with(value="Hello")
        assert label._original_text == "Hello"
        assert label._font is None
        assert label._bg == "white"
        assert label._fg == "black"
        assert label._relief == 'sunken'

    def test_init_with_all_kwargs(self, _full_tk_patch):
        from utils.copyable_widgets import CopyableLabel
        label = CopyableLabel(
            MagicMock(), "测试",
            font=("Arial", 12),
            bg="yellow",
            fg="red",
            relief="groove",
            padx=20,
            pady=10,
            width=30,
            anchor="e",
        )
        assert label._font == ("Arial", 12)
        assert label._bg == "yellow"
        assert label._fg == "red"
        assert label._relief == "groove"
        assert label._padx == 20
        assert label._pady == 10
        assert label._width == 30
        assert label._anchor == "e"

    # ---------- _create_widgets ----------
    def test_create_widgets_text_config(self, _full_tk_patch):
        from utils.copyable_widgets import CopyableLabel
        label = CopyableLabel(MagicMock(), "Hello")
        text = label.text
        # Text 创建参数
        _full_tk_patch.Text.assert_called_once()
        # 文本设置
        text.delete.assert_called_with('1.0', 'end')
        text.insert.assert_called_with('1.0', "Hello")
        # tag 配置
        text.tag_configure.assert_called_with('left', justify='left')
        text.tag_add.assert_called_with('left', '1.0', 'end')
        # pack
        text.pack.assert_called_once_with(fill='both', expand=True)

    def test_create_widgets_anchor_center(self, _full_tk_patch):
        from utils.copyable_widgets import CopyableLabel
        label = CopyableLabel(MagicMock(), "centered", anchor="center")
        label.text.tag_configure.assert_called_with('left', justify='center')

    def test_create_widgets_anchor_e(self, _full_tk_patch):
        from utils.copyable_widgets import CopyableLabel
        label = CopyableLabel(MagicMock(), "right aligned", anchor="e")
        label.text.tag_configure.assert_called_with('left', justify='right')

    def test_create_widgets_anchor_ne_fallback(self, _full_tk_patch):
        from utils.copyable_widgets import CopyableLabel
        label = CopyableLabel(MagicMock(), "fallback", anchor="ne")
        label.text.tag_configure.assert_called_with('left', justify='left')

    def test_create_widgets_width_set(self, _full_tk_patch):
        from utils.copyable_widgets import CopyableLabel
        label = CopyableLabel(MagicMock(), "wide", width=50)
        label.text.config.assert_any_call(width=50)

    # ---------- set_text / get_text ----------
    def test_set_text(self, _full_tk_patch):
        from utils.copyable_widgets import CopyableLabel
        label = CopyableLabel(MagicMock(), "old")
        # reset mock calls from __init__
        label.text.delete.reset_mock()
        label.text.insert.reset_mock()
        label.text.tag_add.reset_mock()
        label._text_var.set.reset_mock()
        label.set_text("new text")
        assert label._original_text == "new text"
        label.text.delete.assert_called_with('1.0', 'end')
        label.text.insert.assert_called_with('1.0', "new text")
        label.text.tag_add.assert_called_with('left', '1.0', 'end')
        label._text_var.set.assert_called_with("new text")

    def test_get_text(self, _full_tk_patch):
        from utils.copyable_widgets import CopyableLabel
        label = CopyableLabel(MagicMock(), "content")
        assert label.get_text() == "content"

    def test_text_widget_property(self, _full_tk_patch):
        from utils.copyable_widgets import CopyableLabel
        label = CopyableLabel(MagicMock(), "x")
        assert label.text_widget is label.text

    # ---------- _copy ----------
    def test_copy_with_selection(self, _full_tk_patch):
        from utils.copyable_widgets import CopyableLabel
        label = CopyableLabel(MagicMock(), "x")
        label.text.tag_ranges.return_value = ('sel_range',)
        label.text.get.return_value = "selected text"
        # 手动注入 clipboard_clear/append mock — 因为 self.clipboard_clear()
        # 是继承自 tk.Misc 的真实方法，在 unit 测试环境中无法拦截
        label.clipboard_clear = MagicMock()
        label.clipboard_append = MagicMock()
        result = label._copy()
        assert result == "break"
        label.clipboard_clear.assert_called_once()
        label.clipboard_append.assert_called_once_with("selected text")

    def test_copy_no_selection(self, _full_tk_patch):
        from utils.copyable_widgets import CopyableLabel
        label = CopyableLabel(MagicMock(), "x")
        label.text.tag_ranges.return_value = ()
        label.clipboard_clear = MagicMock()
        result = label._copy()
        assert result == "break"
        label.clipboard_clear.assert_not_called()

    def test_copy_tcl_error(self, _full_tk_patch):
        """TclError 被安全捕获"""
        from utils.copyable_widgets import CopyableLabel
        label = CopyableLabel(MagicMock(), "x")
        label.text.tag_ranges.side_effect = _full_tk_patch.TclError("模拟错误")
        result = label._copy()
        assert result == "break"

    # ---------- _show_context_menu ----------
    def test_context_menu_with_selection(self, _full_tk_patch):
        from utils.copyable_widgets import CopyableLabel
        label = CopyableLabel(MagicMock(), "x")
        label.text.tag_ranges.return_value = ('sel_range',)
        event = MagicMock()
        event.x_root = 100
        event.y_root = 200
        label._show_context_menu(event)
        # '复制' + 分隔符 + '复制全部'
        add_commands = _full_tk_patch.Menu.return_value.add_command.call_args_list
        labels = [c[1]['label'] for c in add_commands]
        assert '复制' in labels
        assert '复制全部' in labels
        _full_tk_patch.Menu.return_value.add_separator.assert_called_once()
        _full_tk_patch.Menu.return_value.post.assert_called_once_with(100, 200)

    def test_context_menu_tcl_error(self, _full_tk_patch):
        from utils.copyable_widgets import CopyableLabel
        label = CopyableLabel(MagicMock(), "x")
        label.text.tag_ranges.side_effect = _full_tk_patch.TclError("模拟错误")
        event = MagicMock()
        event.x_root = 100
        event.y_root = 200
        label._show_context_menu(event)
        # 无选中 → 只有 '复制全部'
        add_commands = _full_tk_patch.Menu.return_value.add_command.call_args_list
        labels = [c[1]['label'] for c in add_commands]
        assert '复制' not in labels
        assert '复制全部' in labels
        _full_tk_patch.Menu.return_value.add_separator.assert_not_called()

    def test_context_menu_no_selection(self, _full_tk_patch):
        from utils.copyable_widgets import CopyableLabel
        label = CopyableLabel(MagicMock(), "x")
        label.text.tag_ranges.return_value = ()
        event = MagicMock()
        event.x_root = 100
        event.y_root = 200
        label._show_context_menu(event)
        add_commands = _full_tk_patch.Menu.return_value.add_command.call_args_list
        labels = [c[1]['label'] for c in add_commands]
        assert '复制' not in labels
        assert '复制全部' in labels
        _full_tk_patch.Menu.return_value.add_separator.assert_not_called()

    # ---------- _copy_all ----------
    def test_copy_all(self, _full_tk_patch):
        from utils.copyable_widgets import CopyableLabel
        label = CopyableLabel(MagicMock(), "full text")
        label.clipboard_clear = MagicMock()
        label.clipboard_append = MagicMock()
        label._copy_all()
        label.clipboard_clear.assert_called_once()
        label.clipboard_append.assert_called_once_with("full text")

    # ---------- config ----------
    def test_config_text(self, _full_tk_patch):
        from utils.copyable_widgets import CopyableLabel
        label = CopyableLabel(MagicMock(), "old")
        label.text.delete.reset_mock()
        label.text.insert.reset_mock()
        label.config(text="new")
        assert label._original_text == "new"
        label.text.delete.assert_called_with('1.0', 'end')
        label.text.insert.assert_called_with('1.0', "new")

    def test_config_cursor(self, _full_tk_patch):
        from utils.copyable_widgets import CopyableLabel
        label = CopyableLabel(MagicMock(), "x")
        label.text.config.reset_mock()
        label.config(cursor="hand2")
        label.text.config.assert_any_call(cursor="hand2")

    def test_configure_alias(self, _full_tk_patch):
        """configure 调用 config（功能等价，非同一函数对象）"""
        from utils.copyable_widgets import CopyableLabel
        label = CopyableLabel(MagicMock(), "x")
        # 源代码中 configure(**kwargs) 调用 self.config(**kwargs)，两者是不同的函数对象
        # 验证 configure 是否调用了 config
        with patch.object(label, 'config') as mock_config:
            label.configure(text="new text")
            mock_config.assert_called_once_with(text="new text")

    # ---------- _setup_interactions ----------
    def test_setup_interactions_binds(self, _full_tk_patch):
        from utils.copyable_widgets import CopyableLabel
        label = CopyableLabel(MagicMock(), "x")
        label.text.bind.assert_any_call('<Control-c>', label._copy)
        label.text.bind.assert_any_call('<Control-C>', label._copy)
        label.text.bind.assert_any_call('<Button-3>', label._show_context_menu)
        bind_calls = [c for c in label.text.bind.call_args_list if c[0][0] == '<FocusOut>']
        assert len(bind_calls) == 1

    # ---------- __repr__ / __str__ ----------
    def test_repr(self, _full_tk_patch):
        from utils.copyable_widgets import CopyableLabel
        label = CopyableLabel(MagicMock(), "test")
        assert repr(label) is not None


class TestReadonlyEntry:
    """ReadonlyEntry 全覆盖"""

    # ---------- __init__ ----------
    def test_init_defaults(self, _full_tk_patch):
        from utils.copyable_widgets import ReadonlyEntry
        entry = ReadonlyEntry(MagicMock(), "Entry text")
        assert entry._original_text == "Entry text"
        assert entry._font is None
        assert entry._bg == "white"
        assert entry._fg == "black"
        assert entry._relief == 'sunken'

    def test_init_with_all_kwargs(self, _full_tk_patch):
        from utils.copyable_widgets import ReadonlyEntry
        entry = ReadonlyEntry(
            MagicMock(), "test",
            font=("Arial", 14),
            bg="lightblue",
            fg="darkblue",
            relief="ridge",
            padx=15,
            pady=5,
            width=25,
            anchor="center",
        )
        assert entry._font == ("Arial", 14)
        assert entry._bg == "lightblue"
        assert entry._fg == "darkblue"
        assert entry._relief == "ridge"
        assert entry._anchor == "center"

    # ---------- _create_widgets ----------
    def test_create_widgets_entry_created(self, _full_tk_patch):
        from utils.copyable_widgets import ReadonlyEntry
        entry = ReadonlyEntry(MagicMock(), "Entry text")
        _full_tk_patch.Entry.assert_called_once()
        call_kwargs = _full_tk_patch.Entry.call_args[1]
        assert call_kwargs['font'] is None
        assert call_kwargs['bg'] == 'white'
        assert call_kwargs['fg'] == 'black'
        assert call_kwargs['relief'] == 'sunken'
        assert call_kwargs['justify'] == 'left'
        # 验证 insert 和 state
        entry.entry.insert.assert_called_with(0, "Entry text")
        entry.entry.config.assert_any_call(state='readonly')
        entry.entry.pack.assert_called_once_with(fill='both', expand=True)

    def test_create_widgets_width(self, _full_tk_patch):
        from utils.copyable_widgets import ReadonlyEntry
        entry = ReadonlyEntry(MagicMock(), "wide", width=40)
        entry.entry.config.assert_any_call(width=40)

    def test_create_widgets_anchor_map(self, _full_tk_patch):
        from utils.copyable_widgets import ReadonlyEntry
        entry = ReadonlyEntry(MagicMock(), "right", anchor="e")
        call_kwargs = _full_tk_patch.Entry.call_args[1]
        assert call_kwargs['justify'] == 'right'

    def test_create_widgets_anchor_none(self, _full_tk_patch):
        from utils.copyable_widgets import ReadonlyEntry
        entry = ReadonlyEntry(MagicMock(), "fallback", anchor="nw")
        call_kwargs = _full_tk_patch.Entry.call_args[1]
        assert call_kwargs['justify'] == 'left'

    def test_create_widgets_none_text(self, _full_tk_patch):
        from utils.copyable_widgets import ReadonlyEntry
        entry = ReadonlyEntry(MagicMock(), None)
        entry.entry.insert.assert_called_with(0, "")

    # ---------- _copy ----------
    def test_copy(self, _full_tk_patch):
        from utils.copyable_widgets import ReadonlyEntry
        entry = ReadonlyEntry(MagicMock(), "x")
        entry.entry.get.return_value = "copyable text"
        # 手工注入 clipboard mock
        entry.clipboard_clear = MagicMock()
        entry.clipboard_append = MagicMock()
        result = entry._copy()
        assert result == "break"
        entry.clipboard_clear.assert_called_once()
        entry.clipboard_append.assert_called_once_with("copyable text")

    # ---------- _show_context_menu ----------
    def test_context_menu(self, _full_tk_patch):
        from utils.copyable_widgets import ReadonlyEntry
        entry = ReadonlyEntry(MagicMock(), "x")
        event = MagicMock()
        event.x_root = 100
        event.y_root = 200
        entry._show_context_menu(event)
        _full_tk_patch.Menu.assert_called_once()
        _full_tk_patch.Menu.return_value.add_command.assert_called_with(
            label="复制", command=entry._copy
        )
        _full_tk_patch.Menu.return_value.post.assert_called_once_with(100, 200)

    # ---------- _setup_interactions ----------
    def test_setup_interactions_binds(self, _full_tk_patch):
        from utils.copyable_widgets import ReadonlyEntry
        entry = ReadonlyEntry(MagicMock(), "x")
        entry.entry.bind.assert_any_call('<Button-3>', entry._show_context_menu)
        entry.entry.bind.assert_any_call('<Control-c>', entry._copy)
        entry.entry.bind.assert_any_call('<Control-C>', entry._copy)
