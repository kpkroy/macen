import argparse
import logging
import time
from datetime import datetime, timedelta
from multiprocessing import Process, Event, Manager
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
    # options.add_argument("--headless")  # 실제 브라우저 보이게 하기
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(options=options)
    return driver

def login(driver, redirect_url):
    login_url = "https://www.mfac.or.kr/account/login.jsp"
    driver.get(login_url)
    time.sleep(3)  # 페이지 로딩 확인 대기
    try:
        id_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "id"))
        )
        pw_input = driver.find_element(By.ID, "pw")
        login_button = driver.find_element(By.ID, "btnLogin")

        id_input.send_keys("kpkroy")
        pw_input.send_keys("rlathf12")
        driver.execute_script("arguments[0].click();", login_button)
        time.sleep(3)

        logger.info("[🔓] Logged in - navigating to target URL")
        driver.get(redirect_url)
        time.sleep(3)
        return True
    except Exception as e:
        logger.warning(f"[❌] Login failed: {e}")
        return False

def try_register(target_url, target_id, success_flag):
    driver = setup_driver()
    logger.info(f"Tab started: {target_url}")
    try:
        if not login(driver, target_url):
            return

        search_button = driver.find_element(By.CSS_SELECTOR, "button.submit")
        search_button.click()

        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a.end, a.wait, a.regist"))
            )
        except TimeoutException:
            logger.info(f"[{target_id}] '접수하기' not found in time - stopping")
            return

        tbody = driver.find_element(By.CSS_SELECTOR, "tbody.txtcenter")
        register_links = tbody.find_elements(By.CSS_SELECTOR, "a.regist")
        closed_links = tbody.find_elements(By.CSS_SELECTOR, "a.end")
        pending_links = tbody.find_elements(By.CSS_SELECTOR, "a.wait")

        if not register_links:
            logger.info(
                f"[{target_id}] '접수하기' not found - 접수종료 {len(closed_links)}개, 준비중 {len(pending_links)}개 - stopping"
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
        success_flag.set()
    except Exception as e:
        logger.warning(f"[{target_id}] Exception: {e}")
    finally:
        driver.quit()

def wait_until(target_time_str):
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    target_time = datetime.strptime(f"{today_str} {target_time_str}", "%Y-%m-%d %H:%M:%S")
    login_time = target_time - timedelta(seconds=45)
    launch_time = target_time - timedelta(seconds=2)

    # Wait until login time
    logger.info(f"🕒 Waiting for login at: {login_time.strftime('%H:%M:%S')}")
    while datetime.now() < login_time:
        time.sleep(0.1)

    logger.info("[🔑] Time to login")
    return launch_time

def launch_tabs(start_url, target_id, rate, target_time):
    launch_time = wait_until(target_time)

    logger.info("⏱️ Login completed, waiting for final trigger...")
    next_log = datetime.now() + timedelta(seconds=5)
    while datetime.now() < launch_time:
        if datetime.now() >= next_log:
            remaining = launch_time - datetime.now()
            mins, secs = divmod(remaining.total_seconds(), 60)
            logger.info(f"⏳ Launching in {int(mins)} minutes {int(secs)} seconds")
            next_log = datetime.now() + timedelta(seconds=5)
        time.sleep(0.05)

    manager = Manager()
    success_flag = manager.Event()

    procs = []
    interval = 1 / rate
    for i in range(int(2.5 / interval)):
        if success_flag.is_set():
            logger.info("✅ Registration already completed. Stopping further attempts.")
            break
        p = Process(target=try_register, args=(start_url, target_id, success_flag))
        p.start()
        procs.append(p)
        time.sleep(interval)

    for p in procs:
        p.join()

def main():
    parser = argparse.ArgumentParser(description="Course Registration Automation")
    parser.add_argument('--id', type=int, default=3, help="Target course ID")
    parser.add_argument('--url', type=str, default="https://course.mfac.or.kr/fmcs/3?page=1&lecture_type=R&center=MAPOARTCENTER&event=1000000000&class=&subject=&target=&lerturer_name=", help="Start URL")
    parser.add_argument('--time', type=str, help="Target registration time in HH:MM:SS format")
    parser.add_argument('--rate', type=float, default=4.0, help="Number of tabs to open per second")
    args = parser.parse_args()

    if args.time:
        launch_tabs(args.url, args.id, args.rate, args.time)

if __name__ == '__main__':
    main()

    # pip install webdriver-manager

    # python cc.py --id 7 --rate 1 --time 16:10:00 --url "https://course.mfac.or.kr/fmcs/3?page=1&lecture_type=R&center=MAPOARTCENTER&event=1000000000&class=1000020000&subject=&target=&lerturer_name="

