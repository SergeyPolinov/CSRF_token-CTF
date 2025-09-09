from flask import Flask, request
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import time

app = Flask(__name__)

APP_URL = 'http://app:5000'

def visit_url(url):
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
    
    # Простая инициализация драйвера
    try:
        driver = webdriver.Chrome(options=options)
    except Exception as e:
        print(f"Error creating driver: {str(e)}")
        try:
            from selenium.webdriver.chrome.service import Service
            service = Service('/usr/local/bin/chromedriver')
            driver = webdriver.Chrome(service=service, options=options)
        except Exception as e2:
            print(f"Error with service: {str(e2)}")
            return
    
    try:
        print("Logging in as admin...")
        driver.get(APP_URL + '/login')
        driver.find_element(By.NAME, 'username').send_keys('admin')
        driver.find_element(By.NAME, 'password').send_keys('adminpassword')
        driver.find_element(By.CSS_SELECTOR, 'input[type="submit"]').click()
        
        print("Login completed, waiting...")
        time.sleep(1)

        if url.startswith('https://evil:') or url.startswith('https://app:'):
            url = url.replace('https://', 'http://')
            print(f"Converted HTTPS to HTTP: {url}")
        
        print(f"Visiting URL: {url}")
        driver.get(url)
        time.sleep(3)
        print("URL visited successfully")
        
    except Exception as e:
        print(f"Error visiting URL {url}: {str(e)}")
        if 'SSL' in str(e) or 'ERR_SSL_PROTOCOL_ERROR' in str(e):
            try:
                http_url = url.replace('https://', 'http://')
                if http_url != url:
                    print(f"Retrying with HTTP: {http_url}")
                    driver.get(http_url)
                    time.sleep(3)
                    print("HTTP retry successful")
            except Exception as retry_e:
                print(f"HTTP retry also failed: {str(retry_e)}")
    finally:
        driver.quit()
        print("Driver closed")

@app.route('/visit', methods=['POST'])
def visit():
    data = request.json
    url = data.get('url')
    if url:
        print(f"Received request to visit: {url}")
        visit_url(url)
        return 'Visited'
    return 'No URL', 400

if __name__ == '__main__':
    print("Bot starting...")
    app.run(host='0.0.0.0', port=5001)