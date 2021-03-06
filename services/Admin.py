import pymysql
import datetime
import bleach
import json
from services.HighLow import HighLow

HIGHLOWAPP_UID = "46a3abbc-79ed-11ea-9a6a-2b0cd635fce8"

class Admin:
    def __init__(self, host, username, password, database):
        self.host = host
        self.username = username
        self.password = password
        self.database = database

    def total_users(self):
        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM users;")

        user_list = cursor.fetchall()

        conn.commit()
        conn.close()

        return {
            "total_users": len(user_list)
        }

    def get_flags(self):
        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM activity_flags WHERE open=TRUE;")

        flags = cursor.fetchall()

        conn.commit()
        conn.close()

        return {
            "flags": flags
        }

    def dismiss_flag(self, flag_id):
        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        flag_id_str = pymysql.escape_string( bleach.clean(str(flag_id)) )

        cursor.execute("UPDATE activity_flags SET open=false WHERE id={}".format(flag_id_str))

        conn.commit()
        conn.close()

        return {
            "status": "success"
        }

    def take_analytics_snapshot(self):
        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        num_users = 0

        cursor.execute("SELECT COUNT(*) AS num_users FROM users;")

        row = cursor.fetchone()

        num_users = row['num_users']

        cursor.execute("SELECT COUNT(*) AS num_oauth_users FROM (SELECT * FROM oauth_accounts GROUP BY uid) AS unique_oauth;")

        num_oauth_accounts = 0

        row = cursor.fetchone()

        num_oauth_accounts = row['num_oauth_users']

        cursor.execute("SELECT SUM(status=2) AS num_friendships FROM friends;")
        row = cursor.fetchone()
        num_friendships = row['num_friendships']

        cursor.execute("SELECT COUNT(*) AS num_activities FROM activities;")
        row = cursor.fetchone()
        num_activities = row['num_activities']

        cursor.execute("INSERT INTO analytics(num_users, num_oauth_users, num_friendships, num_highlows) VALUES({}, {}, {}, {});".format(num_users, num_oauth_accounts, num_friendships, num_activities))

        conn.commit()
        conn.close()

        return '{"status": "success"}'

    def get_analytics(self, num_days):
        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM analytics ORDER BY date DESC LIMIT {};".format(num_days))

        analytics = cursor.fetchall()

        conn.commit()
        conn.close()

        for snapshot in analytics:
            snapshot['date'] = snapshot['date'].isoformat()

        return {
            "analytics": analytics
        }

    def create_company_highlow(self, username, high, low, high_image, low_image, date):
        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM admins WHERE username='{}';".format(username))

        user = cursor.fetchone()

        conn.commit()
        conn.close()

        if user['permission_level'] < 100:
            return { 'error': 'insufficient-permissions' }
        
        highlow = HighLow(self.host, self.username, self.password, self.database)
        return json.loads( highlow.create(HIGHLOWAPP_UID, date, high=high, low=low, high_image=high_image, low_image=low_image, isPrivate=False) )