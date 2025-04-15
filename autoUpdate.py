import os
import json
import glob
import re
import time
import shutil
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# Установи здесь нужную версию Factorio
TARGET_VERSION = "1.1"

TARGET_URL = "https://re146.dev/factorio/mods/en"

# Абсолютный путь к текущему скрипту
script_dir = os.path.dirname(os.path.abspath(__file__))

# Папка выше (родительская от scripts/)
base_dir = os.path.abspath(os.path.join(script_dir, ".."))

# Путь к mod-list.json
modlist_path = os.path.join(base_dir, "mod-list.json")

# Папка для загрузки
download_dir = base_dir



def wait_for_download_start(mod_name, timeout=5):
    """Ждёт, пока появится .crdownload файл, связанный со скачиванием"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        files = glob.glob(os.path.join(download_dir, '*.crdownload'))
        if files:
            return True
        time.sleep(0.5)
    print(f"[!] Скачивание не началось для мода: {mod_name}")
    return False




# Загрузка списка модов
with open(modlist_path, 'r') as f:
    mod_data = json.load(f)

mods = [mod["name"] for mod in mod_data["mods"] if mod["name"] != "base"]

# Настройка Chrome для автоматической загрузки
chrome_options = Options()
chrome_options.add_experimental_option("prefs", {
    "download.default_directory": download_dir,
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
    "safebrowsing.enabled": True
})
chrome_options.add_argument("--headless")  # Убери если хочешь видеть браузер

driver = webdriver.Chrome(options=chrome_options)
wait = WebDriverWait(driver, 8)

errors = []

for mod_name in mods:
    try:
        url = f"{TARGET_URL}#https://mods.factorio.com/mod/{mod_name}"
        driver.get(url)
        driver.refresh()

        # Ждём пока обновится контент
        wait.until(EC.presence_of_element_located((By.ID, "mod-version")))

        wait.until(lambda d: len(d.find_element(By.ID, "mod-version").find_elements(By.TAG_NAME, "option")) > 1)
        time.sleep(0.5)
        
        select_elem = driver.find_element(By.ID, "mod-version")
        options = select_elem.find_elements(By.TAG_NAME, "option")

        matched_option = None
        for option in options:
            text = option.text
            if f"for {TARGET_VERSION}" in text or f"/{TARGET_VERSION}" in text:
                matched_option = option
                break

        if matched_option:
            matched_option.click()
            download_btn = wait.until(EC.element_to_be_clickable((By.ID, "download-button")))
            driver.execute_script("arguments[0].click();", download_btn)
            if wait_for_download_start(mod_name):
                print(f"[+] Загрузка мода {mod_name} запущена.")
            else:
                errors.append(mod_name)
        else:
            print(f"[!] Не найдена версия {TARGET_VERSION} для мода {mod_name}")
            print(url)
            errors.append(mod_name)

    except Exception as e:
        print(f"[!] Ошибка при обработке мода {mod_name}: {e}")
        errors.append(mod_name)


# Ожидание завершения загрузок
def downloads_done():
    for file in os.listdir(download_dir):
        if file.endswith(".crdownload"):  # Chrome временный файл
            return False
    return True

print("⏳ Ожидание завершения загрузок...")
while not downloads_done():
    time.sleep(1)

driver.quit()
print("✅ Все загрузки завершены.")

if errors:
    print("\n⚠️ Проблемы возникли с модами:")
    for err in errors:
        print(f" - {err}")
