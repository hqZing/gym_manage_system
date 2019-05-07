from flask import *
from flask_cors import *
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, LoginManager, current_user, login_user, logout_user, login_required
from flask_admin import Admin, AdminIndexView
from flask_admin.contrib.sqla import ModelView
from flask_babelex import Babel
import time
import datetime

app = Flask(__name__)
babel = Babel(app)

CORS(app, supports_credentials=True)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///my.db"
app.config["SECRET_KEY"] = "123456"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True
app.config['BABEL_DEFAULT_LOCALE'] = 'zh_CN'

# 数据库模块
db = SQLAlchemy(app)

# 登陆模块
login_manager = LoginManager()
login_manager.login_view = 'login_page'
login_manager.login_message_category = 'info'
login_manager.login_message = 'Access denied.'
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20))
    password = db.Column(db.String(20))
    type = db.Column(db.Integer)

    def __init__(self, u_name, u_password, u_type):
        self.name = u_name
        self.password = u_password
        self.type = u_type



class Book(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    userid = db.Column(db.Integer)
    fieldid = db.Column(db.Integer)
    sttime = db.Column(db.DateTime)
    edtime = db.Column(db.DateTime)
    cmtime = db.Column(db.DateTime)
    iscancel = db.Column(db.Boolean)
    ispayed = db.Column(db.Boolean)


class Field(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20))
    name = db.Column(db.String(20))
    price = db.Column(db.Float)
    descr = db.Column(db.String(200))


class News(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    content = db.Column(db.Text)


class Operation(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    userid = db.Column(db.Integer)
    bookid = db.Column(db.Integer)
    type = db.Column(db.Integer)        # 1表示下单， 0表示取消， 2表示支付
    cmtime = db.Column(db.DateTime)     # 记录下每次操作的时间


# 模块管理视图
class MyModelView(ModelView):
    def is_accessible(self):
        # 这里必须加个条件，验证用户类型为管理员，否则将会引发普通用户可以登陆admin页的bug
        return current_user.is_authenticated and current_user.type == 2

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for("admin_login"))


# 管理员主页视图
class MyAdminIndexView(AdminIndexView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.type == 2

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for("admin_login"))


# 管理员登陆
@app.route('/admin_login', methods=['GET'])
def admin_login():

    u_name = request.args.get("name")
    u_password = request.args.get("password")

    # 空参数则直接返回一个登录页
    if u_name == "" or u_password == "":
        return render_template('/admin/admin_login.html')

    u_type = 2
    u = User.query.filter_by(name=u_name, password=u_password, type=u_type).first()

    if u is not None:
        login_user(u)
        return redirect(url_for("admin.index"))    # 登陆完成，跳转管理员页面
    else:
        return render_template('/admin/admin_login.html')   # 密码错误也直接返回一个登陆页面，不做任何提示


# 管理员登出
@app.route('/admin_logout', methods=['GET'])
def admin_logout():
    logout_user()
    return redirect(url_for("admin_login"))


# 用户注册
@app.route('/api/register')
def register():
    u_name = request.args.get("u_name")
    u_password = request.args.get("u_password")
    u_type = 1          # 注册的用户默认都为普通用户，管理员用户只能亲自操作数据库添加，禁止注册成管理员

    success_dict = {
        "status": 1,
    }

    fail_dict = {
        "status": 0,
        "info": ""
    }

    # 参数检查， 空参数直接返回注册失败。虽然已经前端验证过了，但是为了安全这里必须再验证一遍
    if not u_name or not u_password:
        fail_dict["info"] = "用户名和密码都不能为空"
        return jsonify(fail_dict)

    # 首先检查同名用户是否存在，如果存在则直接返回一个值，告诉前端这个用户已经存在了
    u1 = User.query.filter_by(name=u_name).first()
    if u1:
        fail_dict["info"] = "存在同名用户，注册失败"
        return jsonify(fail_dict)

    # 同名用户不存在，插入新用户
    u = User(u_name, u_password, u_type)
    db.session.add(u)
    db.session.commit()
    return jsonify(success_dict)


# 用户登录
@app.route('/api/login_validation')
def login_validation():
    u_name = request.args.get("u_name")
    u_password = request.args.get("u_password")
    success_dict = {
        "status": 1
    }

    fail_ditc = {
        "status": 0,
        "info": ""
    }

    # 空参数则直接返回0
    if u_name == "" or u_password == "":
        fail_ditc["info"] = "用户名和密码都不能留空"
        return jsonify(fail_ditc)

    u1 = User.query.filter_by(name=u_name).first()  # 检索用户
    u = User.query.filter_by(name=u_name, password=u_password).first()  # 检索用户

    if not u1:
        fail_ditc["info"] = "用户不存在"
        return jsonify(fail_ditc)

    if not u and u1:
        fail_ditc["info"] = "密码不正确"
        return jsonify(fail_ditc)

    if u:
        login_user(u)
        return jsonify(success_dict)     # 登陆成功，返回1


# 用户登出
@app.route('/api/logout', methods=['GET'])
def logout():
    logout_user()
    return redirect(url_for("login_page"))


# 这里只是单纯起到web容器的作用，负责递交页面，验证逻辑有专门的接口：login_validation
@app.route('/login_page')
def login_page():
    return render_template("general/login_page.html")


# 这个不作为web函数之一，单独拆分出来有其特别意义
def cancel_one(idid, **kwargs):

    # 这里还是使用ORM来进行查询比较方便
    if kwargs.__contains__("ispayed"):
        b = Book.query.filter_by(id=idid, userid=current_user.id, iscancel=0, ispayed=kwargs["ispayed"]).first()
    else:
        b = Book.query.filter_by(id=idid, userid=current_user.id, iscancel=0, ).first()

    # 查不到就直接结束
    if not b:
        return

    b.iscancel = 1  # 执行update

    # 在操作表记录这个信息
    o = Operation()
    o.userid = current_user.id
    o.bookid = b.id
    o.type = 0
    o.cmtime = datetime.datetime.now()
    db.session.add(o)
    db.session.commit()


def cancel_all():

    # 当场不支付的人，只要随便刷新一次网页，他的订单就会被自己取消了
    sql2 = """
    select book.id from book
    where book.userid=1
    and book.ispayed=0
    and book.iscancel=0
    """

    res2 = list(db.session.execute(sql2))
    db.session.commit()

    cancel_list = [x[0] for x in res2]
    for x in cancel_list:
        cancel_one(x, ispayed=0)


# 首页，也是起到web容器的作用。不过还有额外加一层登陆验证。不登陆，连页面都无法递交。
# 不止静态文件，其他接口也进行登陆验证。可以尽可能避免接口风险
@app.route('/index_page')
@login_required
def index_page():
    print(current_user.name)
    cancel_all()
    return render_template("general/index_page.html")


# 当前场地使用状况总览
@app.route('/api/summary')
def summary():
    success_dict = {
        "status": 1
    }

    sql1 = "select type, count(*) from field group by type"
    res1 = list(db.session.execute(sql1))

    mytime = request.args.get("time")

    if mytime == "":
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
        """.format(mytime, mytime)

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

    success_dict["info_dict"] = temp_dict
    return jsonify(success_dict)


# 最新预定
@app.route('/api/latest')
def latest():
    success_dict = {
        "status": 1,
        "info_list": []
    }
    sql1 = """
    select user.name,book.cmtime,field.name,book.sttime,book.edtime
    from book, user, field
    where book.userid=user.id 
    and book.fieldid=field.id
    and book.iscancel=0
    and book.ispayed=1
    order by book.cmtime desc limit 3
    """
    res1 = list(db.session.execute(sql1))

    temp_list = []
    for x in res1:
        temp_dict = {
            "username": x[0],
            "cmtime": x[1][:19],
            "fieldname": x[2],
            "sttime": x[3][:19],
            "edtime": x[4][:19],
        }
        temp_list.append(temp_dict)
    success_dict["info_list"] = temp_list
    return jsonify(success_dict)


# 场地查询
@app.route('/api/field_info')
def field_info():
    success_ditc = {
        "status": 1,
        "info_dict": None
    }
    sql2 = """
    select * from field 
    """
    res2 = list(db.session.execute(sql2))
    temp_dict = dict()

    for x in res2:
        if x[1] not in temp_dict:
            temp_dict[x[1]] = []
        temp_dict[x[1]].append(list(x))

    success_ditc["info_dict"] = temp_dict
    return jsonify(success_ditc)


@app.route('/api/field_use')
def field_use():
    idid = request.args.get("idid")
    success_dict = {
        "status": 1,
        "info_list": []
    }

    # 查询该场地有没有被占用
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
    temp_list = [list(x) for x in res1]

    # 在这里处理一下时间，进行截断操作，否则将会有很长的小数点影响观看
    for x in temp_list:
        x[2] = x[2][:19]
        x[3] = x[3][:19]
        x[4] = x[4][:19]
    # print(temp_list)

    success_dict["info_list"] = temp_list
    return jsonify(success_dict)


@app.route('/api/bookit', methods=['GET'])
def bookit():
    idid = request.args.get("idid")
    ed = request.args.get("ed")
    st = request.args.get("st")

    # 准备两个字典，一个成功字典，一个失败字典
    dict_success = {
        "status": 1,
        "hours": 0,
        "totalprice": 0.0,
        "bookid": 0
    }

    dict_fail = {
        "status": 0,
        "info": ""
    }

    # 空参数直接返回失败
    if not st:
        dict_fail["info"] = "起始时间不能为空"
        return jsonify(dict_fail)
    if not ed:
        dict_fail["info"] = "结束时间不能为空"
        return jsonify(dict_fail)

    ed = ed.replace("%20", " ")
    st = st.replace("%20", " ")

    # 任意时间小于现在，也返回失败
    if time.strptime(st, "%Y-%m-%d %X") < time.localtime():
        dict_fail["info"] = "起始时间不能小于现在"
        return jsonify(dict_fail)
    if time.strptime(ed, "%Y-%m-%d %X") < time.localtime():
        dict_fail["info"] = "结束时间不能小于现在"
        return jsonify(dict_fail)

    # 这个SQL语句极易写错
    # 这里我分为三种情况，1：起始点落在时间段内， 2：终止点落在时间段内， 3：起始、终点区间完全涵盖这个时间段
    # 三个条件满足其一则说明有时间冲突
    sql1 = """
    select * from book 
    where book.fieldid={}
    and book.iscancel=0
    and book.ispayed=1
    and ( 
            (book.sttime>'{}' and book.sttime<'{}')
         or (book.edtime>'{}' and book.edtime<'{}') 
         or (book.sttime<'{}' and book.edtime>'{}')
        )
    """.format(idid, st, ed, st, ed, st, ed)
    res1 = list(db.session.execute(sql1))

    if not res1:
        # 将订单写入数据库，同时保留备份到操作表
        b = Book()
        b.sttime = datetime.datetime.strptime(st, "%Y-%m-%d %X")
        b.edtime = datetime.datetime.strptime(ed, "%Y-%m-%d %X")
        b.userid = current_user.id
        b.fieldid = idid
        b.iscancel = 0
        b.cmtime = datetime.datetime.now()
        b.ispayed = 0
        db.session.add(b)
        db.session.commit()

        o = Operation()
        o.userid = current_user.id
        o.bookid = b.id
        o.type = 1
        o.cmtime = datetime.datetime.now()
        db.session.add(o)
        db.session.commit()

        f = Field.query.get(idid)  # 获取一个场地对象，计算价格的时候需要用到单价

        # 计算小时数量，按照单价*小时数量进行收费
        delta = b.edtime - b.sttime
        hours = round(delta.seconds/3600.0)
        dict_success["hours"] = hours
        dict_success["bookid"] = b.id
        dict_success["totalprice"] = hours*f.price
        return jsonify(dict_success)

    else:
        dict_fail["info"] = "与别人的预定有时间冲突，请另外选择时间段"
        return jsonify(dict_fail)


@app.route("/api/pay")
def pay():
    idid = request.args.get("idid")

    success_dict = {
        "status": 1
    }

    b = Book.query.get(idid)
    if b.ispayed == 0:
        b.ispayed = 1
        o = Operation()
        o.userid = current_user.id
        o.type = 2
        o.bookid = b.id
        o.cmtime = datetime.datetime.now()
        db.session.add(o)
    db.session.commit()
    return jsonify(success_dict)


@app.route('/api/get_field_name')
def get_field_name():

    success_dict = {
        "status": 1,
        "name": ""
    }

    fail_dict = {
        "status": 0,
        "info": ""
    }
    idid = request.args.get("idid")

    res = Field.query.filter_by(id=idid).first()
    # print(res)
    if res:
        success_dict["name"] = res.name
        return jsonify(success_dict)
    else:
        fail_dict["info"] = "获取失败，场地id不存在"
        return jsonify(fail_dict)


@app.route('/api/news_list')
def news_list():
    success_dict = {
        "status": 0,
        "info_list": []
    }

    t_list = []
    ns = News.query.order_by(News.id.desc()).all()
    # 单单只是列表而已，有必要进行截断操作
    for x in ns:
        temp_list = list()
        temp_list.append(x.id)
        temp_list.append(x.title)
        if len(x.content) >= 100:
            temp_list.append(x.content[:100] + "......")
        else:
            temp_list.append(x.content)
        t_list.append(temp_list)

    success_dict["info_list"] = t_list
    return jsonify(success_dict)


@app.route('/api/news_detail')
def news_detail():
    idid = request.args.get("idid")

    success_dict = {
        "status": 0,
        "idid": "",
        "title": "",
        "content": ""
    }

    fail_dict = {
        "status": 0,
        "info": ""
    }

    # 在系统中正常使用永远不会执行这条语句，但是如果强行访问接口就会触发这个条件
    if not idid:
        fail_dict["info"] = "获取失败，新闻id不能为空"
        return jsonify(fail_dict)

    n = News.query.get(idid)
    success_dict["idid"] = n.id
    success_dict["title"] = n.title
    success_dict["content"] = n.content

    return jsonify(success_dict)


@app.route('/api/user_book_list')
@login_required
def user_book_list():
    success_dict = {
        "status": 1,
        "info_list": []
    }

    idid = current_user.id
    # 已经失效的订单就不要查询了，必须要是有效订单才进行查询（未取消，时间尚未失效）
    sql1 = """
    select book.id,field.name,book.sttime,book.edtime,book.cmtime 
    from book,field
    where field.id=book.fieldid
    and book.userid={}
    and book.edtime>datetime('now', 'localtime') 
    and book.iscancel=0
    order by book.cmtime desc
    """.format(idid)
    res1 = list(db.session.execute(sql1))
    res1 = [list(x) for x in res1]
    # 截断时间
    for x in res1:
        x[2] = x[2][:19]
        x[3] = x[3][:19]
        x[4] = x[4][:19]
    success_dict["info_list"] = res1
    return jsonify(success_dict)


@app.route('/api/cancel')
def cancel():
    success_dict = {
        "status": 1
    }
    idid = request.args.get("idid")
    cancel_one(idid)

    return jsonify(success_dict)


@app.route('/api/user_get_profile')
def user_get_profile():
    u_name = current_user.name
    success_dict = {
        "status": 1
    }

    success_dict["name"] = u_name
    return jsonify(success_dict)


@app.route('/api/user_change_profile')
def user_change_profile():
    u_name = request.args.get("u_name")
    u_password = request.args.get("u_password")
    success_dict = {
        "status": 1
    }

    fail_dict = {
        "status": 0,
        "info": ""
    }

    # 空参数直接返回失败
    if not u_name or not u_password:
        fail_dict["info"] = "存在空参数"
        return jsonify(fail_dict)

    # 查询一下用户看看有没有重名的，重名直接返回失败
    temp_u = User.query.filter_by(name=u_name).first()
    if not temp_u:
        if temp_u.id != current_user.id
            fail_dict["info"] = "你想要的新用户名已经被其他用户占用"
            return jsonify(fail_dict)

    u = User.query.get(current_user.id)
    u.name = u_name
    u.password = u_password
    db.session.commit()

    # 改完用户信息之后进行一次登出操作
    logout_user()
    return jsonify(success_dict)


@app.route('/api/last_operation')
def last_operation():
    success_dict = {
        "status": 1,
        "info_list": []
    }
    idid = current_user.id

    # 这个查询过于复杂，不适合使用ORM
    sql1 = """
    select operation.cmtime,operation.type,field.name,book.sttime,book.edtime,book.id
    from book,operation,field
    where book.id=operation.bookid
    and field.id=book.fieldid
    and operation.userid={}
    order by operation.cmtime desc
    limit 20
    """.format(idid)

    res1 = list(db.session.execute(sql1))
    # res1 = [list(x) for x in res1]
    temp_list = []
    for x in res1:
        temp_dict = {
            "cmtime": x[0][:19],
            "type": x[1],
            "name": x[2],
            "sttime": x[3][:19],
            "edtime": x[4][:19],
            "idid": x[5]
        }
        temp_list.append(temp_dict)
    success_dict["info_list"] = temp_list
    return jsonify(success_dict)


if __name__ == '__main__':

    # 管理员视图
    admin = Admin(app, name="后台管理", index_view=MyAdminIndexView())

    # 将几个数据库表分别添加
    admin.add_view(MyModelView(User, db.session))
    admin.add_view(MyModelView(Book, db.session))
    admin.add_view(MyModelView(Field, db.session))
    admin.add_view(MyModelView(News, db.session))
    admin.add_view(MyModelView(Operation, db.session))


    app.run(host='0.0.0.0', port=80)


