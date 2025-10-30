import certifi
import urllib.parse
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_pymongo import PyMongo
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import json
import os
import random
from datetime import datetime
from werkzeug.utils import secure_filename
app = Flask(__name__)
app.config['SECRET_KEY'] = 'hello'  
app.config["MONGO_URI"] = "mongodb+srv://aastha:Dolphin#14@cluster0.mik34.mongodb.net/EduConnect?retryWrites=true&w=majority"
mongo = PyMongo(app,tlsCAFile=certifi.where())

from functools import wraps
from flask import abort


def teacher_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = mongo.db.users.find_one({'email': current_user.email})
        if not user or user.get('role') != 'teacher':
            return abort(403)  # Or redirect to a "not allowed" page
        return f(*args, **kwargs)
    return decorated_function

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'



class User(UserMixin):
    def __init__(self, email):
        self.email = email
       
   
    def get_id(self):
        return self.email


@login_manager.user_loader
def load_user(email):
    user = mongo.db.users.find_one({'email': email})
    if not user:
        return None
    return User(email=user['email'])


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
       
        user = mongo.db.users.find_one({'email': email})
       
        if user and check_password_hash(user['password'], password):
            user_obj = User(email=email)
            login_user(user_obj)
            return redirect('/dashboard')
       
        flash('Invalid email or password')
        return redirect(url_for('login'))
   
    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('name')
        password = request.form.get('password')
        email = request.form.get("email")
        confirm = request.form.get("confirm-password")
        role = request.form.get("role")
       
        if mongo.db.users.find_one({'email': email}):
            flash('email already exists')
            return redirect(url_for('signup'))
       
        hashed_password = generate_password_hash(password)
        mongo.db.users.insert_one({'name': username, 'password': hashed_password, "email":email, "role":role, "bio":"", "location":"", "number":"", "picture":""})
       
        return redirect(url_for('login'))
   
    return render_template('signup.html')

import json
import random
import os

def get_daily_quote():
    quotes_path = os.path.join(app.root_path, 'static', 'quotes.json')
    with open(quotes_path, 'r') as f:
        quotes = json.load(f)
    return random.choice(quotes)  

@app.route('/dashboard', methods=["GET", "POST"])
@login_required
def dashboard():
    if request.method == "GET":
        data = mongo.db.classes.find_one({"email": current_user.email})
    x = mongo.db.users.find_one({"email": current_user.email})
    enrolled_classes = list(mongo.db.classes.find({"email": current_user.email}))
    lst = []
    lst2 = []
    for i in enrolled_classes:
        y = mongo.db.posts.find({"classname": i["classname"], "classcode": i["classcode"]})
        z = mongo.db.assignments.find({"classcode": i["classcode"]})
        for j in y:
            lst.append(j)
        for a in z:
            lst2.append(a)
    daily_quote = get_daily_quote()
    return render_template('dashboard.html', user=x, posts=lst, data=data, enrolled_classes=enrolled_classes, assign=lst2, quote=daily_quote)
 

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/message', methods=["GET", "POST"])
@login_required
def message():
    users = list(mongo.db.users.find())
    users = [u for u in users if u['email'] != current_user.email]

    recipient = request.args.get('recipient')
    selected_user = mongo.db.users.find_one({'email': recipient})
    messages = []

    if recipient:
        messages = list(mongo.db.messages.find({
            '$or': [
                {'sender': current_user.email, 'recipient': recipient},
                {'sender': recipient, 'recipient': current_user.email}
            ]
        }).sort('timestamp', 1))

    # Get full user document for current_user.email
    user = mongo.db.users.find_one({"email": current_user.email})

    return render_template('message.html', 
                           users=users, 
                           current_user=current_user,
                           selected_recipient=recipient,
                           selected_user=selected_user,
                           messages=messages,
                           user=user)

@app.route('/get_messages/<recipient>')
@login_required
def get_messages(recipient):
    # Get the timestamp of the last message received
    after_timestamp = request.args.get('after')
    
    query = {
        '$or': [
            {'sender': current_user.email, 'recipient': recipient},
            {'sender': recipient, 'recipient': current_user.email}
        ]
    }
    
    # If after_timestamp is provided, only get newer messages
    if after_timestamp:
        query['timestamp'] = {'$gt': datetime.fromisoformat(after_timestamp)}
    
    messages = list(mongo.db.messages.find(query).sort('timestamp', 1))
    
    # Convert ObjectId to string for JSON serialization
    for message in messages:
        message['_id'] = str(message['_id'])
        message['timestamp'] = message['timestamp'].isoformat()
    
    return jsonify({'messages': messages})


@app.route('/get_users')
@login_required
def get_users():
    users = list(mongo.db.users.find({}, {'email': 1, '_id': 0}))
    users = [user['email'] for user in users if user['email'] != current_user.email]
    return {'users': users}


@app.route('/send_message', methods=['POST'])
@login_required
def send_message():
    data = request.json
    recipient = data.get('recipient')
    message_content = data.get('message')
    
    if recipient and message_content:
        timestamp = datetime.utcnow()
        message = {
            'sender': current_user.email,
            'recipient': recipient,
            'content': message_content,
            'timestamp': timestamp
        }
        result = mongo.db.messages.insert_one(message)
        return jsonify({
            'success': True,
            'timestamp': timestamp.isoformat(),
            'message_id': str(result.inserted_id)
        })
    
    return jsonify({'success': False})

@app.route("/point")
@login_required
def point():
    return render_template("point.html")


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "GET":
        data = mongo.db.users.find_one({"email":current_user.email})
        print(data)
        return render_template("profile.html", data=data)
    return render_template("profile.html", data=data)

@app.route("/edit_profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    data = mongo.db.users.find_one({"email":current_user.email})
    print(data)
    return render_template("edit_profile.html", data=data)

@app.route("/save", methods=["GET", "POST"])
@login_required
def save():
    if request.method == "POST":
        bio = request.form.get('bio')
        number = request.form.get('phone')
        name = request.form.get('full-name')
        
        mongo.db.users.update_one(
            {"email": current_user.email},
            {"$set": {
                "bio": bio,
                "name": name,
                "number": number
            }}
        )
    return redirect("/edit_profile")


@app.route("/notification")
@login_required
def notification():
    return render_template("notification.html")




@app.route("/setting")
@login_required
def setting():
    return render_template("setting.html")


@app.route("/post", methods=["GET", "POST"])
@login_required
@teacher_required
def post():
    if request.method == "POST":
        post_name = request.form.get("post_name")
        like = 0
        link = request.form.get("link")
        try:
            link = urllib.parse.parse_qs(urllib.parse.urlparse(link).query)['v'][0]
        except (KeyError, IndexError):
            link = ""  # fallback if 'v' param isn't found

        description = request.form.get("description")
        classname = request.form.get("classname")
        classcode = request.form.get("classcode")

        data = {
            "postname": post_name,
            "likes": like,
            "postlink": link,
            "desc": description,
            "classname": classname,
            "classcode": classcode
        }

        mongo.db.posts.insert_one(data)
        return render_template("post.html", post_success=True, post_data=data)

    return render_template("post.html", post_success=False)




@app.route("/classes", methods=["GET", "POST"])
@login_required
def classes():
    classes = mongo.db.classes.find({"email":current_user.email})
    if request.method == "POST":
        class_name = request.form.get("classname")
        class_code = request.form.get("classcode")
        data = {"classname":class_name, "classcode":class_code, "email":current_user.email}
        mongo.db.classes.insert_one(data)
        return redirect(url_for("classes"))
    return render_template("classes.html", classes = classes)

@app.route("/remove_class", methods=["POST"])
@login_required
def remove_class():
    class_name = request.form.get("classname")
    class_code = request.form.get("classcode")

    mongo.db.classes.delete_one({
        "email": current_user.email,
        "classname": class_name,
        "classcode": class_code
    })

    return redirect(url_for("classes"))

@app.route("/grades", methods=["GET", "POST"])
@login_required
def grades():
    user_role = mongo.db.users.find_one({"email": current_user.email}).get("role", "student")

    if request.method == "POST":
        classname_filter = request.form.get("classname", "").strip()
        enrolled_classes = list(mongo.db.classes.find({
            "email": current_user.email,
            "classname": classname_filter
        })) if classname_filter else list(mongo.db.classes.find({"email": current_user.email}))
    else:
        enrolled_classes = list(mongo.db.classes.find({"email": current_user.email}))

    classes_with_grades = []
    for c in enrolled_classes:
        classes_with_grades.append({
            "classname": c.get("classname"),
            "classcode": c.get("classcode"),
            "grade": c.get("grade", "N/A")
        })

    return render_template("grades.html", classes=classes_with_grades, user_role=user_role)


from flask_login import current_user

@app.route("/assignment", methods=["GET", "POST"])
@login_required
@teacher_required
def assignment():
    assignment_s = mongo.db.assignments.find({"email": current_user.email})
    
    if request.method == "POST":
        name = request.form.get("name")
        file = request.files.get("pdf")
        classcode = request.form.get("classcode")
        max_points = request.form.get("max_points")

        if file and file.filename:
            filename = secure_filename(file.filename)
            filepath = os.path.join("static/uploads", filename)
            file.save(filepath)

        assignment_data = {
            "name": name,
            "classcode": classcode,
            "max_points": int(max_points),
            "filename": filename,
            "filepath": filepath,
            "email": current_user.email
        }
        mongo.db.assignments.insert_one(assignment_data)

    return render_template(
        "assignment.html",
        assignments=assignment_s,
        user=current_user  # <-- pass user here
    )

if __name__ == '__main__':
    app.run(debug=True)

