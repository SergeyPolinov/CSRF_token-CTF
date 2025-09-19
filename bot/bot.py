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

def is_safe_url(url):
    try:
        parsed_url = urlparse(url)
        host = parsed_url.hostname
        
        if not host:
            print(f"SSRF Protection: No hostname in URL: {url}")
            return False, "Invalid URL - no hostname"
        
        print(f"SSRF Protection: Checking host: {host}")

        if host in ALLOWED_HOSTS:
            print(f"SSRF Protection: Host {host} is in allowed hosts list")
            return True, "Allowed host"

        app_host = urlparse(APP_URL).hostname
        if host == app_host:
            print(f"SSRF Protection: Host {host} is app host")
            return True, "App host"

        try:
            ip = socket.gethostbyname(host)
            print(f"SSRF Protection: Resolved {host} to {ip}")
        except Exception as e:
            print(f"SSRF Protection: Cannot resolve host {host}: {str(e)}")
            return False, f"Cannot resolve host: {host}"

        if ip == '127.0.0.1' or ip.startswith('127.'):
            print(f"SSRF Protection: IP {ip} is localhost - ALLOWED")
            return True, "Localhost IP"

        print(f"SSRF Protection: IP {ip} is not allowed")
        return False, "Public IP addresses are not allowed"
        
    except Exception as e:
        print(f"SSRF Protection: Error checking URL {url}: {str(e)}")
        return False, f"Error checking URL: {str(e)}"

def visit_url(url):
    admin_username = os.environ.get('ADMIN_USERNAME')
    admin_password = os.environ.get('ADMIN_PASSWORD')
    
    if not admin_username or not admin_password:
        print("Bot: ADMIN_USERNAME and ADMIN_PASSWORD environment variables must be set")
        return
    
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
            return
    
    try:
        print(f"Bot: Logging in as admin to {APP_URL}/login...")
        driver.get(APP_URL + '/login')

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
        driver.get(url)

        print("Bot: Waiting for page to load and execute JavaScript...")
        time.sleep(1)
        
        print(f"Bot: Target page URL: {driver.current_url}")
        print(f"Bot: Target page title: {driver.title}")

        try:
            page_source = driver.page_source
            print(f"Bot: Page source length: {len(page_source)}")
            if "form" in page_source.lower() and ("csrf" in page_source.lower() or "evil" in page_source.lower()):
                print("Bot: CSRF payload detected on page")
        except:
            print("Bot: Could not get page source")
        
        print("Bot: URL visited successfully, waiting for CSRF execution...")
        time.sleep(1)
        
    except Exception as e:
        print(f"Bot: Error visiting URL {url}: {str(e)}")
        print(f"Bot: Current URL at error: {driver.current_url if 'driver' in locals() else 'N/A'}")
    finally:
        if 'driver' in locals():
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
    visit_url(url)
    return 'Visited'

@app.route('/health', methods=['GET'])
def health():
    return 'Bot is running'

if __name__ == '__main__':
    print("Bot starting with SSRF protection...")
    print(f"APP_URL configured as: {APP_URL}")
    print(f"Allowed hosts: {ALLOWED_HOSTS}")
    app.run(host='0.0.0.0', port=5001)