from datetime import datetime
from enum import Enum, auto
import sqlite3
import json
from email_validator import validate_email, EmailNotValidError


########################################
############Data Modeling###############
########################################
class User:
    def __init__(
            self,
            user_id: int,
            name: str,
            email: str,
            password: str,
            mobile_number: int,
            last_used_at: datetime,
            location: set[str]
    ):
        self.email = email
        self.password = password
        self.id = user_id
        self.name = name
        self.mobile_number = mobile_number
        self.last_used_at = last_used_at
        self.location = location


class Restaurant:
    def __init__(
            self,
            restaurant_id: int,
            name: str,
            location: set[str],
            num_of_bags: int,
            remaining_bags: int,
            overall_rating: float,
            opening_time: datetime,
            closing_time: datetime
    ):
        self.id = restaurant_id
        self.name = name
        self.location = location
        self.num_of_bags = num_of_bags
        self.remaining_bags = remaining_bags
        self.overall_rating = overall_rating
        self.opening_time = opening_time
        self.closing_time = closing_time


class PurchaseStatus(Enum):
    RESERVED = auto()
    CANCELED = auto()
    COMPLETED = auto()


class PurchaseOrder:
    def __init__(self,
                 purchase_order_id: int,
                 user_id: int,
                 location: str,
                 restaurant_id: int,
                 num_of_bags: int,
                 ordered_at: datetime,
                 status: PurchaseStatus):
        self.id = purchase_order_id
        self.user_id = user_id
        self.location = location
        self.restaurant_id = restaurant_id
        self.num_of_bags = num_of_bags
        self.ordered_at = ordered_at
        self.status = status


class UserRating:
    def __init__(
            self,
            id: int,
            user_id: int,
            restaurant_id: int,
            rating: float
    ):
        self.id = id
        self.user_id = user_id
        self.restaurant_id = restaurant_id
        self.rating = rating


##############################################
##############################################
##############################################

def initialize_db():
    conn = sqlite3.connect('app_backend.db')
    cursor = conn.cursor()

    # Create User table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS USER (
    USER_ID INTEGER PRIMARY KEY AUTOINCREMENT,
    NAME TEXT NOT NULL,
    EMAIL TEXT NOT NULL,
    PASSWORD TEXT NOT NULL,
    MOBILE_NUMBER INTEGER NOT NULL,
    LAST_USED_AT TIMESTAMP NOT NULL,
    LOCATION TEXT)
    """)

    # Create Restaurant table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS RESTAURANT (
    RESTAURANT_ID INTEGER NOT NULL,
    NAME TEXT NOT NULL,
    LOCATION TEXT NOT NULL,
    NUM_OF_BAGS INTEGER NOT NULL,
    REMAINING_BAGS INTEGER NOT NULL,
    OVERALL_RATING FLOAT,
    OPENING_TIME TIMESTAMP NOT NULL,
    CLOSING_TIME TIMESTAMP NOT NULL)
    """)

    # Create Purchase order table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS PURCHASE_ORDER (
    PURCHASE_ORDER_ID INTEGER NOT NULL,
    USER_ID INTEGER NOT NULL,
    RESTAURANT_ID INTEGER NOT NULL,
    NUM_OF_BAGS INTEGER NOT NULL,
    LOCATION TEXT NOT NULL,
    ORDERD_AT TIMESTAMP NOT NULL,
    STATUS INTEGER NOT NULL)
    """)

    # Create User Rating table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS USER_RATING (
    ID INTEGER NOT NULL,
    USER_ID INTEGER NOT NULL,
    RESTAURANT_ID INTEGER NOT NULL,
    RATING FLOAT NOT NULL)
    """)
    return cursor


simplex_rating_threshold = 2.5
default_num_of_restaurants = 5


def map_user(user_row: tuple):
    print("user-row ", user_row)
    return User(
        user_row[0],
        user_row[1],
        user_row[2],
        user_row[3],
        user_row[4],
        user_row[5],
        set(json.loads(user_row[6])) if user_row[6] else set()
    )


def map_restaurants(restaurant_rows: tuple):
    restaurants = []
    for restaurant_row in restaurant_rows:
        restaurant_object = Restaurant(
            restaurant_row[0],
            restaurant_row[1],
            set(json.loads(restaurant_row[2])) if restaurant_row[2] else set(),
            restaurant_row[3],
            restaurant_row[4],
            restaurant_row[5],
            restaurant_row[6],
            restaurant_row[7]
        )
        restaurants.append(restaurant_object)
    return restaurants


class RestaurantResponse:
    def __init__(self,
                 name: str,
                 num_of_bags: int):
        self.name = name
        self.num_of_bags = num_of_bags

    def to_api(self) -> dict:
        return {
            "name": self.name,
            "num_of_bags": self.num_of_bags
        }


def validate_inputs(cursor, data: dict, required_fields: list):
    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")

    if "numberOfBags" in data and data["numberOfBags"] <= 0:
        raise ValueError("numberOfBags must be > 0")

    # check if this statement makes sense
    restaurants = map_restaurants(cursor.execute("SELECT * FROM RESTAURANT").fetchall())
    restaurant = next((r for r in restaurants if "restaurantId" in data and r.id == data["restaurantId"]), None)
    if restaurant is None and "restaurantId" in data:
        raise ValueError(f"Restaurant '{data['restaurantId']}' not found")

    try:
        if "email" in data:
            validate_email(data["email"])
    except EmailNotValidError as error:
        raise ValueError(f"Email '{data['email']}' is not a valid email")


def add_customer_location_if_not_exists(cursor, location: str, customer_locations: set[str], user_id: int):
    if customer_locations is None:
        customer_locations = set()
    if location not in customer_locations:
        customer_locations.add(location)
        cursor.execute("""
        UPDATE USER SET LOCATION = ? WHERE USER_ID = ?
        """, (json.dumps(list(customer_locations)), user_id,))
        cursor.connection.commit()


def get_user(cursor, email: str):
    return map_user(cursor.execute("SELECT * FROM USER WHERE EMAIL = ?", (email,)).fetchone())


def simplex_strategy(location, cursor):
    restaurants = map_restaurants(cursor.execute("SELECT * FROM RESTAURANT").fetchall())
    customer_restaurants = [r for r in restaurants if
                            r.location == location and r.overall_rating >= simplex_rating_threshold]
    response = list()
    for restaurant in customer_restaurants:
        restaurant_response = RestaurantResponse(restaurant.name, restaurant.remaining_bags)
        response.append(restaurant_response.to_api())
    return response


def customer_inquiry(cursor, input_data):
    validate_inputs(cursor, input_data, ["email", "location", "selectionStrategy"])
    email = input_data["email"]
    location = input_data["location"]
    user = get_user(cursor, email)
    print(user)
    if user is None:
        raise ValueError(f"User '{email}' not subscribed")
    add_customer_location_if_not_exists(cursor, location, user.location, user.id)
    match input_data["selectionStrategy"]:
        case "simplex":
            return simplex_strategy(location, cursor)
        case "Kareem":
            return None
        case "Omar":
            return None
        case "Bassel":
            return None
        case "Farah":
            return None
        case _:
            return None


def customer_inquiry_api(input_data):
    cursor = initialize_db()
    try:
        response = customer_inquiry(cursor, input_data)
    finally:
        cursor.connection.close()
    return response


if __name__ == "__main__":
    input_data = {
        "email": "hank@gmail.com",
        "location": "CAIRO",
        "selectionStrategy": "simplex"
    }
    cursor = initialize_db()
    cursor.execute("DELETE FROM RESTAURANT")
    cursor.execute("DELETE FROM USER")
    cursor.connection.commit()

    cursor.execute("""
    INSERT INTO USER (EMAIL, NAME, PASSWORD, MOBILE_NUMBER, LAST_USED_AT)
    VALUES (?, ?, ?, ?, ?)
    """, (input_data["email"], "hank", "hank", 11111111, datetime.now()))
    restaurants = [
        (
            1,
            'Pizza Palace',
            '["CAIRO", "ALEXANDRIA"]',
            40,
            12,
            4.6,
            '2025-01-01T10:00:00',
            '2025-01-01T22:00:00'
        ),
        (
            2,
            'Sushi Central',
            '["CAIRO"]',
            30,
            5,
            4.8,
            '2025-01-01T11:00:00',
            '2025-01-01T21:00:00'
        ),
        (
            3,
            'Taco Fiesta',
            '["SUEZ"]',
            50,
            20,
            4.4,
            '2025-01-01T09:30:00',
            '2025-01-01T23:00:00'
        ),
        (
            4,
            'Burger Haven',
            '["SUEZ"]',
            25,
            8,
            4.2,
            '2025-01-01T10:00:00',
            '2025-01-01T20:00:00'
        ),
        (
            5,
            'Vegan Delight',
            '["SUEZ"]',
            35,
            15,
            4.7,
            '2025-01-01T08:00:00',
            '2025-01-01T22:00:00'
        )
    ]

    cursor.executemany(
        """
        INSERT INTO restaurant (
            restaurant_id, name, location, num_of_bags, remaining_bags,
            overall_rating, opening_time, closing_time
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        restaurants
    )
    cursor.connection.commit()
    cursor.execute("""
    select * from USER
    """).fetchall()
    print(customer_inquiry_api(input_data))
