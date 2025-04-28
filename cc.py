import argparse
import logging
import time
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import threading

# Logger setup
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')
logger = logging.getLogger("BurstRegister")

success_event = threading.Event()

def setup_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

def login(driver, redirect_url, user_id, user_pw):
    login_url = "https://www.mfac.or.kr/account/login.jsp"
    driver.get(login_url)
    time.sleep(3)
    try:
        id_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "id"))
        )
        pw_input = driver.find_element(By.ID, "pw")
        login_button = driver.find_element(By.ID, "btnLogin")

        id_input.send_keys(user_id)
        pw_input.send_keys(user_pw)
        driver.execute_script("arguments[0].click();", login_button)
        time.sleep(3)

        logger.info("[🔓] Logged in - navigating to target URL")
        driver.get(redirect_url)
        time.sleep(3)
        return True
    except Exception as e:
        logger.warning(f"[❌] Login failed: {e}")
        return False

def try_register(driver, target_url, target_id, trigger_time, final_click_time, class_name):
    try:
        now = datetime.now()
        if now < trigger_time:
            time_to_wait = (trigger_time - now).total_seconds()
            logger.info(f"[{target_id}] ⏱ Waiting {time_to_wait:.2f}s for FLOW start...")
            time.sleep(time_to_wait)

        if success_event.is_set():
            logger.info(f"[{target_id}] Skipped due to prior success.")
            return

        logger.info(f"[{target_id}] Launching FLOW")
        driver.get(target_url)
        WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.submit"))
        ).click()

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a.end, a.wait, a.regist"))
        )

        rows = driver.find_elements(By.CSS_SELECTOR, "tbody.txtcenter tr")
        found = False
        for row in rows:
            try:
                title_cell = row.find_element(By.CSS_SELECTOR, 'td[data-title="강좌명"]')
                title = title_cell.text.strip()
                if class_name and class_name not in title:
                    continue

                register_links = row.find_elements(By.CSS_SELECTOR, "a.regist")
                if not register_links:
                    continue

                logger.info(f"[{target_id}] Found '접수하기' for [{title}] → clicking")
                register_links[0].click()

                apply_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.button.action_write"))
                )
                apply_button.click()

                now = datetime.now()
                if now < final_click_time:
                    delay = (final_click_time - now).total_seconds()
                    logger.info(f"[{target_id}] ⏳ Waiting {delay:.2f}s to accept popup at exact moment")
                    time.sleep(delay)

                WebDriverWait(driver, 10).until(EC.alert_is_present())
                alert = driver.switch_to.alert
                logger.info(f"[{target_id}] ⚠️ Alert: {alert.text}")
                alert.accept()

                logger.info(f"[{target_id}] ✅ Registration completed!")
                success_event.set()
                found = True
                break
            except Exception as inner:
                logger.warning(f"[{target_id}] Error processing row: {inner}")

        if not found:
            logger.info(f"[{target_id}] No matching class found or no '접수하기' link - skipping")

    except Exception as e:
        logger.warning(f"[{target_id}] Exception: {e}")
    finally:
        driver.quit()

def launch_burst(target_url, target_id, target_time_str, rate, user_id, user_pw, class_name):
    today = datetime.now().strftime("%Y-%m-%d")
    target_time = datetime.strptime(f"{today} {target_time_str}", "%Y-%m-%d %H:%M:%S")
    login_time = target_time - timedelta(seconds=45)
    tab_start_time = target_time - timedelta(seconds=2)
    tab_end_time = target_time + timedelta(seconds=1)

    logger.info(f"🕒 Waiting for login at: {login_time.strftime('%H:%M:%S')}")
    while datetime.now() < login_time:
        time.sleep(0.1)

    main_driver = setup_driver()
    if not login(main_driver, target_url, user_id, user_pw):
        main_driver.quit()
        return

    logger.info("⏱️ Login complete. Launching tabs...")
    interval = (tab_end_time - tab_start_time).total_seconds() / rate
    threads = []
    for i in range(rate):
        trigger_time = tab_start_time + timedelta(seconds=i * interval)
        t_driver = setup_driver()
        t = threading.Thread(
            target=try_register,
            args=(t_driver, target_url, f"Tab-{i+1}", trigger_time, target_time, class_name)
        )
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    logger.info("🎯 Burst registration attempt completed.")
    main_driver.quit()

def main():
    parser = argparse.ArgumentParser(description="Burst Course Registration")
    parser.add_argument('--id', type=int, default=3, help="Target course ID")
    parser.add_argument('--url', type=str, required=True, help="Target course URL")
    parser.add_argument('--time', type=str, required=True, help="Target registration time in HH:MM:SS format")
    parser.add_argument('--rate', type=int, default=5, help="Number of tabs to launch")
    parser.add_argument('--user_id', type=str, required=True, help="Login user ID")
    parser.add_argument('--user_pw', type=str, required=True, help="Login password")
    parser.add_argument('--class_name', type=str, help="Optional class name to filter")
    args = parser.parse_args()

    launch_burst(args.url, args.id, args.time, args.rate, args.user_id, args.user_pw, args.class_name)

if __name__ == '__main__':
    main()

    # 예시 실행:
    # python cc.py --id 7 --rate 5 --time 00:00:00 --url "..." --user_id yourid --user_pw yourpw --class_name 효자수영

