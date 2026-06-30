# -*- coding: utf-8 -*-
"""
操作员管理视图
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import requests
from config import CONTAINER_CENTER_URL
from models.operator import OperatorDAO, OperatorLogDAO


def _format_date(val):
    """安全格式化日期，处理datetime对象或字符串"""
    if hasattr(val, 'strftime'):
        return val.strftime('%Y-%m-%d %H:%M:%S')
    elif val:
        return str(val)[:19]
    return "-"


class OperatorManagerView(tk.Frame):
    """操作员管理视图"""

    def __init__(self, parent, current_operator=None):
        super().__init__(parent)
        self.current_operator = current_operator or {'operator_id': 'admin', 'name': '管理员', 'role': '管理员'}
        self._wechat_employees = []

        self._create_widgets()
        self._load_data()

    def _create_widgets(self):
        """创建组件"""
        # 顶部工具栏
        toolbar = ttk.Frame(self)
        toolbar.pack(fill='x', padx=5, pady=5)

        ttk.Button(toolbar, text="➕ 添加操作员", command=self._add_operator).pack(side='left', padx=2)
        ttk.Button(toolbar, text="✏️ 编辑", command=self._edit_operator).pack(side='left', padx=2)
        ttk.Button(toolbar, text="🔑 修改密码", command=self._change_password).pack(side='left', padx=2)
        ttk.Button(toolbar, text="🗑️ 删除", command=self._delete_operator).pack(side='left', padx=2)
        ttk.Separator(toolbar, orient='vertical').pack(side='left', fill='y', padx=10)
        ttk.Button(toolbar, text="📥 从企业微信同步", command=self._sync_from_wechat).pack(side='left', padx=2)
        ttk.Separator(toolbar, orient='vertical').pack(side='left', fill='y', padx=10)
        ttk.Button(toolbar, text="📋 操作日志", command=self._show_logs).pack(side='left', padx=2)

        # 操作员列表
        list_frame = ttk.Frame(self)
        list_frame.pack(fill='both', expand=True, padx=5, pady=5)

        # 表格
        columns = ('operator_id', 'name', 'role', 'status', 'last_login', 'created_at')
        self.tree = ttk.Treeview(list_frame, columns=columns, show='headings', selectmode='browse')

        self.tree.heading('operator_id', text='工号')
        self.tree.heading('name', text='姓名')
        self.tree.heading('role', text='角色')
        self.tree.heading('status', text='状态')
        self.tree.heading('last_login', text='最后登录')
        self.tree.heading('created_at', text='创建时间')

        self.tree.column('operator_id', width=100)
        self.tree.column('name', width=100)
        self.tree.column('role', width=80)
        self.tree.column('status', width=80)
        self.tree.column('last_login', width=150)
        self.tree.column('created_at', width=150)

        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # 状态栏
        status_bar = ttk.Label(self, text=f"当前用户: {self.current_operator['name']} ({self.current_operator['role']})", anchor='w')
        status_bar.pack(fill='x', padx=5, pady=2)

    def _load_data(self):
        """加载数据"""
        for item in self.tree.get_children():
            self.tree.delete(item)

        operators = OperatorDAO.get_all()
        for op in operators:
            self.tree.insert('', 'end', values=(
                op['operator_id'],
                op['name'],
                op['role'],
                op['status'],
                _format_date(op.get('last_login')),
                _format_date(op.get('created_at'))
            ))

    def _get_selected(self):
        """获取选中项"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("提示", "请先选择操作员")
            return None
        return self.tree.item(selection[0])['values']

    def _add_operator(self):
        """添加操作员"""
        dialog = tk.Toplevel(self)
        dialog.title("添加操作员")
        from utils.window_manager import setup_resizable_window
        setup_resizable_window(dialog, "add_operator", "400x360")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        row = 0

        # 从企业微信选择
        ttk.Label(dialog, text="从企业微信选择:").grid(row=row, column=0, sticky='e', padx=10, pady=5)
        wechat_var = tk.StringVar()
        if self._wechat_employees:
            choices = [f"{e['name']} ({e['userid']})" for e in self._wechat_employees]
            wechat_combo = ttk.Combobox(dialog, textvariable=wechat_var, values=choices, width=25, state='readonly')
            wechat_combo.grid(row=row, column=1, pady=5)

            def on_wechat_select(event):
                val = wechat_var.get()
                if not val or '(' not in val:
                    return
                name = val.rsplit(' (', 1)[0]
                userid = val.rsplit(' (', 1)[1].rstrip(')')
                entry_id.delete(0, tk.END)
                entry_id.insert(0, userid)
                entry_name.delete(0, tk.END)
                entry_name.insert(0, name)
            wechat_combo.bind('<<ComboboxSelected>>', on_wechat_select)
        else:
            wechat_combo = ttk.Combobox(dialog, textvariable=wechat_var, values=['请先同步企业微信成员'], width=25, state='disabled')
            wechat_combo.grid(row=row, column=1, pady=5)
        row += 1

        # 分隔线
        ttk.Separator(dialog, orient='horizontal').grid(row=row, column=0, columnspan=2, sticky='ew', padx=10, pady=5)
        row += 1

        # 工号
        ttk.Label(dialog, text="工号:").grid(row=row, column=0, sticky='e', padx=10, pady=5)
        entry_id = ttk.Entry(dialog, width=20)
        entry_id.grid(row=row, column=1, pady=5)
        row += 1

        # 姓名
        ttk.Label(dialog, text="姓名:").grid(row=row, column=0, sticky='e', padx=10, pady=5)
        entry_name = ttk.Entry(dialog, width=20)
        entry_name.grid(row=row, column=1, pady=5)
        row += 1

        # 角色
        ttk.Label(dialog, text="角色:").grid(row=row, column=0, sticky='e', padx=10, pady=5)
        role_var = ttk.Combobox(dialog, values=['管理员', '主管', '操作员'], width=18)
        role_var.current(2)
        role_var.grid(row=row, column=1, pady=5)
        row += 1

        # 密码
        ttk.Label(dialog, text="密码:").grid(row=row, column=0, sticky='e', padx=10, pady=5)
        entry_pwd = ttk.Entry(dialog, width=20, show='*')
        entry_pwd.insert(0, '')
        entry_pwd.grid(row=row, column=1, pady=5)
        row += 1

        # 状态
        ttk.Label(dialog, text="状态:").grid(row=row, column=0, sticky='e', padx=10, pady=5)
        status_var = ttk.Combobox(dialog, values=['正常', '停用'], width=18)
        status_var.current(0)
        status_var.grid(row=row, column=1, pady=5)
        row += 1

        def save():
            op_id = entry_id.get().strip()
            name = entry_name.get().strip()
            role = role_var.get()
            pwd = entry_pwd.get()
            status = status_var.get()

            if not op_id or not name:
                messagebox.showerror("错误", "工号和姓名不能为空")
                return

            if OperatorDAO.add({
                'operator_id': op_id,
                'name': name,
                'role': role,
                'password': pwd,
                'status': status
            }):
                OperatorLogDAO.add(
                    self.current_operator['operator_id'],
                    self.current_operator['name'],
                    '添加操作员',
                    'operators',
                    op_id,
                    f"添加操作员: {name} ({role})"
                )
                messagebox.showinfo("成功", "操作员添加成功")
                dialog.destroy()
                self._load_data()
            else:
                messagebox.showerror("错误", "工号已存在")

        ttk.Button(dialog, text="保存", command=save).grid(row=row, column=0, columnspan=2, pady=15)

    def _edit_operator(self):
        """编辑操作员"""
        selected = self._get_selected()
        if not selected:
            return

        op_id = selected[0]

        dialog = tk.Toplevel(self)
        dialog.title("编辑操作员")
        from utils.window_manager import setup_resizable_window
        setup_resizable_window(dialog, "edit_operator", "350x220")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        ttk.Label(dialog, text="工号:").grid(row=0, column=0, sticky='e', padx=10, pady=5)
        ttk.Label(dialog, text=op_id, font=('', 10, 'bold')).grid(row=0, column=1, sticky='w', pady=5)

        ttk.Label(dialog, text="姓名:").grid(row=1, column=0, sticky='e', padx=10, pady=5)
        entry_name = ttk.Entry(dialog, width=20)
        entry_name.insert(0, selected[1])
        entry_name.grid(row=1, column=1, pady=5)

        ttk.Label(dialog, text="角色:").grid(row=2, column=0, sticky='e', padx=10, pady=5)
        role_var = ttk.Combobox(dialog, values=['管理员', '主管', '操作员'], width=18)
        role_var.set(selected[2])
        role_var.grid(row=2, column=1, pady=5)

        ttk.Label(dialog, text="状态:").grid(row=3, column=0, sticky='e', padx=10, pady=5)
        status_var = ttk.Combobox(dialog, values=['正常', '停用'], width=18)
        status_var.set(selected[3])
        status_var.grid(row=3, column=1, pady=5)

        def save():
            if OperatorDAO.update(op_id, {
                'name': entry_name.get().strip(),
                'role': role_var.get(),
                'status': status_var.get()
            }):
                OperatorLogDAO.add(
                    self.current_operator['operator_id'],
                    self.current_operator['name'],
                    '编辑操作员',
                    'operators',
                    op_id,
                    f"编辑操作员: {entry_name.get()} ({role_var.get()})"
                )
                messagebox.showinfo("成功", "操作员更新成功")
                dialog.destroy()
                self._load_data()
            else:
                messagebox.showerror("错误", "更新失败")

        ttk.Button(dialog, text="保存", command=save).grid(row=4, column=0, columnspan=2, pady=15)

    def _change_password(self):
        """修改密码"""
        selected = self._get_selected()
        if not selected:
            return

        op_id = selected[0]

        dialog = tk.Toplevel(self)
        dialog.title("修改密码")
        from utils.window_manager import setup_resizable_window
        setup_resizable_window(dialog, "change_password", "300x180")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        ttk.Label(dialog, text=f"操作员: {selected[1]}").pack(pady=10)

        ttk.Label(dialog, text="新密码:").pack(pady=5)
        entry_pwd = ttk.Entry(dialog, width=20, show='*')
        entry_pwd.pack(pady=5)

        def save():
            new_pwd = entry_pwd.get()
            if len(new_pwd) < 4:
                messagebox.showerror("错误", "密码长度不能少于4位")
                return

            if OperatorDAO.update(op_id, {'password': new_pwd}):
                OperatorLogDAO.add(
                    self.current_operator['operator_id'],
                    self.current_operator['name'],
                    '修改密码',
                    'operators',
                    op_id,
                    f"重置操作员 {selected[1]} 的密码"
                )
                messagebox.showinfo("成功", "密码修改成功")
                dialog.destroy()
            else:
                messagebox.showerror("错误", "修改失败")

        ttk.Button(dialog, text="保存", command=save).pack(pady=10)

    def _delete_operator(self):
        """删除操作员"""
        selected = self._get_selected()
        if not selected:
            return

        op_id = selected[0]

        if op_id == 'admin':
            messagebox.showwarning("提示", "不能删除管理员账号")
            return

        if op_id == self.current_operator['operator_id']:
            messagebox.showwarning("提示", "不能删除当前登录账号")
            return

        if messagebox.askyesno("确认", f"确定删除操作员 {selected[1]} ({op_id}) 吗？"):
            if OperatorDAO.delete(op_id):
                OperatorLogDAO.add(
                    self.current_operator['operator_id'],
                    self.current_operator['name'],
                    '删除操作员',
                    'operators',
                    op_id,
                    f"删除操作员: {selected[1]}"
                )
                messagebox.showinfo("成功", "操作员已删除")
                self._load_data()
            else:
                messagebox.showerror("错误", "删除失败")

    def _sync_from_wechat(self):
        """从企业微信同步成员名单（仅缓存，不自动创建操作员）"""
        import threading
        btn_frame = None
        progress = None

        def _do_sync():
            url = f"{CONTAINER_CENTER_URL}/api/enterprise/structure/sync"
            try:
                resp = requests.post(url, timeout=30)
                ret = resp.json()
            except requests.exceptions.ConnectTimeout:
                self.after(0, lambda: _finish(False, "容器中心连接超时！\n请确认容器中心 (5002) 是否已启动"))
                return
            except requests.exceptions.ConnectionError:
                self.after(0, lambda: _finish(False, "无法连接容器中心！\n请确认地址: " + url))
                return
            except Exception as e:
                self.after(0, lambda: _finish(False, f"请求失败: {e}"))
                return

            if ret.get('code') != 0:
                self.after(0, lambda: _finish(False, ret.get('message', '云端同步失败')))
                return

            users = ret.get('data', {}).get('users', [])
            if not users:
                self.after(0, lambda: _finish(False, "企业微信未找到人员"))
                return

            self._wechat_employees = [
                {'userid': u.get('userid', ''), 'name': u.get('name', '').strip()}
                for u in users if u.get('userid') and u.get('name', '').strip()
            ]

            count = len(self._wechat_employees)
            self.after(0, lambda: _finish(True, f"同步完成！\n已缓存 {count} 名企业微信成员\n可在添加操作员时选择"))

        def _finish(success, msg):
            if progress:
                progress.destroy()
            if btn_frame:
                sync_btn.pack_forget()
                btn_frame.pack_forget()
            if success:
                messagebox.showinfo("同步结果", msg)
            else:
                messagebox.showerror("同步失败", msg)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill='x', padx=5)
        progress = ttk.Progressbar(btn_frame, mode='indeterminate')
        progress.pack(side='left', fill='x', expand=True, padx=2)
        progress.start()
        sync_btn = ttk.Button(btn_frame, text="同步中...", state='disabled')
        sync_btn.pack(side='left', padx=2)
        ttk.Label(btn_frame, text="正在从企业微信同步成员...").pack(side='left', padx=5)

        threading.Thread(target=_do_sync, daemon=True).start()

    def _show_logs(self):
        """显示操作日志"""
        LogViewer(self.window, self.current_operator)


class LogViewer:
    """操作日志查看器"""

    def __init__(self, parent, current_operator):
        self.window = tk.Toplevel(parent)
        self.window.title("操作日志")
        from utils.window_manager import setup_resizable_window
        setup_resizable_window(self.window, "log_viewer", "900x500")

        # 创建表格
        frame = ttk.Frame(self.window)
        frame.pack(fill='both', expand=True, padx=10, pady=10)

        columns = ('operator_id', 'operator_name', 'action', 'target_type', 'details', 'created_at')
        self.tree = ttk.Treeview(frame, columns=columns, show='headings')

        self.tree.heading('operator_id', text='工号')
        self.tree.heading('operator_name', text='操作员')
        self.tree.heading('action', text='操作')
        self.tree.heading('target_type', text='对象类型')
        self.tree.heading('details', text='详情')
        self.tree.heading('created_at', text='时间')

        self.tree.column('operator_id', width=80)
        self.tree.column('operator_name', width=80)
        self.tree.column('action', width=100)
        self.tree.column('target_type', width=80)
        self.tree.column('details', width=300)
        self.tree.column('created_at', width=150)

        scrollbar = ttk.Scrollbar(frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        self._load_data()

    def _load_data(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        logs = OperatorLogDAO.get_logs(200)
        for log in logs:
            self.tree.insert('', 'end', values=(
                log.get('operator_id', ''),
                log.get('operator_name', ''),
                log.get('action', ''),
                log.get('target_type', ''),
                log.get('details', ''),
                _format_date(log.get('created_at'))
            ))


class LoginDialog:
    """登录对话框"""

    def __init__(self, parent):
        self.result = None
        self.window = tk.Toplevel(parent)
        self.window.title("操作员登录")
        self.window.geometry("300x200")
        self.window.transient(parent)
        self.window.grab_set()
        self.window.resizable(False, False)

        # 居中
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() - 300) // 2
        y = (self.window.winfo_screenheight() - 200) // 2
        self.window.geometry(f"300x200+{x}+{y}")

        self._create_widgets()

    def _create_widgets(self):
        ttk.Label(self.window, text="不锈钢输送网带跟单系统", font=('', 12, 'bold')).pack(pady=20)
        ttk.Label(self.window, text="工号:").pack(pady=5)
        self.entry_id = ttk.Entry(self.window, width=20, justify='center')
        self.entry_id.pack(pady=3)
        self.entry_id.focus()

        ttk.Label(self.window, text="密码:").pack(pady=5)
        self.entry_pwd = ttk.Entry(self.window, width=20, show='*', justify='center')
        self.entry_pwd.pack(pady=3)
        self.entry_pwd.bind('<Return>', lambda e: self._do_login())

        ttk.Button(self.window, text="登录", command=self._do_login).pack(pady=15)

    def _do_login(self):
        op_id = self.entry_id.get().strip()
        pwd = self.entry_pwd.get()

        if not op_id or not pwd:
            messagebox.showwarning("提示", "请输入工号和密码")
            return

        operator = OperatorDAO.login(op_id, pwd)
        if operator:
            OperatorLogDAO.add(op_id, operator['name'], '登录', 'system', '', '系统登录')
            self.result = operator
            self.window.destroy()
        else:
            messagebox.showerror("错误", "工号或密码错误")
            self.entry_pwd.delete(0, tk.END)
