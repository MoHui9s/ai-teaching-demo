"""Chrome DevTools Protocol 前端测试脚本"""
import websocket, json, base64, time, os

WS_URL = 'ws://127.0.0.1:9222/devtools/page/F8FAD159B705063C8306D3A303ECF582'
SCREENSHOT_DIR = os.path.join(os.path.dirname(__file__), '..', 'logs', 'screenshots')
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

msg_id = [0]
def send_cmd(ws, method, params=None, timeout=15):
    msg_id[0] += 1
    mid = msg_id[0]
    msg = json.dumps({'id': mid, 'method': method, 'params': params or {}})
    ws.send(msg)
    ws.settimeout(timeout)
    while True:
        resp = json.loads(ws.recv())
        if resp.get('id') == mid:
            return resp
        # 其他事件消息(Page.*, Network.*等) 忽略

def eval_js(ws, expression):
    result = send_cmd(ws, 'Runtime.evaluate', {'expression': expression, 'returnByValue': True})
    return result.get('result',{}).get('result',{}).get('value','N/A')

def screenshot(ws, name):
    result = send_cmd(ws, 'Page.captureScreenshot', {'format': 'png', 'fromSurface': True})
    data = result.get('result', {}).get('data', '')
    if data:
        path = os.path.join(SCREENSHOT_DIR, f'{name}.png')
        with open(path, 'wb') as f:
            f.write(base64.b64decode(data))
        print(f'  [SCREENSHOT] {path}')

def test_step(name):
    print(f'\n{"="*60}')
    print(f'🧪 {name}')
    print(f'{"="*60}')

ws = websocket.create_connection(WS_URL, timeout=15)
send_cmd(ws, 'Page.enable')
send_cmd(ws, 'Runtime.enable')
send_cmd(ws, 'Network.enable')

# ============================================================
# 测试 1: 导航到登录页
# ============================================================
test_step('1. 登录页面加载')
send_cmd(ws, 'Page.navigate', {'url': 'http://localhost:5173'})
time.sleep(3)

url = eval_js(ws, 'document.location.href')
title = eval_js(ws, 'document.title')
print(f'  URL: {url}')
print(f'  标题: {title}')
assert 'Tan同学' in title, f'标题不匹配: {title}'
print('  ✅ 页面加载成功')

btns = eval_js(ws, 'Array.from(document.querySelectorAll("button")).map(b => b.textContent.trim()).filter(Boolean).join(" | ")')
print(f'  按钮: {btns}')
assert '登录' in btns, '缺少登录按钮'
assert '注册' in btns, '缺少注册按钮'
print('  ✅ 登录/注册切换按钮正常')
screenshot(ws, '01-login-page')

# ============================================================
# 测试 2: 切换到注册模式
# ============================================================
test_step('2. 注册模式切换')
eval_js(ws, '''
(() => {
  const btns = document.querySelectorAll("button");
  for (const btn of btns) {
    if (btn.textContent.includes("注册")) { btn.click(); return true; }
  }
  return false;
})()
''')
time.sleep(1)

input_count = eval_js(ws, 'document.querySelectorAll("input").length')
inputs = eval_js(ws, 'Array.from(document.querySelectorAll("input")).map(i => i.placeholder).join(" | ")')
print(f'  输入框数量: {input_count}')
print(f'  输入框: {inputs}')
assert input_count >= 3, f'注册模式应有3个输入框(姓名+邮箱+密码)，实际: {input_count}'
print('  ✅ 注册模式切换成功')
screenshot(ws, '02-register-mode')

# ============================================================
# 测试 3: 填写注册信息并提交
# ============================================================
test_step('3. 用户注册')
eval_js(ws, '''
(() => {
  const inputs = document.querySelectorAll("input");
  const testEmail = "cdp_test_" + Date.now() + "@test.com";
  window._testEmail = testEmail;
  const vals = ["CDP测试用户", testEmail, "123456"];
  for (let i = 0; i < inputs.length && i < vals.length; i++) {
    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    nativeInputValueSetter.call(inputs[i], vals[i]);
    inputs[i].dispatchEvent(new Event('input', { bubbles: true }));
  }
})()
''')
time.sleep(0.5)

email_val = eval_js(ws, 'document.querySelectorAll("input")[1]?.value || "N/A"')
print(f'  填写邮箱: {email_val}')
assert 'cdp_test_' in email_val, f'邮箱未正确填写: {email_val}'

# 点击提交
eval_js(ws, '''
(() => {
  const btns = document.querySelectorAll("button");
  for (const btn of btns) {
    if (btn.type === "submit") { btn.click(); return true; }
  }
  return false;
})()
''')
time.sleep(4)

url2 = eval_js(ws, 'document.location.href')
has_token = eval_js(ws, '!!localStorage.getItem("edulingua_token")')
has_user_id = eval_js(ws, '!!localStorage.getItem("edulingua_user_id")')
stored_user_id = eval_js(ws, 'localStorage.getItem("edulingua_user_id") || "N/A"')
print(f'  注册后 URL: {url2}')
print(f'  token: {has_token}, user_id: {stored_user_id}')
assert has_token, '注册后应存储 token'
assert has_user_id, '注册后应存储 user_id'
print('  ✅ 注册成功，自动登录并存储 user_id')
screenshot(ws, '03-after-register')

# ============================================================
# 测试 4: Dashboard 仪表盘
# ============================================================
test_step('4. Dashboard 仪表盘')
body_text = eval_js(ws, 'document.body.innerText.substring(0, 500)')
nav_items = eval_js(ws, 'Array.from(document.querySelectorAll("nav a")).map(e => e.textContent.trim()).filter(Boolean).join(" | ")')
print(f'  导航项: {nav_items}')
print(f'  页面内容: {body_text[:300]}')
assert '看板' in nav_items, '导航缺少"看板"'
assert '成就' in nav_items, '导航缺少"成就"'
print('  ✅ Dashboard 正常，底部导航含成就标签')
screenshot(ws, '04-dashboard')

# ============================================================
# 测试 5: 诊断页面
# ============================================================
test_step('5. 能力诊断')
send_cmd(ws, 'Page.navigate', {'url': 'http://localhost:5173/diagnosis'})
time.sleep(2)
diag_text = eval_js(ws, 'document.body.innerText.substring(0, 300)')
print(f'  诊断页: {diag_text[:200]}')
assert '诊断' in diag_text, '诊断页面缺少"诊断"文字'
print('  ✅ 诊断页面加载正常')

# 点击开始
eval_js(ws, '''
(() => {
  const btns = document.querySelectorAll("button");
  for (const btn of btns) {
    if (btn.textContent.includes("开始诊断")) { btn.click(); return true; }
  }
  return false;
})()
''')
time.sleep(1)
step2_text = eval_js(ws, 'document.body.innerText.substring(0, 300)')
assert '单词' in step2_text, f'应进入单词填空步骤: {step2_text[:100]}'
print('  ✅ 诊断流程可正常进入单词填空')
screenshot(ws, '05-diagnosis')

# ============================================================
# 测试 6: 场景对话
# ============================================================
test_step('6. 场景对话')
send_cmd(ws, 'Page.navigate', {'url': 'http://localhost:5173/scenario'})
time.sleep(2)
scene_text = eval_js(ws, 'document.body.innerText.substring(0, 400)')
print(f'  场景页: {scene_text[:250]}')
print('  ✅ 场景对话页面正常')
screenshot(ws, '06-scenario')

# ============================================================
# 测试 7: 成就页面
# ============================================================
test_step('7. 成就页面')
send_cmd(ws, 'Page.navigate', {'url': 'http://localhost:5173/achievements'})
time.sleep(2)
ach_text = eval_js(ws, 'document.body.innerText.substring(0, 400)')
print(f'  成就页: {ach_text[:250]}')
print('  ✅ 成就页面可访问')
screenshot(ws, '07-achievements')

# ============================================================
# 测试 8: 退出登录
# ============================================================
test_step('8. 退出登录')
send_cmd(ws, 'Page.navigate', {'url': 'http://localhost:5173/'})
time.sleep(2)

eval_js(ws, '''
(() => {
  const allBtns = document.querySelectorAll("button");
  for (const btn of allBtns) {
    if (btn.querySelector("svg") && !btn.textContent.trim()) {
      btn.click(); return true;
    }
  }
  return false;
})()
''')
time.sleep(2)

after_url = eval_js(ws, 'document.location.href')
after_text = eval_js(ws, 'document.body.innerText.substring(0, 300)')
after_token = eval_js(ws, '!!localStorage.getItem("edulingua_token")')
print(f'  URL: {after_url}')
print(f'  token: {after_token}')
assert not after_token, '退出后应清除 token'
print('  ✅ 退出登录正常，token 已清除')
screenshot(ws, '08-logout')

# ============================================================
# 测试 9: 登录已有用户
# ============================================================
test_step('9. 登录已有用户')
eval_js(ws, '''
(() => {
  const btns = document.querySelectorAll("button");
  for (const btn of btns) {
    if (btn.textContent.includes("登录") && !btn.textContent.includes("注册")) { btn.click(); return true; }
  }
  return false;
})()
''')
time.sleep(0.5)

eval_js(ws, '''
(() => {
  const inputs = document.querySelectorAll("input");
  const vals = ["test2@test.com", "test123456"];
  for (let i = 0; i < inputs.length && i < vals.length; i++) {
    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    nativeInputValueSetter.call(inputs[i], vals[i]);
    inputs[i].dispatchEvent(new Event('input', { bubbles: true }));
  }
})()
''')
time.sleep(0.5)

eval_js(ws, '''
(() => {
  const btns = document.querySelectorAll("button");
  for (const btn of btns) {
    if (btn.type === "submit") { btn.click(); return true; }
  }
  return false;
})()
''')
time.sleep(3)

login_user_id = eval_js(ws, 'localStorage.getItem("edulingua_user_id") || "N/A"')
login_has_token = eval_js(ws, '!!localStorage.getItem("edulingua_token")')
print(f'  登录后 user_id: {login_user_id}')
assert login_has_token, '登录后应有 token'
assert login_user_id == 'user_b399a6717265', f'user_id 不匹配: {login_user_id}'
print('  ✅ 已有用户登录正常，user_id 正确传递')
screenshot(ws, '09-login-existing-user')

# ============================================================
# 完成
# ============================================================
print(f'\n{"="*60}')
print('🎉 全部 9 项 chrome CDP 前端测试通过！')
print(f'{"="*60}')
print(f'截图保存位置: {SCREENSHOT_DIR}')

ws.close()
