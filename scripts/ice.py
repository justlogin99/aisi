#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# scripts/icehost_renew.py

import os
import time
import asyncio
import aiohttp
import random
import re
from urllib.parse import unquote
from seleniumbase import SB
from datetime import datetime

BASE_URL = "https://dash.icehost.pl"
DOMAIN = "dash.icehost.pl"

# ✅ Cookie 白名单
COOKIE_WHITELIST = ["cf_clearance", "XSRF-TOKEN", "icehostpl_session"]


def mask_sensitive(text, show_chars=3):
    """脱敏敏感信息"""
    if not text:
        return "***"
    text = str(text)
    if len(text) <= show_chars * 2:
        return "*" * len(text)
    return text[:show_chars] + "*" * (len(text) - show_chars * 2) + text[-show_chars:]


def mask_server_id(server_id):
    """脱敏服务器 ID"""
    if not server_id:
        return "***"
    if len(server_id) <= 4:
        return "*" * len(server_id)
    return server_id[:2] + "*" * (len(server_id) - 4) + server_id[-2:]


def parse_cookie(cookie_str):
    """✅ 解析 Cookie 并只保留白名单中的字段"""
    if not cookie_str:
        return {}
    cookies = {}
    cookie_str = cookie_str.strip()
    cookie_pairs = [c.strip() for c in cookie_str.split(";") if c.strip()]
    
    for pair in cookie_pairs:
        if "=" in pair:
            parts = pair.split("=", 1)
            if len(parts) == 2:
                name = parts[0].strip()
                value = unquote(parts[1].strip())
                
                # 白名单过滤
                is_whitelisted = any(
                    name.startswith(w) if w.endswith("_") else name == w
                    for w in COOKIE_WHITELIST
                )
                
                if is_whitelisted:
                    cookies[name] = value
                    print(f"[Cookie] 保留字段: {name}")
                else:
                    print(f"[Cookie] 已过滤字段: {name}")
    
    print(f"[Cookie] 共保留 {len(cookies)} 个有效字段")
    return cookies


def random_delay(min_sec=0.5, max_sec=2.0):
    """随机延迟"""
    time.sleep(random.uniform(min_sec, max_sec))


async def tg_notify(message):
    """异步发送 Telegram 消息"""
    token = os.environ.get("TG_BOT_TOKEN")
    chat_id = os.environ.get("TG_CHAT_ID")
    if not token or not chat_id:
        return
    async with aiohttp.ClientSession() as session:
        try:
            await session.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
            )
        except Exception as e:
            print(f"[TG] 发送失败: {e}")


async def tg_notify_photo(photo_path, caption=""):
    """异步发送 Telegram 图片"""
    token = os.environ.get("TG_BOT_TOKEN")
    chat_id = os.environ.get("TG_CHAT_ID")
    if not token or not chat_id or not os.path.exists(photo_path):
        return
    async with aiohttp.ClientSession() as session:
        try:
            with open(photo_path, "rb") as f:
                data = aiohttp.FormData()
                data.add_field("chat_id", chat_id)
                data.add_field("photo", f, filename=os.path.basename(photo_path))
                data.add_field("caption", caption)
                data.add_field("parse_mode", "HTML")
                await session.post(f"https://api.telegram.org/bot{token}/sendPhoto", data=data)
        except Exception as e:
            print(f"[TG] 图片发送失败: {e}")


def sync_tg_notify(message):
    """同步发送 Telegram 消息"""
    asyncio.run(tg_notify(message))


def sync_tg_notify_photo(photo_path, caption=""):
    """同步发送 Telegram 图片"""
    asyncio.run(tg_notify_photo(photo_path, caption))


EXPAND_POPUP_JS = """
(function() {
    var turnstileInput = document.querySelector('input[name="cf-turnstile-response"]');
    if (!turnstileInput) return 'no turnstile input';
    var el = turnstileInput;
    for (var i = 0; i < 20; i++) {
        el = el.parentElement;
        if (!el) break;
        var style = window.getComputedStyle(el);
        if (style.overflow === 'hidden' || style.overflowX === 'hidden' || style.overflowY === 'hidden') {
            el.style.overflow = 'visible';
        }
        el.style.minWidth = 'max-content';
    }
    var iframes = document.querySelectorAll('iframe');
    iframes.forEach(function(iframe) {
        if (iframe.src && iframe.src.includes('challenges.cloudflare.com')) {
            iframe.style.width = '300px';
            iframe.style.height = '65px';
            iframe.style.minWidth = '300px';
            iframe.style.visibility = 'visible';
            iframe.style.opacity = '1';
            iframe.style.position = 'relative';
            iframe.style.zIndex = '99999';
        }
    });
    return 'done';
})();
"""


def check_turnstile_exists(sb):
    """检查 Turnstile 是否存在"""
    try:
        return sb.execute_script(
            "return document.querySelector('input[name=\"cf-turnstile-response\"]') !== null;"
        )
    except:
        return False


def check_turnstile_solved(sb):
    """检查 Turnstile 是否已解决"""
    try:
        return sb.execute_script("""
            var input = document.querySelector('input[name="cf-turnstile-response"]');
            return input && input.value && input.value.length > 20;
        """)
    except:
        return False


def scroll_to_turnstile(sb):
    """滚动到 Turnstile"""
    try:
        sb.execute_script("""
            var iframes = document.querySelectorAll('iframe');
            for (var i = 0; i < iframes.length; i++) {
                if (iframes[i].src && iframes[i].src.includes('cloudflare')) {
                    iframes[i].scrollIntoView({behavior: 'instant', block: 'center'});
                    break;
                }
            }
        """)
        time.sleep(0.5)
    except:
        pass


def get_turnstile_checkbox_coords(sb):
    """获取 Turnstile 复选框坐标"""
    try:
        return sb.execute_script("""
            var iframes = document.querySelectorAll('iframe');
            for (var i = 0; i < iframes.length; i++) {
                var src = iframes[i].src || '';
                if (src.includes('cloudflare') || src.includes('turnstile')) {
                    var rect = iframes[i].getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        var cx = Math.round(rect.x + 12);
                        var cy = rect.height > 100 ? Math.round(rect.y + 12) : Math.round(rect.y + (rect.height / 2));
                        return { x: rect.x, y: rect.y, width: rect.width, height: rect.height, click_x: cx, click_y: cy };
                    }
                }
            }
            return null;
        """)
    except:
        return None


def activate_browser_window():
    """激活浏览器窗口"""
    try:
        import subprocess
        result = subprocess.run(
            ["xdotool", "search", "--onlyvisible", "--class", "chrome"],
            capture_output=True, text=True, timeout=3
        )
        window_ids = result.stdout.strip().split('\n')
        if window_ids and window_ids[0]:
            subprocess.run(
                ["xdotool", "windowactivate", window_ids[0]],
                timeout=2, stderr=subprocess.DEVNULL
            )
            time.sleep(0.2)
            return True
    except:
        pass
    return False


def click_turnstile_checkbox(sb, coords=None):
    """点击 Turnstile 复选框"""
    import os
    scroll_to_turnstile(sb)
    time.sleep(0.3)
    if not coords:
        coords = get_turnstile_checkbox_coords(sb)
    if not coords:
        print("[!] 无法获取 Turnstile 坐标")
        return False
    
    print(f"[*] Turnstile iframe 尺寸: {coords['width']:.0f}x{coords['height']:.0f}")
    print(f"[*] Turnstile 页面坐标: ({coords['x']:.0f}, {coords['y']:.0f})")
    
    try:
        window_info = sb.execute_script("""
            return {
                screenX: window.screenX || 0,
                screenY: window.screenY || 0,
                outerHeight: window.outerHeight,
                innerHeight: window.innerHeight,
                scrollY: window.scrollY || 0
            };
        """)
        chrome_bar_height = window_info["outerHeight"] - window_info["innerHeight"]
        zoom_level = 0.8
        abs_x = int((coords["click_x"] * zoom_level) + window_info["screenX"])
        abs_y = int((coords["click_y"] * zoom_level) + window_info["screenY"] + chrome_bar_height)
        print(f"[*] 屏幕绝对点击坐标: ({abs_x}, {abs_y})")
        
        activate_browser_window()
        os.system(f"xdotool mousemove {abs_x} {abs_y}")
        time.sleep(0.5)
        os.system("xdotool mousedown 1 sleep 0.1 mouseup 1")
        return True
    except Exception as e:
        print(f"[!] 鼠标定位执行失败: {e}")
        return False


def handle_cf_challenge(sb, screenshot_prefix=""):
    """处理 Cloudflare Turnstile 挑战"""
    screenshot_name = f"{screenshot_prefix}_cf_challenge.png" if screenshot_prefix else "cf_challenge.png"
    
    print("\n[CF] 等待 Turnstile 出现...")
    turnstile_ready = False
    for _ in range(15):
        if check_turnstile_exists(sb):
            turnstile_ready = True
            print("[+] 检测到 Turnstile")
            break
        time.sleep(1)
    
    if not turnstile_ready:
        print("[!] 未检测到 Turnstile")
        sb.save_screenshot(screenshot_name)
        return False
    
    print("\n[CF] 修复样式并滚动到 Turnstile...")
    for _ in range(3):
        sb.execute_script(EXPAND_POPUP_JS)
        time.sleep(0.5)
    scroll_to_turnstile(sb)
    time.sleep(0.8)
    sb.save_screenshot(screenshot_name)
    
    print("\n[CF] 点击 Turnstile...")
    if not check_turnstile_solved(sb):
        sb.execute_script(EXPAND_POPUP_JS)
        time.sleep(0.3)
        scroll_to_turnstile(sb)
        time.sleep(0.3)
        coords = get_turnstile_checkbox_coords(sb)
        click_turnstile_checkbox(sb, coords)
        
        for i in range(10):
            time.sleep(0.5)
            if check_turnstile_solved(sb):
                print("[+] Turnstile 验证通过!")
                return True
        
        print("[!] Turnstile 验证未通过")
        sb.save_screenshot(screenshot_name)
        return False
    else:
        print("[+] Turnstile 已自动通过!")
        return True


def get_expiry_time_from_page(sb):
    """从页面获取到期时间"""
    try:
        text = sb.execute_script("""
            var elements = document.querySelectorAll('p, div, span');
            for (var i = 0; i < elements.length; i++) {
                var content = elements[i].textContent;
                if (content && content.toLowerCase().includes('data ważności:')) {
                    return content;
                }
            }
            return null;
        """)
        
        if text:
            # 提取 "XXXX-XX-XX XX:XX:XX" 格式的日期时间
            match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', text)
            if match:
                time_str = match.group(1)
                print(f"[*] 成功提取到期时间: {time_str}")
                return time_str
        return None
    except Exception as e:
        print(f"[!] 获取到期时间异常: {e}")
        return None


def is_logged_in(sb):
    """检查是否已登陆"""
    try:
        url = sb.get_current_url()
        print(f"[*] 当前 URL: {url}")
        
        # 检查是否在登陆页面
        if "/login" in url or "/auth" in url:
            print("[!] 在登陆页面，未登陆")
            return False
        
        # 尝试获取到期时间作为登陆验证
        expiry = get_expiry_time_from_page(sb)
        if expiry:
            return True
        
        print("[!] 未找到到期时间信息")
        return False
    except Exception as e:
        print(f"[!] 登陆检查异常: {e}")
        return False


def renew_server(sb, screenshot_prefix=""):
    """续期服务器"""
    print("\n" + "=" * 60)
    print("[续期] 执行续期操作")
    print("=" * 60)
    
    # 获取续期前的时间
    time_before = get_expiry_time_from_page(sb)
    
    # 点击续期按钮
    print("\n[续期] 查找续期按钮...")
    try:
        # 查找包含 "Dodaj 6 godzin" 的按钮
        renew_btn_xpath = '//button[contains(., "Dodaj 6 godzin")]'
        if sb.is_element_present(renew_btn_xpath):
            print("[续期] 找到续期按钮，点击...")
            sb.click(renew_btn_xpath)
            time.sleep(2)
        else:
            print("[!] 未找到续期按钮")
            screenshot_path = f"{screenshot_prefix}_no_button.png" if screenshot_prefix else "no_button.png"
            sb.save_screenshot(screenshot_path)
            return {"status": "error", "message": "未找到续期按钮"}
    except Exception as e:
        print(f"[!] 点击续期按钮异常: {e}")
        return {"status": "error", "message": str(e)}
    
    # 检查是否有 CF 验证
    print("\n[续期] 检查 Cloudflare 验证...")
    if check_turnstile_exists(sb):
        print("[续期] 检测到 CF 验证，开始处理...")
        if not handle_cf_challenge(sb, screenshot_prefix):
            return {"status": "error", "message": "CF 验证失败"}
        time.sleep(2)
    else:
        print("[续期] 无需 CF 验证")
    
    # 根据页面文本判断续期结果
    print("\n[续期] 检查执行结果提示...")
    status = "uncertain"
    message = ""
    
    # 轮询 5 次检测页面提示文字
    for _ in range(5):
        try:
            page_text = sb.execute_script("return document.body.innerText || document.body.textContent;").lower()
            
            if "przedłużyłeś ważność swojego serwera" in page_text:
                status = "success"
                break
            elif "nie możesz przedłużyć serwera" in page_text and "niedawno" in page_text:
                status = "cooldown"
                message = "冷却期内无法续期"
                break
        except:
            pass
        time.sleep(1)

    if status == "success":
        print(f"\n[+] ✅ 续期成功！")
    elif status == "cooldown":
        print(f"\n[!] ⏳ 处于冷却期，无法续期")
    else:
        print(f"\n[!] ⚠️ 未检测到明确的成功或冷却提示")

    # 页面可能会自动刷新，等待一下并手动刷新获取最新时间
    print("\n[续期] 刷新页面以获取最新时间...")
    time.sleep(3)
    try:
        sb.refresh()
        time.sleep(2)
    except:
        time.sleep(1)
    
    # 获取续期后的时间
    time_after = get_expiry_time_from_page(sb)
    
    screenshot_path = f"{screenshot_prefix}_{status}.png" if screenshot_prefix else f"{status}.png"
    sb.save_screenshot(screenshot_path)
    
    return {"status": status, "time_before": time_before, "time_after": time_after, "screenshot": screenshot_path, "message": message}


def main():
    """主函数"""
    # 从环境变量读取配置
    server_url = os.environ.get("ICEHOST_SERVER_URL", "https://dash.icehost.pl/server/e863a61e")
    cookie_str = os.environ.get("ICEHOST_COOKIE", "").strip()
    
    if not server_url:
        print("❌ 错误: ICEHOST_SERVER_URL 环境变量未设置")
        sync_tg_notify("❌ IceHost 续期脚本\n\nICEHOST_SERVER_URL 环境变量未设置")
        return
    
    if not cookie_str:
        print("❌ 错误: ICEHOST_COOKIE 环境变量未设置")
        sync_tg_notify("❌ IceHost 续期脚本\n\nICEHOST_COOKIE 环境变量未设置")
        return
    
    # 解析 Cookie
    cookies_dict = parse_cookie(cookie_str)
    if not cookies_dict:
        print("❌ 错误: Cookie 格式错误或为空")
        sync_tg_notify("❌ IceHost 续期脚本\n\nCookie 格式错误或为空")
        return
    
    print("=" * 60)
    print("🎮 IceHost 自动续期脚本")
    print(f"服务器: {server_url}")
    print("=" * 60)
    
    result = {
        "status": "unknown",
        "message": "",
        "server_url": server_url,
        "time_before": None,
        "time_after": None,
        "screenshot": None
    }
    
    try:
        with SB(
            uc=True,
            test=True,
            locale="zh-CN",
            headless=False,
            window_size="1920,1080",
            chromium_arg="--disable-dev-shm-usage,--no-sandbox,--disable-gpu,--disable-software-rasterizer,--disable-background-timer-throttling,--force-device-scale-factor=0.8"
        ) as sb:
            print("\n[*] 浏览器已启动")
            
            # 步骤1：设置 Cookie
            print("\n[步骤1] 设置 Cookie...")
            try:
                sb.uc_open_with_reconnect(f"https://{DOMAIN}", reconnect_time=3)
                time.sleep(1)
                sb.delete_all_cookies()
            except:
                pass
            
            sb.uc_open_with_reconnect(f"https://{DOMAIN}", reconnect_time=3)
            time.sleep(2)
            
            for cookie_name, cookie_value in cookies_dict.items():
                try:
                    sb.add_cookie({
                        "name": cookie_name,
                        "value": cookie_value,
                        "domain": DOMAIN,
                        "path": "/"
                    })
                    print(f"[+] 设置 Cookie: {cookie_name}")
                except Exception as e:
                    print(f"[!] 设置 cookie {cookie_name} 失败: {e}")
            
            print(f"[+] 共设置 {len(cookies_dict)} 个 Cookie")
            
            # 步骤2：访问服务器页面
            print("\n[步骤2] 访问服务器页面...")
            sb.uc_open_with_reconnect(server_url, reconnect_time=5)
            time.sleep(4)
            
            # 检查是否需要处理 CF 验证
            if check_turnstile_exists(sb):
                print("\n[步骤3] 检测到 Cloudflare 验证，开始处理...")
                if not handle_cf_challenge(sb, "login"):
                    print("[!] CF 验证失败，脚本结束")
                    result["status"] = "cf_error"
                    result["message"] = "CF 验证失败"
                    sb.save_screenshot("cf_verify_failed.png")
                    return
                time.sleep(2)
            else:
                print("\n[步骤3] 无需 CF 验证，继续...")
            
            # 步骤4：检查登陆状态
            print("\n[步骤4] 检查登陆状态...")
            if not is_logged_in(sb):
                print("[!] 登陆失败")
                result["status"] = "login_failed"
                result["message"] = "Cookie 失效或登陆失败"
                sb.save_screenshot("login_failed.png")
                return
            
            print("[+] 登陆成功")
            
            # 步骤5：执行续期
            print("\n[步骤5] 执行续期...")
            renew_result = renew_server(sb, "icehost")
            
            result.update(renew_result)
    
    except Exception as e:
        import traceback
        print(f"\n[!] 异常: {repr(e)}")
        traceback.print_exc()
        result["status"] = "error"
        result["message"] = str(e)[:100]
    
    # 发送通知
    print("\n" + "=" * 60)
    print("📢 发送通知...")
    print("=" * 60)
    
    status_emoji = {
        "success": "✅",
        "cooldown": "⏳",
        "cf_error": "🚫",
        "login_failed": "❌",
        "error": "❌",
        "uncertain": "⚠️"
    }.get(result["status"], "❓")
    
    message = f"""
{status_emoji} <b>IceHost 续期报告</b>

🖥️ 服务器: <code>{server_url}</code>

"""
    
    if result["status"] == "success":
        message += f"""<b>✅ 续期成功！</b>

⏱️ 续期前: <code>{result['time_before']}</code>
⏱️ 续期后: <code>{result['time_after']}</code>
"""
    elif result["status"] == "cooldown":
        message += "<b>⏳ 冷却期内无法续期</b>\n\n"
        message += "请稍后再试。服务器在最近已经续期过。"
    elif result["status"] == "cf_error":
        message += "<b>🚫 Cloudflare 验证失败</b>\n\n"
        message += "无法通过 CF 验证，请检查网络或稍后重试。"
    elif result["status"] == "login_failed":
        message += "<b>❌ 登陆失败</b>\n\n"
        message += "Cookie 可能已过期，请重新获取。"
    elif result["status"] == "uncertain":
        message += f"""<b>⚠️ 续期结果未知</b>

⏱️ 续期前: <code>{result['time_before']}</code>
⏱️ 续期后: <code>{result['time_after']}</code>

请手动检查网站确认续期是否成功。
"""
    else:
        message += f"<b>❌ 续期失败</b>\n\n错误: {result['message']}"
    
    if result.get("screenshot") and os.path.exists(result["screenshot"]):
        sync_tg_notify_photo(result["screenshot"], message)
    else:
        sync_tg_notify(message)
    
    print("[+] 通知已发送")


if __name__ == "__main__":
    main()
