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

# Logger setup
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')
logger = logging.getLogger("CourseRegister")

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

def try_register(driver, target_url, target_id):
    logger.info(f"[🔍] Checking: {target_url}")
    try:
        driver.get(target_url)
        WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.submit"))
        ).click()

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a.end, a.wait, a.regist"))
        )

        tbody = driver.find_element(By.CSS_SELECTOR, "tbody.txtcenter")
        register_links = tbody.find_elements(By.CSS_SELECTOR, "a.regist")
        closed_links = tbody.find_elements(By.CSS_SELECTOR, "a.end")
        pending_links = tbody.find_elements(By.CSS_SELECTOR, "a.wait")

        if not register_links:
            logger.info(
                f"[{target_id}] '접수하기' not found - 접수종료 {len(closed_links)}개, 준비중 {len(pending_links)}개 - skipping"
            )
            return False

        register_link = register_links[0]
        logger.info(f"[{target_id}] Found '접수하기' → clicking")
        register_link.click()

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "button.button.action_write"))
        )
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.button.action_write"))
        ).click()

        WebDriverWait(driver, 10).until(EC.alert_is_present())
        alert = driver.switch_to.alert
        logger.info(f"[{target_id}] ⚠️ Alert text: {alert.text}")
        time.sleep(1)
        alert.accept()
        time.sleep(1)

        logger.info(f"[{target_id}] Registration completed!")
        return True
    except Exception as e:
        logger.warning(f"[{target_id}] Exception: {e}")
        return False

def keep_checking_until(target_url, target_id, interval_sec, end_time_str, user_id, user_pw):
    logger.info(f"[🔁] Starting keep-checking loop every {interval_sec} sec until {end_time_str}")
    today_str = datetime.now().strftime("%Y-%m-%d")
    end_time = datetime.strptime(f"{today_str} {end_time_str}", "%Y-%m-%d %H:%M:%S")

    driver = setup_driver()

    if not login(driver, target_url, user_id, user_pw):
        driver.quit()
        return

    while datetime.now() < end_time:
        success = try_register(driver, target_url, target_id)
        if success:
            logger.info("[🏁] Registration succeeded. Stopping loop.")
            break

        now = datetime.now()
        if now < end_time:
            remaining = (end_time - now).total_seconds()
            wait_time = min(interval_sec, remaining)
            logger.info(f"[🕒] Waiting {int(wait_time)} seconds before next try...")
            time.sleep(wait_time)
        else:
            logger.info("[🛑] End time reached. Exiting.")
            break

    driver.quit()

def main():
    parser = argparse.ArgumentParser(description="Course Registration Automation")
    parser.add_argument('--id', type=int, default=3, help="Target course ID")
    parser.add_argument('--url', type=str, required=True, help="Target course URL")
    parser.add_argument('--end_time', type=str, required=True, help="End time in HH:MM:SS format")
    parser.add_argument('--interval', type=int, default=300, help="Interval in seconds between checks")
    parser.add_argument('--user_id', type=str, required=True, help="Login user ID")
    parser.add_argument('--user_pw', type=str, required=True, help="Login password")
    args = parser.parse_args()

    keep_checking_until(args.url, args.id, args.interval, args.end_time, args.user_id, args.user_pw)

if __name__ == '__main__':
    main()

    # 예시 실행:
    # python kp.py --end_time 23:25:00 --interval 30 --url "https://course.mfac.or.kr/fmcs/3?..." --user_id yourid --user_pw yourpw
