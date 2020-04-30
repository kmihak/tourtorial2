from flask import Flask, jsonify, request
from flask_restful import Api, Resource
from pymongo import MongoClient
import bcrypt

app = Flask(__name__)
api = Api(app)
client = MongoClient("mongodb://db:27017")

db = client.BankAPI
users = db["Users"]


def user_exist(username):
    if users.find_one({"Username": username}) is None:
        return False
    else:
        return True


def grd(status, msg):
    return {
        "status": status,
        "msg": msg
    }


def verify_password(username, password):
    if not user_exist(username):
        return False

    hashed_pw = users.find_one({"Username": username})["Password"]

    if bcrypt.hashpw(password.encode("utf-8"), hashed_pw) == hashed_pw:
        return True
    else:
        return False


def cash_with_user(username):
    return users.find_one({"Username": username})["Own"]


def debt_with_user(username):
    return users.find_one({"Username": username})["Debt"]


# The functions returns tuple: Error Dictionary, True/False
def verify_credentials(username, password):
    if not user_exist(username):
        return grd(301, "Invalid Username"), True

    correct_pw = verify_password(username, password)

    if not correct_pw:
        return grd(302, "Incorrect Password"), True

    return None, False


def update_account(username, balance):
    users.update_one({"Username": username}, {"$set": {"Own": balance}})


def update_debt(username, balance):
    users.update({"Username": username}, {"$set": {"Debt": balance}})


class Register(Resource):
    def post(self):

        posted_data = request.get_json()

        username = posted_data["username"]
        password = posted_data["password"]

        if user_exist(username):
            return jsonify(grd(301, "Invalid username, pick new username"))

        hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

        users.insert_one({
            "Username": username,
            "Password": hashed_pw,
            "Own": 0,
            "Debt": 0
        })

        return jsonify(grd(200, "You successfully signed up for API"))


class Add(Resource):
    def post(self):
        posted_data = request.get_json()

        username = posted_data["username"]
        password = posted_data["password"]
        money = posted_data["amount"]

        ret_json, error = verify_credentials(username, password)

        if error:
            return jsonify(ret_json)

        if money <= 0:
            return jsonify(grd(304, "The money amount is less than zero"))

        cash = cash_with_user(username)
        money -= 1
        bank_cash = cash_with_user("BANK")
        update_account("BANK", bank_cash + 1)
        update_account(username, money + cash)

        return jsonify(grd(200, "Amount added successfully to account"))


class Transfer(Resource):
    def post(self):
        posted_data = request.get_json()
        username = posted_data["username"]
        password = posted_data["password"]
        money = posted_data["amount"]
        to = posted_data["to"]


        ret_json, error =  verify_credentials(username, password)

        if error:
            return jsonify(ret_json)

        cash = cash_with_user(username)
        if cash <= 0:
            return jsonify(grd(304, "You are out  of money, please add more "
                                    "money"))

        if not user_exist(to):
            return jsonify(grd(301, "Receiver username is invalid"))

        cash_from = cash_with_user(username)
        cash_to = cash_with_user(to)
        bank_cash = cash_with_user("BANK")

        update_account("BANK", bank_cash + 1)
        update_account(to, cash_to + money)
        update_account(username, cash_from - money - 1)

        return jsonify(grd(200, "Amount transferred successfully"))


class Balance(Resource):
    def post(self):
        posted_data = request.get_json()

        username = posted_data["username"]
        password = posted_data["password"]

        ret_json, error = verify_credentials(username, password)

        if error:
            return jsonify(ret_json)

        ret_json = users.find_one({"Username": username},
                                  {"Password": 0, "_id": 0})

        return jsonify(ret_json)


class TakeLoan(Resource):
    def post(self):
        posted_data = request.get_json()

        username = posted_data["username"]
        password = posted_data["password"]

        money = posted_data["amount"]

        ret_json, error = verify_credentials(username, password)

        if error:
            return jsonify(ret_json)

        cash = cash_with_user(username)
        debt = debt_with_user(username)
        update_account(username, cash + money)
        update_debt(username, debt + money)

        return jsonify(grd(200, "Loan added to your account"))


class PayLoan(Resource):
    def post(self):
        posted_data = request.get_json()
        username = posted_data["username"]
        password = posted_data["password"]
        money = posted_data["amount"]

        ret_json, error = verify_credentials(username, password)
        cash = cash_with_user(username)

        if cash < money:
            return jsonify(grd(303, "Not enough cash in your account"))

        debt = debt_with_user(username)

        update_account(username, cash - money)
        update_debt(username, debt - money)

        return jsonify(grd(200, "You have successfully paid off your loan"))


api.add_resource(Register, '/register')
api.add_resource(Add, '/add')
api.add_resource(Transfer, '/transfer')
api.add_resource(Balance, '/balance')
api.add_resource(TakeLoan, '/takeloan')
api.add_resource(PayLoan, '/payloan')

if __name__ == '__main__':
    app.run(host='0.0.0.0')


