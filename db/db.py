import pandas as pd
from sqlalchemy import INTEGER, Integer, create_engine, Column, String, VARCHAR, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from logs import logger
import app

Base = declarative_base()
Base2 = declarative_base()

class User(Base):
    __tablename__ = 'users'

    # id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    email = Column(VARCHAR, unique=True)
    otp = Column(Integer)
    password = Column(String)
    last_login = Column(String)
    license_number = Column(VARCHAR, unique=True, primary_key=True)
    license_valid = Column(Boolean)

class Admin(Base2):
    __tablename__ = 'Admin'

    admin_id = Column(VARCHAR, unique=True, primary_key=True)
    admin_password = Column(VARCHAR)
    email = Column(VARCHAR, unique=True)
    last_login = Column(String)
    admin_role = Column(String)
    otp = Column(Integer)

# Example of creating a user with encrypted password
def create_user(username, password,license_number,email):
    encrypted_password = encrypt_password(password)

    new_user = User(username=username, password=encrypted_password, email=email, last_login = datetime.now().strftime(f"%Y-%m-%d %H:%M:%S"), license_number=license_number, license_valid=0)

    user = session.query(User).filter_by(username=username).first()

    
    if user:
        session.rollback()
        return "User name already exists."
    else:
        session.add(new_user)
        session.commit()
        logger.create_log(username,app.session['guest_user_ip'],"got registered as new user.","info","user")
        return "done"
    

def delete_user(username):
    username = session.query(User).filter_by(username=username).first()
    
    try:
        session.delete(username)
        session.commit()
        return "User and license Deleted Successfully."
    except Exception as e:
        session.rollback()
        return e

def show_user(username):
    logger.create_log(username,app.session['guest_user_ip'],"was checked in the 'users' database.","info",'user')
    data = session.query(User).filter_by(username=username).first()
    if data:
        logger.create_log(username,app.session['guest_user_ip'],"was found in the database.","info",'user')
        return data.username, decrypt_password(data.password), data.license_number, data.license_valid, data.email
    else:
        session.rollback()   
        logger.create_log(username,app.session['guest_user_ip'],"was not found in the database.","info",'user')
        return "wrong"

def update_last_login(username):
    user = session.query(User).filter_by(username=username).first()
    if user:
        user.last_login = datetime.now().strftime(f"%Y-%m-%d %H:%M:%S") # type: ignore
        session.commit()
        return "LastLoginUpdated"
    else:
        session.rollback()
        return "Error"
        
def sendotp(email, otp):
    user = session.query(User).filter_by(email=email).first()
    if user:
        user.otp = otp
        session.commit()
        return "Success"
    else:
        return "Error" 

def validate_license_by_user(username, license_number):
    user = session.query(User).filter_by(username=username, license_number=license_number).first()
    if user:
        user.license_valid = True  # type: ignore
        session.commit()
        logger.create_log(app.session['username'],app.session['user_ip'],f"{username} validated License using OTP verification.","info","user")
        return "success"
    else:
        session.rollback()
        return "fail"

# Example of hashing a password
def encrypt_password(password):
    password = str(password)
    password = password[::-1]
    return password

def decrypt_password(password):
    password = str(password)
    password = password[::-1]
    return password
    
# ------------------------------------------------------------------------------------------------------------------------------------

def create_admin(admin_id, admin_password,admin_role, email):
    encrypted_password = encrypt_password(admin_password)

    new_admin = Admin(admin_id=admin_id,email=email, admin_password=encrypted_password, last_login = datetime.now().strftime(f"%Y-%m-%d %H:%M:%S"), admin_role=admin_role )

    admin = session.query(Admin).filter_by(admin_id=admin_id).first()

    try:
        if admin:
            return "Admin already exists."
        else:
            session.add(new_admin)
            session.commit()
            logger.create_log(admin_id,app.session['guest_admin_ip'],"got registered as new user.","info",admin_role)
            return "Admin created Successfully."
    except Exception as e:
        session.rollback()
        return e

def show_admin(admin_id):
    admin = session.query(Admin).filter_by(admin_id=admin_id).first()
    logger.create_log(admin_id,app.session['guest_admin_ip'],"was checked in the 'Admin' database.","info","Admin")
    
    if admin:
        logger.create_log(admin_id,app.session['guest_admin_ip'],"was found in the 'Admin' database.","info",admin.admin_role)    
        return admin.admin_id, decrypt_password(admin.admin_password), admin.admin_role, admin.email
    else:
        session.rollback()
        logger.create_log(admin_id,app.session['guest_admin_ip'],"was not found in the 'Admin' database.","info","Admin")    
        return "Wrong"

def update_last_login_admin(admin_id):
    admin = session.query(Admin).filter_by(admin_id=admin_id).first()
    if admin:
        admin.last_login = datetime.now().strftime(f"%Y-%m-%d %H:%M:%S") # type: ignore
        session.commit()
        return "LastLoginUpdated"
    else:
        session.rollback()
        return "Error"

def display_licenses():
    user = session.query(User).all()
    if user:
        return user
    else:
        session.rollback()
        exit()  

def update_license(username, license_number):
    user = session.query(User).filter_by(username=username).first()
    if user:
        user.license_number = license_number
        # user.license_valid = license_valid
        logger.create_log(app.session['admin_id'],app.session['admin_ip'],f"updated {username}'s existing license details.","info",app.session['admin_role'])
        session.commit()
        return "success"
    else:
        session.rollback()
        logger.create_log(app.session['admin_id'],app.session['admin_ip'],f"found no license of {username}.","info",app.session['admin_role'])
        return "fail"

def validate_license(username, license_number):
    user = session.query(User).filter_by(username=username, license_number=license_number).first()
    if user:
        user.license_valid = True  # type: ignore
        session.commit()
        logger.create_log(app.session['admin_id'],app.session['admin_ip'],f"validated license of {username}.","info",app.session['admin_role'])
        return "success"
    else:
        session.rollback()
        logger.create_log(app.session['admin_id'],app.session['admin_ip'],f"found no license of {username}.","info",app.session['admin_role'])
        return "fail"

def create_license(username, password,email,license_number):
    user = session.query(User).filter_by(username=username).first()

    if user:
        return "user already exists"
    else:
        new_user = User(username=username, password=password, email=email, last_login = datetime.now().strftime(f"%Y-%m-%d %H:%M:%S"), license_number=license_number, license_valid=0)
        session.add(new_user)
        session.commit()
        return "New license added Successfully."

def show_license(username):
    user = session.query(User).filter_by(username=username).first()
    
    if user:
        return f"Username : {user.username}, License Number : {user.license_number}, Last Login : {user.last_login}, License Valid : {user.license_valid}"
    else:
        return "No user exists with this username"
    
def show_stats():
    user = session.query(User).all()
    if user:
        # columns = ["username","email","otp","password","last_login","license_number","license_valid"]
        usertable = pd.DataFrame([vars(item) for item in user])
        total_user_count = pd.Series(usertable['username']).count()
        total_valid_invalid_licenses = pd.Series(usertable['license_valid']).value_counts()
        registered_mails = pd.Series(usertable['email']).value_counts()
        return {"Total Licenses Registered":total_user_count, 'Total Valid Licenses':total_valid_invalid_licenses[1],'Total Invalid Licenses':total_valid_invalid_licenses[0],
                'Total Registered Emails':registered_mails[1],'Total Unregistered Emails':registered_mails[0]}
    else:
        return "No data found"


# Example usage
engine = create_engine('mysql://uzzdxqgvtazr0upw:VZMtOFURcuOciDdgCiux@b30uyzfdqkmsnkdgcyte-mysql.services.clever-cloud.com:3306/b30uyzfdqkmsnkdgcyte')
Base.metadata.create_all(bind=engine)
Session = sessionmaker(bind=engine)
session = Session()