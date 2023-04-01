from flask import Flask, render_template, flash,Markup, request,session,redirect, url_for,get_flashed_messages
from forms import LoginForm,RegistrationForm,UploadFile,AdminRegistration
from flask_bcrypt import Bcrypt,check_password_hash
from flask_mail import Mail, Message
from db import connection
import openpyxl
import pandas as pd
import secrets
from openpyxl.utils import get_column_letter
import os
from utility import SheetsExamine, Metric, QualitativeMetric
import json
from werkzeug.utils import secure_filename




app = Flask(__name__)

app.config['SECRET_KEY'] = 'skdfjoeir535803930f@###$%%^gjrDSWWEFD$#$%^^%&'
app.config['SESSION_TYPE'] = 'filesystem'
app.config['UPLOAD_FOLDER'] = 'static/files'
# app.config['MAIL_SERVER'] = 'smtp.mail.yahoo.com'
# app.config['MAIL_PORT'] = 587
# app.config['MAIL_USE_SSL'] = True
# app.config['MAIL_USERNAME'] = 'abdullatiffaqeeri@yahoo.com'
# app.config['MAIL_PASSWORD'] = '*******'

bcrypt = Bcrypt(app)
mail = Mail(app)

 

    
    
     
# Routes
@app.route('/')
@app.route('/login', methods = ['GET','POST'])
def login():
    
    form = LoginForm()
    admin = ''       
    if form.validate_on_submit():
        email = form.college_email.data
        password = form.password.data
        
        # Search college in Database
        cursor = connection.cursor()
        cursor.execute('SELECT * from college WHERE coll_email = %s',(email))
        college = cursor.fetchone()
        # Search admin in Database if admin logins
        if not college:
            cursor.execute('SELECT * from admin WHERE email = %s',(email))
            admin = cursor.fetchone()
            
        if college:
            # Check the login credentials for success case
            if (college['coll_email'] == email) and check_password_hash(college['password'],password):
                  
                session['college_email'] = email
                session['college_category'] = college['coll_type']
                cursor.execute('SELECT sheet_no,template FROM excel_sheets WHERE  template = ( SELECT MAX(template_id) from template)')

                metrics = cursor.fetchall()
                session['metrics'] = metrics
                
                return redirect('/dashboard')
            
            # Check the login credentials for failure case 
            else:
                session['college_email'] = email 
                flash('Email or password is wrong !')
                return redirect('/login')
            
        elif admin:
            # Check the login credentials for success case
            if (admin['email'] == email) and admin['password']==password:
                  
                session['admin_email'] = email
                session['admin_role'] = admin['role']
                session['admin_access'] = admin['access']
                session['admin_name'] = admin['first_name']+" "+admin['last_name']
    
                return redirect('/admin/dashboard')
            else:
                flash('Email or password is wrong !')
                return redirect('/login')
        else:  
            flash('Sorry, account does not exist !')  
            return redirect('/login')
        
    return render_template('login.html',form=form)




@app.route('/sign-up', methods = ['GET', 'POST'])
def sign_up():
    
    form = RegistrationForm()
        
    if form.validate_on_submit():
        college_name = form.college_name.data
        college_loc = form.city.data
        established_year = form.established_year.data
        parent_university = form.parent_university.data
        college_email = form.college_email.data
        college_phone = form.college_phone.data
        college_type = form.select.data
        college_mentor = form.select_mentor.data
        password = form.password.data
                        
        #create cursor
        cursor = connection.cursor()
        
        # Hashed Password
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        # Checks if account is already existed in the Database
        cursor.execute('SELECT * from college where coll_email = %s',(college_email))
        
        college = cursor.fetchone()
        
        if college:
            # Redirect to sign up page 
            flash('This Email is already registered.')
            return redirect('/sign-up')
            
        # Storing the college in to Database
        else:
            token = secrets.token_hex(16)
            cursor.execute('INSERT INTO college (coll_name, coll_loc, estab_year, parent_univ, coll_email,coll_type, coll_mobile,password,email_verification_token,mentor_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)'
            ,(college_name, college_loc, established_year, parent_university, college_email,college_type, college_phone,hashed_password,token,college_mentor))
            
            # session['college_name'] = college_name
            # session['college_email'] = college_email
            # send_email_verification(college_email,token)
            
            # Flash message
            flash("Thanks for signing up. College account has been created.")  
            
            connection.commit()
            cursor.close()
            # connection.close()
            # return redirect('/verify-email')
            redirect('/login')
    return render_template('sign-up.html',form=form)


# def send_email_verification(email,token):
#     """Sends the verification email to the college email"""
#     msg = Message('Welcome ',sender = 'abdullatiffaqeeri@yahoo.com', recipients = [email])
#     msg.body = f"this is a test mail <a href='https://www.google.com'> verify email</a>"
#     mail.send(msg)      
         
         
@app.route('/verify-email')


@app.route('/dashboard', methods = ['GET', 'POST'])
def dashboard():
    # checks if the college is not logged in redirects to login page
    if not session.get('college_email'):
        return redirect('/login')
    
    # if college is logged in, allows to access dashboard page
    else:
        form = UploadFile()
        metrics = session['metrics']
        return render_template('dashboard.html',form=form ,metrics = metrics)


@app.route('/dashboard/upload-metrics', methods=['GET','POST'])
def upload_metrics():
    
    form = UploadFile()
    
    if request.method == 'POST':
        excel_file= request.files['workbook']
        template_id= int(request.form.get('select'))
       
        cursor = connection.cursor()
        cursor.execute("SELECT sheet_no FROM excel_sheets WHERE template=%s",(template_id))
        session['sheets'] = cursor.fetchall()
        
        connection.commit()
        cursor.close()
        sheet_examine = SheetsExamine(excel_file,template_id)
        sheet_examine.check_sheets()
   
    return redirect('/dashboard')
    
@app.route('/dashboard/view/<sheet_no>/<int:template>', methods = ['GET'])
def render_metric(sheet_no,template):
    
    metric = Metric()   
    output = metric.render(sheet_no,template)
    print(output) 
    return output
 
@app.route("/dashboard/update",methods=['GET','PUT'])
def update_metrics():
    a = ''
    if request.method == 'PUT':
        byte_str = request.data
        json_str = byte_str.decode('utf-8')
        data = json.loads(json_str)
        metric = Metric()
        a = metric.update_metric(data)
    print('update result: ',a) 
    return a

@app.route("/dashboard/delete",methods=['DELETE'])
def delete_metric():
    a = ''
    if request.method == 'DELETE':
        byte_str = request.data
        json_str = byte_str.decode('utf-8')
        data = json.loads(json_str)
        metric = Metric()
        a = metric.delete_metric(data)
    print('delete result, ',a)    
    return a

@app.route("/dashboard/add",methods=['GET','POST'])
def add_metric():
    a = ''
    if request.method == 'POST':
        byte_str = request.data
        json_str = byte_str.decode('utf-8')
        data = json.loads(json_str)
        metric = Metric()
        a = metric.add_metric(data)
    print("addition result,",a)    
    return a

@app.route('/dashboard/questions', methods=['GET'])
def get_questions():
    qualitativeQuestion = QualitativeMetric()
    questions = qualitativeQuestion.getQuestions()
    return questions
    

@app.route('/dashboard/upload/qualitative_questions', methods=['POST'])
def upload_questions():
    
    if request.method == 'POST':
        textarea1 = request.form.getlist('textarea')
        print(textarea1)
        files = request.files
        for key in files:
            file = files[key]
            filename = secure_filename(file.filename)
            file.save(os.path.join(os.path.abspath(os.path.dirname(__file__)),app.config['UPLOAD_FOLDER'],filename))
            # file.save(os.path.join(app.config['UPLOAD_FOLDER'],filename))
        # print(files_names)
        # textarea2 = request.form['question-2']
        # print(textarea1)
        # print(textarea2)
    return redirect('/dashboard')    
        
# Admin Dashboard Route
@app.route('/admin/dashboard',methods=['GET'])
def adminPanel():
     # checks if the admin is not logged in redirects to login page
    if not session.get('admin_email'):
        return redirect('/login')
    
    form = AdminRegistration()
    return render_template('admin_panel.html',form=form)    

# Create Admin Route
@app.route('/admin/create',methods=['GET','POST']) 
def create_admin():
    
    form = AdminRegistration()
        
    if form.validate_on_submit():
       title = form.select_title.data
       first_name = form.first_name.data
       middle_name = form.middle_name.data
       last_name = form.last_name.data
       designation = form.designation.data
       role = form.select_role.data
       address = form.address.data
       pin_code = form.pin_code.data
       phone = form.phone.data
       email = form.email.data
       password = form.password.data
    # print('here')
    # form_data = request.form
    # print(form_data)    
    # Hashed Password
       hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
       
       # create cursor
       cursor = connection.cursor()
       
       # Checks if account is already existed in the Database
       cursor.execute('SELECT * from admin where email = %s',(email))
       
       admin = cursor.fetchone()
       
       if admin:
           # Redirect to admin dashboard page 
           flash('This Email is already registered.','danger')
           return redirect('/admin/dashboard')
           
       # Storing the college in to Database
       else:
           cursor.execute('INSERT INTO admin (first_name, middle_name, last_name, title, designation,email, phone,address,role,password) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)'
           ,(first_name, middle_name, last_name, title, designation,email, phone,address,role,hashed_password))
           
           # Flash message
           flash("Admin created.",'success')  
           
           connection.commit()
           cursor.close()
           
           redirect('/admin/dashboard')
    return render_template('admin_panel.html',form=form)

@app.route('/admin/accounts',methods=['GET','POST'])
def fetch_accounts():
    
    # select * admin accounts from DB
    cursor = connection.cursor()
    cursor.execute(f'''SELECT first_name,middle_name,last_name,title,designation,email
                   ,phone,address,access from admin where role=%s''',('admin'))
    admins = cursor.fetchall()
    
    cursor.close()
    return (admins)

      
             
# Logout Route
@app.route('/logout', methods=['GET','POST'])
def logout():
    session.pop('college_email',None)
    return redirect('login')    


#   Palwinder's temporary work

@app.route('/all_colleges')
def display_colleges():
    cursor = connection.cursor()
    cursor.execute('SELECT college.coll_name,college.coll_email, college.coll_loc, college.parent_univ, admin.email, CONCAT(admin.first_name," ", admin.middle_name," ", admin.last_name) AS Mentor FROM college JOIN admin ON admin.email=college.mentor_id')
    colleges = cursor.fetchall()
    print(':::::::::::::::')
    print(colleges[2]['coll_email'])
    cursor.close()

    cursor = connection.cursor()
    cursor.execute('SELECT email, CONCAT (first_name, " ", middle_name, " ", last_name) AS Mentors FROM admin')
    all_mentors = cursor.fetchall()
    cursor.close()
    return render_template('all_colleges.html', colleges = colleges, all_mentors = all_mentors)

@app.route('/change_mentor', methods = ['GET', 'POST'])
@app.route('/change_mentor', methods = ['GET', 'POST'])
def change_mentor():
    cursor = connection.cursor()
    cursor.execute('SELECT email, CONCAT(admin.first_name," ", admin.middle_name," ", admin.last_name) AS Mentors FROM admin')
    all_mentors = cursor.fetchall()
    cursor.close()

    if request.method == 'GET':
        global coll_email
        coll_email = request.args.get('coll_email')

    if request.method == 'POST':
        global new_mentor
        new_mentor = request.form.get('new_mentor')
        print('new_mentor', new_mentor)

        cursor = connection.cursor()
        cursor.execute(f'UPDATE college SET mentor_id = "{new_mentor}" WHERE coll_email = "{coll_email}"')
        cursor.connection.commit()
        cursor.close()
    return render_template('update_mentor.html', coll_email = coll_email, all_mentors = all_mentors)



if __name__ == '__main__':
    app.run(debug=True)
