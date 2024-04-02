#this is a big wraparound script that boots all parts of the pipeline (except the db)
#and in case anything crashes, or the emulator slows to a crawl, it reboots the pipeline

import subprocess
import shlex
import io
import time
from appium.webdriver.appium_service import AppiumService
import re
import psycopg2


mitm_port = 9250
avd_name = "test0"
appium_port = 4723

emulator_command = shlex.split(f'emulator -avd {avd_name} -writable-system -no-snapshot-load -http-proxy localhost:{mitm_port} -memory 4000 -cores 4 -no-boot-anim')


i = 0
while True:

    print(i, flush=True)
    #boot up adb server
    adb_process = subprocess.Popen(shlex.split("adb start-server"))
    #boot up appium server and log its output
    with io.open(f"appium_status_{i}", "w") as appium_writer, io.open(f"appium_status_{i}", "r", 1) as appium_reader:
        service = AppiumService()
        service.start(node="/usr/local/bin/node",
                    npm="/usr/local/bin/npm",
                    main_script="/usr/local/lib/node_modules/appium/build/lib/main.js",
                    args=['--address', 'localhost', '-p', str(appium_port)],
                    stdout=appium_writer,
                    stderr=appium_writer)
        #once it booted up, we can let the script progree
        while service._process.poll() is None:
            text = appium_reader.read()
            print(text, flush=True)
            if "No plugins have been installed. Use the" in text:
                print("appium started", flush=True)
                break
            time.sleep(1)
    
    #boot up the emulator and log its output
    filename = "emulator.log"
    with io.open(filename, "w") as writer, io.open(filename, "r", 1) as reader:
        process = subprocess.Popen(emulator_command, stdout=writer)
        emulator_pid = process.pid
        while process.poll() is None:
            text = reader.read()
            print(text, flush=True)
            #once the boot completed, we let the script proceed
            if "Boot completed" in text:
                break
            time.sleep(1)
    #start logging the output of the mitm proxy
    with io.open(f"mitm_output_{i}", "w") as writer_mitm, io.open(f"mitm_output_{i}", "r", 1) as reader_mitm:
        #start mitmproxy
        mitm_process = subprocess.Popen(shlex.split(f"mitmdump -s mitm_script.py -p {mitm_port}"), stdout=writer_mitm)
        mitm_pid = mitm_process.pid
        swipe_hang = False
        #log the main script
        with io.open(f"script_output_{i}", "w") as writer, io.open(f"script_output_{i}", "r", 1) as reader:
            #boot up the main script, can plug any of the 3 collection scripts here
            scrape_process = subprocess.Popen(shlex.split("python3 comment_collection.py"), stdout=writer, stderr=writer)
            script_pid = scrape_process.pid
            #some counters to see different errors when the main script stops outputting anything
            empty_lines = 0
            stuck_lines = 0
            swipe_lines = 0
            while scrape_process.poll() is None:
                text = reader.read()
                mitm_text = reader_mitm.read()
                print(text, flush=True)
                if "current page:" in mitm_text:
                    current_page = [line for line in mitm_text.split("\n") if "current page:" in line]
                    current_page = int("".join(char for char in current_page[0] if char.isnumeric()))
                if "max pages:" in mitm_text:
                    max_pages = [line for line in mitm_text.split("\n") if "max pages:" in line]
                    max_pages = int("".join(char for char in max_pages[0] if char.isnumeric()))

                if text == '':
                    empty_lines += 1
                    stuck_lines += 1
                    swipe_lines += 1
                    if empty_lines >= 150:
                        break
                elif 'tick' in text or 'lost' in text:
                    stuck_lines += 1
                    if stuck_lines >= 150:
                        break
                #we have to parse the output of mitmproxy when doing follower collection
                #since sometimes the follower count has reduced since we visited the profile
                #so we have to make sure it doesn't hang endlessly trying to scroll to a nonexistent page
                #elif 'swipe' in text:
                #    swipe_lines += 1
                #    if max_pages - current_page <= 1:
                #        print("on penultimate page", flush=True)
                #        if swipe_lines >= 10:
                #            print("random false follow count", flush=True)
                #            with open("/home/seb/thesis/scroll_done", "w") as f:
                #                f.write("True")
                #            break
                #    else:
                #        swipe_lines = 0
                    
                #if the main script return output, we can reset the indicators
                else:
                    empty_lines = 0
                    stuck_lines = 0
                    swipe_lines = 0
                """
                print(f"empty line: {empty_lines}", flush=True)
                print(f"stuck lines: {stuck_lines}", flush=True)
                print(f"swipe lines: {swipe_lines}", flush=True)
                """
                time.sleep(3)



    i += 1
    #make sure that all parts of the pipeline are killed
    #so we can cleanly reboot them
    service.stop()
    subprocess.run(shlex.split(f"kill {emulator_pid}"))
    print("restarting", flush=True)
    subprocess.run(shlex.split(f"rm {filename}"))
    subprocess.run(shlex.split(f"kill {mitm_pid}"))
    subprocess.run(shlex.split(f"kill {adb_process.pid}"))
    #some time for the system to settle
    time.sleep(20)
