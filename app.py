from asyncio import threads
from datetime import datetime, timedelta
from flask import Flask, flash, make_response, render_template, redirect, request, session, url_for
from flask_cors import CORS
from db import db
import verification, random
from logs import logger
from waitress import serve

app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = "LMS"

# --------------------------------------------------------------------------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")

@app.route('/logout')
def logout():
    session.clear()
    return render_template('index.html', output="Logged out successfully.")

@app.route('/otpverification', methods=['POST'])
def otpverification():
    if request.method == 'POST':
        otp = request.form.get('otp')
        buttonclicked = request.form.get('buttonclicked')
        if buttonclicked == None:
            if otp == str(session['otp']):
                if session['operator'] == 'Manager' or session['operator']=='CEO':
                    logger.create_log(session['admin_id'],session['admin_ip'],"logged in successfully.","info",session['operator'])
                    return redirect(url_for('admindash'))
                if session['operator']=='user':
                    logger.create_log(session['username'],session['user_ip'],"logged in successfully.","info","user")    
                    return redirect(url_for('userdash'))
                else:
                    return render_template('index.html',  output='Error occoured while logging in')
            else:
                flash("Invalid OTP entered.")
                return render_template('otpverification.html')                
        elif buttonclicked == 'sendvalidationotp':
            session['otp'] = random.randint(0,999999)
            flag = verification.SendEmail(toaddr=session['user_email'], subject='License Validation OTP', message=f"Your otp to validate license is {session['otp']}")
            if flag == 1:
                return "OTP sent successfully to registered email linked to this account."
            else:
                return "Error sending OTP"
        elif buttonclicked == 'ValidateLicense':
            if otp == str(session['otp']):
                flag = db.validate_license_by_user(username=session['username'], license_number=session['license_number'])
                if flag == 'success':
                    logger.create_log(session['username'],session['user_ip'],"updated license successfully.","info","user")    
                    return f"License Validated successfully. Re-Login to see changes."
                elif flag == 'fail':
                    return "License already validated or not found."
                else:
                    return "License not validated due to database error."
            else:
                return "Invalid OTP entered."
        else:
            flash(f"Some error occoured try again")
            return render_template('otpverification.html')
    else:
        return redirect(url_for('logout'))

@app.route('/userdash/checklicensevalidity')
def checklicensevalidity():
    session_valid = checksessionvalid()
    logger.create_log(session['username'],session['user_ip'],"initiated a license validation request.","warning","user")

    if session['username'] and session_valid=="Valid" :
        if session['valid']==1:
            logger.create_log(session['username'],session['user_ip'],"Found License as Valid.","info","user")
            return render_template("userdash.html", output="Congratulations, your license is valid.",name=session['username'],logintime=session['logintime'],user_ip=session['user_ip'])
        else:
            logger.create_log(session['username'],session['user_ip'],"Found License as Invalid.","info","user")
            return render_template("userdash.html", output="Sorry, your license is not valid. Contact team to get it validated.",name=session['username'],logintime=session['logintime'],user_ip=session['user_ip'])
    else:
        flash("Login Session Timed Out, kindly login again.")
        return render_template("userlogin.html")

@app.route('/registeruser')
def registeruser():
    return render_template("registeruser.html")

@app.route('/create', methods=["POST"])
def create_user():
    if request.method == "POST":
        session['guest_user_ip'] = f'{request.remote_addr}'
        logger.create_log('Unregistered user',session['guest_user_ip'],"initiated user registration","warning","user")
        username = request.form.get('username')
        password = request.form.get('password')
        repeat_password = request.form.get('repeat_password')
        license_number = request.form.get('license_number')
        email = request.form.get('email')
        output=""
        if password==repeat_password:
            output=db.create_user(username=username, password=password, license_number=license_number, email=email)
            db.session.commit()
            if output=="User name already exists.":
                flash(f"{output}")
                session.clear()
                return render_template("registeruser.html")
            else:
                flash(f"{output}")
                db.session.rollback()
                return render_template("userlogin.html")
        else:
            flash(f"{output}")
            db.session.rollback()
            return render_template("registeruser.html")
    
    return render_template("registeruser.html")

@app.route('/userlogin')
def userlogin():
    return render_template("userlogin.html")

@app.route('/userdash')
def userdash():
    session_valid = checksessionvalid()

    if session['username'] and session_valid=="Valid":
        return render_template("userdash.html",name=session['username'], logintime=session['logintime'], user_ip=session['user_ip'])
    else:
        session.clear()
        flash("Login Session Timed Out, kindly login again.")
        return redirect(url_for('userlogin'))

@app.route("/userlogincheck", methods=['GET','POST'])
def userlogincheck():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        session['guest_user_ip'] = f'{request.remote_addr}'
        logger.create_log(username,session['guest_user_ip'],"initiated user login.","warning","user")
        output = db.show_user(username)
        if output[1] == '':
            flash("Wrong password, reset password now.")
            return render_template("userlogin.html")
        if username==output[0] and password==output[1]:
            session["username"] = username
            session['operator'] = 'user'
            session['logintime'] = datetime.now().strftime(f"%Y-%m-%d %H:%M:%S")
            session["expiry"] = datetime.now() + timedelta(minutes=60)
            session['license_number'] = output[2]
            session['otp'] = random.randint(0,999999)
            session['valid']=output[3]
            session['user_email'] = output[4]
            session['active'] = 1
            session['user_ip'] = f"{request.remote_addr} __ {request.remote_user}"
            db.update_last_login(username)
            otpflag = verification.SendEmail(toaddr=output[4],subject="LMS user OTP Verification", message=f"Your otp is {session['otp']}")
            if otpflag==1:
                return render_template('otpverification.html')
            else:
                flash("Error while sending email")
                return redirect(url_for('userlogin'))
        else:
            flash(f"No, user found, kindly register with {username} and {password}")
            return render_template("userlogin.html")

    return render_template("userlogin.html") 

def checksessionvalid():
    try:
        expiry = session['expiry']
        expiry = datetime.strptime(expiry.strftime(f"%Y-%m-%d %H:%M:%S"), f"%Y-%m-%d %H:%M:%S")

        if datetime.strptime(datetime.now().strftime(f"%Y-%m-%d %H:%M:%S"),f"%Y-%m-%d %H:%M:%S") < expiry and session['active']==1:
            return "Valid"
        else:
            return "Invalid"
    except Exception as e:
        flash('Session timed out, sorry')
        return redirect(url_for('adminlogin'))


# -----------------------------------------------------------------------------------------------------
    
@app.route('/adminlogin')
def adminlogin():
    session['guest_admin_ip'] = f'{request.remote_addr} __ {request.remote_user}'
    logger.create_log("Admin_Registered",session['guest_admin_ip'],"initiated a admin login.","warning","Admin")
    return render_template("adminlogin.html")

@app.route('/registeradmin')
def registeradmin():
    return render_template("registeradmin.html")

@app.route('/createadmin', methods=["POST"])
def createadmin():
    if request.method == "POST":
        admin_id = request.form.get('admin_id')
        password = request.form.get('password')
        repeat_password = request.form.get('repeat_password')
        admin_role = request.form.get('admin_role')
        email = request.form.get('email')
        session['guest_admin_ip'] = f'{request.remote_addr} __ {request.remote_user}'
        logger.create_log(admin_id,session['guest_admin_ip'],"initiated an admin registration.","warning","Admin")
        output=""
        if password==repeat_password:
            # output=db.create_admin(admin_id=admin_id, email=email,admin_password=password, admin_role=admin_role)
            output = db.create_admin(admin_id=admin_id, admin_password=password, email=email, admin_role=admin_role)
            db.session.commit()
            if output=="Admin already exists.":
                flash(f"{output}")
                return render_template("registeradmin.html")
            else:
                flash(f"{output}")
                return render_template("adminlogin.html")
        else:
            flash(f"{output}")
            return render_template("registeradmin.html")
    
    return render_template("registeradmin.html")

@app.route('/admindash')
def admindash():
    session_valid = checksessionvalid()
    logs = logger.display_logs()
    logs.reverse()
    try:
        if session['admin_id'] and session_valid=="Valid":
            licenses = db.display_licenses()
            stats = db.show_stats()
            return render_template("admindash.html",stats=stats,logs=logs,licenses=licenses,admin_id=session['admin_id'], admin_role=session['admin_role'],logintime=session['admin_logintime'], admin_ip=session['admin_ip'])
        else:
            db.session.rollback()
            session.clear()
            flash("Login Session Timed Out, kindly login again.")
            return redirect(url_for('adminlogin'))
    except Exception as e:
            flash(f'{e}')
            return redirect(url_for('adminlogin'))
    


@app.route("/adminlogincheck", methods=['GET','POST'])
def adminlogincheck():
    if request.method == "POST":
        admin_id = request.form.get("admin_id")
        password = request.form.get("password")
        session['guest_admin_ip'] = f'{request.remote_addr}'
        output = db.show_admin(admin_id)
        logger.create_log(admin_id,session['guest_admin_ip'],"initiated user login.","warning","Admin")
        if admin_id==output[0] and password==output[1]:
            session["admin_id"] = admin_id
            session['admin_logintime'] = datetime.now().strftime(f"%Y-%m-%d %H:%M:%S")
            session["expiry"] = datetime.now() + timedelta(minutes=60)
            session['admin_role']=output[2]
            session['operator'] = session['admin_role']
            session['otp'] = random.randint(0,999999)
            session['active']=1
            session['admin_ip'] = f"{request.remote_addr} __ {request.remote_user}"
            db.update_last_login(admin_id)
            otpflag = verification.SendEmail(toaddr=output[3],subject="LMS Admin OTP Verification", message=f"Your otp is {session['otp']}")
            if otpflag==1:
                return render_template('otpverification.html')
            else:
                flash("Error while sending email")
                return redirect(url_for('userlogin'))
        else:
            db.session.rollback()
            flash(f"No, Admin found, kindly register with {admin_id} and {password}")
            return render_template("adminlogin.html")

    return render_template("adminlogin.html")

@app.route('/admindash/managelicenses')
def managelicenses():
    sessionvalid = checksessionvalid()
    if sessionvalid == 'Valid':
        stats = db.show_stats()
        return render_template('managelicenses.html',stats=stats,admin_id=session['admin_id'],admin_role=session['admin_role'], licenses=db.display_licenses())
    else:
        db.session.rollback()
        flash("Session timed out! Kindly relogin")
        return redirect(url_for('adminlogin'))

@app.route('/admindash/managelicenses/modifylicense', methods=['POST'])
def modifylicense():
    sessionvalid = checksessionvalid()
    if sessionvalid == 'Valid':
        if request.method == "POST":
            username = request.form.get('username')
            license_number = request.form.get('license_number')
            # license_valid = request.form.get('license_valid')
            buttonclicked = request.form.get('buttonclicked')

            if buttonclicked == 'add':
                logger.create_log(session['admin_id'],session['admin_ip'],"inititated new license addition.","info",session['admin_role'])
                output = db.create_license(username=username, password="",email="", license_number=license_number)
                if output:
                    logger.create_log(session['admin_id'],session['admin_ip'],f"registered new license : {username} with L.No. {license_number}.","info",session['admin_role'])
                # output = "User and license created Sucessfully."
            elif buttonclicked == 'update':
                logger.create_log(session['admin_id'],session['admin_ip'],f"initiated license updation.","info",session['admin_role'])
                output = db.update_license(username, license_number)
            elif buttonclicked == 'validate':
                logger.create_log(session['admin_id'],session['admin_ip'],f"initiated license validation.","info",session['admin_role'])
                output = db.validate_license(username, license_number)
            elif buttonclicked == 'delete':
                logger.create_log(session['admin_id'],session['admin_ip'],f"initiated license deletion.","info",session['admin_role'])
                output = db.delete_user(username)
                if output == 'User and license Deleted Successfully.':
                    logger.create_log(session['admin_id'],session['admin_ip'],f"deleted license owned by '{username}'.","info",session['admin_role'])    
            elif buttonclicked == 'get_l':
                output = db.show_license(username)
            else:
                return "No Input Data Recieved"
            res = make_response(output)
            return res
        else:
            return "wrong method, not post"
    else:
        return render_template('adminlogin.html')

if __name__ == "__main__":
    # app.run(debug=True)
    serve(app, host='0.0.0.0', port=5000, threads=1)