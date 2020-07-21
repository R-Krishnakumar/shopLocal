import os, sys

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, timedelta
from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
#app.jinja_env.filters["usd"] = usd
#app.jinja_env.globals.update(usd=usd)
#app.jinja_env.globals.update(lookup=lookup)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///project.db")

# Make sure API key is set
#if not os.environ.get("API_KEY"):
#    raise RuntimeError("API_KEY not set")


@app.route("/homepage", methods=["GET", "POST"])
@login_required
def homepage():
        rows = db.execute("SELECT * FROM products")
        credit_limit = db.execute("SELECT * FROM users WHERE user_id = :user_id", user_id=session["user_id"])[0]["credit_limit"]
        return render_template("homepage.html", rows=rows, username=session['username'], credit_limit=credit_limit)


@app.route("/order/<product_id>", methods=["GET", "POST"])
@login_required
def order(product_id):
    if request.method=="GET":
        # print('Hello world!!!')
        # print(product_id)
        row = db.execute("SELECT * FROM products WHERE product_id=?", product_id)
        product_name=row[0]["product_name"]
        unit = row[0]["unit"]
        unit_cost = row[0]["unit_cost"]
        return render_template("order.html", product_name = product_name, unit=unit, unit_cost=unit_cost)


@app.route("/cart", methods=["GET", "POST"])
@login_required
def cart():
    if request.method=="POST" and not request.form.get("delete_product")==None:
        transaction_id=request.form.get("delete_product")
        db.execute("DELETE FROM cart WHERE transaction_id=:transaction_id", transaction_id=transaction_id)
        return cartload()
    elif request.method=="POST" :
        product_name=request.form.get("product_name")
        unit=request.form.get("unit")
        unit_cost=float(request.form.get("unit_cost"))
        quantity=float(request.form.get("quantity"))
        value = quantity * unit_cost
        if request.form.get("user_ids") != "":
            user_ids = session["user_id"]
        if len(db.execute("SELECT * from cart WHERE product_name=:product_name AND user_id=:user_id", product_name=product_name, user_id=session["user_id"]))==0:
            db.execute("INSERT INTO cart (product_name, unit, unit_cost, quantity, value, user_id) VALUES (:product_name, :unit, :unit_cost, :quantity, :value, :user_id)", product_name = product_name, unit = unit, unit_cost=unit_cost, quantity=quantity, value=value, user_id=user_ids)
        else:
            db.execute("UPDATE cart SET quantity = :quantit, value=:valu WHERE product_name=:product_nam AND user_id=:user_id", quantit=quantity+db.execute("SELECT * from cart WHERE product_name=:product_name", product_name=product_name)[0]["quantity"], valu=value+db.execute("SELECT * from cart WHERE product_name=:product_name", product_name=product_name)[0]["value"],product_nam=product_name, user_id=user_ids)
        return cartload()
    elif request.method=="GET":
        return cartload()

@app.route("/history", methods=["GET", "POST"])
@login_required
def history():
    # if session["user_id"]==3:
    #     rows = db.execute("SELECT * FROM transactions")
    #     products=db.execute("SELECT * FROM products")
    #     total_value=0
    #     for row in rows:
    #         user_id=row["user_id"]
    #         row["user_name"] = db.execute("SELECT * FROM users WHERE user_id=:user_id", user_id=user_id)[0]["username"]
    #         total_value += row["value"]
    #     return render_template("history.html", rows=rows, products=products, total_value=total_value)
    # else:
        products=db.execute("SELECT * FROM products")
        users=db.execute("SELECT * FROM users")
        message=""
        if request.method == "GET":
            if session["user_id"]==3:
                rows = db.execute("SELECT * FROM transactions ORDER BY date DESC")
            else:
                rows = db.execute("SELECT * FROM transactions WHERE user_id =:user_id  ORDER BY date DESC", user_id=session["user_id"])
        else:
            if not request.form.get("product"):
                product_name = "x"
            else:
                product_name=request.form.get("product")
            if not request.form.get("from"):
                from_date = datetime.strptime('2020-06-01', '%Y-%m-%d')
            else:
               from_date = datetime.strptime(request.form.get('from'), '%Y-%m-%d') - timedelta(days=1)
            if not request.form.get("to"):
                to_date = datetime.today()
            else:
               to_date = datetime.strptime(request.form.get('to'), '%Y-%m-%d')
            if session["user_id"]==3:
                if not request.form.get("user"):
                    user_id = "y"
                else:
                    user_id=request.form.get("user")
                rows = db.execute("SELECT * FROM transactions WHERE (product_name=:product_name OR :product_name ='x') AND date>=:from_date AND date<=:to_date AND (user_id=:user_id OR :user_id='y')  ORDER BY date DESC", product_name=product_name, from_date=from_date, to_date=to_date, user_id=user_id)
            else:
                print(request.form.get("user"), session["user_id"])
                if not request.form.get("user") or request.form.get("user")==str(session["user_id"]):
                    message=""
                else:
                    message="You are only allowed to see your own data"

                rows = db.execute("SELECT * FROM transactions WHERE (product_name=:product_name OR :product_name ='x') AND date>=:from_date AND date<=:to_date AND user_id=:user_id  ORDER BY date DESC", product_name=product_name, from_date=from_date, to_date=to_date, user_id=session["user_id"] )
        total_value=0
        for row in rows:
            total_value += row["value"]
            user_id=row["user_id"]
            row["user_name"] = db.execute("SELECT * FROM users WHERE user_id=:user_id", user_id=user_id)[0]["username"]
        return render_template("history.html", rows=rows, products=products, users=users, total_value=total_value, user_name=session["username"], message=message)

@app.route("/orderbook", methods=["GET", "POST"])
@login_required
def orderbook():
    if request.method == "GET":
        rows = db.execute("SELECT * FROM transactions WHERE status = :status", status = "To be delivered")
        return render_template("orderbook.html", rows=rows)
    # elif request.form.get("for_address") !=None:
    #     address = "address"
    else:
        i = 1
        count = db.execute("SELECT COUNT(*) FROM transactions WHERE status =:status", status="To be delivered")[0]["COUNT(*)"]
        print(count)
        while (i <= count):
            print(request.form.get("status"+str(i)))
            if request.form.get("status"+str(i)) == "0":
                db.execute("UPDATE transactions SET status = :status WHERE transaction_id=:tran_id", status = "Delivered", tran_id = tran_id)
            i +=1
        rows = db.execute("SELECT * FROM transactions WHERE status = :status", status = "To be delivered")
        return render_template("orderbook.html", rows=rows)


@app.route("/order_book/<user_id>", methods=["GET", "POST"])
@login_required
def order_book(user_id):
    # if request.method=="GET":
    address = db.execute("SELECT * FROM users WHERE user_id=?", user_id)[0]["address"]
    user_name = db.execute("SELECT * FROM users WHERE user_id=?", user_id)[0]["username"]
    rows = db.execute("SELECT * FROM transactions WHERE status = :status", status = "To be delivered")
    return render_template("orderbook.html", rows = rows, address = address, user_name = user_name)

@app.route("/credit_limit", methods=["GET", "POST"])
@login_required
def credit_limit():
    if request.method == "GET":
        rows = db.execute("SELECT * FROM users")
        return render_template("credit_limit.html", rows=rows)
    else:
        i = 1
        count = db.execute("SELECT COUNT(*) FROM users")[0]["COUNT(*)"]
        print(count)
        while (i <= count):
            print(request.form.get("amount"+str(i)))
            if int(request.form.get("status"+str(i))) != 0:
                db.execute("UPDATE users SET credit_limit = credit_limit + :amount WHERE user_id=:user_id", amount = request.form.get("amount"+str(i)).value, user_id = request.form.get("user_id"+str(i)).value)
            i +=1
        rows = db.execute("SELECT * FROM users")
        return render_template("credit_limit.html", rows=rows)


@app.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    if session["user_id"] == 3:
        user_id = request.form.get("user_ids")
    else :
        user_id = session["user_id"]
    print(user_id)
    if float(request.form.get("total_value")) < db.execute("SELECT * FROM users WHERE user_id = :user_id", user_id = user_id)[0]["credit_limit"]:
        print(request.form.get("total_value"))
        x = (datetime.today()).strftime('%Y-%m-%d')
        rows = db.execute("SELECT * FROM cart")
        for row in rows:
            product_name = row["product_name"]
            unit = row["unit"]
            unit_cost = row["unit_cost"]
            quantity = row["quantity"]
            value=quantity * unit_cost
        db.execute("INSERT INTO transactions (product_name, unit, unit_cost, quantity, value, date, user_id, status) VALUES (:product_name, :unit, :unit_cost, :quantity, :value, :date, :user_id, :status)", product_name = product_name, unit = unit, unit_cost=unit_cost, quantity=quantity, value=value, date=x, user_id=user_id, status="To be delivered")
        total_value=db.execute("SELECT SUM(value) FROM cart")[0]["SUM(value)"]
        db.execute("DELETE FROM cart")
        db.execute("UPDATE users SET credit_limit = :credit_limit WHERE user_id=:user_id", user_id = user_id, credit_limit = db.execute("SELECT * FROM users WHERE user_id = :user_id", user_id = user_id)[0]["credit_limit"] - total_value)
        return homepage()
    else:
        message = "Please top up your wallet"
        rows = db.execute("SELECT * FROM cart")
        total_value=db.execute("SELECT SUM(value) FROM cart")[0]["SUM(value)"]
        return render_template("cart.html", rows = rows, total_value=total_value, message = message)


@app.route("/", methods=["GET", "POST"])
def login():
    session.clear()
    if request.method == "POST":
        if not request.form.get("username"):
            return render_template("login.html", message="must provide username")
        elif not request.form.get("password"):
            return render_template("login.html", message="must provide password")
        rows = db.execute("SELECT * FROM users WHERE username = :username",username=request.form.get("username"))
        if len(rows) != 1 or (rows[0]["password"]!=request.form.get("password")):
            return render_template("login.html", message="invalid username and/or password")
        session["user_id"] = rows[0]["user_id"]
        session["username"] = rows[0]["username"]
        return redirect("/homepage")
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method=="GET":
        return render_template("register.html")
    else:
        username = request.form.get("username")
        password1 = request.form.get("password1")
        password2 = request.form.get("password2")
        address = request.form.get("address")
    if not request.form.get("username"):
        return render_template("register.html", message="Need to give username")
    elif not request.form.get("password1"):
        return render_template("register.html", message = "Need to give password")
    elif (password1 != password2):
        return render_template("register.html", message = "Password do not match")
    elif len(db.execute("SELECT * FROM users WHERE username = :username",username=username)) != 0:
        return render_template("register.html", message="username already exists")
    else :
        db.execute("INSERT INTO users(username, password, address) VALUES(:username, :password, :address)", username = username, password= password1, address = address)
        return redirect("/")

def cartload():
    rows = db.execute("SELECT * FROM cart")
    total_value=db.execute("SELECT SUM(value) FROM cart")[0]["SUM(value)"]
    if len(rows)>0:
        return render_template("cart.html", rows = rows, total_value=total_value, user_id = session["user_id"])
    else:
        return homepage()


# import requests

# url = "https://covid-193.p.rapidapi.com/statistics"

# headers = {
#     'x-rapidapi-host': "covid-193.p.rapidapi.com",
#     'x-rapidapi-key': "e5558e0829mshfbb4d64a2b0a928p158550jsn91a941e7f664"
#     }

# response = requests.request("GET", url, headers=headers)
# print("hello")



# def errorhandler(e):
#     """Handle error"""
#     if not isinstance(e, HTTPException):
#         e = InternalServerError()
#     return apology(e.name, e.code)
# print(response.text)


# # Listen for errors
# for code in default_exceptions:
#     app.errorhandler(code)(errorhandler)

# # Check if positive integer
# def CheckInt(s):
#     try:
#         int(s)
#         return True
#     except ValueError:
#         return False
