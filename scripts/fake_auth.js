// Inject fake auth token for testing
const fakeUser = {id: 1, name: '测试用户', department: '生产部', role: 'worker', wechat_userid: ''};
const token = btoa('1:测试用户');
localStorage.setItem('dispatch_token', token);
localStorage.setItem('dispatch_user', JSON.stringify(fakeUser));
window.location.href = '/orders';
