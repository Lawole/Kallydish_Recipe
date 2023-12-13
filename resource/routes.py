from flask import request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt, create_refresh_token
from flask_restx import Resource, Namespace, fields
from resource import db, bcrypt
from resource.models import Users, RevokeToken, DishView
from datetime import datetime
import base64
from flask import make_response

user = Namespace("user", description="Operations on users..")
dish = Namespace("dish", description="Operations regarding dishes..")

user_model = user.model('Users', {
    'id': fields.Integer(required=True, description='User id'),
    'firstname': fields.String(required=True, description='User first name'),
    'lastname': fields.String(required=True, description='User last name'),
    'email': fields.String(required=True, description='User email'),
    'password': fields.String(required=True, description='User password'),
    'phone': fields.String(required=True, description='User phone'),
})

user_login = user.model("UserLogin", {
    "email": fields.String(required=True, description="user email"),
    "password": fields.String(required=True, description="user password")
})

dish_model = dish.model('Dish', {
    'id': fields.Integer(required=True, description='Dish id'),
    'name': fields.String(required=True, description='Dish name'),
    'Instructions': fields.String(required=True, description='Dish instruction'),
    'Ingredients': fields.List(fields.String(description="Ingredient", required=True)),
    'date_posted': fields.DateTime(description="Date when the dish was posted")
})

dish_view_model = dish.model("DishView", {
    'id': fields.Integer(required=True, description='DishView id'),
    'name': fields.String(required=True, description='DishView name'),
    'Instructions': fields.String(required=True, description='Instruction'),
    'Ingredients': fields.List(fields.String(), required=True, description="Ingredient"),
    'date_posted': fields.DateTime(required=True, description="Date when the dish was viewed"),
    "dish_image_url": fields.String(required=True, description="Dish image"),
    "user_id": fields.Integer(required=True, description="user id"),
    "user_likes": fields.List(fields.Nested(user_model), required=True)
})


# >>>>>>>>>>> Endpoints for operations on user <<<<<<<<<<<<<<
@user.route('/register')
class Register(Resource):
    @user.doc(description="user registration")
    @user.expect(user_model, dish.parser().add_argument('X-Fields', location='headers', required=False),
                 validate=True)
    @user.response(200, "user created successfully")
    @user.response(400, "user with email address already exist")
    def post(self):
        data = request.get_json()
        firstname = data.get("firstname")
        lastname = data.get("lastname")
        email = data.get("email")
        password = data.get("password")
        phone = str(data.get("phone"))

        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

        email_exist = Users.query.filter_by(email=email).first()

        if email_exist:
            response = {
                "Error": "Email already exist..."
            }
            return jsonify(response)

        new_user = Users(firstname=firstname,
                         lastname=lastname,
                         email=email,
                         password=hashed_password,
                         phone=phone)

        db.session.add(new_user)
        db.session.commit()

        return {
            "message": "User created successfully...",
            "firstname": firstname,
            "lastname": lastname,
            "email": email,
            "phone": phone
        }, 200


def verify_user(email, password):
    """Function that verify each user login"""
    # Retrieve the user from the database based on the provided email
    user = Users.query.filter_by(email=email).first()

    if user and bcrypt.check_password_hash(user.password, password):
        return user.id

    return None


@user.route("/login")
class Login(Resource):
    @user.doc(description="Generate access token")
    @user.expect(user_login, validate=True)
    @user.response(200, "User successfully logged in", user_login)
    @user.response(400, "Invalid credentials")
    def post(self):
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        user_id = verify_user(email, password)
        if user_id:
            access_token = create_access_token(identity=user_id)
            refresh_token = create_refresh_token(identity=user_id)
            return {"access_token": access_token, "refresh_token": refresh_token}, 200

        return {"Message": "Invalid Credentials!"}, 401


@user.route("/welcome")
class Welcome(Resource):
    @jwt_required()
    def get(self):
        current_user = get_jwt_identity()
        return {"user_id": current_user}, 200


"""needs a valid refresh token. You might have obtained a refresh token by initially logging in and receiving both an 
access token and a refresh token. Use the obtained refresh token in the request's authorization or body to test the 
/refresh endpoint."""


@user.route("/refresh")
class RefreshToken(Resource):
    @jwt_required(refresh=True)
    @user.doc(description="Refresh token", security="jwt")
    @user.response(200, "access token generated")
    @user.response(400, "user not logged in")
    def post(self):
        current_user = get_jwt_identity()
        refresh_token = create_refresh_token(identity=current_user)

        return {"refresh_token": refresh_token}, 200


@user.route("/logout")
class Logout(Resource):
    @jwt_required(refresh=True)
    @user.doc(description="Logout user", security="jwt")
    def post(self):
        jti = get_jwt()["jti"]
        revoke_token = RevokeToken(jti=jti)

        db.session.add(revoke_token)
        db.session.commit()

        return {"message": "User successfully logged out!!"}, 200


# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

"""Creating a dish"""


@dish.route("")
class PostDishView(Resource):
    @jwt_required(refresh=True)
    @dish.expect(dish_model, validate=True)
    @dish.response(201, "Dish created successfully")
    @dish.response(400, "Bad request")
    @dish.doc(description="Creating a dish", security="jwt")
    def post(self):
        data = request.get_json()

        name = data.get("name")
        instructions = data.get("Instructions")
        ingredients = data.get("Ingredients")
        date_posted = datetime.utcnow()
        dish_image_url = data.get("dish_image_url")
        user_ids = data.get("user_likes", [])

        if not all([name, instructions, ingredients, dish_image_url]):
            return {"Error": "Missing some fields"}, 400

        try:
            image64 = base64.b64decode(dish_image_url)
        except Exception as e:
            return {"Error": "Invalid image data"}, 400

        new_dish = DishView(
            name=name,
            Instructions=instructions,
            Ingredients=ingredients,
            date_posted=date_posted,
            dish_image_url=image64,
            user_id=2
        )

        if image64:
            new_dish.dish_image_url = image64

        for user_id in user_ids:
            user = Users.query.get(user_id)
            if user:
                new_dish.user_likes.append(user)

                return {"Error": f"User with ID {user_id} not found!"}, 404

        try:
            db.session.add(new_dish)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return {f"Failed to create Dishview: {str(e)}"}, 500

        return jsonify(
            {
                "message": f"Dish successfully created for {user_ids}",
                "dish_view_id": new_dish.id
            }
        )


# Get all the dishes in the DishView table
@dish.route("/")
class GetDishView(Resource):
    @jwt_required(refresh=True)
    @dish.expect(dish.parser().add_argument('X-Fields', location='headers', required=False),
                 validate=True)
    @dish.response(200, "Success", dish_view_model)
    @dish.response(400, "Not found")
    @dish.doc(description="Get all dishes")
    def get(self):
        dishes = DishView.query.all()
        users = Users.query.all()

        recipe_list = []
        for dish in dishes:
            user_likes = []
            for user in users:
                if user in dish.user_likes:
                    user_data = {
                        "id": user.id,
                        "first_name": user.firstname,
                        "last_name": user.lastname,
                        "email": user.email,
                        "password": user.password,
                        "phone_number": user.phone
                    }
                    user_likes.append(user_data)

            recipe_data = {
                "id": dish.id,
                "name": dish.name,
                "instructions": dish.Instructions,
                "ingredients": dish.Ingredients,
                "date_posted": dish.date_posted.isoformat(),
                "user_likes": user_likes,
                "user_id": dish.user_id
            }
            recipe_list.append(recipe_data)

        response = {"recipes": recipe_list}
        return jsonify(response)


# uploading a dish image by dish_id
@dish.route("/image/<int:dish_id>/")
class UpdateDishImage(Resource):
    @jwt_required(refresh=True)
    @dish.response(201, "Imagae uploaded successfully")
    @dish.response(400, "Bad request")
    @dish.response(500, "Server error")
    @dish.doc(description="Uploading an image", security="jwt")
    def put(self, dish_id):
        data = request.get_json()
        dish = DishView.query.get(dish_id)

        if dish is None:
            return {"error": f"Dish with ID {dish_id} does not exist"}

        if "dish_image_data" in data:
            try:
                # Assuming 'dish_image_data' contains base64 encoded image data
                image_data = data["dish_image_data"]
                decoded_image = base64.b64decode(image_data)
                dish.dish_image_url = decoded_image
                db.session.commit()
                return {"message": f"Image updated for dish ID {dish_id}"}, 200
            except Exception as e:
                db.session.rollback()
                return {"error": str(e)}, 500
        else:
            return {"error": "No image data provided"}, 400


# Endpoint to view dish image by dish_id
@dish.route("/image/view/<int:dish_id>")
class ViewDishImage(Resource):
    @dish.response(201, "Image viewed successfully")
    @dish.response(404, "Not found")
    @dish.response(500, "Server error")
    def get(self, dish_id):
        dish = DishView.query.get(dish_id)

        if dish is None:
            return {"error": f"Dish with ID {dish_id} does not exist"}, 404

        dish_image = dish.dish_image_url

        if dish_image:
            encoded_image = base64.b64encode(dish_image).decode("utf-8")
            response = make_response(encoded_image)
            response.headers.set('Content-Type', 'image')  # Adjust the content type based on the image format
            return response

        return {"error": "No image found for this dish"}, 404


# Delete a dish image by dish_id
@dish.route("/image/delete/<int:dish_id>")
class DeleteDishImage(Resource):
    @dish.response(201, "Imagae deleted successfully")
    @dish.response(404, "Not found")
    @dish.response(500, "Server unavailable")
    @jwt_required(refresh=True)
    @dish.doc(description="Delete an image", security="jwt")
    def delete(self, dish_id):
        dish = DishView.query.get(dish_id)

        if dish is None:
            return {"error": f"Dish with ID {dish_id} does not exist"}, 404

        dish.dish_image_url = None
        # Assuming dish_image_url is a column holding image data
        # Delete the record from the database

        db.session.commit()

        return {"message": f"Image for dish ID {dish_id} deleted successfully"}, 200


# USER LIKES User likes dishes
@dish.route("/likes/<int:dish_id>")
class LikeDish(Resource):
    @jwt_required(refresh=True)
    @dish.doc(description="like a dish", security="jwt")
    @dish.response(201, "like successful")
    @dish.response(403, "Forbidden")
    @dish.response(404, "Not found")
    def post(self, dish_id):
        current_user_id = get_jwt_identity()

        user = Users.query.get(current_user_id)
        dish = DishView.query.get(dish_id)

        if not user or not dish:
            return {"Error": "User or dish not found!"}

        if user in user.liked_dishes:
            return {"Error": "User already liked the dish"}

        user.liked_dishes.append(dish)
        db.session.commit()

        return {"message": "Dish liked successful"}


# Get all the dishes by a particular user
@dish.route("/user/<int:user_id>")
class GetDishByUser(Resource):
    @jwt_required(refresh=True)
    @dish.expect(dish.parser().add_argument('X-Fields', location='headers', required=False),
                 validate=True)
    @dish.response(200, "Success", dish_view_model)
    @dish.response(400, "Not found")
    @dish.doc(description="User", security="jwt")
    def get(self, user_id):
        user = Users.query.get(user_id)
        if not user:
            return jsonify({"message": "User not found"}), 404

        user_dishes = DishView.query.filter_by(user_id=user_id).all()

        dish_list = []
        for dish in user_dishes:
            dish_data = {
                "id": dish.id,
                "name": dish.name,
                "instructions": dish.Instructions,
                "ingredients": dish.Ingredients,
                "date_posted": dish.date_posted.isoformat(),

            }
            dish_list.append(dish_data)

        response = {
            "user_id": user_id,
            "dishes": dish_list
        }
        return jsonify(response)


# updating a dish by dish_id
@dish.route("/<int:dish_id>")
class UpdateDish(Resource):
    @jwt_required(refresh=True)
    @dish.doc(description="Updating a dish", security="jwt")
    @dish.response(201, "dish updated successfully")
    @dish.response(403, "Forbidden")
    @dish.response(404, "Not found")
    def put(self, dish_id):
        data = request.get_json()
        dish = DishView.query.get(dish_id)

        if dish is None:
            return {"error": f"dish with dish_id {dish_id} does not exist! "}

        if "name" in data:
            dish.name = data["name"]
        if "instructions" in data:
            dish.instructions = data["Instructions"]
        if "ingredients" in data:
            dish.ingredients = data["Ingredients"]

        db.session.commit()

        return {"message": f"Dish updated for dish ID {dish_id} successfully!"}


# delete a dish by dish ID
@dish.route("/delete/<int:dish_id>")
class DeleteDish(Resource):
    @jwt_required(refresh=True)
    @dish.doc(description="Delete a dish", security="jwt")
    @dish.response(201, "Dish deleted successfully")
    @dish.response(403, "Forbidden")
    @dish.response(404, "Not found")
    def delete(self, dish_id):
        dish = DishView.query.get(dish_id)

        if dish:
            try:
                db.session.delete(dish)
                db.session.commit()
                return {"message": f"Dish with ID {dish_id} deleted successfully"}, 200
            except Exception as e:
                db.session.rollback()
                return {"error": str(e)}, 500
        else:
            return {"error": f"Dish with ID {dish_id} not found"}, 404


# get a single dish
@dish.route("/dishes/<int:dish_id>")
class GetSingleDish(Resource):
    @dish.response(201, "Success", dish_model)
    @dish.response(404, "Not found")
    @dish.doc(description="Get a particular dish")
    def get(self, dish_id):
        dish = DishView.query.get(dish_id)

        if dish:
            response = {
                "resource": {
                    "id": dish.id,
                    "name": dish.name,
                    "instructions": dish.Instructions,
                    "ingredients": dish.Ingredients,
                    "date_posted": dish.date_posted.isoformat()
                }
            }
            return response, 200
        else:
            return {"error": f"Dish with ID {dish_id} not found"}, 404

