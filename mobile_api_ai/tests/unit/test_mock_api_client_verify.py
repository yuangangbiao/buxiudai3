def test_mock_api_client_patches_import(mock_api_client):
    from container_center.client import ContainerCenterClient
    client = ContainerCenterClient()
    assert client is mock_api_client


def test_mock_api_client_query_documents(mock_api_client):
    result = mock_api_client.query_documents('work_order', status='pending')
    assert result['total'] == 2
    assert len(result['items']) == 2


def test_mock_api_client_get_document(mock_api_client):
    result = mock_api_client.get_document('work_order', 'WO001')
    assert result['id'] == 'WO001'
    assert result['customer_name'] == '测试客户'


def test_mock_api_client_create_document(mock_api_client):
    result = mock_api_client.create_document('work_order', {'customer': '新客户'})
    assert result['id'] == 'WO001'


def test_mock_api_client_send_message(mock_api_client):
    result = mock_api_client.send_message('hello', to='user', msg_type='text', channel='wechat')
    assert result['message_id'] == 'MSG001'


def test_mock_api_client_get_operators(mock_api_client):
    result = mock_api_client.get_operators('编织组')
    assert len(result) == 3
    assert result[0]['name'] == '张三'
