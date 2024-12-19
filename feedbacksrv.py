import os
import sys
import pymysql
import hashlib
import uuid
from datetime import datetime
from flask import Flask, request, render_template, abort, g, redirect
from config import config

class Feedbacker:
    def __init__(self):
        self.app = Flask(__name__, static_url_path='/static')
        self.app.url_map.strict_slashes = False

        self.gitsha = self.gitsharoot()
        print(f"[+] running code revision: {self.gitsha}")

    def gitsharoot(self):
        try:
            ref = ""

            with open(".git/HEAD", "r") as f:
                head = f.read()
                if not head.startswith("ref:"):
                    return None

                ref = head[5:].strip()

            with open(f".git/{ref}", "r") as f:
                sha = f.read()
                return sha[:8]

        except Exception as e:
            print(e)
            return None

    def routes(self):
        @self.app.context_processor
        def inject_now():
            return {"now": datetime.utcnow(), "revision": self.gitsha}

        @self.app.before_request
        def before_request_handler():
            g.db = pymysql.connect(
                host=config['db-server'],
                user=config['db-user'],
                password=config['db-pass'],
                database=config['db-name'],
                autocommit=True
            )

        @self.app.after_request
        def after_request_handler(response):
            g.db.close()
            return response

        @self.app.route('/fill/<gid>', methods=['GET', 'POST'])
        def feedback_fill(gid):
            cursor = g.db.cursor()
            query = "SELECT name, greeting, color FROM groups WHERE id = %s"
            cursor.execute(query, (gid))

            row = cursor.fetchone()
            if row == None:
                abort(404)

            content = {
                "gid": gid,
                "name": row[0],
                "greeting": row[1],
                "primary": row[2]
            }

            if request.method == "POST":
                cursor = g.db.cursor()
                query = "INSERT INTO feedbacks (gid, feedback) VALUES (%s, %s)"
                cursor.execute(query, (gid, request.form['feedback']))

                return render_template("thanks.html", **content)

            return render_template("fill.html", **content)

        @self.app.route('/login/<gid>/<token>', methods=['GET'])
        def feedback_login_credentials(gid, token):
            cursor = g.db.cursor()
            query = "SELECT name FROM groups WHERE id = %s AND token = %s"
            cursor.execute(query, (gid, token))

            row = cursor.fetchone()
            if row == None:
                return render_template("login.html", error="login")

            name = row[0]
            feedbacks = []

            query = "SELECT created, feedback FROM feedbacks WHERE gid = %s ORDER BY created DESC"
            cursor.execute(query, (gid))

            for row in cursor.fetchall():
                feedbacks.append({"date": row[0], "feedback": row[1]})

            content = {
                "name": name,
                "feedbacks": feedbacks,
                "id": gid,
                "token": token,
            }

            return render_template("manage.html", **content)

        @self.app.route('/login/<gid>/<token>/settings', methods=['GET', 'POST'])
        def feedback_login_credentials_settings(gid, token):
            if request.method == "POST":
                greeting = request.form['greeting']
                color = request.form['color']

                cursor = g.db.cursor()
                query = "UPDATE groups SET greeting = %s, color = %s WHERE id = %s AND token = %s"
                cursor.execute(query, (greeting, color, gid, token))

                return redirect(f"/login/{gid}/{token}")

            cursor = g.db.cursor()
            query = "SELECT name, greeting, color FROM groups WHERE id = %s AND token = %s"
            cursor.execute(query, (gid, token))

            row = cursor.fetchone()
            if row == None:
                return render_template("login.html", error="login")

            content = {
                "name": row[0],
                "id": gid,
                "token": token,
                "greeting": row[1],
                "color": row[2]
            }

            return render_template("settings.html", **content)

        @self.app.route('/login', methods=['GET', 'POST'])
        def feedback_login():
            if request.method == "POST":
                return feedback_login_credentials(request.form['id'], request.form['token'])

            return render_template("login.html", error=None)

        @self.app.route('/create', methods=['GET', 'POST'])
        def feedback_create():
            if request.method == "POST":
                name = request.form['name']
                gid = str(uuid.uuid4())

                tokenid = str(uuid.uuid4())
                token = hashlib.md5(tokenid.encode('utf-8')).hexdigest()

                cursor = g.db.cursor()
                query = "INSERT INTO groups (id, name, token) VALUES (%s, %s, %s)"
                cursor.execute(query, (gid, name, token))

                return redirect(f"/login/{gid}/{token}")

            return render_template("create.html")

        @self.app.route('/', methods=['GET'])
        def feedback_index():
            return render_template("default.html")

def gunicorn_main():
    root = Feedbacker()
    root.routes()
    return root.app

