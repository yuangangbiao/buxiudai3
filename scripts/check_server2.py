import urllib.request
r = urllib.request.urlopen('http://localhost:5001/shipment')
c = r.read().decode('utf-8')
print('cFreight:', 'cFreight' in c)
print('cShipQty:', 'cShipQty' in c)
print('cFinishedGoods:', 'cFinishedGoods' in c)
print('cOrderNo:', 'cOrderNo' in c)
print('Total length:', len(c))
