
import datetime
import os
import urllib.request
import urllib.parse
import threading
import time
import cv2 
from flask import (
    Flask,
    render_template,
    request,
    Response,
    flash,
    redirect,
    session,
    url_for,
    abort,
    jsonify,
    send_file)

from flask_sqlalchemy import SQLAlchemy
from psycopg2 import DataError
from form import sign_up_form, LoginForm
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from flask_login import LoginManager, login_user, login_required, logout_user,current_user
from io import BytesIO
import base64
from base64 import b64encode
# global varaibles for the camera recording 
capture = False
rec = False
out = None
img = None

app = Flask(__name__)
#app.jinja_env.filters['b64encode'] = b64encode
#moment = Moment(app)
app.config.from_object('config')
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 300


#Creating the camera variable ,
camera = cv2.VideoCapture('rtsp://admin:abrar123@192.168.1.64:554/Streaming/Channels/101')
#camera=cv2.VideoCapture(0)# if we want to use the device web cam 
#creating the frame dimension for the camera 
frame_width = int(camera.get(3))
frame_height = int(camera.get(4))
size = (frame_width, frame_height)

#Creating the directory for the videos 
os.makedirs('./clips', exist_ok=True)
os.makedirs('./shots', exist_ok=True)

#csrf = CSRFProtect(app)

db = SQLAlchemy(app)
from models import Camera_list, db, Users , Contact, Recording
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

migrate = Migrate(app, db,compare_type=True)
#migrate.init_app(app, db)

with app.app_context():
    db.create_all()










@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Headers',
                         'Content-Type, Authorization')
    response.headers.add('Access-Control-Allow-Headers',
                         'GET, POST, PATCH, DELETE, OPTION')
    return response







@app.route('/')
def index():
    #form= sign_up_form()
    return render_template('pages/index.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = sign_up_form(request.form)
    if request.method == 'POST':
    
        #check confirm password
        if form.password.data != form.confirm_password.data:
            flash('Password and confirm password must be the same')
            return redirect(request.url)
            #check lenth of password
        elif len(form.password.data) <8: 
             print("lenth of pass ",len(form.password.data))
             flash(message='Password must be at least 8 characters',category='danger')
             return redirect(request.url)
           #check if the email is already exists
        if (db.session.query(Users).filter_by(email=form.email.data).first()):
            flash('Email already exists')
            return redirect(request.url)
        # genrate hashed password
        hashed_password = generate_password_hash(
            form.password.data, method='sha256')

        # create a new user

        new_user = Users(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data,
            phone=form.phone.data,
            password=hashed_password,
        )


    
        # save user obj into database
        db.session.add(new_user)
        db.session.commit()
        print('You have successfully registered', 'success')
        flash(message='You have successfully registered', category='success')

        return redirect(url_for('success'))
    else:
        return render_template('pages/signup.html', form=form)


#pic 
#already email exists
#password not the same 
#invalid password
@app.route('/success')
def success ():
 return render_template('pages/success.html')





@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm(request.form)

    if request.method == 'POST' and form.validate():
        #check if email is exists form database
        user = db.session.query(Users).filter_by(email=form.email.data).first()
        #if user email is exist
        if user:
            #hash the password
            if check_password_hash(user.password, form.password.data):
                #set login = true 
                session['logged_in'] = True
                session['logged_in_user_id'] = user.id
                login_user(user)
                #flash('You have successfully logged in.', "success")
                return redirect(url_for('mainpage'))
            else:
                #check the password 
                flash(message='Invalid password', category='danger')
                return redirect(url_for('login'))
        else:
            #if user email not exist 
            flash(message='Invalid email address', category='danger')
            return redirect(url_for('login'))
    return render_template('pages/login.html', form=form)




@app.route('/mainpage', methods=['GET', 'POST'])
@login_required
def mainpage():
 

  return render_template('pages/mainpage.html')

#Getting the Camera frames
def gen_frames():
    global capture
    global img
    
    print('[DEBUG] gen_frames: start')

    while True:
        success, img = camera.read()
        
        if not success:
            break
        
        if capture:
            capture = False

            now = datetime.datetime.now()
            filename = "shot_{}.png".format(str(now).replace(":",''))
            path = os.path.sep.join(['shots', filename])

            print('[DEBUG] capture:', path)

            cv2.imwrite(path, img)

        frame = cv2.imencode('.jpg', img)[1].tobytes()
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')




@app.route('/video_feed' )
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

#Thread Class for the camera recording 
class TimerClass(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.event = threading.Event()

    def run(self):
        seconds_10 = datetime.timedelta(seconds=10)
        
        while rec and not self.event.is_set():
            now = datetime.datetime.now()
            filename = "vid_{}.avi".format(str(now).replace(":", ''))
            path = os.path.sep.join(['clips', filename])
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            out = cv2.VideoWriter(path, fourcc, 25.0, size)

            end = now + seconds_10
            
            print('[DEBUG] end:', end)
            
            while now < end and rec and not self.event.is_set():
                if img is not None:  # `img` can be `numpy.array` so it can't check `if img:`
                    out.write(img)
                time.sleep(0.03)  # 1s / 25fps = 0.04  # it needs some time for code.
                now = datetime.datetime.now()
        
            out.release()
            
    def stop (self):
        self.event.set()
        




import mimetypes


@app.route('/requests', methods=['POST', 'GET'])
def tasks():
    global capture
    global rec
    
    print('[DEBUG] click:', request.form.get('click'))
    print('[DEBUG] rec  :', request.form.get('rec'))
    
    if request.method == 'POST':
        if request.form.get('click') == 'Capture':
            capture = True

        if request.form.get('rec') == 'Start/Stop Recording':
            rec = not rec
    
            tmr = TimerClass()
            #resp=sendSMS()
            #print (resp)
    
            if rec:
                print("start")
                tmr.start()
            else:
                print("stop")
                tmr.stop()
                path='clips'
                for filename in os.listdir(path):
                    if filename.endswith('.avi'):
                        with open(os.path.join(path,filename),'rb')as file:
                            video_data = file.read()
                            mimetype, _ = mimetypes.guess_type(filename)
                            upload=Recording(filename=filename, data=video_data,mimetype=mimetype)
                            print(upload)
                            db.session.add(upload)
                            db.session.commit()

    return render_template('pages/mainpage.html')

   



def sendSMS():
        apikey='NmU2YTU4NjM2YzQxNDY0MzcxNzM2Yzc0MzM3ODczMzE='
        numbers='+447706650731'
        camera='Camera 1'
        Time=str(datetime.datetime.now())
        Recording='Recording 1'
        message='This is an alert from AstorX, a fight has occured.'+ camera + Time + Recording
        sender='AstorX'
        data =  urllib.parse.urlencode({'apikey': apikey, 'numbers': numbers,
        'message' : message, 'sender': sender})
        data = data.encode('utf-8')
        request = urllib.request.Request("https://api.txtlocal.com/send/?")
        f = urllib.request.urlopen(request, data)
        fr = f.read()
        print(fr)




@app.route('/recording' , methods=['GET' ,'POST'])
def recording():
    videos = Recording.query.all()
    
    

    return render_template('pages/recording.html', videos=videos)


@app.route('/video/<int:video_id>')
def video(video_id):
    video = Recording.query.filter_by(id=video_id).first()
    video_data = video.data
    base64_video = b64encode(video_data).decode('utf-8')
    video_uri = f'data:{video.mimetype};base64,{base64_video}'
    return render_template('recording.html', video_uri=video_uri)








  

@app.route('/myprofile' , methods=['GET' ,'POST'])
def myprofile(): 
     if 'logged_in' not in session:
        return redirect('/login')
        # Get the  data from the form
     else:
       #get current user information
       user = db.session.query(Users).filter(Users.id == session['logged_in_user_id']).first()
       first_name = user.first_name
       last_name = user.last_name
       email = user.email 
       phone = user.phone

       return render_template('pages/myprofile.html', first_name=first_name , 
      last_name=last_name , email=email , phone=phone )
    
   

   

@app.route('/contactlist' , methods=['GET' , 'POST'])
def contactlist(): 
    if 'logged_in_user_id' not in session:
         return redirect(url_for('login'))

    
    user_id = session['logged_in_user_id']
    data = Contact.query.filter_by(user_id=user_id).all()
    print(f'data: {data}')

    return render_template('pages/contactlist.html' , data = data)



@app.route('/contactlist/insert', methods = ['POST' , 'GET'])
def insert():

    if request.method == 'POST':
        if 'logged_in_user_id' not in session:
            return redirect(url_for('login'))
        else:
            user_id = session['logged_in_user_id']
            name = request.form['name']
            phone = request.form['phone']
         #for test in the termanl , to show the data if save correctly 
            my_data = Contact(name=name, phone=phone, user_id=user_id)
            
            db.session.add(my_data)
            print(my_data.name)
            db.session.commit()

            flash("Contact Inserted Successfully ")

            return redirect(url_for('contactlist'))




@app.route('/delete/<id>',methods=['GET', 'POST','DELETE'] )
def delete(id):
    # Get the contact and check if the user has permission to delete it
    try:
        id = int(id)
        data = Contact.query.get(id)
        if data.user_id != session['logged_in_user_id']:
            flash('You do not have permission to delete this contact')
            return redirect(url_for('contactlist'))
    except (ValueError, TypeError):
        flash('Invalid id')
        return redirect(url_for('contactlist'))
    except DataError:
        flash('Error deleting contact')
        return redirect(url_for('contactlist'))


    # Delete the contact
    db.session.delete(data)
    db.session.commit()
    flash('Contact deleted')
    return redirect(url_for('contactlist'))






@app.route('/logout')
@login_required
def logout():
    logout_user()
    session['logged_in'] = False
    #flash('You have successfully logged out.', "success")
    return redirect(url_for('login'))



@login_manager.user_loader
def load_user(user_id):
    if user_id is not None:
        user_id = db.session.query(Users).get(user_id)
        db.session.close()
        return user_id
    return None


@app.route('/cameramenu' , methods=['GET' , 'POST'])
def cameramenu():
     if 'logged_in_user_id' not in session:
         return redirect(url_for('login'))

    
     user_id = session['logged_in_user_id']
     data = Camera_list.query.filter_by(user_id=user_id).all()
     print(f'data: {data}')

     return render_template('pages/cameramenu.html' , data = data)





@app.route('/cameramenu/insert' , methods=['GET' , 'POST'])
def camera_insert():
    if request.method == 'POST':
           
        if 'logged_in_user_id' not in session:
            return redirect(url_for('login'))
        else:
            user_id = session['logged_in_user_id']
            camera_name =request.form['camera']
            camera_ip = request.form['IP']
            my_data = Camera_list(camera_name=camera_name, camera_ip=camera_ip, user_id=user_id)
                
            db.session.add(my_data)
            db.session.commit()

            flash("Camera Inserted Successfully ")

            return redirect(url_for('cameramenu'))



@app.route('/delete_camera/<id>',methods=['GET', 'POST','DELETE'] )
def delete_camera(id):
    # Get the contact and check if the user has permission to delete it
    try:
        id = int(id)
        data = Camera_list.query.get(id)
        if data.user_id != session['logged_in_user_id']:
            flash('You do not have permission to delete this camera')
            return redirect(url_for('cameramenu'))
    except (ValueError, TypeError):
        flash('Invalid id')
        return redirect(url_for('cameramenu'))
    except DataError:
        flash('Error deleting camera')
        return redirect(url_for('cameramenu'))


    # Delete the contact
    db.session.delete(data)
    db.session.commit()
    flash('Camera deleted')
    return redirect(url_for('cameramenu'))




    

# ----------------------------------------------------------------------------#
# Launch.
# ----------------------------------------------------------------------------#


# Default port:
if __name__ == '__main__':
    thread_cam = threading.Thread(target=gen_frames)
    thread_cam.start()
    app.run(debug=True , threaded=True)
