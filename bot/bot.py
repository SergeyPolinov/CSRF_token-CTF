from flask import Flask, request
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import os
from urllib.parse import urlparse
import socket

app = Flask(__name__)

APP_URL = os.environ.get('APP_URL', 'http://localhost:5000')
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

def is_private_ip(ip):
    parts = ip.split('.')
    if len(parts) != 4:
        return False
    
    try:
        first = int(parts[0])
        second = int(parts[1])
        # 10.0.0.0-10.255.255.255
        if first == 10:
            return True
        # 100.64.0.0-100.127.255.255
        if first == 100 and 64 <= second <= 127:
            return True
        # 172.16.0.0-172.31.255.255
        if first == 172 and 16 <= second <= 31:
            return True
        # 192.168.0.0-192.168.255.255
        if first == 192 and second == 168:
            return True
        return False

    except ValueError:
        return False

def is_safe_url(url):
    try:
        parsed_url = urlparse(url)
        host = parsed_url.hostname
        
        if not host:
            print(f"SSRF Protection: No hostname in URL: {url}")
            return False, "Invalid URL - no hostname"
        
        print(f"SSRF Protection: Checking host: {host}")

        try:
            ip = socket.gethostbyname(host)
            print(f"SSRF Protection: Resolved {host} to {ip}")
        except Exception as e:
            print(f"SSRF Protection: Cannot resolve host {host}: {str(e)}")
            return False, f"Cannot resolve host: {host}"

        if is_private_ip(ip):
            print(f"SSRF Protection: IP {ip} is private - BLOCKED")
            return False, "Private IP addresses are not allowed"

        print(f"SSRF Protection: IP {ip} is public - ALLOWED")
        return True, "Public IP address"
        
    except Exception as e:
        print(f"SSRF Protection: Error checking URL {url}: {str(e)}")
        return False, f"Error checking URL: {str(e)}"

def check_page_for_localhost_forms(driver):
    """Проверяет страницу на наличие форм с localhost в action"""
    try:
        forms = driver.find_elements(By.TAG_NAME, 'form')
        for form in forms:
            action = form.get_attribute('action')
            if action:
                print(f"Bot: Found form with action: {action}")
                action_lower = action.lower()

                localhost_patterns = [
                    'localhost',
                    '127.0.0.1',
                    'localhost:',
                    '127.0.0.1:',
                    '//localhost',
                    '//127.0.0.1'
                ]
                
                for pattern in localhost_patterns:
                    if pattern in action_lower:
                        error_msg = f"Security violation: Form action contains forbidden host (localhost/127.0.0.1): {action}, must be app"
                        print(f"Bot: BLOCKED - {error_msg}")
                        return False, error_msg
                        
        print("Bot: No localhost forms found - page is safe")
        return True, "No localhost forms found"
    except Exception as e:
        print(f"Bot: Error checking forms: {str(e)}")
        return True, "Could not check forms"

def visit_url(url):
    admin_username = os.environ.get('ADMIN_USERNAME')
    admin_password = os.environ.get('ADMIN_PASSWORD')
    
    if not admin_username or not admin_password:
        print("Bot: ADMIN_USERNAME and ADMIN_PASSWORD environment variables must be set")
        return "Error: Admin credentials not configured"
    
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--ignore-ssl-errors')
    options.add_argument('--ignore-certificate-errors-spki-list')
    options.add_argument('--disable-web-security')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--remote-debugging-port=9222')

    driver = None
    try:
        driver = webdriver.Chrome(options=options)
        print("Chrome driver initialized successfully")
    except Exception as e:
        print(f"Error creating driver: {str(e)}")
        try:
            from selenium.webdriver.chrome.service import Service
            service = Service('/usr/local/bin/chromedriver')
            driver = webdriver.Chrome(service=service, options=options)
            print("Chrome driver initialized with service")
        except Exception as e2:
            print(f"Error with service: {str(e2)}")
            return "Error: Could not initialize browser"
    
    try:
        login_url = f'{APP_URL}/login'
        print(f"Bot: Logging in as admin to {login_url}...")
        driver.get(login_url)

        print(f"Bot: Current page title: {driver.title}")
        print(f"Bot: Current URL: {driver.current_url}")
        
        username_field = driver.find_element(By.NAME, 'username')
        password_field = driver.find_element(By.NAME, 'password')
        submit_button = driver.find_element(By.CSS_SELECTOR, 'input[type="submit"]')
        
        username_field.send_keys(admin_username)
        password_field.send_keys(admin_password)
        submit_button.click()
        
        print("Bot: Login form submitted, waiting...")
        time.sleep(1)

        print(f"Bot: After login - Current URL: {driver.current_url}")
        print(f"Bot: After login - Page title: {driver.title}")
        
        if 'localhost:8000' in url:
            url = url.replace('localhost:8000', 'evil:8000')
            print(f"Bot: Replaced localhost:8000 with evil:8000 for Docker network compatibility: {url}")
        
        if url.startswith('https://'):
            url = url.replace('https://', 'http://')
            print(f"Bot: Converted HTTPS to HTTP: {url}")
        
        print(f"Bot: Visiting target URL: {url}")
        
        driver.execute_cdp_cmd('Emulation.setScriptExecutionDisabled', {'value': True})
        print("Bot: JavaScript execution disabled for security check")
        
        driver.get(url)

        print("Bot: Waiting for page to load (JS disabled)...")
        time.sleep(0.3)

        print("Bot: Checking page for localhost forms...")
        is_safe, reason = check_page_for_localhost_forms(driver)
        
        if not is_safe:
            print(f"Bot: Security check FAILED: {reason}")
            driver.quit()
            print("Bot: Driver closed due to security violation")
            return reason
        
        print("Bot: Page passed security check")
        
        driver.execute_cdp_cmd('Emulation.setScriptExecutionDisabled', {'value': False})
        print("Bot: JavaScript execution enabled")
        
        driver.refresh()
        
        print("Bot: Waiting for JavaScript execution and form submission...")
        time.sleep(2)
        
        print(f"Bot: Target page URL: {driver.current_url}")
        print(f"Bot: Target page title: {driver.title}")

        try:
            page_source = driver.page_source
            print(f"Bot: Page source length: {len(page_source)}")
            if "form" in page_source.lower() and ("csrf" in page_source.lower() or "evil" in page_source.lower()):
                print("Bot: CSRF payload detected on page")
        except:
            print("Bot: Could not get page source")
        
        print("Bot: URL visited successfully")
        
        return "Success"
        
    except Exception as e:
        error_msg = f"Error visiting URL {url}: {str(e)}"
        print(f"Bot: {error_msg}")
        print(f"Bot: Current URL at error: {driver.current_url if driver else 'N/A'}")
        return error_msg
    finally:
        if driver:
            driver.quit()
            print("Bot: Driver closed")

@app.route('/visit', methods=['POST'])
def visit():
    data = request.json
    url = data.get('url')
    if not url:
        print("Bot API: No URL provided")
        return 'No URL', 400
    
    print(f"Bot API: Received request to visit: {url}")

    is_safe, reason = is_safe_url(url)
    if not is_safe:
        print(f"Bot API: BLOCKED - {reason}")
        return f'SSRF Protection: {reason}', 403
    
    print(f"Bot API: URL passed SSRF check - {reason}")
    print(f"Bot API: Starting to visit URL: {url}")
    result = visit_url(url)
    
    if result and ("Security violation" in result or "Blocked" in result):
        print(f"Bot API: Visit blocked due to security check: {result}")
        return result, 403
    
    return 'Visited'

@app.route('/health', methods=['GET'])
def health():
    return 'Bot is running'

if __name__ == '__main__':
    print("Bot starting with SSRF protection...")
    print(f"APP_URL configured as: {APP_URL}")
    print(f"Allowed hosts: {ALLOWED_HOSTS}")
    app.run(host='0.0.0.0', port=5001)