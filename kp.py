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

# Logger setup
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')
logger = logging.getLogger("CourseRegister")

def setup_driver():
    options = Options()
    # options.add_argument("--headless")  # 실제 창 띄우기
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(options=options)
    return driver

def login(driver, redirect_url):
    login_url = "https://www.mfac.or.kr/account/login.jsp"
    driver.get(login_url)
    time.sleep(3)  # 페이지 로딩 확인을 위한 대기
    try:
        id_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "id"))
        )
        pw_input = driver.find_element(By.ID, "pw")
        login_button = driver.find_element(By.ID, "btnLogin")

        id_input.send_keys("kpkroy")
        pw_input.send_keys("rlathf12")
        driver.execute_script("arguments[0].click();", login_button)
        time.sleep(3)  # 로그인 후 리디렉션 대기

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
        time.sleep(3)
        search_button = driver.find_element(By.CSS_SELECTOR, "button.submit")
        search_button.click()

        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a.end, a.wait, a.regist"))
            )
        except TimeoutException:
            logger.info(f"[{target_id}] '접수하기' not found in time - skipping")
            return

        tbody = driver.find_element(By.CSS_SELECTOR, "tbody.txtcenter")
        register_links = tbody.find_elements(By.CSS_SELECTOR, "a.regist")
        closed_links = tbody.find_elements(By.CSS_SELECTOR, "a.end")
        pending_links = tbody.find_elements(By.CSS_SELECTOR, "a.wait")

        if not register_links:
            logger.info(
                f"[{target_id}] '접수하기' not found - 접수종료 {len(closed_links)}개, 준비중 {len(pending_links)}개 - skipping"
            )
            return

        register_link = register_links[0]
        logger.info(f"[{target_id}] Found '접수하기' → clicking")
        register_link.click()

        apply_button = WebDriverWait(driver, 2).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.button.action_write"))
        )
        apply_button.click()
        logger.info(f"[{target_id}] Registration completed!")
        return True
    except Exception as e:
        logger.warning(f"[{target_id}] Exception: {e}")
        return False

def keep_checking_until(target_url, target_id, interval_sec, end_time_str):
    logger.info(f"[🔁] Starting keep-checking loop every {interval_sec} sec until {end_time_str}")
    today_str = datetime.now().strftime("%Y-%m-%d")
    end_time = datetime.strptime(f"{today_str} {end_time_str}", "%Y-%m-%d %H:%M:%S")

    driver = setup_driver()

    if not login(driver, target_url):
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
    args = parser.parse_args()

    keep_checking_until(args.url, args.id, args.interval, args.end_time)

if __name__ == '__main__':
    main()

    # python kp.py --end_time 23:25:00 --interval 30 --url "https://course.mfac.or.kr/fmcs/3?page=1&lecture_type=R&center=MAPOARTCENTER&event=1000000000&class=1000020000&subject=&target=&lerturer_name="