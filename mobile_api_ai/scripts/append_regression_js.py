# -*- coding: utf-8 -*-
"""Append regression JS to the end of dispatch_center.html"""
with open('D:/yuan/不锈钢网带跟单3.0/mobile_api_ai/templates/dispatch_center.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Check if already properly completed
if 'function closeSrHistoryModal' in content and '</html>' in content:
    print("Already complete, skipping")
    exit(0)

# The file was truncated in submitOrUpdate. Remove the last partial function and replace with complete code.
# Find where the truncation happened
idx = content.rfind('function submitOrUpdate(){')
if idx == -1:
    print("Cannot find submitOrUpdate anchor")
    exit(1)

# Remove everything after submitOrUpdate (including the partial function)
content = content[:idx]

# Append complete code
content += """
function submitOrUpdate(){if(!orEditingId){alert('记录ID缺失');return;}fetch(OR_API+'/update',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({record_id:orEditingId,admin_user:window.currentUser||'调度员',reason:document.getElementById('ore-reason').value,title:document.getElementById('ore-title').value,priority:document.getElementById('ore-priority').value,target_operator:document.getElementById('ore-target-op').value})}).then(function(r){return r.json();}).then(function(ret){if(ret.code===0){alert('✅ '+ret.message);closeOrEditModal();loadOutsourceRegression();}else{alert('❌ '+ret.message);}}).catch(function(e){alert('❌ 请求失败: '+e.message);});}
function openOrWithdrawModal(id,order,step,op){orWithdrawingId=id;document.getElementById('orw-order').innerText=order;document.getElementById('orw-step').innerText=step;document.getElementById('orw-operator').innerText=op;document.getElementById('orw-reason').value='';document.getElementById('or-withdraw-modal').style.display='flex';}
function closeOrWithdrawModal(){document.getElementById('or-withdraw-modal').style.display='none';orWithdrawingId=null;}
function submitOrWithdraw(){if(!orWithdrawingId){alert('记录ID缺失');return;}var r=document.getElementById('orw-reason').value.trim();if(!r){alert('请填写撤回原因');return;}fetch(OR_API+'/withdraw',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({record_id:orWithdrawingId,admin_user:window.currentUser||'调度员',reason:'admin_withdraw:'+r})}).then(function(r){return r.json();}).then(function(ret){if(ret.code===0){alert('✅ '+ret.message);closeOrWithdrawModal();loadOutsourceRegression();}else{alert('❌ '+ret.message);}}).catch(function(e){alert('❌ 请求失败: '+e.message);});}
function openOrHistoryModal(id){document.getElementById('or-history-modal').style.display='flex';var bd=document.getElementById('orh-body');bd.innerHTML='<div style="text-align:center;color:#999;padding:30px;">加载中...</div>';fetch(OR_API+'/history_full?record_id='+encodeURIComponent(id)).then(function(r){return r.json();}).then(function(ret){if(ret.code!==0){bd.innerHTML='<div style="color:#e74c3c;">'+ret.message+'</div>';return;}var rec=(ret.data||{}).record||{},h=(ret.data||{}).history||[];var html='<div style="margin-bottom:15px;padding:12px;background:#f8f9fa;border-radius:6px;font-size:13px;"><div>订单: <strong>'+(rec.related_order||'')+'</strong></div></div>';if(!h.length){html+='<div style="text-align:center;color:#999;padding:20px;">暂无修改记录</div>';}else{h.forEach(function(item){html+='<div style="padding:12px;background:#fff;border-left:3px solid #1abc9c;margin-bottom:8px;border-radius:4px;"><div style="font-size:12px;color:#888;">'+item.reverted_at+'</div><div style="margin-top:5px;"><strong>'+(item.revert_reason||'')+'</strong></div><div style="font-size:12px;color:#666;margin-top:3px;">操作人: '+item.reverted_by+'</div></div>';});}bd.innerHTML=html;});}
function closeOrHistoryModal(){document.getElementById('or-history-modal').style.display='none';}

// ============= 排产回归审计 JS =============
var SR_API = 'http://localhost:5008/api/schedule_record';
var srCurrentPage = 1; var srEditingId = null; var srWithdrawingId = null;

function loadScheduleRegression(page){
  if(page) srCurrentPage = page; var params = [];
  ['sr-filter-order','sr-filter-operator','sr-filter-start','sr-filter-end'].forEach(function(id){
    var el=document.getElementById(id);if(!el||!el.value) return; var k=id.replace('sr-filter-','');
    if(k==='order') params.push('order_no='+encodeURIComponent(el.value));
    else if(k==='operator') params.push('operator='+encodeURIComponent(el.value));
    else if(k==='start') params.push('start_date='+encodeURIComponent(el.value+' 00:00:00'));
    else if(k==='end') params.push('end_date='+encodeURIComponent(el.value+' 23:59:59'));
  });
  params.push('page='+srCurrentPage,'page_size=20');
  var listBox=document.getElementById('sr-list');
  listBox.innerHTML='<div style="padding:30px;text-align:center;color:#999;">加载中...</div>';
  fetch(SR_API+'/list?'+params.join('&')).then(function(r){return r.json();}).then(function(ret){
    if(ret.code!==0){listBox.innerHTML='<div style="padding:30px;text-align:center;color:#e74c3c;">'+(ret.message||'')+'</div>';return;}
    var data=ret.data||{},rows=data.list||[];
    document.getElementById('sr-total').innerText=data.total||0;
    if(!rows.length){listBox.innerHTML='<div style="padding:30px;text-align:center;color:#999;">暂无数据</div>';document.getElementById('sr-pagination').innerHTML='';return;}
    var html='<table style="width:100%;border-collapse:collapse;font-size:13px;"><thead><tr style="background:#f8f9fa;">'+
      '<th style="padding:10px;text-align:left;border-bottom:1px solid #eee;">订单号</th>'+
      '<th style="padding:10px;text-align:left;border-bottom:1px solid #eee;">标题</th>'+
      '<th style="padding:10px;text-align:left;border-bottom:1px solid #eee;">操作员</th>'+
      '<th style="padding:10px;text-align:left;border-bottom:1px solid #eee;">优先级</th>'+
      '<th style="padding:10px;text-align:left;border-bottom:1px solid #eee;">状态</th>'+
      '<th style="padding:10px;text-align:left;border-bottom:1px solid #eee;">时间</th>'+
      '<th style="padding:10px;text-align:center;border-bottom:1px solid #eee;">审计</th>'+
      '<th style="padding:10px;text-align:center;border-bottom:1px solid #eee;">操作</th></tr></thead><tbody>';
    rows.forEach(function(r){
      var d=new Date(r.created_at),ts=d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0')+' '+String(d.getHours()).padStart(2,'0')+':'+String(d.getMinutes()).padStart(2,'0');
      var pc=r.priority==='urgent'?'#e74c3c':r.priority==='high'?'#e67e22':'#95a5a6';
      html+='<tr style="border-bottom:1px solid #f0f0f0;">'+
        '<td style="padding:10px;">'+(r.related_order||'')+'</td>'+
        '<td style="padding:10px;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">'+(r.title||'')+'</td>'+
        '<td style="padding:10px;">'+(r.target_operator||'')+'</td>'+
        '<td style="padding:10px;font-size:12px;color:'+pc+';">'+(r.priority||'')+'</td>'+
        '<td style="padding:10px;font-size:12px;">'+(r.status||'')+'</td>'+
        '<td style="padding:10px;font-size:12px;color:#888;">'+ts+'</td>'+
        '<td style="padding:10px;text-align:center;font-size:11px;">'+(r.history_count?'<span style="color:#3498db;">'+r.history_count+'次</span>':'-')+'</td>'+
        '<td style="padding:10px;text-align:center;">'+
        '<button class="sr-btn-edit" data-id="'+r.id+'" data-order="'+(r.related_order||'')+'" data-step="'+(r.related_process||'')+'" data-op="'+(r.target_operator||'')+'" data-title="'+escapeHtml(r.title||'')+'" data-pri="'+(r.priority||'')+'" style="padding:3px 8px;background:#3498db;color:#fff;border:none;border-radius:4px;cursor:pointer;margin-right:4px;font-size:12px;">修改</button>'+
        '<button class="sr-btn-wd" data-id="'+r.id+'" data-order="'+(r.related_order||'')+'" data-step="'+(r.related_process||'')+'" data-op="'+(r.target_operator||'')+'" style="padding:3px 8px;background:#e74c3c;color:#fff;border:none;border-radius:4px;cursor:pointer;margin-right:4px;font-size:12px;">撤回</button>'+
        '<button class="sr-btn-hist" data-id="'+r.id+'" style="padding:3px 8px;background:#95a5a6;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:12px;">历史</button></td></tr>';
    });
    html+='</tbody></table>';
    listBox.innerHTML=html;
    listBox.querySelectorAll('.sr-btn-edit').forEach(function(b){b.onclick=function(){var d=b.dataset;openSrEditModal(d.id,d.order,d.step,d.op,d.title,d.pri);};});
    listBox.querySelectorAll('.sr-btn-wd').forEach(function(b){b.onclick=function(){var d=b.dataset;openSrWithdrawModal(d.id,d.order,d.step,d.op);};});
    listBox.querySelectorAll('.sr-btn-hist').forEach(function(b){b.onclick=function(){openSrHistoryModal(b.dataset.id);};});
    var tp=Math.ceil((data.total||0)/(data.page_size||20)),pg='';
    if(tp>1) for(var i=1;i<=tp;i++){var a=(i===srCurrentPage)?'background:#3498db;color:#fff;':'background:#fff;color:#333;';pg+='<button onclick="loadScheduleRegression('+i+')" style="padding:5px 10px;border:1px solid #ddd;border-radius:4px;cursor:pointer;'+a+'">'+i+'</button>';}
    document.getElementById('sr-pagination').innerHTML=pg;
  }).catch(function(e){listBox.innerHTML='<div style="padding:30px;text-align:center;color:#e74c3c;">加载失败: '+e.message+'</div>';});
}
function resetScheduleRegressionFilter(){['sr-filter-order','sr-filter-operator','sr-filter-start','sr-filter-end'].forEach(function(id){var el=document.getElementById(id);if(el)el.value='';});loadScheduleRegression(1);}
function openSrEditModal(id,order,step,op,title,pri){srEditingId=id;document.getElementById('sre-order').innerText=order;document.getElementById('sre-step').innerText=step;document.getElementById('sre-operator').innerText=op;document.getElementById('sre-title').value=title||'';document.getElementById('sre-priority').value=pri||'normal';document.getElementById('sre-target-op').value=op||'';document.getElementById('sre-reason').value='admin_force';document.getElementById('sr-edit-modal').style.display='flex';}
function closeSrEditModal(){document.getElementById('sr-edit-modal').style.display='none';srEditingId=null;}
function submitSrUpdate(){if(!srEditingId){alert('记录ID缺失');return;}fetch(SR_API+'/update',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({record_id:srEditingId,admin_user:window.currentUser||'调度员',reason:document.getElementById('sre-reason').value,title:document.getElementById('sre-title').value,priority:document.getElementById('sre-priority').value,target_operator:document.getElementById('sre-target-op').value})}).then(function(r){return r.json();}).then(function(ret){if(ret.code===0){alert('✅ '+ret.message);closeSrEditModal();loadScheduleRegression();}else{alert('❌ '+ret.message);}}).catch(function(e){alert('❌ 请求失败: '+e.message);});}
function openSrWithdrawModal(id,order,step,op){srWithdrawingId=id;document.getElementById('srw-order').innerText=order;document.getElementById('srw-step').innerText=step;document.getElementById('srw-operator').innerText=op;document.getElementById('srw-reason').value='';document.getElementById('sr-withdraw-modal').style.display='flex';}
function closeSrWithdrawModal(){document.getElementById('sr-withdraw-modal').style.display='none';srWithdrawingId=null;}
function submitSrWithdraw(){if(!srWithdrawingId){alert('记录ID缺失');return;}var r=document.getElementById('srw-reason').value.trim();if(!r){alert('请填写撤回原因');return;}fetch(SR_API+'/withdraw',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({record_id:srWithdrawingId,admin_user:window.currentUser||'调度员',reason:'admin_withdraw:'+r})}).then(function(r){return r.json();}).then(function(ret){if(ret.code===0){alert('✅ '+ret.message);closeSrWithdrawModal();loadScheduleRegression();}else{alert('❌ '+ret.message);}}).catch(function(e){alert('❌ 请求失败: '+e.message);});}
function openSrHistoryModal(id){document.getElementById('sr-history-modal').style.display='flex';var bd=document.getElementById('srh-body');bd.innerHTML='<div style="text-align:center;color:#999;padding:30px;">加载中...</div>';fetch(SR_API+'/history_full?record_id='+encodeURIComponent(id)).then(function(r){return r.json();}).then(function(ret){if(ret.code!==0){bd.innerHTML='<div style="color:#e74c3c;">'+ret.message+'</div>';return;}var rec=(ret.data||{}).record||{},h=(ret.data||{}).history||[];var html='<div style="margin-bottom:15px;padding:12px;background:#f8f9fa;border-radius:6px;font-size:13px;"><div>订单: <strong>'+(rec.related_order||'')+'</strong></div></div>';if(!h.length){html+='<div style="text-align:center;color:#999;padding:20px;">暂无修改记录</div>';}else{h.forEach(function(item){html+='<div style="padding:12px;background:#fff;border-left:3px solid #3498db;margin-bottom:8px;border-radius:4px;"><div style="font-size:12px;color:#888;">'+item.reverted_at+'</div><div style="margin-top:5px;"><strong>'+(item.revert_reason||'')+'</strong></div><div style="font-size:12px;color:#666;margin-top:3px;">操作人: '+item.reverted_by+'</div></div>';});}bd.innerHTML=html;});}
function closeSrHistoryModal(){document.getElementById('sr-history-modal').style.display='none';}

  </script>
</body>
</html>
"""

with open('D:/yuan/不锈钢网带跟单3.0/mobile_api_ai/templates/dispatch_center.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Done: dispatch_center.html is complete")
