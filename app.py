import user
from flask import Flask, render_template, request ,url_for, redirect, session
from flask_socketio import SocketIO, emit, send
from flask_cors import CORS
import json
import bcrypt
from flask.helpers import flash
from dotenv import load_dotenv
import pymongo
from pymongo import MongoClient

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)
CORS(app)
socketio.init_app(app, cors_allowed_origins="*")
users = []

client = pymongo.MongoClient("mongodb+srv://AJ_15:ANAJESSICA@cluster0.7ylpe.mongodb.net/?retryWrites=true&w=majority&ssl=true&ssl_cert_reqs=CERT_NONE")

# client = pymongo.MongoClient(os.environ.get('MONGO_URI'))

#get the database name
# db = client.get_database('coonnect_peeps')

db = client['coonnect_peeps']

#get the particular collection that contains the data
records = db.login

#assign URLs to have a particular route 
@app.route("/", methods=['post', 'get'])
def index():
    message = ''
    #if method post in index
    if "email" in session:
        return redirect(url_for("logged_in"))
    if request.method == "POST":
        user = request.form.get("fullname")
        email = request.form.get("email")
        password1 = request.form.get("password")
        password2 = request.form.get("password2")
        #if found in database showcase that it's found 
        user_found = records.find_one({"name": user})
        email_found = records.find_one({"email": email})
        if user_found:
            message = 'There already is a user by that name'
            return render_template('main.html', message=message)
        if email_found:
            message = 'This email already exists in database'
            return render_template('main.html', message=message)
        if password1 != password2:
            message = 'Passwords should match!'
            return render_template('main.html', message=message)
        else:
            #hash the password and encode it
            hashed = bcrypt.hashpw(password2.encode('utf-8'), bcrypt.gensalt())
            #assing them in a dictionary in key value pairs
            user_input = {'name': user, 'email': email, 'password': hashed}
            #insert it in the record collection
            records.insert_one(user_input)
            
            #find the new created account and its email
            user_data = records.find_one({"email": email})
            new_email = user_data['email']
            #if registered redirect to logged in as the registered user
            return render_template('index.html', email=new_email)
    return render_template('main.html')



@app.route("/login", methods=["POST", "GET"])
def login():
    message = 'LOGIN IN '
    if "email" in session:
        return redirect(url_for("logged_in"))

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        #check if email exists in database
        email_found = records.find_one({"email": email})
        if email_found:
            email_val = email_found['email']
            passwordcheck = email_found['password']
            #encode the password and check if it matches
            if bcrypt.checkpw(password.encode('utf-8'), passwordcheck):
                session["email"] = email_val
                return redirect(url_for('logged_in'))
            else:
                if "email" in session:
                    return redirect(url_for("logged_in"))
                message = 'Wrong password'
                return render_template('login.html', message=message)
        else:
            message = 'Email not found'
            return render_template('login.html', message=message)
    return render_template('login.html', message=message)

@app.route('/logged_in')
def logged_in():
    if "email" in session:
        email = session["email"]
        return render_template('index.html', email=email)
    else:
        return redirect(url_for("login"))

@app.route("/logout", methods=["POST", "GET"])
def logout():
    if "email" in session:
        session.pop("email", None)
        return render_template("signout.html")
    else:
        return render_template('main.html')

@app.route("/meeting/<uid>")
def meeting(uid):
    return render_template("meeting.html")


@socketio.on('newUser')
def newUser(msg):
    print('New user: '+msg)
    data = json.loads(msg)
    print(data["username"])
    newuser = user.User(data["username"], data["meetingID"], data["userID"])
    users.append(newuser)
    emit('newUser',msg, broadcast=True)


@socketio.on('checkUser')
def checkUser(msg):
    data = json.loads(msg)
    existing = False
    for user in users:
        print(user.username)
        if(data["username"] == user.username):
            if(data["meetingID"] == user.meetingID):
                existing = True
    if (existing):
        send('userExists', broadcast=False)
    else:
        send('userOK', broadcast=False)


@socketio.on('userDisconnected')
def onDisconnect(msg):
    i = 0
    posArray = 0
    data = json.loads(msg)
    for user in users:
        if(data["username"] == user.username):
            if(data["meetingID"] == user.meetingID):
                posArray = i
        i = i + 1
    users.pop(posArray)
    print("user "+ data["username"]+ " from meeting "+data["meetingID"]+ " disconnected")
    emit('userDisconnected',msg, broadcast=True)
    
@socketio.on('message')
def handleMessage(msg):
    print('Message: ' + msg)
    send(msg, broadcast=True)

if __name__ == '__main__':
    socketio.run(app)