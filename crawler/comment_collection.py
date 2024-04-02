#very similar to network collection script, but contains 
#a function that drives the comment collection

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
import lxml.etree

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

#main function to collect comments
def collect_answers(driver, count, went_back=0):
    #the reason why we return multiple values is to help recovering when something unexpected happens

    #find all the comment buttons
    comments = driver.find_elements(AppiumBy.XPATH, '//android.widget.ImageView[contains(@content-desc, "Comment")]')
     
    for i in range(went_back, len(comments)):
        #if to counter drift
        if i < len(comments):
            #the number of comments is visible before before going on the post page
            #so we can skip open the post pages  when we know they have 0 comments
            answer_count = int("".join(ch for ch in comments[i].get_attribute("content-desc").split("\n")[0] if ch.isnumeric()))
        else:
            return count+i+1, 0
        
        #if the post has comments
        if answer_count > 0:
            #open post page, revealing comments that the mitm script can capture
            comments[i].click()
            print(i, len(comments))
            
            WebDriverWait(driver, 10)
            #sometimes instead of going on the comment page, it goes back to the seach page
            #which will make us scroll down to where we left off
            if page_finder(driver) == "search_2":
                return count+i+1, i+1
            #some posts are unavailable, just ok the error
            elif page_finder(driver) == "groupie":
                WebDriverWait(driver, 2).until(EC.presence_of_element_located((AppiumBy.XPATH, '//android.widget.Button[@content-desc="OK"]')))
                driver.find_element(AppiumBy.XPATH, '//android.widget.Button[@content-desc="OK"]').click()
            #when we get to the right page
            elif page_finder(driver) == "comments":
                    #see if their are any comment chains to open
                    nested_reps = driver.find_elements(AppiumBy.XPATH, '//android.view.View[starts-with(@content-desc, "Replies")]')
                    #if there are, open them
                    if len(nested_reps) > 0:
                        for j in range(len(nested_reps)):
                            nested_reps[j].click()
                            #close the comment chain
                            WebDriverWait(driver, 3).until(EC.presence_of_element_located((AppiumBy.XPATH, '//android.view.View[@content-desc="Hide Replies"]')))
                            driver.find_element(AppiumBy.XPATH, '//android.view.View[@content-desc="Hide Replies"]').click()
                            nested_reps = driver.find_elements(AppiumBy.XPATH, '//android.view.View[starts-with(@content-desc, "Replies")]')
                    #for some reason it is broken and can't scroll this page with any of the 4 scrolling gestures
                    #scrollable = driver.find_elements(AppiumBy.XPATH, '//android.view.View[@scrollable="true"]')
                    #if len(scrollable) > 0:
                    #    print(driver.execute_script('mobile: swipeGesture', {
                    #        "elementId": str(scrollable[0].id),
                    #        'direction': 'up',
                    #        'percent': 0.1,
                            #'speed': 200
                    #        }))
                    #else:
                    #    comment_scroll = False
                    print("going back")
                    WebDriverWait(driver, 3).until(EC.presence_of_element_located((AppiumBy.XPATH, '//android.widget.Button[@content-desc="Back"]')))
                    driver.find_element(AppiumBy.XPATH, '//android.widget.Button[@content-desc="Back"]').click()
            elif page_finder(driver) == "posts":
                return count+i+1, i+1
            else:
                print(page_finder(driver))
                return count+i+1, 0
            
            

            WebDriverWait(driver, 5).until(EC.presence_of_element_located((AppiumBy.XPATH, '//android.widget.ImageView[contains(@content-desc, "Comment")]')))
            comments = driver.find_elements(AppiumBy.XPATH, '//android.widget.ImageView[contains(@content-desc, "Comment")]')

    #when all comments on the current page are collected, scroll down
    #exactly one screen's length
    scrollable = driver.find_elements(AppiumBy.XPATH, '//android.view.View[@scrollable="true"]')
    driver.execute_script('mobile: scrollGesture', {
                            "elementId": str(scrollable[0].id),
                            'direction': 'down',
                            'percent': 1.0
                            }) 
    return count+len(comments), 0   

def page_finder(driver):
    page_source = ET.fromstring(driver.page_source)
    root = lxml.etree.fromstring(bytes(driver.page_source, encoding='utf-8'))
    dump_tree = driver.page_source
    
    if len(page_source.findall('.//android.view.View[@content-desc="Welcome to Vent, a \nsupportive community for \nexpressing emotions"]')) > 0:
        return "login_1"
    elif len(page_source.findall('.//android.view.View[@content-desc="Login with email"]')) > 0:
        return "login_2"
    elif len(page_source.findall('.//android.widget.EditText[@text="Write a comment..."]')) > 0:
        return "comments"
    elif len(page_source.findall("./android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View[1]/android.view.View/android.view.View/android.view.View/android.widget.Button")) > 1:
        if page_source.findall("./android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View[1]/android.view.View/android.view.View/android.view.View/android.widget.Button")[0].attrib["content-desc"] == "Feed":
            return "landing_page"
    elif len(page_source.findall('.//android.view.View[@content-desc="Private Account"]')) > 0:
        return "private_account"
    elif page_source.findall(""".//android.view.View[@content-desc="We're sorry, this member may have been deactivated, suspended, or they may have permanently deleted their account."]"""):
        return "banned"
    elif len(page_source.findall("./android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View/android.widget.ImageView")) > 0 and "content-desc" in page_source.findall("./android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View/android.widget.ImageView")[0].attrib and "Listening" in page_source.findall("./android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View/android.widget.ImageView")[0].attrib["content-desc"]:
        return "user_landing"
    #elif len(page_source.findall("./android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View")) > 2:
    #    if page_source.findall("./android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View")[2].attrib["content-desc"] == "Clear History":
    elif len(page_source.findall('.//android.view.View[@content-desc="What are you looking for?"]')) > 0:
        if page_source.findall('.//android.view.View[@content-desc="What are you looking for?"]')[0].attrib["content-desc"] == "What are you looking for?":
            return "search_1"
    elif (len(page_source.findall("./android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.view.View/android.view.View/android.view.View/android.view.View/android.widget.EditText")) > 0 and "hint" not in page_source.findall("./android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.view.View/android.view.View/android.view.View/android.view.View/android.widget.EditText")[0].attrib) or second_search_page:
        return "search_2"
    elif len(page_source.findall("./android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View")) > 0 and "content-desc" in page_source.findall("./android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View")[0].attrib and page_source.findall("./android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View")[0].attrib["content-desc"] == "Listening":
        return "listening"
    elif len(page_source.findall("./android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View")) > 0 and "content-desc" in page_source.findall("./android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View")[0].attrib and page_source.findall("./android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View")[0].attrib["content-desc"] == "Listeners":
        return "listeners"
    elif len(page_source.findall(""".//android.view.View[@content-desc="We're sorry, but this group post is not available. The group may have been removed."]""")):
        return "groupie"
    elif len(page_source.findall("./android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.view.View/android.view.View/android.view.View/android.view.View/android.widget.ImageView")) > 0 and page_source.findall("./android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.view.View/android.view.View/android.view.View/android.view.View/android.widget.ImageView")[0].attrib["content-desc"] == "Profile avatar":
        if len(root.xpath('//android.widget.ImageView[contains(@content-desc, "Comment")]')) > 0:
            return "posts"
    
    else:
        with open("page_log.xml", "w") as f:
            f.write(dump_tree)
        return "lost"    


while True:
    user_db = psycopg2.connect("dbname=vent")
    cur = user_db.cursor()
    cur.execute("select users.user_id, post_count, user_name, total_post_clicks from user_details left join users on user_details.user_id = users.user_id where post_count < 615 and completed = False and is_deleted = False order by post_count desc")
    user_id, post_count, user, total_post_clicks = cur.fetchone()
    print(user_id, flush=True)
    print(user, flush=True)
    user_start_time = time.time()

    second_search_page = False
    went_back = 0
    #until we collect (in the vicinity) of 75% of posts
    while total_post_clicks < post_count * 0.75:
        print(total_post_clicks, post_count)
        print("tick", flush=True)
        page_source = ET.fromstring(driver.page_source)
        dump_tree = driver.page_source

        current_page = page_finder(driver)
        print(current_page)
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
            except:
                if second_search_page is True:
                    cur.execute(f"update users set is_deleted = True where user_id ={user_id}")
                    cur.execute(f"update users set visited = True where user_id ={user_id}")
                    user_db.commit()
                    print(f"{user_id} {user} user deleted")
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
        elif current_page == "private_account":
            print("private account", flush=True)
            #mark as complete and go back
            driver.find_element(AppiumBy.XPATH, '//android.widget.Button[@content-desc="Back"]').click()
            cur.execute(f"update users set listening_complete = True where user_id ={user_id}")
            cur.execute(f"update users set listeners_complete = True where user_id ={user_id}")
            cur.execute(f"update users set completed = True where user_id ={user_id}")
            cur.execute(f"update users set visited = True where user_id ={user_id}")
            user_db.commit()

        elif current_page == "user_landing":
            print("on user landing page", flush=True)               
            cur.execute(f"update users set visited = True where user_id ={user_id}")
            user_db.commit()
            #get first batch of comments
            comments = driver.find_elements(AppiumBy.XPATH, '//android.widget.ImageView[contains(@content-desc, "Comment")]')
            #if we have already opened posts, then get back to the point we were at
            if total_post_clicks > 0:
                temp_post_count = 0
                while temp_post_count < total_post_clicks:
                    temp_post_count += len(driver.find_elements(AppiumBy.XPATH, '//android.widget.ImageView[contains(@content-desc, "Comment")]'))
                    WebDriverWait(driver, 5).until(EC.presence_of_element_located((AppiumBy.XPATH, '//android.view.View[@scrollable="true"]')))
                    scroll_elem = driver.find_element(AppiumBy.XPATH, '//android.view.View[@scrollable="true"]')
                    driver.execute_script('mobile: scrollGesture', {
                        "elementId": str(scroll_elem.id),
                        #'left': 0, 'top': 66, 'width': 1080, 'height': 2186,
                        'direction': 'down',
                        'percent': 1.0
                    })
                    
                    print(temp_post_count)
            #see if there are any posts on the landing page
            elif len(comments) < 1:
                #if no posts, scroll down one page
                WebDriverWait(driver, 5).until(EC.presence_of_element_located((AppiumBy.XPATH, '//android.view.View[@scrollable="true"]')))
                scroll_elem = driver.find_element(AppiumBy.XPATH, '//android.view.View[@scrollable="true"]')
                driver.execute_script('mobile: scrollGesture', {
                    "elementId": str(scroll_elem.id),
                    #'left': 0, 'top': 66, 'width': 1080, 'height': 2186,
                    'direction': 'down',
                    'percent': 1.0
                })
            else:
                total_post_clicks, went_back = collect_answers(driver, total_post_clicks, went_back)    
        elif current_page == "posts":
            print("on posts page", flush=True)
            total_post_clicks, went_back = collect_answers(driver, total_post_clicks, went_back)

        elif current_page == "lost":
            print("lost", flush=True)
            time.sleep(2)
        elif current_page == "comments":
            WebDriverWait(driver, 3).until(EC.presence_of_element_located((AppiumBy.XPATH, '//android.widget.Button[@content-desc="Back"]')))
            driver.find_element(AppiumBy.XPATH, '//android.widget.Button[@content-desc="Back"]').click()
        else:
            print("wtfishappening", flush=True)
            
        cur.execute(f"update user_details set total_post_clicks = {total_post_clicks} where user_id ={user_id}")
        user_db.commit()

    cur.execute(f"update users set completed = True where user_id ={user_id}")
    user_db.commit()

    while page_finder(driver) not in ["search_1", "landing_page"]:
                WebDriverWait(driver, 5).until(EC.presence_of_element_located((AppiumBy.XPATH, '//android.widget.Button[@content-desc="Back"]')))
                driver.find_element(AppiumBy.XPATH, '//android.widget.Button[@content-desc="Back"]').click()

