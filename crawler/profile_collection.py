#the only difference to the network collection script is
#that we exit the main loop once we are on a users landaing page

from appium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.common.keys import Keys
import time

import json
import psycopg2
import xml.etree.ElementTree as ET
import sys
from appium.options.common import AppiumOptions
import random

base_path = "/home/seb/thesis/mitmdump_sample"


capabilities = dict(
    platformName='Android',
    automationName='uiautomator2',
    deviceName='Android',
    #appPackage='com.android.chrome',
    #appActivity='.Settings',
    language='en',
    locale='US'
)

appium_server_url = 'http://localhost:4723'
driver = webdriver.Remote(appium_server_url, options=AppiumOptions().load_capabilities(capabilities))

driver.execute_script('mobile: activateApp', {'appId': 'com.vent'})

deviceSize = driver.get_window_size()
screenWidth = deviceSize['width']
screenHeight = deviceSize['height']

def scroll_follows(driver, screenWidth, screenHeight):
    done = "False"
    ### scroll follower and following list
    with open("/home/seb/thesis/scroll_var", "r") as f:
        to_scroll = f.read().strip()
    #print(to_scroll)
    if to_scroll == "True":
        driver.swipe(screenWidth/2, screenHeight*7/9, screenWidth/2, screenHeight/9, 500)
        print("swipe", flush=True)
    with open("/home/seb/thesis/scroll_done", "r") as f:
        done = f.read().strip()
    if done == "True":
        with open("/home/seb/thesis/scroll_done", "w") as f:
            f.write("False")
    return done

def page_finder(driver):
    page_source = ET.fromstring(driver.page_source)
    dump_tree = driver.page_source
    if len(page_source.findall('.//android.view.View[@content-desc="Welcome to Vent, a \nsupportive community for \nexpressing emotions"]')) > 0:
        return "login_1"
    elif len(page_source.findall('.//android.view.View[@content-desc="Login with email"]')) > 0:
        return "login_2"
    elif len(page_source.findall("./android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View[1]/android.view.View/android.view.View/android.view.View/android.widget.Button")) > 1:
        if page_source.findall("./android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View[1]/android.view.View/android.view.View/android.view.View/android.widget.Button")[0].attrib["content-desc"] == "Feed":
            return "landing_page"
    elif len(page_source.findall('.//android.view.View[@content-desc="Private Account"]')) > 0:
        return "private_account"
    elif page_source.findall(""".//android.view.View[@content-desc="We're sorry, this member may have been deactivated, suspended, or they may have permanently deleted their account."]"""):
        return "banned"
    elif len(page_source.findall("./android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View/android.widget.ImageView")) > 0 and "content-desc" in page_source.findall("./android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View/android.widget.ImageView")[0].attrib and "Listening" in page_source.findall("./android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View/android.widget.ImageView")[0].attrib["content-desc"]:
        return "user_landing"
    elif len(page_source.findall('.//android.view.View[@content-desc="What are you looking for?"]')) > 0:
        if page_source.findall('.//android.view.View[@content-desc="What are you looking for?"]')[0].attrib["content-desc"] == "What are you looking for?":
            return "search_1"
    elif (len(page_source.findall("./android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.view.View/android.view.View/android.view.View/android.view.View/android.widget.EditText")) > 0 and "hint" not in page_source.findall("./android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.view.View/android.view.View/android.view.View/android.view.View/android.widget.EditText")[0].attrib) or second_search_page:
        return "search_2"
    elif len(page_source.findall("./android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View")) > 0 and "content-desc" in page_source.findall("./android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View")[0].attrib and page_source.findall("./android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View")[0].attrib["content-desc"] == "Listening":
        return "listening"
    elif len(page_source.findall("./android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View")) > 0 and "content-desc" in page_source.findall("./android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View")[0].attrib and page_source.findall("./android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View")[0].attrib["content-desc"] == "Listeners":
        return "listeners"
    
    elif len(page_source.findall("./android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.view.View/android.view.View/android.view.View/android.view.View/android.widget.ImageView")) > 0 and page_source.findall("./android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.view.View/android.view.View/android.view.View/android.view.View/android.widget.ImageView")[0].attrib["content-desc"] == "Profile avatar":
        if page_source.findall("./android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View/android.widget.Button/android.widget.ImageView")[0].attrib["content-desc"] == "Comment":
            return "posts"
    elif page_source.findall('.//android.widget.EditText[@hint="Write a comment..."]'):
        return "comments"
    else:
        with open("page_log.xml", "w") as f:
            f.write(dump_tree)
        return "lost"    


while True:
    user_db = psycopg2.connect("dbname=vent")
    cur = user_db.cursor()
    cur.execute(f"select user_id, user_name, listening_complete, listeners_complete, visited from users where visited = 'False' offset {random.randint(0,100)}")
    user_id, user, listening_complete, listeners_complete, visited = cur.fetchone()
    print(user_id, flush=True)
    print(user, flush=True)
    user_start_time = time.time()

    second_search_page = False
    #listening_complete = False
    #listeners_complete = False

    while not visited:
        print("tick", flush=True)
        page_source = ET.fromstring(driver.page_source)
        dump_tree = driver.page_source

        current_page = page_finder(driver)
        if current_page == "login_1":
            print("on first login", flush=True)
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((AppiumBy.XPATH, '//android.widget.Button[@content-desc="Log in"]')))
            driver.find_element(AppiumBy.XPATH, '//android.widget.Button[@content-desc="Log in"]').click()
        elif current_page == "login_2":
            print("on second login page", flush=True)
            #fill email
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((AppiumBy.XPATH, '//android.widget.EditText[@index="1"]')))
            driver.find_element(AppiumBy.XPATH, '//android.widget.EditText[@index="1"]').send_keys("nsebi97@gmail.com")
            #fill password
            #WebDriverWait(driver, 3)
            driver.find_element(AppiumBy.XPATH, '//android.widget.EditText[@index="2"]').click()
            driver.find_element(AppiumBy.XPATH, '//android.widget.EditText[@index="2"]').send_keys('patroklosz')
            #click login
            #WebDriverWait(driver, 3)
            driver.find_element(AppiumBy.XPATH, '//android.widget.Button[@content-desc="Login"]').click()
            time.sleep(3)
        elif current_page == "landing_page":
            print("on landing page", flush=True)
            #click search button
            WebDriverWait(driver, 5).until(EC.element_to_be_clickable((AppiumBy.XPATH, '//android.widget.ImageView[@content-desc="Search"]')))
            driver.find_element(AppiumBy.XPATH, '//android.widget.ImageView[@content-desc="Search"]').click()
        #on first search page
        elif current_page == "search_1":
            print("on first search page", flush=True)
            #click the text box
            WebDriverWait(driver, 5).until(EC.element_to_be_clickable((AppiumBy.XPATH, '//android.widget.ImageView[@content-desc="Search ..."]')))
            driver.find_element(AppiumBy.XPATH, '//android.widget.ImageView[@content-desc="Search ..."]').click()
        #on second search page
        #if found editable text field
        elif current_page == "search_2":
            print("on second search page", flush=True)
            #driver.find_element(AppiumBy.XPATH, '//android.widget.ImageView[@content-desc="Search ..."]').click()
            WebDriverWait(driver, 5).until(EC.element_to_be_clickable((AppiumBy.XPATH, '//android.widget.EditText[@index="1"]')))
            elem = driver.find_element(AppiumBy.XPATH, '//android.widget.EditText[@index="1"]')
            if elem.text == "":
                elem.send_keys(user)
            try:
                #wait until the button with the search result shows up
                WebDriverWait(driver, 5).until(EC.presence_of_element_located((AppiumBy.XPATH, f'//android.widget.Button[contains(@content-desc, "{user}\n{user}")]')))
                driver.find_element(AppiumBy.XPATH, f'//android.widget.Button[contains(@content-desc, "{user}\n{user}")]').click()
                second_search_page = False
                print(second_search_page)
            except:
                if second_search_page is True:
                    cur.execute(f"update users set is_deleted = True where user_id ={user_id}")
                    cur.execute(f"update users set visited = True where user_id ={user_id}")
                    user_db.commit()
                    print(f"{user_id} {user} user deleted")
                    visited = True
                second_search_page = True
                print("set second search true", flush=True)
        #on user landing page
        elif current_page == "banned":
            print("banned", flush=True)
            driver.find_element(AppiumBy.XPATH, '//android.widget.Button[@content-desc="Close"]').click()
            cur.execute(f"update users set listening_complete = True where user_id ={user_id}")
            cur.execute(f"update users set listeners_complete = True where user_id ={user_id}")
            cur.execute(f"update users set completed = True where user_id ={user_id}")
            cur.execute(f"update users set visited = True where user_id ={user_id}")
            user_db.commit()
            visited = True
        elif current_page == "private_account":
            print("private account", flush=True)
            #mark as complete and go back
            driver.find_element(AppiumBy.XPATH, '//android.widget.Button[@content-desc="Back"]').click()
            cur.execute(f"update users set listening_complete = True where user_id ={user_id}")
            cur.execute(f"update users set listeners_complete = True where user_id ={user_id}")
            cur.execute(f"update users set completed = True where user_id ={user_id}")
            cur.execute(f"update users set visited = True where user_id ={user_id}")
            user_db.commit()
            visited=True
        #we have the metadata, time to move on
        elif current_page == "user_landing":
            print("on user landing page", flush=True)               
            cur.execute(f"update users set visited = True where user_id ={user_id}")
            user_db.commit()
            visited = True
        elif current_page == "lost":
            print("lost", flush=True)
            time.sleep(1)
        else:
            print("wtfishappening", flush=True)

    while page_finder(driver) not in ["search_1", "landing_page"]:
                WebDriverWait(driver, 5).until(EC.presence_of_element_located((AppiumBy.XPATH, '//android.widget.Button[@content-desc="Back"]')))
                driver.find_element(AppiumBy.XPATH, '//android.widget.Button[@content-desc="Back"]').click()

