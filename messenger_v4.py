from flask import Flask, request, jsonify, render_template_string, session
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Change this to a long random value for a real deployment.
app.secret_key = "change-this-secret-key"

DATABASE = "messenger.db"


# =========================================================
# DATABASE
# =========================================================

def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db


def setup_database():

    db = get_db()

    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            message TEXT NOT NULL,
            time TEXT NOT NULL
        )
    """)

    db.commit()
    db.close()


setup_database()


# =========================================================
# WEB PAGE
# =========================================================

HTML = """
<!DOCTYPE html>

<html>

<head>

<title>My Messenger V4</title>

<meta name="viewport"
      content="width=device-width, initial-scale=1.0">

<style>

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    font-family: Arial;
    background: #eeeeee;
}

.header {
    background: #075e54;
    color: white;
    padding: 16px;
    font-size: 21px;
    font-weight: bold;
}

.login {
    max-width: 400px;
    margin: 60px auto;
    background: white;
    padding: 25px;
    border-radius: 15px;
}

.login h2 {
    text-align: center;
}

input {
    width: 100%;
    padding: 13px;
    margin: 7px 0;
    border: 1px solid #ccc;
    border-radius: 8px;
    font-size: 16px;
}

button {
    padding: 12px 18px;
    border: none;
    border-radius: 8px;
    background: #075e54;
    color: white;
    font-weight: bold;
    cursor: pointer;
}

.login button {
    width: 100%;
    margin-top: 10px;
}

.error {
    color: #c00;
    text-align: center;
}

.chat {
    height: 70vh;
    overflow-y: auto;
    padding: 15px;
}

.message {
    background: white;
    padding: 10px;
    margin: 8px 0;
    border-radius: 10px;
    max-width: 80%;
}

.name {
    font-weight: bold;
    color: #075e54;
}

.time {
    font-size: 11px;
    color: gray;
    margin-top: 4px;
}

.bottom {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: white;
    padding: 10px;
    display: flex;
    gap: 8px;
}

.message-input {
    margin: 0;
    flex: 1;
}

.logout {
    float: right;
    background: #444;
    padding: 7px 10px;
}

</style>

</head>


<body>

{% if not logged_in %}

<div class="login">

<h2>💬 My Messenger</h2>

<p>Login or create an account</p>

<input id="username"
       placeholder="Username">

<input id="password"
       type="password"
       placeholder="Password">

<button onclick="login()">
    LOGIN
</button>

<button onclick="register()">
    CREATE ACCOUNT
</button>

<p id="result" class="error"></p>

</div>


<script>

function login() {

    sendAuth("/login");

}


function register() {

    sendAuth("/register");

}


function sendAuth(url) {

    let username =
        document.getElementById("username").value;

    let password =
        document.getElementById("password").value;


    fetch(url, {

        method: "POST",

        headers: {
            "Content-Type": "application/json"
        },

        body: JSON.stringify({
            username: username,
            password: password
        })

    })

    .then(response => response.json())

    .then(data => {

        if (data.success) {

            location.reload();

        } else {

            document.getElementById("result").innerText =
                data.error;

        }

    });

}

</script>


{% else %}

<div class="header">

💬 My Messenger

<button class="logout"
        onclick="logout()">

Logout

</button>

<div style="font-size:12px;">
Logged in as {{ username }}
</div>

</div>


<div id="chat"
     class="chat">
</div>


<div class="bottom">

<input id="message"
       class="message-input"
       placeholder="Type a message..."
       onkeydown="checkEnter(event)">

<button onclick="sendMessage()">
SEND
</button>

</div>


<script>

function loadMessages() {

    fetch("/messages")

    .then(response => response.json())

    .then(data => {

        let chat =
            document.getElementById("chat");

        chat.innerHTML = "";


        data.forEach(message => {

            let div =
                document.createElement("div");

            div.className = "message";


            let name =
                document.createElement("div");

            name.className = "name";

            name.innerText =
                message.username;


            let text =
                document.createElement("div");

            text.innerText =
                message.message;


            let time =
                document.createElement("div");

            time.className = "time";

            time.innerText =
                message.time;


            div.appendChild(name);
            div.appendChild(text);
            div.appendChild(time);

            chat.appendChild(div);

        });


        chat.scrollTop =
            chat.scrollHeight;

    });

}


function sendMessage() {

    let box =
        document.getElementById("message");

    let text =
        box.value.trim();


    if (text === "") {
        return;
    }


    fetch("/send", {

        method: "POST",

        headers: {
            "Content-Type": "application/json"
        },

        body: JSON.stringify({
            message: text
        })

    })

    .then(() => {

        box.value = "";

        loadMessages();

    });

}


function checkEnter(event) {

    if (event.key === "Enter") {

        sendMessage();

    }

}


function logout() {

    fetch("/logout")
    .then(() => location.reload());

}


loadMessages();

setInterval(
    loadMessages,
    1000
);

</script>

{% endif %}

</body>

</html>
"""


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    logged_in = "user_id" in session

    username = session.get("username", "")

    return render_template_string(
        HTML,
        logged_in=logged_in,
        username=username
    )


# =========================================================
# REGISTER
# =========================================================

@app.route("/register", methods=["POST"])
def register():

    data = request.get_json()

    username = data.get("username", "").strip()
    password = data.get("password", "")


    if len(username) < 3:

        return jsonify({
            "success": False,
            "error": "Username must have at least 3 characters."
        })


    if len(password) < 6:

        return jsonify({
            "success": False,
            "error": "Password must have at least 6 characters."
        })


    db = get_db()


    try:

        db.execute(
            """
            INSERT INTO users
            (username, password)
            VALUES (?, ?)
            """,
            (
                username,
                generate_password_hash(password)
            )
        )

        db.commit()

    except sqlite3.IntegrityError:

        db.close()

        return jsonify({
            "success": False,
            "error": "Username already exists."
        })


    user = db.execute(
        """
        SELECT id
        FROM users
        WHERE username = ?
        """,
        (username,)
    ).fetchone()


    db.close()


    session["user_id"] = user["id"]
    session["username"] = username


    return jsonify({
        "success": True
    })


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["POST"])
def login():

    data = request.get_json()

    username = data.get("username", "").strip()
    password = data.get("password", "")


    db = get_db()


    user = db.execute(
        """
        SELECT *
        FROM users
        WHERE username = ?
        """,
        (username,)
    ).fetchone()


    db.close()


    if user is None:

        return jsonify({
            "success": False,
            "error": "Username or password is incorrect."
        })


    if not check_password_hash(
        user["password"],
        password
    ):

        return jsonify({
            "success": False,
            "error": "Username or password is incorrect."
        })


    session["user_id"] = user["id"]
    session["username"] = user["username"]


    return jsonify({
        "success": True
    })


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return jsonify({
        "success": True
    })


# =========================================================
# GET MESSAGES
# =========================================================

@app.route("/messages")
def messages():

    if "user_id" not in session:

        return jsonify([])


    db = get_db()


    rows = db.execute(
        """
        SELECT username, message, time
        FROM messages
        ORDER BY id ASC
        """
    ).fetchall()


    db.close()


    return jsonify([
        dict(row)
        for row in rows
    ])


# =========================================================
# SEND MESSAGE
# =========================================================

@app.route("/send", methods=["POST"])
def send():

    if "user_id" not in session:

        return jsonify({
            "error": "Please login."
        }), 401


    data = request.get_json()

    text = data.get(
        "message",
        ""
    ).strip()


    if not text:

        return jsonify({
            "error": "Empty message."
        })


    username = session["username"]

    time = datetime.now().strftime(
        "%H:%M"
    )


    db = get_db()


    db.execute(
        """
        INSERT INTO messages
        (username, message, time)
        VALUES (?, ?, ?)
        """,
        (
            username,
            text,
            time
        )
    )


    db.commit()
    db.close()


    return jsonify({
        "success": True
    })


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    print()
    print("======================================")
    print("       MY MESSENGER - VERSION 4")
    print("======================================")
    print()
    print("Database: messenger.db")
    print()
    print("Open on this laptop:")
    print("http://127.0.0.1:5000")
    print()
    print("For your phone:")
    print("http://YOUR-LAPTOP-IP:5000")
    print()
    print("Server running...")
    print()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )
