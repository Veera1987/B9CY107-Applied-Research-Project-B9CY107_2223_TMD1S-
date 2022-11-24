from flask import Flask, render_template, request, redirect, url_for, session
import os
from datetime import datetime
from flask_mysqldb import MySQL
from flask_mail import Mail, Message
from modules import AES_module
from modules import keywords
import ftplib
import hashlib
import random

application = Flask(__name__)
application.secret_key = 'new'

application.config['MYSQL_HOST'] = 'localhost'
application.config['MYSQL_USER'] = 'root'
application.config['MYSQL_PASSWORD'] = ''
application.config['MYSQL_DB'] = 'access_control'

mysql = MySQL(application)

application.config['MAIL_SERVER'] = 'smtp.gmail.com'
application.config['MAIL_PORT'] = 465
application.config['MAIL_USERNAME'] = 'bittuve@gmail.com'
application.config['MAIL_PASSWORD'] = ''
application.config['MAIL_USE_TLS'] = False
application.config['MAIL_USE_SSL'] = True
mail = Mail(application)

HOSTNAME = "ftp.drivehq.com"
USERNAME = "bittuve@gmail.com   "
PASSWORD = ""
FTP_PORT = '21'

user_mailId = ''
user_name = ''
user_branch = ''

# -----------------------------------    Admin routes --------------------------------------------


@application.route('/')
@application.route('/admin_login', methods=['POST', 'GET'])
def admin_login():
    if request.method == 'POST':
        admin_id = request.form["admin_id"]
        admin_pwd = request.form["admin_pwd"]
        cur = mysql.connection.cursor()
        cur.execute("select * from m_admin where admin_id=%s and admin_pwd=%s", (admin_id, admin_pwd))
        user = cur.fetchone()
        print(user)
        if user:
            session['logged_in'] = True
            return redirect(url_for('admin_home'))
        else:
            msg = 'Invalid Login Details Try Again'
            return render_template('admin/login.html', msg=msg)
    return render_template('admin/login.html')


@application.route('/admin_home', methods=['POST', 'GET'])
def admin_home():
    return render_template('admin/home.html')


@application.route('/users_list', methods=['POST', 'GET'])
def users_list():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM m_user")
    data = cur.fetchall()
    return render_template('admin/users_list.html', data=data)


@application.route('/user_files_list', methods=['POST', 'GET'])
def user_files_list():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM m_file_upload")
    data = cur.fetchall()
    return render_template('admin/user_files_list.html', data=data)


def domain_list():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT d_name FROM m_domain")
    domain_list1 = cursor.fetchall()
    domain_list2 = []
    for i in domain_list1:
        domain_list2.append(i[0])
    return domain_list2


@application.route('/create_user_page', methods=['POST', 'GET'])
def create_user_page():
    domain_list1 = domain_list()
    if request.method == 'POST':
        user_id = request.form['user_id']
        username = request.form['username']
        branch = request.form['branch']
        email = request.form['email']
        mobile = request.form['mobile']
        Password = request.form['password']
        address = request.form['address']

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT u_email FROM m_user WHERE u_email=%s", (email,))
        user = cursor.fetchone()
        if not user:
            cursor.execute('INSERT INTO m_user(u_id,u_name,u_branch,u_email,u_mobile,u_pwd,u_address)'
                           'VALUES(%s,%s,%s,%s,%s,%s,%s)', (user_id, username, branch, email, mobile, Password, address))

            mysql.connection.commit()
            cursor.close()

            with open('static/credentials.txt', 'w') as file:
                file.write('Hello {}...\n You can use below Credentials to login into your account.\n\nUser id : {}\n'
                           'User mail id: {}\nPassword : {}\n\n*Note : Do not forget to change your password after '
                           'login. '.format(username, user_id, email, Password))

            try:
                subject = 'User Login Credentials'
                msg = Message(subject, sender='smtp.gmail.com', recipients=[email])
                msg.body = "Hello  " + username + "  You have been created as user below file contains your credentials"
                with application.open_resource("static/credentials.txt") as fp:
                    msg.attach("credentials.txt", "application/txt", fp.read())
                mail.send(msg)
            except Exception as e:
                print(e)
                print("Something went wrong")

            msg = "User successfully added..."
            print(msg)
            return render_template('admin/create_user_page.html', msg1=msg, domains=domain_list1)
        msg2 = "This Email Id is already Registered"
        return render_template('admin/create_user_page.html', msg1=msg2, domains=domain_list1)
    return render_template('admin/create_user_page.html', domains=domain_list1)


def download_salt_values(branch):
    cur = mysql.connection.cursor()
    salt_list = []
    for i in branch:
        cur.execute("select d_salt from m_domain  where d_name=%s", (i,))
        salt = cur.fetchone()
        salt_list.append(salt[0])
    return salt_list


def create_hashing(key_list, branch_list):
    keywords_list1 = []
    salt_values = download_salt_values(branch_list)
    for i in salt_values:
        for j in key_list:
            new_word = j + i
            hashed = hashlib.md5(new_word.encode()).hexdigest()
            keywords_list1.append(hashed)
    return keywords_list1


@application.route('/admin_file_upload', methods=['POST', 'GET'])
def admin_file_upload():
    domains_list1 = domain_list()
    if request.method == 'POST':
        file = request.files['image']
        branch = request.form.getlist('branch')
        sub = request.form["subject"]
        time = datetime.today().date()
        original_filename = file.filename

        cursor = mysql.connection.cursor()
        try:
            cursor.execute('INSERT INTO m_file_upload(f_name,f_date_time,f_remarks) '
                           'VALUES(%s,%s,%s)', (original_filename, str(time), sub))
            mysql.connection.commit()
        except Exception as e:
            msg = e.args
            if msg[0] == 1062:
                msg = "{} is already Presented in database".format(original_filename)
                return render_template("admin/file_upload.html", msg=msg, domains=domains_list1)
            return render_template("admin/file_upload.html", msg=msg, domains=domains_list1)

        cursor.execute("SELECT f_no FROM m_file_upload WHERE f_name=%s", (original_filename,))
        f_no = cursor.fetchone()
        f_no = f_no[0]
        cursor.close()

        file_path = "static/upload/" + original_filename
        file.save(file_path)

        key_words = keywords.generate_keywords(file_path)
        print(key_words)
        keywords_weight = key_words[1] * len(branch)
        keywords_list = create_hashing(key_words[0], branch)

        new_filename = str(f_no) + '_' + original_filename + '.enc'
        infile = file_path
        outfile = "static/upload/" + new_filename

        with open(infile, 'rb') as in_file1, open(outfile, 'wb') as out_file1:
            enc_file = AES_module.encrypt(in_file1, out_file1)

        enc_key = enc_file
        file_path1 = 'static/download/' + new_filename

        with open(outfile, "rb") as file:
            # Command for Uploading the file "STOR filename"
            ftp_server = ftplib.FTP(HOSTNAME, USERNAME, PASSWORD)
            ftp_server.storbinary(f"STOR {file_path1}", file)
            ftp_server.encoding = "utf-8"

        cursor = mysql.connection.cursor()
        cursor.execute("UPDATE m_file_upload SET enc_key = %s, cloud_f_name= %s  WHERE f_no = %s",
                       (enc_key, new_filename, f_no))
        mysql.connection.commit()
        cursor.close()

        cursor = mysql.connection.cursor()
        for i in range(len(keywords_list)):
            cursor.execute('INSERT INTO m_keywords(keyword,weight,f_no) '
                           'VALUES(%s,%s,%s)', (keywords_list[i], keywords_weight[i], f_no))
        mysql.connection.commit()
        cursor.close()
        os.remove(infile)
        os.remove(outfile)
        msg = "File Uploaded Successfully"
        return render_template("admin/file_upload.html", msg=msg, domains=domains_list1)
    print(domains_list1)
    return render_template('admin/file_upload.html', domains=domains_list1)


@application.route('/admin_file_delete', methods=['POST', 'GET'])
def admin_file_delete():
    f_no = request.form['file_num']

    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM m_keywords WHERE f_no= %s", [f_no])
    mysql.connection.commit()

    cursor.execute("DELETE FROM m_file_upload WHERE f_no = %s ", [f_no])
    mysql.connection.commit()
    cursor.close()
    msg = "File deleted Successfully"

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM m_file_upload")
    data = cur.fetchall()
    return render_template('admin/user_files_list.html', data=data, msg=msg)


@application.route('/admin_domain_change', methods=['POST', 'GET'])
def admin_domain_change():
    d = domain_list()
    return render_template('admin/update_domains.html', domains=d)


@application.route('/single_domain_delete', methods=['POST', 'GET'])
def single_domain_delete():
    if request.method == 'POST':
        domain_name = request.form['domain_name']
        cursor = mysql.connection.cursor()
        cursor.execute("DELETE FROM m_domain WHERE d_name= %s", [domain_name])
        mysql.connection.commit()
        d = domain_list()
        return render_template('admin/update_domains.html', domains=d)


@application.route('/all_domain_delete', methods=['POST', 'GET'])
def all_domain_delete():
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM m_domain")
    mysql.connection.commit()
    d = domain_list()
    return render_template('admin/update_domains.html', domains=d)


@application.route('/add_domain', methods=['POST', 'GET'])
def add_domain():
    if request.method == 'POST':
        domainName = request.form['new_domains']
        print(domainName)
        domainNameList = domainName.split(' ')
        newSaltList = []
        for i in range(len(domainNameList)):
            rn = random.randint(1000, 10000)
            word = domainNameList[i] + str(rn)
            newSaltList.append(word)

        cursor = mysql.connection.cursor()
        for i in range(len(domainNameList)):
            cursor.execute('INSERT INTO m_domain (d_name,d_salt) VALUES(%s,%s)', (domainNameList[i], newSaltList[i]))
        mysql.connection.commit()
        d = domain_list()

        return redirect(url_for('admin_domain_change', domains=d))


@application.route('/admin_password_change', methods=['POST', 'GET'])
def admin_password_change():
    if request.method == 'POST':
        current_pass = request.form['old']
        new_pass = request.form['new']
        verify_pass = request.form['verify']
        cur = mysql.connection.cursor()
        cur.execute("select admin_pwd from m_admin")
        user = cur.fetchone()
        if user:
            if user[0] == current_pass:
                if new_pass == verify_pass:
                    msg = 'Password changed successfully'
                    cur.execute("UPDATE m_admin SET admin_pwd = %s ", (new_pass,))
                    mysql.connection.commit()
                    return render_template('admin/admin_password_change.html', msg1=msg)
                else:
                    msg = 'Re-entered password is not matched'
                    return render_template('admin/admin_password_change.html', msg2=msg)
            else:
                msg = 'Incorrect password'
                return render_template('admin/admin_password_change.html', msg3=msg)
        else:
            msg = 'Incorrect password'
            return render_template('admin/admin_password_change.html', msg3=msg)
    return render_template('admin/admin_password_change.html')


@application.route('/admin_user_edit', methods=['POST', 'GET'])
def admin_user_edit():
    domain_list1 = domain_list()
    if request.method == 'POST':
        email = request.form['email']
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM m_user WHERE u_email=%s", (email,))
        data = cursor.fetchone()
        cursor.close()
        print(data)
        return render_template('admin/update_user_page.html', data=data, domains=domain_list1)
    return render_template('admin/update_user_page.html', domains=domain_list1)


@application.route('/admin_user_update', methods=['POST', 'GET'])
def admin_user_update():
    domain_list1 = domain_list()
    if request.method == 'POST':
        user_id = request.form['user_id']
        username = request.form['username']
        email = request.form['email']
        mobile = request.form['mobile']
        branch = request.form['branch']
        address = request.form['address']

        cursor = mysql.connection.cursor()
        cursor.execute("UPDATE m_user SET u_name=%s, u_branch=%s, u_email=%s, u_mobile=%s, u_address=%s  WHERE u_id = %s",
                       (username, branch, email, mobile, address, user_id))
        mysql.connection.commit()
        cursor.close()

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM m_user WHERE u_id=%s", (user_id,))
        data1 = cursor.fetchone()
        cursor.close()
        msg = "User details updated successfully ..."
        print(msg)
        return render_template('admin/update_user_page.html', msg1=msg, data=data1, domains=domain_list1)
    return render_template('admin/update_user_page.html', domains=domain_list1)


@application.route('/admin_user_delete', methods=['POST', 'GET'])
def admin_user_delete():
    if request.method == 'POST':
        email = request.form['email']

        cursor = mysql.connection.cursor()
        cursor.execute("DELETE  FROM m_user WHERE u_email = %s ", [email])
        mysql.connection.commit()
        cursor.close()

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM m_user")
        data = cur.fetchall()
        return render_template('admin/users_list.html', data=data)
    return render_template('admin/users_list.html')


# -------------------------------------    User routes  -------------------------------------


@application.route('/user_login', methods=['POST', 'GET'])
def user_login():
    if request.method == 'POST':
        user_email = request.form["email"]
        user_pwd = request.form["password"]
        cur = mysql.connection.cursor()
        cur.execute("select * from m_user where u_email=%s and u_pwd=%s", (user_email, user_pwd))
        user = cur.fetchone()
        print(user)
        if user:
            session['logged_in'] = True
            global user_mailId, user_name, user_branch
            user_mailId = user_email
            user_name = user[2]
            user_branch = user[3]
            return render_template('user/home.html', user_name=user_name)
        else:
            msg = 'Invalid Login Details Try Again'
            return render_template('user/login.html', msg=msg)
    return render_template('user/login.html')


@application.route('/user_home', methods=['POST', 'GET'])
def user_home():
    return render_template('user/home.html', user_name=user_name)


def download_keywords(keyword, branch):
    keyword = keyword.split(' ')
    branch = branch.split(' ')
    keyword1 = create_hashing(keyword, branch)

    cur = mysql.connection.cursor()
    condition = ""
    for i in keyword1:
        condition = condition + "keyword = '" + i + "' or "
    condition = condition[:-3]
    cur.execute("select a.f_no, a.f_name, a.f_remarks, a.enc_key, a.cloud_f_name, sum(b.weight) from m_file_upload a "
                "inner join m_keywords b on a.f_no = b.f_no where " + condition + " group by f_no order by weight desc")

    data = cur.fetchall()
    return data


@application.route('/keyword-search', methods=['POST', 'GET'])
def keyword_search():
    if request.method == 'POST':
        keyword = request.form["keyword"]
        keyword = keyword.lower()
        branch = user_branch
        if len(branch) > 1:
            data = download_keywords(keyword, branch)
            if len(data) != 0:
                return render_template('user/home.html', data=data, keyword=keyword, user_name=user_name)
            else:
                msg = "Theres are no files available with the keyword of  '{}' , Please try with another keyword.. ".format(keyword)
                return render_template('user/home.html', keyword=keyword, msg=msg, user_name=user_name)
        else:
            msg = 'Session expired please login again !!'
            return render_template('user/login.html', msg=msg)


@application.route('/user_file_download', methods=['POST', 'GET'])
def user_file_download():
    if request.method == 'POST':
        file_name = request.form["file_name"]
        new_file_name = request.form["new_file_name"]
        key = request.form["key"]
        keyword = request.form["key_word"]
        branch = user_branch
        data = download_keywords(keyword, branch)

        in_file1 = "static/download/" + new_file_name
        out_file1 = "static/download/" + file_name

        with open(in_file1, "wb") as file:
            try:
                ftp_server = ftplib.FTP(HOSTNAME, USERNAME, PASSWORD)
                ftp_server.encoding = "utf-8"
                ftp_server.retrbinary(f"RETR {in_file1}", file.write)
                file.close()
                with open(in_file1, 'rb') as infile, open(out_file1, 'wb') as outfile:
                    AES_module.decrypt(infile, outfile, key)

                os.remove(in_file1)
                return render_template("user/home.html", data=data, keyword=keyword, file=out_file1, user_name=user_name)
            except Exception as e:
                print(e)
                msg = "Ftp server is not responding"
                print(msg)
                return render_template("user/home.html", msg=msg, data=data, keyword=keyword, user_name=user_name)


@application.route('/user_profile', methods=['POST', 'GET'])
def user_profile():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM m_user WHERE u_email=%s", (user_mailId,))
    data = cursor.fetchone()
    cursor.close()
    print(data)
    if data is not None:
        return render_template('user/profile.html', data=data, user_name=user_name)
    else:
        msg = 'Session completed please login again..'
        return render_template('user/login.html', msg=msg)


@application.route('/user_change_password', methods=['POST', 'GET'])
def user_change_password():
    if request.method == 'POST':
        current_pass = request.form['old']
        new_pass = request.form['new']
        verify_pass = request.form['verify']
        email = user_mailId
        cur = mysql.connection.cursor()
        cur.execute("select password from m_user where email=%s", (email,))
        user = cur.fetchone()
        if user:
            if user == current_pass:
                if new_pass == verify_pass:
                    msg1 = 'Password changed successfully'
                    cur.execute("UPDATE data SET password = %s WHERE password=%s", (new_pass, current_pass))
                    mysql.connection.commit()
                    return render_template('user/user_change_password.html', msg1=msg1, user_name=user_name)
                else:
                    msg2 = 'Re-entered password is not matched'
                    return render_template('user/user_change_password.html', msg2=msg2, user_name=user_name)
            else:
                msg3 = 'Incorrect password'
                return render_template('user/user_change_password.html', msg3=msg3, user_name=user_name)
        else:
            msg3 = 'Incorrect password'
            return render_template('user/user_change_password.html', msg3=msg3, user_name=user_name)

    return render_template('user/user_change_password.html', user_name=user_name)


@application.route('/logout')
def logout():
    session.clear()
    session['logged_out'] = True
    msg = 'You are now logged out', 'success'
    return redirect(url_for('admin_login', msg=msg))


@application.route('/user_logout')
def user_logout():
    session.clear()
    session['logged_out'] = True
    msg = 'Bye Bye {} .., See you soon'.format(user_name)
    return render_template('user/login.html', msg=msg)


if __name__ == '__main__':
    application.run(debug=True)
