import pymysql
import bleach
import Helpers
import json
import firebase_admin
from firebase_admin import messaging
import random
import threading

#Admin password
notifications_config = Helpers.read_json_from_file("config/notifications_config.json")
ADMIN_PASSWORD = notifications_config["admin_password"]

#Initialize firebase app
firebase_app = firebase_admin.initialize_app()



class Notifications:

    def __init__(self, host, username, password, database):
        self.host = host
        self.username = username
        self.password = password
        self.database = database


    def register_device(self, platform, device_id, uid):
        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        platform = pymysql.escape_string( bleach.clean(platform) )
        device_id = pymysql.escape_string( bleach.clean(device_id) )
        uid = pymysql.escape_string( bleach.clean(uid) )

        cursor.execute("SELECT * FROM devices WHERE device_id='{}' AND uid='{}' AND platform={}".format(device_id, uid, platform))

        potential_duplicate = cursor.fetchone()

        if potential_duplicate is not None:
            return json.dumps( { "device_id": device_id, "uid": uid, "platform": platform } )

        cursor.execute( "INSERT INTO devices(device_id, uid, platform) VALUES('{}', '{}', {});".format(device_id, uid, platform) )

        conn.commit()
        conn.close()

        return json.dumps( { "device_id": device_id, "uid": uid, "platform": platform } )

    def deregister_device(self, device_id, uid):
        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        device_id = pymysql.escape_string( bleach.clean(device_id) )
        uid = pymysql.escape_string( bleach.clean(uid) )

        cursor.execute("DELETE FROM devices WHERE device_id='{}' AND uid='{}';".format(device_id, uid))

        conn.commit()
        conn.close()

    def send_notification_to_user(self, title, message, uid, data=None):
        title = pymysql.escape_string( bleach.clean(title) )
        message = pymysql.escape_string( bleach.clean(message) )

        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM devices WHERE uid='{}';".format(uid))

        devices = cursor.fetchall()

        conn.commit()
        conn.close()

        device_tokens = [device["device_id"] for device in devices]

        push_notification = messaging.MulticastMessage(
            device_tokens,
            notification=messaging.Notification(title=title, body=message),
            data=data,
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    messaging.Aps(sound="default")
                )
            ),
            android=messaging.AndroidConfig(
                notification=messaging.AndroidNotification(
                    sound="default",
                    click_action="OPEN_FROM_NOTIFICATION"
                )
            )
        )

        response = messaging.send_multicast(push_notification)

    def send_notification_to_users(self, title, message, uids, setting, data=None):
        settings = ['users.notify_new_friend_req', 'users.notify_new_friend_acc', 'notify_new_feed_item', 'notify_new_like', 'notify_new_comment']
        
        title = pymysql.escape_string( bleach.clean(title) )
        message = pymysql.escape_string( bleach.clean(message) )

        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        cursor.execute("""SELECT device_id, devices.uid AS uid FROM users

LEFT OUTER JOIN devices ON devices.uid = users.uid

WHERE devices.uid IN ({}) AND {} = 1;""".format(",".join(["'{}'".format(uid) for uid in uids]), settings[setting]))

        conn.commit()
        conn.close()

        devices = cursor.fetchall()

        device_tokens = [device["device_id"] for device in devices]
        push_notification = messaging.MulticastMessage(
            device_tokens,
            notification=messaging.Notification(title=title, body=message),
            data=data,
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    messaging.Aps(sound="default")
                )
            ),
            android=messaging.AndroidConfig(
                notification=messaging.AndroidNotification(
                    sound="default",
                    click_action="OPEN_FROM_NOTIFICATION"
                )
            )
        )

        response = messaging.send_multicast(push_notification)

    def send_notification(self, title, message, device_filter=".+", platform=0, random_drop=0, admin_password=""):
        device_list = []

        platform = pymysql.escape_string( bleach.clean(platform) )

        query = "SELECT * FROM devices WHERE device_id REGEXP '{}'"

        if platform > 0:
            query += " AND platform=" + platform + ";"

        else:
            query += ";"

        if admin_password != ADMIN_PASSWORD:
            return json.dumps( { "error": "incorrect-password"} )

        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        cursor.execute(query)

        devices = cursor.fetchall()

        for i in devices:
            if random.random() > random_drop:
                device_list.append(i["device_id"])

        push_notification = firebase_admin.messaging.Message(
            notification=firebase_admin.messaging.Notification(title=title, body=message)
        )

        response = firebase_admin.messaging.send(push_notification)

        #Future - log the response?

        conn.commit()
        conn.close()