# -*- coding: utf-8 -*-
"""
库存管理系统打印模块 - 完善版
支持出库单、入库单、库存报表等打印
"""
import os
import tempfile
import webbrowser
from datetime import datetime
from urllib.parse import quote


A5_W_MM = 210
A5_H_MM = 148
TABLE_ROWS = 10


COMPANY_INFO = {
    "name": os.getenv('COMPANY_NAME', ''),
    "address": os.getenv('COMPANY_ADDRESS', ''),
    "phone": os.getenv('COMPANY_PHONE', ''),
    "fax": os.getenv('COMPANY_FAX', '')
}


def num_to_cn(n):
    """数字转中文大写金额"""
    if n == 0:
        return "零元整"
    digits = ["零","壹","贰","叁","肆","伍","陆","柒","捌","玖"]
    units  = ["","拾","佰","仟"]
    big_u  = ["","万","亿"]
    c = round(n * 100)
    cs = str(c)
    r = ""
    if len(cs) > 2:
        jiao = digits[int(cs[-2])] + "角" if cs[-2] != '0' else ""
        fen   = digits[int(cs[-1])] + "分" if cs[-1] != '0' else ""
        r = jiao + fen
        cs = cs[:-2]
    if cs == '0':
        return r or "零元整"
    yp = ""
    for i in range(len(cs)):
        dgt = int(cs[i])
        pos = len(cs) - 1 - i
        u = units[pos % 4]
        bu = big_u[pos // 4]
        yp += digits[dgt] + u
        if pos % 4 == 0 and pos != 0:
            yp += bu
    while "零零" in yp:
        yp = yp.replace("零零","零")
    yp = yp.rstrip("零")
    return yp + "元" + (r or "整")


def fmt_qty(q):
    """格式化数量"""
    try:
        qv = float(q)
        return str(int(qv)) if qv == int(qv) else f"{qv:.1f}"
    except:
        return str(q)


def generate_outbound_html(data):
    """生成出库单HTML"""
    order_no = data.get('order_no', '')
    date_str = data.get('date', datetime.now().strftime('%Y-%m-%d'))
    customer = data.get('customer', '')
    handler = data.get('handler', '')
    warehouse = data.get('warehouse', '')
    remark = data.get('remark', '')
    items = data.get('items', [])
    operator = data.get('operator', '')
    contact = data.get('contact', '')
    phone = data.get('phone', '')

    total_amt = sum(float(it.get('amount', 0)) for it in items) if items else 0
    total_qty = sum(float(it.get('quantity', 0)) for it in items) if items else 0
    words_cn = num_to_cn(total_amt)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    rows_html = ""
    filled = 0
    for item in items:
        if filled >= TABLE_ROWS:
            break
        name = item.get('name', item.get('product_name', ''))
        spec = item.get('spec', item.get('specification', ''))
        qty = fmt_qty(item.get('quantity', item.get('qty', 0)))
        price = float(item.get('unit_price', item.get('price', 0)) or 0)
        amt = float(item.get('amount', 0) or (float(qty) * price if qty else 0))
        unit = item.get('unit', '件')
        rows_html += f"""                <tr>
                    <td class="c-name">{name}</td>
                    <td class="c-spec">{spec}</td>
                    <td class="c-unit">{unit}</td>
                    <td class="c-num">{qty}</td>
                    <td class="c-num">{price:.2f}</td>
                    <td class="c-num">{amt:.2f}</td>
                </tr>
"""
        filled += 1

    while filled < TABLE_ROWS:
        rows_html += """                <tr>
                    <td class="c-name">&nbsp;</td>
                    <td class="c-spec">&nbsp;</td>
                    <td class="c-unit">&nbsp;</td>
                    <td class="c-num">&nbsp;</td>
                    <td class="c-num">&nbsp;</td>
                    <td class="c-num">&nbsp;</td>
                </tr>
"""
        filled += 1

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>出库单_{order_no}</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family: 'Microsoft YaHei','微软雅黑','SimSun',sans-serif; color: #222; background: #e8e8e8; }}
.page-wrap {{ width:{A5_W_MM}mm; height:{A5_H_MM}mm; margin:10px auto; overflow:hidden; }}
.page {{ width:{A5_W_MM}mm; height:{A5_H_MM}mm; background:#fff; padding:5mm 6mm; box-shadow:0 2px 8px rgba(0,0,0,.15); overflow:hidden; display:flex; flex-direction:column; }}
@page {{ size:{A5_W_MM}mm {A5_H_MM}mm landscape; margin:5mm; }}
@media print {{ body{{background:#fff;margin:0;}} .page-wrap{{width:{A5_W_MM}mm;height:{A5_H_MM}mm;margin:0 auto;}} .page{{width:{A5_W_MM}mm;height:{A5_H_MM}mm;margin:0;padding:4mm 5mm;box-shadow:none;page-break-inside:avoid;}} .no-print{{display:none!important;}} .noprint{{display:none;}} }}
.header {{ display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:3mm; }}
.title-section {{ flex:1; }}
.title-bar {{ text-align:center; border-bottom:2pt solid #1a5276; padding-bottom:3pt; margin-bottom:3pt; }}
.title-bar h1 {{ font-size:18pt; letter-spacing:8pt; color:#1a5276; font-weight:bold; margin:0; }}
.company {{ font-size:10pt; color:#666; text-align:center; margin-top:2pt; }}
.qr-section {{ width:25mm; text-align:right; }}
.qr-box {{ border:1pt solid #ddd; padding:2mm; text-align:center; font-size:7pt; color:#999; }}
.info-section {{ margin-bottom:3mm; }}
.info-table {{ width:100%; border-collapse:collapse; font-size:9pt; }}
.info-table td {{ padding:2pt 4pt; }}
.info-label {{ color:#555; white-space:nowrap; }}
.info-value {{ color:#111; font-weight:500; }}
.highlight {{ color:#1a5276; font-weight:bold; }}
.div-line {{ height:1pt; background:#1a5276; margin:2pt 0; }}
.table-wrap {{ flex:1; display:flex; flex-direction:column; min-height:0; margin:3pt 0; }}
.inv-table {{ width:100%; border-collapse:collapse; flex:1; table-layout:fixed; border:1pt solid #333; }}
.inv-table th, .inv-table td {{ border:0.5pt solid #333; padding:2pt 3mm; font-size:8pt; }}
.inv-table th {{ background:#1a5276; color:#fff; font-weight:bold; text-align:center; }}
.inv-table td {{ vertical-align:middle; }}
.c-name {{ width:25%; }}
.c-spec {{ width:20%; }}
.c-unit {{ width:10%; }}
.c-num {{ width:15%; text-align:right; }}
.total-section {{ display:flex; gap:3mm; margin-top:3pt; }}
.total-box {{ flex:1; background:#eaf2f8; border:1pt solid #1a5276; padding:3pt 5pt; }}
.total-label {{ font-size:8pt; color:#1a5276; }}
.total-value {{ font-size:14pt; color:#c0392b; font-weight:bold; }}
.words-box {{ flex:2; background:#fffde7; border:1pt solid #d4ac0d; padding:3pt 5pt; }}
.words-label {{ font-size:7pt; color:#666; }}
.words-value {{ font-size:10pt; color:#333; font-weight:bold; }}
.sign-section {{ display:flex; justify-content:space-between; margin-top:8mm; }}
.sign-item {{ text-align:center; width:28%; }}
.sign-box {{ border-top:0.5pt solid #555; padding-top:2mm; font-size:8pt; color:#333; }}
.sign-role {{ font-size:7pt; color:#888; margin-bottom:1pt; }}
.footer {{ text-align:center; font-size:6pt; color:#aaa; margin-top:5mm; border-top:0.5pt dotted #ddd; padding-top:2mm; }}
.btn-print {{ display:none; }}
</style>
</head>
<body>
<div class="page-wrap">
<div class="page">
    <div class="header">
        <div class="title-section">
            <div class="title-bar"><h1>出 库 单</h1></div>
            <div class="company">{COMPANY_INFO["name"]}</div>
        </div>
        <div class="qr-section">
            <div class="qr-box">
                <div>单号:</div>
                <div style="font-weight:bold; font-size:9pt;">{order_no}</div>
            </div>
        </div>
    </div>

    <div class="div-line"></div>

    <div class="info-section">
        <table class="info-table">
            <tr>
                <td width="15%"><span class="info-label">日　　期：</span></td>
                <td width="30%"><span class="info-value">{date_str}</span></td>
                <td width="15%"><span class="info-label">存放仓库：</span></td>
                <td width="40%"><span class="info-value highlight">{warehouse}</span></td>
            </tr>
            <tr>
                <td><span class="info-label">客　　户：</span></td>
                <td><span class="info-value">{customer}</span></td>
                <td><span class="info-label">联 系 人：</span></td>
                <td><span class="info-value">{contact} {phone}</span></td>
            </tr>
            <tr>
                <td><span class="info-label">经 手 人：</span></td>
                <td><span class="info-value">{handler}</span></td>
                <td><span class="info-label">备　　注：</span></td>
                <td><span class="info-value">{remark or '无'}</span></td>
            </tr>
        </table>
    </div>

    <div class="table-wrap">
        <table class="inv-table">
            <thead>
                <tr>
                    <th>商品名称</th>
                    <th>规格型号</th>
                    <th>单位</th>
                    <th>数量</th>
                    <th>单价</th>
                    <th>金额</th>
                </tr>
            </thead>
            <tbody>
{rows_html}
            </tbody>
        </table>
    </div>

    <div class="total-section">
        <div class="total-box">
            <div class="total-label">合计数量: {fmt_qty(total_qty)}</div>
            <div class="total-value">¥{total_amt:.2f}</div>
        </div>
        <div class="words-box">
            <div class="words-label">大写金额</div>
            <div class="words-value">{words_cn}</div>
        </div>
    </div>

    <div class="sign-section">
        <div class="sign-item">
            <div class="sign-role">发货方（签章）</div>
            <div class="sign-box">&nbsp;</div>
        </div>
        <div class="sign-item">
            <div class="sign-role">仓库管理员</div>
            <div class="sign-box">{operator}</div>
        </div>
        <div class="sign-item">
            <div class="sign-role">客户（签收）</div>
            <div class="sign-box">{customer}</div>
        </div>
    </div>

    <div class="footer">
        {COMPANY_INFO["name"]} | 地址: {COMPANY_INFO["address"]} | 电话: {COMPANY_INFO["phone"]}<br/>
        打印时间: {now_str} | 库存管理系统 V3.0
    </div>
</div>
</div>
<div class="no-print" style="text-align:center; margin:20px;">
    <button class="btn-print" onclick="window.print()">打印</button>
</div>
<script>
function doPrint(){{
    document.querySelector('.btn-print').style.display='none';
    window.print();
    setTimeout(function(){{document.querySelector('.btn-print').style.display='block';}},100);
}}
document.addEventListener('DOMContentLoaded',function(){{
    setTimeout(doPrint,500);
}});
</script>
</body>
</html>'''
    return html


def generate_inbound_html(data):
    """生成入库单HTML"""
    order_no = data.get('order_no', '')
    date_str = data.get('date', datetime.now().strftime('%Y-%m-%d'))
    supplier = data.get('supplier', '')
    handler = data.get('handler', '')
    warehouse = data.get('warehouse', '')
    remark = data.get('remark', '')
    items = data.get('items', [])
    operator = data.get('operator', '')
    contact = data.get('contact', '')
    phone = data.get('phone', '')

    total_amt = sum(float(it.get('amount', 0)) for it in items) if items else 0
    total_qty = sum(float(it.get('quantity', 0)) for it in items) if items else 0
    words_cn = num_to_cn(total_amt)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    rows_html = ""
    filled = 0
    for item in items:
        if filled >= TABLE_ROWS:
            break
        name = item.get('name', item.get('product_name', ''))
        spec = item.get('spec', item.get('specification', ''))
        qty = fmt_qty(item.get('quantity', item.get('qty', 0)))
        price = float(item.get('unit_price', item.get('price', 0)) or 0)
        amt = float(item.get('amount', 0) or (float(qty) * price if qty else 0))
        unit = item.get('unit', '件')
        rows_html += f"""                <tr>
                    <td class="c-name">{name}</td>
                    <td class="c-spec">{spec}</td>
                    <td class="c-unit">{unit}</td>
                    <td class="c-num">{qty}</td>
                    <td class="c-num">{price:.2f}</td>
                    <td class="c-num">{amt:.2f}</td>
                </tr>
"""
        filled += 1

    while filled < TABLE_ROWS:
        rows_html += """                <tr>
                    <td class="c-name">&nbsp;</td>
                    <td class="c-spec">&nbsp;</td>
                    <td class="c-unit">&nbsp;</td>
                    <td class="c-num">&nbsp;</td>
                    <td class="c-num">&nbsp;</td>
                    <td class="c-num">&nbsp;</td>
                </tr>
"""
        filled += 1

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>入库单_{order_no}</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family: 'Microsoft YaHei','微软雅黑','SimSun',sans-serif; color: #222; background: #e8e8e8; }}
.page-wrap {{ width:{A5_W_MM}mm; height:{A5_H_MM}mm; margin:10px auto; overflow:hidden; }}
.page {{ width:{A5_W_MM}mm; height:{A5_H_MM}mm; background:#fff; padding:5mm 6mm; box-shadow:0 2px 8px rgba(0,0,0,.15); overflow:hidden; display:flex; flex-direction:column; }}
@page {{ size:{A5_W_MM}mm {A5_H_MM}mm landscape; margin:5mm; }}
@media print {{ body{{background:#fff;margin:0;}} .page-wrap{{width:{A5_W_MM}mm;height:{A5_H_MM}mm;margin:0 auto;}} .page{{width:{A5_W_MM}mm;height:{A5_H_MM}mm;margin:0;padding:4mm 5mm;box-shadow:none;page-break-inside:avoid;}} .no-print{{display:none!important;}} }}
.header {{ display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:3mm; }}
.title-section {{ flex:1; }}
.title-bar {{ text-align:center; border-bottom:2pt solid #1d8348; padding-bottom:3pt; margin-bottom:3pt; }}
.title-bar h1 {{ font-size:18pt; letter-spacing:8pt; color:#1d8348; font-weight:bold; margin:0; }}
.company {{ font-size:10pt; color:#666; text-align:center; margin-top:2pt; }}
.qr-section {{ width:25mm; text-align:right; }}
.qr-box {{ border:1pt solid #ddd; padding:2mm; text-align:center; font-size:7pt; color:#999; }}
.info-section {{ margin-bottom:3mm; }}
.info-table {{ width:100%; border-collapse:collapse; font-size:9pt; }}
.info-table td {{ padding:2pt 4pt; }}
.info-label {{ color:#555; white-space:nowrap; }}
.info-value {{ color:#111; font-weight:500; }}
.highlight {{ color:#1d8348; font-weight:bold; }}
.div-line {{ height:1pt; background:#1d8348; margin:2pt 0; }}
.table-wrap {{ flex:1; display:flex; flex-direction:column; min-height:0; margin:3pt 0; }}
.inv-table {{ width:100%; border-collapse:collapse; flex:1; table-layout:fixed; border:1pt solid #333; }}
.inv-table th, .inv-table td {{ border:0.5pt solid #333; padding:2pt 3mm; font-size:8pt; }}
.inv-table th {{ background:#1d8348; color:#fff; font-weight:bold; text-align:center; }}
.inv-table td {{ vertical-align:middle; }}
.c-name {{ width:25%; }}
.c-spec {{ width:20%; }}
.c-unit {{ width:10%; }}
.c-num {{ width:15%; text-align:right; }}
.total-section {{ display:flex; gap:3mm; margin-top:3pt; }}
.total-box {{ flex:1; background:#eafaf1; border:1pt solid #1d8348; padding:3pt 5pt; }}
.total-label {{ font-size:8pt; color:#1d8348; }}
.total-value {{ font-size:14pt; color:#c0392b; font-weight:bold; }}
.words-box {{ flex:2; background:#fffde7; border:1pt solid #d4ac0d; padding:3pt 5pt; }}
.words-label {{ font-size:7pt; color:#666; }}
.words-value {{ font-size:10pt; color:#333; font-weight:bold; }}
.sign-section {{ display:flex; justify-content:space-between; margin-top:8mm; }}
.sign-item {{ text-align:center; width:28%; }}
.sign-box {{ border-top:0.5pt solid #555; padding-top:2mm; font-size:8pt; color:#333; }}
.sign-role {{ font-size:7pt; color:#888; margin-bottom:1pt; }}
.footer {{ text-align:center; font-size:6pt; color:#aaa; margin-top:5mm; border-top:0.5pt dotted #ddd; padding-top:2mm; }}
.btn-print {{ display:none; }}
</style>
</head>
<body>
<div class="page-wrap">
<div class="page">
    <div class="header">
        <div class="title-section">
            <div class="title-bar"><h1>入 库 单</h1></div>
            <div class="company">{COMPANY_INFO["name"]}</div>
        </div>
        <div class="qr-section">
            <div class="qr-box">
                <div>单号:</div>
                <div style="font-weight:bold; font-size:9pt;">{order_no}</div>
            </div>
        </div>
    </div>

    <div class="div-line"></div>

    <div class="info-section">
        <table class="info-table">
            <tr>
                <td width="15%"><span class="info-label">日　　期：</span></td>
                <td width="30%"><span class="info-value">{date_str}</span></td>
                <td width="15%"><span class="info-label">存放仓库：</span></td>
                <td width="40%"><span class="info-value highlight">{warehouse}</span></td>
            </tr>
            <tr>
                <td><span class="info-label">供 应 商：</span></td>
                <td><span class="info-value">{supplier}</span></td>
                <td><span class="info-label">联 系 人：</span></td>
                <td><span class="info-value">{contact} {phone}</span></td>
            </tr>
            <tr>
                <td><span class="info-label">经 手 人：</span></td>
                <td><span class="info-value">{handler}</span></td>
                <td><span class="info-label">备　　注：</span></td>
                <td><span class="info-value">{remark or '无'}</span></td>
            </tr>
        </table>
    </div>

    <div class="table-wrap">
        <table class="inv-table">
            <thead>
                <tr>
                    <th>商品名称</th>
                    <th>规格型号</th>
                    <th>单位</th>
                    <th>数量</th>
                    <th>单价</th>
                    <th>金额</th>
                </tr>
            </thead>
            <tbody>
{rows_html}
            </tbody>
        </table>
    </div>

    <div class="total-section">
        <div class="total-box">
            <div class="total-label">合计数量: {fmt_qty(total_qty)}</div>
            <div class="total-value">¥{total_amt:.2f}</div>
        </div>
        <div class="words-box">
            <div class="words-label">大写金额</div>
            <div class="words-value">{words_cn}</div>
        </div>
    </div>

    <div class="sign-section">
        <div class="sign-item">
            <div class="sign-role">供应商（签章）</div>
            <div class="sign-box">{supplier}</div>
        </div>
        <div class="sign-item">
            <div class="sign-role">仓库管理员</div>
            <div class="sign-box">{operator}</div>
        </div>
        <div class="sign-item">
            <div class="sign-role">收货方（签收）</div>
            <div class="sign-box">&nbsp;</div>
        </div>
    </div>

    <div class="footer">
        {COMPANY_INFO["name"]} | 地址: {COMPANY_INFO["address"]} | 电话: {COMPANY_INFO["phone"]}<br/>
        打印时间: {now_str} | 库存管理系统 V3.0
    </div>
</div>
</div>
<div class="no-print" style="text-align:center; margin:20px;">
    <button class="btn-print" onclick="window.print()">打印</button>
</div>
<script>
function doPrint(){{
    document.querySelector('.btn-print').style.display='none';
    window.print();
    setTimeout(function(){{document.querySelector('.btn-print').style.display='block';}},100);
}}
document.addEventListener('DOMContentLoaded',function(){{
    setTimeout(doPrint,500);
}});
</script>
</body>
</html>'''
    return html


def generate_inventory_report_html(data):
    """生成库存报表HTML"""
    stats = data.get('stats', {})
    inventory = data.get('inventory', [])
    low_stock = data.get('low_stock', [])
    date_str = datetime.now().strftime('%Y-%m-%d %H:%M')

    total_value = float(stats.get('total_value', 0) or 0)
    total_qty = float(stats.get('total_qty', 0) or 0)

    rows_html = ""
    for i, inv in enumerate(inventory[:100], 1):
        current = float(inv.get('current_qty', 0) or 0)
        safety = float(inv.get('safety_stock', 0) or 0)
        max_s = float(inv.get('max_stock', 0) or 0)
        price = float(inv.get('unit_price', 0) or inv.get('product_price', 0) or 0)
        amount = current * price

        if current <= 0:
            status = "缺货"
            status_color = "#FF4B5C"
        elif current < safety:
            status = "预警"
            status_color = "#FF8C42"
        elif current > max_s and max_s > 0:
            status = "超储"
            status_color = "#3B9EFF"
        else:
            status = "正常"
            status_color = "#27AE60"

        bg = "#EBF5FB" if i % 2 == 0 else "#FFFFFF"
        rows_html += f"""                <tr style="background:{bg};">
                    <td style="text-align:center;">{i}</td>
                    <td>{inv.get('sku', '')}</td>
                    <td>{inv.get('product_name', inv.get('name', ''))}</td>
                    <td>{inv.get('spec', inv.get('specification', ''))}</td>
                    <td>{inv.get('warehouse_name', inv.get('warehouse', ''))}</td>
                    <td style="text-align:right;">{current:.0f}</td>
                    <td style="text-align:right;">{safety:.0f}</td>
                    <td style="text-align:right;">{max_s:.0f}</td>
                    <td style="text-align:right;">¥{price:.2f}</td>
                    <td style="text-align:right;">¥{amount:.2f}</td>
                    <td style="color:{status_color}; font-weight:bold;">{status}</td>
                </tr>
"""

    if len(inventory) > 100:
        rows_html += f"""                <tr>
                    <td colspan="11" style="text-align:center; color:#666;">... 还有 {len(inventory) - 100} 条记录未显示 ...</td>
                </tr>
"""

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>库存报表_{date_str}</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:'Microsoft YaHei','微软雅黑','SimSun',sans-serif; color:#222; background:#e8e8e8; }}
.page {{ width:297mm; margin:10px auto; background:#fff; padding:15mm 20mm; box-shadow:0 2px 8px rgba(0,0,0,.15); }}
@page {{ size:A4 landscape; margin:10mm; }}
@media print {{ body{{background:#fff;}} .page{{margin:0;box-shadow:none;padding:10mm 15mm;}} .no-print{{display:none!important;}} }}
.title {{ text-align:center; margin-bottom:8mm; }}
.title h1 {{ font-size:20pt; color:#1a5276; margin-bottom:3mm; letter-spacing:4pt; }}
.title .subtitle {{ font-size:10pt; color:#666; }}
.stats-grid {{ display:grid; grid-template-columns:repeat(5, 1fr); gap:5mm; margin-bottom:8mm; }}
.stat-card {{ background:#f8f9fa; border:1pt solid #e0e0e0; border-radius:2mm; padding:5mm; text-align:center; }}
.stat-value {{ font-size:14pt; font-weight:bold; color:#1a5276; }}
.stat-label {{ font-size:8pt; color:#666; margin-top:2mm; }}
.stat-card.warning .stat-value {{ color:#FF8C42; }}
.stat-card.danger .stat-value {{ color:#FF4B5C; }}
.stat-card.success .stat-value {{ color:#27AE60; }}
.table-wrap {{ margin-top:5mm; }}
.table {{ width:100%; border-collapse:collapse; font-size:7.5pt; }}
.table th, .table td {{ border:0.5pt solid #999; padding:2mm 2mm; text-align:left; }}
.table th {{ background:#1a5276; color:#fff; font-weight:bold; text-align:center; }}
.table td {{ vertical-align:middle; }}
.footer {{ text-align:center; font-size:7pt; color:#aaa; margin-top:10mm; border-top:0.5pt dotted #ddd; padding-top:3mm; }}
.btn-print {{ display:none; }}
</style>
</head>
<body>
<div class="page">
    <div class="title">
        <h1>库 存 明 细 报 表</h1>
        <div class="subtitle">{COMPANY_INFO["name"]} | 打印时间: {date_str}</div>
    </div>

    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-value">{stats.get('product_count', 0)}</div>
            <div class="stat-label">商品种类</div>
        </div>
        <div class="stat-card success">
            <div class="stat-value">{total_qty:,.0f}</div>
            <div class="stat-label">库存总量</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">¥{total_value:,.2f}</div>
            <div class="stat-label">库存总值</div>
        </div>
        <div class="stat-card warning">
            <div class="stat-value">{stats.get('low_stock_count', len(low_stock))}</div>
            <div class="stat-label">低库存预警</div>
        </div>
        <div class="stat-card danger">
            <div class="stat-value">{stats.get('out_stock_count', 0)}</div>
            <div class="stat-label">缺货商品</div>
        </div>
    </div>

    <div class="table-wrap">
        <table class="table">
            <thead>
                <tr>
                    <th>序号</th>
                    <th>SKU编码</th>
                    <th>商品名称</th>
                    <th>规格</th>
                    <th>仓库</th>
                    <th>当前库存</th>
                    <th>安全库存</th>
                    <th>最高库存</th>
                    <th>单价</th>
                    <th>库存金额</th>
                    <th>状态</th>
                </tr>
            </thead>
            <tbody>
{rows_html}
            </tbody>
        </table>
    </div>

    <div class="footer">
        {COMPANY_INFO["name"]} | 地址: {COMPANY_INFO["address"]} | 电话: {COMPANY_INFO["phone"]}<br/>
        库存管理系统 V3.0 | MySQL版
    </div>
</div>
<div class="no-print" style="text-align:center; margin:20px;">
    <button class="btn-print" onclick="window.print()">打印</button>
</div>
<script>
function doPrint(){{
    document.querySelector('.btn-print').style.display='none';
    window.print();
    setTimeout(function(){{document.querySelector('.btn-print').style.display='block';}},100);
}}
document.addEventListener('DOMContentLoaded',function(){{
    setTimeout(doPrint,500);
}});
</script>
</body>
</html>'''
    return html


def open_in_browser(html_content, filename="temp_invoice.html"):
    """在浏览器中打开HTML内容并自动打印"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', encoding='utf-8', delete=False) as f:
        f.write(html_content)
        filepath = f.name

    abs_path = os.path.abspath(filepath)
    file_url = f'file:///{abs_path.replace(chr(92), "/")}'

    try:
        webbrowser.open(file_url, new=2)
        return True
    except:
        try:
            os.startfile(abs_path)
            return True
        except:
            return False


def preview_in_browser(html_content, title="打印预览"):
    """在浏览器中打开HTML内容进行预览（不自动打印）"""
    import tempfile
    import threading

    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', encoding='utf-8', delete=False) as f:
        f.write(html_content)
        filepath = f.name

    abs_path = os.path.abspath(filepath)
    file_url = f'file:///{abs_path.replace(chr(92), "/")}'

    def open_browser():
        try:
            webbrowser.open(file_url, new=2)
        except Exception as e:
            try:
                os.startfile(abs_path)
            except Exception as e2:
                logger.warning(f"无法打开文件: {e2}")

    thread = threading.Thread(target=open_browser, daemon=True)
    thread.start()

    return filepath


def save_to_file(html_content, filename):
    """保存HTML内容到文件"""
    try:
        downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        filepath = os.path.join(downloads_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        return filepath
    except:
        temp_dir = tempfile.gettempdir()
        filepath = os.path.join(temp_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        return filepath


def print_outbound(data):
    """打印出库单"""
    html = generate_outbound_html(data)
    return open_in_browser(html, "出库单.html")


def print_inbound(data):
    """打印入库单"""
    html = generate_inbound_html(data)
    return open_in_browser(html, "入库单.html")


def print_inventory_report(data):
    """打印库存报表"""
    html = generate_inventory_report_html(data)
    return open_in_browser(html, "库存报表.html")


def preview_outbound(data):
    """预览出库单"""
    html = generate_outbound_html(data)
    return save_to_file(html, f"出库单预览_{data.get('order_no', datetime.now().strftime('%Y%m%d'))}.html")


def preview_inbound(data):
    """预览入库单"""
    html = generate_inbound_html(data)
    return save_to_file(html, f"入库单预览_{data.get('order_no', datetime.now().strftime('%Y%m%d'))}.html")


def preview_inventory_report(data):
    """预览库存报表"""
    html = generate_inventory_report_html(data)
    return save_to_file(html, f"库存报表预览_{datetime.now().strftime('%Y%m%d%H%M')}.html")


def set_company_info(name, address="", phone="", fax=""):
    """设置公司信息"""
    global COMPANY_INFO
    COMPANY_INFO["name"] = name
    COMPANY_INFO["address"] = address
    COMPANY_INFO["phone"] = phone
    COMPANY_INFO["fax"] = fax


def get_company_info():
    """获取公司信息"""
    return COMPANY_INFO.copy()
