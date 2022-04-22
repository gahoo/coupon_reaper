from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException, NoSuchElementException, ElementNotInteractableException
from selenium.webdriver.common.keys import Keys

import atexit
import time
import pickle
import os
import pdb
import argparse
import datetime

def connect_to_remote_driver(host, port):
    options = Options()
    options.add_experimental_option('w3c', True)
    
    driver = webdriver.Remote(
       command_executor='http://{host}:{port}/wd/hub'.format(host=host, port=port),
       desired_capabilities=DesiredCapabilities.CHROME,
       options=options)
    return driver

@atexit.register
def clean():
    if 'driver' in globals():
        driver.close()

def get_cookies(cookie_file):
    if os.path.exists(cookie_file):
        cookies = pickle.load(open(cookie_file, "rb"))
        for cookie in cookies:
            driver.add_cookie(cookie)
    else:
        input('Waiting for login.')
        with open(cookie_file,"wb") as f:
            pickle.dump( driver.get_cookies() ,f) 

def find_coupons(btn_class):
    return driver.find_elements(By.XPATH, args.coupon_xpath)

def close_alert():
    try:
        close_button = driver.find_element(By.XPATH, '//div[@class="close-button"]')
        print("Close Alert")
        close_button.click()
    except NoSuchElementException:
        pass

def hide_elements(css_selectors):
    styles = map(lambda x: x + ' {display: none;}', css_selectors)
    styles = "\n".join(styles)
    print(styles)
    driver.execute_script('''
    var styles = `
    {styles}
    `
    
    var styleSheet = document.createElement("style")
    styleSheet.innerText = styles
    document.head.appendChild(styleSheet)
    '''.format(styles=styles))




parser = argparse.ArgumentParser(description='JD Coupon reaper.')
parser.add_argument('--host', type=str, default='localhost', help="Remote Driver Host.")
parser.add_argument('--port', type=str, default='4444', help="Remote Driver port.")
parser.add_argument('--url', type=str, help="Coupon URL.")
parser.add_argument('--select', type=int, nargs='+',
                            help='which coupon to click.')
parser.add_argument('--date', nargs='+', type=lambda x:datetime.datetime.strptime(x, '%Y-%m-%dT%H:%M'))
parser.add_argument('--coupon_xpath', default='//a[contains(@class,"coupon")]', help="Hide elements with xpath selectors")
parser.add_argument('--hide_elements', nargs='*', help="Hide elements with css selectors")
parser.add_argument('--cookie', default='cookies.pkl', help="Hide elements with css selectors")
parser.add_argument('--refresh', action='store_true')
parser.add_argument('--interactive', action='store_true')
parser.add_argument('--auto_close', action='store_true')


args = parser.parse_args()

driver = connect_to_remote_driver(args.host, args.port)
driver.get(args.url)
get_cookies(args.cookie)
driver.refresh()
if args.hide_elements:
    hide_elements(args.hide_elements)
coupons = find_coupons(args.coupon_xpath)
print("{cnt} coupons found".format(cnt=len(coupons)))

if args.select:
    selected = list(map(lambda x:x - 1, args.select))
else:
    selected = range(len(coupons))

when_to_reap = args.date.pop(0)

while True:
    if len(coupons) == 0:
        break
    for i in selected:
        if 'coupon_today_receive' not in coupons[i].get_attribute('class'):
            try:
                coupons[i].click()
                print("Clicked {i}".format(i=i))
            except WebDriverException:
                try:
                    coupons[i].send_keys(Keys.ENTER)
                    print("{i} is not clickable".format(i=i))
                except ElementNotInteractableException:
                    print("Not interactable, please check xpath")
            if args.auto_close:
                close_alert()
        else:
            print("{i} has been recived".format(i=i))
    time_to_go = when_to_reap - datetime.datetime.now()
    seconds_to_go = float(time_to_go.total_seconds())
    if seconds_to_go < 5:
        wait_for = 0.1
    elif seconds_to_go < 10:
        wait_for = 1
    elif seconds_to_go < 60:
        wait_for = 5
    elif seconds_to_go < 300:
        wait_for = 60
    else:
        coupons = find_coupons(args.coupon_xpath)
        wait_for = 300
    if args.interactive:
        input('Press Enter to continue.')
        continue
    print("{when}: {to_go} seconds to go, wait for another {wait_for}".format(when=when_to_reap, to_go=seconds_to_go, wait_for=wait_for))
    time.sleep(wait_for)
    if args.refresh and seconds_to_go > 15:
        driver.refresh()
        if args.hide_elements:
            hide_elements(args.hide_elements)
        coupons = find_coupons(args.coupon_xpath)
    if seconds_to_go < -60:
        if len(args.date) == 0:
            break
        else:
            when_to_reap = args.date.pop(0)
            
    
