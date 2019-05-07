from flask import *
from flask_cors import *
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, LoginManager, current_user, login_user, logout_user
from flask_admin import Admin, AdminIndexView
from flask_admin.contrib.sqla import ModelView
from flask_babelex import Babel


app = Flask(__name__)
babel = Babel(app)

CORS(app, supports_credentials=True)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///my.db"
app.config["SECRET_KEY"] = "123456"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True
app.config['BABEL_DEFAULT_LOCALE'] = 'zh_CN'


db = SQLAlchemy(app)
login = LoginManager(app)


@login.user_loader
def load_user(user_id):
    return User.query.get(user_id)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20))
    password = db.Column(db.String(20))
    type = db.Column(db.Integer)


class Book(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    userid = db.Column(db.Integer)
    fieldid = db.Column(db.Integer)
    sttime = db.Column(db.DateTime)
    edtime = db.Column(db.DateTime)
    cmtime = db.Column(db.DateTime)
    iscancel = db.Column(db.Boolean)


class Field(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20))
    name = db.Column(db.String(20))
    price = db.Column(db.Float)
    descr = db.Column(db.String(20))


class News(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(20))
    content = db.Column(db.Text)


class Operation(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    userid = db.Column(db.Integer)
    bookid = db.Column(db.Integer)
    type = db.Column(db.Integer)


# 模块管理视图
class MyModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for("admin_login"))


# 管理员主页视图
class MyAdminIndexView(AdminIndexView):
    def is_accessible(self):
        return current_user.is_authenticated

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for("admin_login"))


# 管理员登陆
@app.route('/admin_login', methods=['GET'])
def admin_login():

    u_name = request.args.get("name")
    u_password = request.args.get("password")
    u_type = 2

    u = User.query.filter_by(name=u_name, password=u_password, type=u_type).first()
    print(u)

    if u is not None:
        login_user(u)
        return redirect(url_for("admin.index"))    # 登陆完成，跳转管理员页面
    else:
        return "请使用正确的用户名和密码进行登陆"


# 管理员登出
@app.route('/admin_logout', methods=['GET'])
def admin_logout():
    logout_user()
    return "登出成功"


# 当前场地使用状况总览
@app.route('/summary', methods=['GET'])
def summary():

    sql1 = "select type, count(*) from field group by type"
    res1 = list(db.session.execute(sql1))

    time = request.args.get("time")

    if time == "":
        sql2 = """
        select type,count(*) 
        from field,book 
        where  field.id=book.fieldid
        and book.sttime<datetime('now', 'localtime')
        and book.edtime>datetime('now', 'localtime') 
        group by field.type 
        """
    else:
        sql2 = """
        select type,count(*) 
        from field,book 
        where  field.id=book.fieldid
        and book.sttime<'{}'   
        and book.edtime >'{}'
        group by field.type 
        """.format(time, time)

    res2 = list(db.session.execute(sql2))

    temp_list = [x[0] for x in res1]

    temp_dict = {}

    for x in temp_list:
        temp_dict.update({x: ""})

    for x in res2:
        temp_dict[x[0]] += str(x[1])

    for x in res1:
        if temp_dict[x[0]] == "":
            temp_dict[x[0]] = "0"

        temp_dict[x[0]] += "/"+str(x[1])

    return jsonify(temp_dict)


# 最新预定
@app.route('/latest', methods=['GET'])
def latest():
    sql1 = """
    select user.name,book.cmtime,field.name from book, user, field
    where book.userid=user.id 
    and book.fieldid=field.id
    order by book.cmtime desc limit 3
    """
    res1 = list(db.session.execute(sql1))

    temp_list = []
    for x in res1:
        temp_dict = {
            "username": x[0],
            "cmtime": x[1],
            "fieldname": x[2]
        }
        temp_list.append(temp_dict)

    return jsonify(temp_list)


# 场地查询
@app.route('/field_info', methods=['GET'])
def field_info():
    sql1 = """
    select DISTINCT field.type from field 
    """
    res1 = list(db.session.execute(sql1))
    print(res1)
    sql2 = """
    select * from field 
    """
    res2 = list(db.session.execute(sql2))

    print(res2)

    temp_dict = dict()

    for x in res2:
        if x[1] not in temp_dict:
            temp_dict[x[1]] = []
        temp_dict[x[1]].append(list(x))

    print(temp_dict)

    return jsonify(temp_dict)


@app.route('/qry', methods=['GET'])
def qry():
    idid = request.args.get("idid")
    sql1 = """
    select user.name,field.name,book.sttime,book.edtime,book.cmtime
    from book,field,user 
    where field.id={}
    and book.fieldid=field.id
    and book.userid=user.id
    and book.iscancel=0
    and book.edtime>datetime('now', 'localtime') 
    order by book.cmtime desc
    """.format(idid)
    res1 = list(db.session.execute(sql1))
    print(res1)
    temp_list = [list(x) for x in res1]
    return jsonify(temp_list)


def bookit():
    sql1 = """
    
    """

if __name__ == '__main__':

    # 管理员视图
    admin = Admin(app, name="后台管理", index_view=MyAdminIndexView())
    admin.add_view(MyModelView(User, db.session))

    app.run(host='0.0.0.0', port=80)
    # qry()

