import os
import sys
import git
import pymysql
import hashlib
import uuid
from datetime import datetime
from flask import Flask, request, render_template, abort, g, redirect
from config import config

app = Flask(__name__, static_url_path='/static')
app.url_map.strict_slashes = False

repo = git.Repo(search_parent_directories=True)
sha = repo.head.object.hexsha
gitsha = sha[0:8]

@app.context_processor
def inject_now():
    return {"now": datetime.utcnow(), "revision": gitsha}

@app.before_request
def before_request_handler():
    g.db = pymysql.connect(
        host=config['db-server'],
        user=config['db-user'],
        password=config['db-pass'],
        database=config['db-name'],
        autocommit=True
    )

@app.route('/fill/<gid>', methods=['GET', 'POST'])
def feedback_fill(gid):
    cursor = g.db.cursor()
    query = "SELECT name FROM groups WHERE id = %s"
    cursor.execute(query, (gid))

    row = cursor.fetchone()
    if row == None:
        abort(404)

    content = {
        "gid": gid,
        "name": row[0],
    }

    if request.method == "POST":
        cursor = g.db.cursor()
        query = "INSERT INTO feedbacks (gid, feedback) VALUES (%s, %s)"
        cursor.execute(query, (gid, request.form['feedback']))

        return render_template("thanks.html", **content)

    return render_template("fill.html", **content)

@app.route('/login/<gid>/<token>', methods=['GET'])
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

@app.route('/login', methods=['GET', 'POST'])
def feedback_login():
    if request.method == "POST":
        return feedback_login_credentials(request.form['id'], request.form['token'])

    return render_template("login.html", error=None)

@app.route('/create', methods=['GET', 'POST'])
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

@app.route('/', methods=['GET'])
def feedback_index():
    return render_template("default.html")

def production():
    return app

if __name__ == '__main__':
    print("[+] listening into debug mode")
    app.run(host=config['listen'], port=config['port'], debug=config['debug'], threaded=True)

