#this script triggers on every network request
#mostly writes the traffic to disk

import mitmproxy
import json
import os
import time
import re
import psycopg2

base_path = "/home/seb/thesis/mitmdump_sample"

#setting attributes allows us retain information between requests
class Process():
    def __init__(self) -> None:
        #I think these aren't used in the end, since we couldn't
        #directly integrate this script with the crawler
        self.follower_count = 0
        self.following_count = 0
        self.post_count = 0
        #page index matters still
        self.page_index = 0
        self.user_id = 0
        self.answer_count = 0
        self.post_id = 0
        self.posts_clicked = 0
        self.created_on = ""
        self.user_db = psycopg2.connect("dbname=vent")

    #when we send request, we do nothing
    def request(self, flow):
        pass
    #when we receive responses, we write them to disk
    #we use regex to figure out the type of response we are getting
    def response(self, flow):
        start = time.time()
        if "v6/users/" in flow.request.path:
            self.get_profile(flow)
            print(self.user_id, self.follower_count, self.following_count)
        followers_re = re.compile("/api/v5/users/[\d]+/followers")
        if followers_re.search(flow.request.path):
            print("#########FOLLOWERS##########")
            self.get_follow(flow, "followers")
        followings_re = re.compile("/api/v5/users/[\d]+/followings")
        if followings_re.search(flow.request.path):
            print("#########FOLLOWINGS#########")
            self.get_follow(flow, "followings")
        post_re = re.compile("/api/v5/questions/[\d]+$")
        if post_re.search(flow.request.path):
            self.get_post(flow)
        
        answers_re = re.compile("/api/v5/questions/[\d]+/answers\?")
        if answers_re.search(flow.request.path):
            self.get_answers(flow)

        replies_re = re.compile("/api/v5/questions/[\d]+/answers/[\d]+/replies")
        if replies_re.search(flow.request.path):
            self.get_replies(flow)

        history_re = re.compile("/api/v5/feeds/post-history")
        if history_re.search(flow.request.path):
            self.get_user_history(flow)
        end = time.time()
        print(f"time: {round(end-start, 2)}")   

    #when response is a comment chain, write the content to disk
    def get_replies(self, flow):
        resp = flow.response.json()
        question_id = int(flow.request.path.split("/")[-4])
        with open(f"{base_path}/{self.user_id}/posts/{question_id}/{resp['maxReplyId']}-reply", "w") as f:
            json.dump(resp, f)
        print("replies written")
    #when response is users timeline, write all posts on the page to disk
    #it comes paginated, so we get 20 posts per request
    def get_user_history(self, flow):
        page_index = int(flow.request.path.split("?")[-1].split("&")[0].split("=")[-1])
        print(page_index)
        if not os.path.exists(f"{base_path}/{self.user_id}/posts"):
            os.mkdir(f"{base_path}/{self.user_id}/posts")
        resp = flow.response.json()
        for post in resp["questions"]:
            if not os.path.exists(f'{base_path}/{self.user_id}/posts/{post["id"]}'):
                os.mkdir(f'{base_path}/{self.user_id}/posts/{post["id"]}')
            with open(f'{base_path}/{self.user_id}/posts/{post["id"]}/post.json', "w") as f:
                json.dump(post, f)
    #when response is user's profile info
    def get_profile(self, flow):
        self.user_id = int(flow.request.path.split("/")[-1])
        resp = flow.response.json()
        self.follower_count = int(resp["beFollowedCount"])
        self.following_count = int(resp["followingCount"])
        self.post_count = int(resp["createdQuestionCount"])
        self.created_on = resp["createdOn"].replace("T", " ")
        if not os.path.exists(f"{base_path}/{self.user_id}"):
            os.mkdir(f"{base_path}/{self.user_id}")
        if not os.path.exists(f"{base_path}/{self.user_id}/posts"):
            os.mkdir(f"{base_path}/{self.user_id}/posts")
        #write user bio to disk
        with open(f"{base_path}/{self.user_id}/bio.json", "w") as f:
            json.dump(resp, f)
        #add users profile info to database
        db_cursor = self.user_db.cursor()
        db_cursor.execute(f"SELECT * from user_details where user_id = {self.user_id}")
        if db_cursor.fetchone() is None:
            db_cursor.execute(f"""INSERT INTO user_details VALUES
                            ({self.user_id}, {self.post_count}, {self.follower_count}, {self.following_count}, '{self.created_on}'), 0""")
            db_cursor.execute(f"update users set visited = 'True' where user_id = {self.user_id}")
            self.user_db.commit()
        else:
            print(f"{self.user_id} already in db")
    #this is from a time before comment counters were visible early
    #and we had to open each post for comments anyways
    #now get_user_history() does the same in bulk
    def get_post(self, flow):
        resp = flow.response.json()
        self.answer_count = int(resp["answerCount"])
        print(self.answer_count)
        self.post_id = int(flow.request.path.split("/")[-1])
        if not os.path.exists(f"{base_path}/{self.user_id}/posts/{self.post_id}"):
            os.mkdir(f"{base_path}/{self.user_id}/posts/{self.post_id}")
        with open(f"{base_path}/{self.user_id}/posts/{self.post_id}/post.json", "w") as f:
            json.dump(resp, f)
        self.posts_clicked += 1
        

    #when response is comments, write them to file
    def get_answers(self, flow):
        question_id = int(flow.request.path.split("/")[-2])
        resp = flow.response.json()
        for comment in resp["comments"]:
            with open(f"{base_path}/{self.user_id}/posts/{question_id}/{comment['id']}", "w") as f:
                json.dump(comment, f)
    #when collecting followers, communicate to the main script when we are done
    #by setting an indicator file
    def get_follow(self, flow, direction):
        self.page_index = int(flow.request.path.split("?")[-1].split("&")[0].split("=")[-1])
        if self.page_index == 0:
            if not os.path.exists(f"{base_path}/{self.user_id}/{direction}"):
                os.mkdir(f"{base_path}/{self.user_id}/{direction}")
        print(f"current page: {self.page_index}")
        if direction == "followers":
            print(f"max pages: {(self.follower_count-1)//20}")
            if (self.follower_count-1)//20 > self.page_index:
                with open("scroll_var", "w") as f:
                    f.write("True")
                print("scroll_var set True")
            else:
                with open("scroll_var", "w") as f:
                    f.write("False")
                print("scroll_var set False")
                with open("scroll_done", "w") as f:
                    f.write("True")
                print("scroll_done set True")

        elif direction == "followings":
            print(f"max pages: {(self.following_count-1)//20}")
            if (self.following_count-1)//20 > self.page_index:
                with open("scroll_var", "w") as f:
                    f.write("True")
                print("scroll_var set True")

            else:
                with open("scroll_var", "w") as f:
                    f.write("False")
                print("scroll_var set False")
                with open("scroll_done", "w") as f:
                    f.write("True")
                print("scroll_done set True")
        db_cursor = self.user_db.cursor()
        for user in flow.response.json():
            #for each user that we are connected, write their id to disk
            with open(f"{base_path}/{self.user_id}/{direction}/{user['userId']}", "w") as f:
                print(f'writing user: {user["userId"]}')
                json.dump(user, f)

            print(user["userId"], user["username"])
            #add newly discovered users to database
            db_cursor.execute(f"select * from users where user_id = {user['userId']}")
            if db_cursor.fetchone() is None:
                db_cursor.execute(f"""INSERT INTO users (user_id, user_name, completed, listening_complete, listeners_complete, is_deleted, visited) VALUES
                                    ({user["userId"]}, '{user["username"].replace("'", "''")}', False, False, False, False, False)""")
                print(f"{user['userId']} added to db")
            else:
                print(f"{user['userId']} already in database")
        self.user_db.commit()
addons = [Process()]