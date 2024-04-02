from appium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.common.keys import Keys
from appium.options.common import AppiumOptions

import psycopg2
import time
import json
import xml.etree.ElementTree as ET
import re
import sys
import random
base_path = "/home/seb/thesis/mitmdump_sample"
# in case of multiple crawlers running, set these to unique values
appium_port = 4723
system_port = 8901
avd_name = "test0"
#scraper_id = 0

#specify appium options
capabilities = dict(
    platformName='Android',
    automationName='uiautomator2',
    avd=avd_name,
    language='en',
    locale='US'
)
#connect to appium server and initialize webdriver
appium_server_url = f'http://127.0.0.1:{appium_port}'
driver = webdriver.Remote(appium_server_url, options=AppiumOptions().load_capabilities(capabilities))

#open vent
driver.execute_script('mobile: activateApp', {'appId': 'com.vent'})

#needed for some scrolling gestures
deviceSize = driver.get_window_size()
screenWidth = deviceSize['width']
screenHeight = deviceSize['height']

#had some issues with it, so now its initialiazed once for every user instead
del driver

#when scrolling the follower page, mitm-proxy writes this file to indicate when last page reached
def scroll_follows(driver, screenWidth, screenHeight):
    done = "False"
    ### scroll follower and following list
    with open("/home/seb/thesis/scroll_var", "r") as f:
        to_scroll = f.read().strip()
    if to_scroll == "True":
        driver.swipe(screenWidth/2, screenHeight*7/9, screenWidth/2, screenHeight/9, 500)
        print("swipe", flush=True)
    with open("/home/seb/thesis/scroll_done", "r") as f:
        done = f.read().strip()
    if done == "True":
        with open("/home/seb/thesis/scroll_done", "w") as f:
            f.write("False")
    return done

#function to disambiguate pages, later actions are performed accordingly
def page_finder(driver):
    page_source = ET.fromstring(driver.page_source)
    dump_tree = driver.page_source
    if len(page_source.findall('.//android.widget.Button[@resource-id="android:id/aerr_close"]')) > 0:
        return "crashed"
    elif len(page_source.findall('.//android.view.View[@content-desc="Your session has expired. Please try logging in again"]')) > 0:
        return "new login"
    elif len(page_source.findall('.//android.view.View[@content-desc="Welcome to Vent, a \nsupportive community for \nexpressing emotions"]')) > 0:
        return "login_1"
    elif len(page_source.findall('.//android.view.View[@content-desc="Login with email"]')) > 0:
        return "login_2"
    elif len(page_source.findall('.//android.view.View[@content-desc="Are you finding Vent helpful?"]')) > 0:
        return "popup"
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
    #connect to database storing user data
    user_db = psycopg2.connect("dbname=vent")
    cur = user_db.cursor()
    cur.execute(f"select user_id, user_name, listening_complete, listeners_complete from users where listening_complete = 'False' and listeners_complete = 'False' and is_deleted = 'False' offset {random.randint(0,100)}")
    #get one user where followers and followings are incomplete
    user_id, user, listening_complete, listeners_complete = cur.fetchone()
    print(user_id, flush=True)
    print(user, flush=True)
    user_start_time = time.time()

    #workaround for funky stuff on the second search page
    second_search_page = False

    #intialize new webdriver
    driver = webdriver.Remote(appium_server_url, options=AppiumOptions().load_capabilities(capabilities))

    while not (listening_complete and listeners_complete):
        print("tick", flush=True)
        page_source = ET.fromstring(driver.page_source)
        dump_tree = driver.page_source

        #the main loop, execute something depending on the page its on
        current_page = page_finder(driver)
        if current_page == "crashed":
            print("app crashed")
            #if app crashed close popup and restart app
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((AppiumBy.XPATH, './/android.widget.Button[@resource-id="android:id/aerr_close"]')))
            driver.find_element(AppiumBy.XPATH, './/android.widget.Button[@resource-id="android:id/aerr_close"]').click()
            WebDriverWait(driver, 10)
            driver.execute_script('mobile: activateApp', {'appId': 'com.vent'})
        elif current_page == "new login":
            #click ok button
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((AppiumBy.XPATH, '//android.view.Button[@content-desc="OK"]')))
            driver.find_element(AppiumBy.XPATH, '//android.view.Button[@content-desc="OK"]').click()
        elif current_page == "login_1":
            #click login button
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
        elif current_page == "popup":
            print("popup")
            #sometimes the app throws popups with random stuff, just click yes
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((AppiumBy.XPATH, '//android.widget.Button[@content-desc="Yes"]')))
            driver.find_element(AppiumBy.XPATH, '//android.widget.Button[@content-desc="Yes"]').click()
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

        elif current_page == "search_2":
            print("on second search page", flush=True)
            #sometimes the this page would have hiccups, crashing the pipeline
            #so this try except is and inelegant workaround
            try:
                #driver.find_element(AppiumBy.XPATH, '//android.widget.ImageView[@content-desc="Search ..."]').click()
                WebDriverWait(driver, 5).until(EC.element_to_be_clickable((AppiumBy.XPATH, '//android.widget.EditText[@index="1"]')))
                elem = driver.find_element(AppiumBy.XPATH, '//android.widget.EditText[@index="1"]')
                if elem.text == "":
                    elem.send_keys(user)
                #wait until the button with the search result shows up
                WebDriverWait(driver, 5).until(EC.presence_of_element_located((AppiumBy.XPATH, f'//android.widget.Button[contains(@content-desc, "{user}\n{user}")]')))
                driver.find_element(AppiumBy.XPATH, f'//android.widget.Button[contains(@content-desc, "{user}\n{user}")]').click()
                second_search_page = False
            except:
                #if the user doesnt show up the second time we got here, then there's no hit
                if second_search_page is True:
                    cur.execute(f"update users set is_deleted = True where user_id ={user_id}")
                    user_db.commit()
                    print(f"{user_id} {user} user deleted")
                    break
                second_search_page = True
                print("set second search true", flush=True)
        #on user landing page
        elif current_page == "banned":
            print("banned", flush=True)
            #this message appeared a couple of times, so ignore user and move on
            driver.find_element(AppiumBy.XPATH, '//android.widget.Button[@content-desc="Close"]').click()
            cur.execute(f"update users set listening_complete = True where user_id ={user_id}")
            cur.execute(f"update users set listeners_complete = True where user_id ={user_id}")
            cur.execute(f"update users set completed = True where user_id ={user_id}")
            user_db.commit()
            break
        elif current_page == "private_account":
            print("private account", flush=True)
            #mark as complete and go back
            driver.find_element(AppiumBy.XPATH, '//android.widget.Button[@content-desc="Back"]').click()
            cur.execute(f"update users set listening_complete = True where user_id ={user_id}")
            cur.execute(f"update users set listeners_complete = True where user_id ={user_id}")
            cur.execute(f"update users set completed = True where user_id ={user_id}")
            user_db.commit()
            break

        elif current_page == "user_landing":
            print("on user landing page", flush=True)
            #when we arrive on a users page, click followings
            #when complete click followers
            if not listening_complete:
                driver.find_element(AppiumBy.XPATH, '//android.widget.ImageView[contains(@content-desc, "Listening")]').click()
            elif not listeners_complete:
                driver.find_element(AppiumBy.XPATH, '//android.widget.ImageView[contains(@content-desc, "Listener")]').click()                

        elif current_page == "listening":
            print("on listening page", flush=True)
            done = "False"
            starttime = time.monotonic()
            #check file every one second to see if on last page yet
            while done == "False":
                time.sleep(1 - ((time.monotonic() - starttime) % 1))
                done = scroll_follows(driver, screenWidth, screenHeight)
                #print(done)
            WebDriverWait(driver, 3).until(EC.presence_of_element_located((AppiumBy.XPATH, '//android.widget.Button[@content-desc="Back"]')))
            driver.find_element(AppiumBy.XPATH, '//android.widget.Button[@content-desc="Back"]').click()
            listening_complete = True
            cur.execute(f"update users set listening_complete = True where user_id ={user_id}")
            user_db.commit()

        elif current_page == "listeners":
            print("on listeners page", flush=True)
            done = "False"
            starttime = time.monotonic()
            #check file every one second to see if on last page yet
            while done == "False":
                time.sleep(1 - ((time.monotonic() - starttime) % 1))
                done = scroll_follows(driver, screenWidth, screenHeight)
                #print(done)
            WebDriverWait(driver, 3).until(EC.presence_of_element_located((AppiumBy.XPATH, '//android.widget.Button[@content-desc="Back"]')))
            driver.find_element(AppiumBy.XPATH, '//android.widget.Button[@content-desc="Back"]').click()
            listeners_complete = True
            cur.execute(f"update users set listeners_complete = True where user_id ={user_id}")
            user_db.commit()
        #sometimes a page would not be loaded when the script tries to find where it is
        #so wait a sec and go again
        elif current_page == "lost":
            print("lost", flush=True)
            time.sleep(1)
        else:
            #should absolutely never happen
            print("wtfishappening", flush=True)
    #when followers and followings collected, leave profile page
    while page_finder(driver) not in ["search_1", "landing_page"]:
        WebDriverWait(driver, 5).until(EC.presence_of_element_located((AppiumBy.XPATH, '//android.widget.Button[@content-desc="Back"]')))
        driver.find_element(AppiumBy.XPATH, '//android.widget.Button[@content-desc="Back"]').click()
    print(f"{user_id} completed in {round((time.time()-user_start_time)/60, 2)} minutes")
    #delete driver, will be reinitialized for the new user
    del driver
