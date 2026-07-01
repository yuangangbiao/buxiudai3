import json
with open('d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center_data.json','r',encoding='utf-8') as f:
    d=json.load(f)
processes = d.get('processes',[])
print(f"cache processes: {len(processes)} tiao")
