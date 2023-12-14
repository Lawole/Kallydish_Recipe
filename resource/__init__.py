from flask import Flask
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_sqlalchemy import SQLAlchemy
from flask_restx import Api
from flask_bcrypt import Bcrypt


app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://kally_user:YZV7XuuWXYmxClQubT9T4MLkdXoPkSQV@dpg-clt4uf8l5elc73dk3tb0-a.oregon-postgres.render.com/kally"
# /"postgresql://postgres:password@localhost:5432/kally"
# postgresql://kally_user:YZV7XuuWXYmxClQubT9T4MLkdXoPkSQV@dpg-clt4uf8l5elc73dk3tb0-a.oregon-postgres.render.com/kally
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config["SECRET_KEY"] = "EGGRO11$$123"
db = SQLAlchemy(app)
jwt = JWTManager(app)
migrate = Migrate(app, db)
bcrypt = Bcrypt(app)


from resource import models

api = Api(app, version="1.0", title="Food Valve", description="API for your KallyDish")

from resource.routes import user, dish


api.add_namespace(user)
api.add_namespace(dish)


with app.app_context():
    db.create_all()
