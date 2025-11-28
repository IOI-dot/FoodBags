import uuid #Ids
restaurants = {
    "r1": {"remaining_bags": 10},
    "r2": {"remaining_bags": 5},
}
customer_locations = set()
purchase_orders = {}
def validate_inputs(data: dict, required_fields: list):
    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")

    if "numberOfBags" in data and data["numberOfBags"] <= 0:
        raise ValueError("numberOfBags must be > 0")

    if "restaurantId" in data and data["restaurantId"] not in restaurants:
        raise ValueError(f"Restaurant '{data['restaurantId']}' not found")

#Helper Functions
def add_customer_location_if_not_exists(location: str):
    if location not in customer_locations:
        customer_locations.add(location)
def update_restaurant_remaining_bags(restaurant_id: str, change: int):
    remaining = restaurants[restaurant_id]["remaining_bags"] + change
    if remaining < 0:
        raise ValueError("Not enough remaining bags at restaurant")

    restaurants[restaurant_id]["remaining_bags"] = remaining

def store_customer_purchase_order(order: dict):
    purchase_id = str(uuid.uuid4()) #Random value for now
    purchase_orders[purchase_id] = order
    return purchase_id

def send_cancellation_to_customers(restaurant_id: str):
    print(f"Restaurant '{restaurant_id}' canceled")
def update_purchase_order(order_id: str):
    if order_id not in purchase_orders:
        raise ValueError("Purchase order not found")
    purchase_orders[order_id]["status"] = "cancelled"
    return purchase_orders[order_id]

#Main Functions
def customer_purchase(input_data: dict):
    validate_inputs(input_data, ["restaurantId", "numberOfBags", "emailOrPhone", "location"])
    add_customer_location_if_not_exists(input_data["location"])
    update_restaurant_remaining_bags(input_data["restaurantId"], -input_data["numberOfBags"])

    order = {
        "restaurantId": input_data["restaurantId"],
        "bags": input_data["numberOfBags"],
        "emailOrPhone": input_data["emailOrPhone"],
        "location": input_data["location"],
        "status": "active",
    }
    purchase_id = store_customer_purchase_order(order)

    return {
        "message": "Purchase successful",
        "purchaseOrderId": purchase_id,
        "remainingBags": restaurants[input_data["restaurantId"]]["remaining_bags"],
    }


def restaurant_cancel(input_data: dict):
    validate_inputs(input_data, ["restaurantId", "numberOfBags"])
    send_cancellation_to_customers(input_data["restaurantId"])
    update_restaurant_remaining_bags(input_data["restaurantId"], input_data["numberOfBags"])

    return {
        "message": "Restaurant cancellation processed",
        "remainingBags": restaurants[input_data["restaurantId"]]["remaining_bags"],
    }


def customer_cancel(input_data: dict):
    validate_inputs(input_data, ["purchaseOrderId", "emailOrPhone"])
    order = update_purchase_order(input_data["purchaseOrderId"])
    update_restaurant_remaining_bags(order["restaurantId"], order["bags"])

    return {
        "message": "Customer cancellation processed",
        "remainingBags": restaurants[order["restaurantId"]]["remaining_bags"],
    }


if __name__ == "__main__":
    print("Initial restaurant state:", restaurants)
    purchase_result = customer_purchase({
        "restaurantId": "r1",
        "numberOfBags": 3,
        "emailOrPhone": "hank@example.com",
        "location": "Downtown"
    })
    print("Customer Purchase Result:")
    print(purchase_result)
    print("Restaurants after purchase:", restaurants)
    print("Purchase Orders:", purchase_orders)
    # Save the purchase ID for later cancellation
    pid = purchase_result["purchaseOrderId"]
    cancel_result = customer_cancel({
        "purchaseOrderId": pid,
        "emailOrPhone": "hank@example.com"
    })
    print("Customer Cancellation Result:")
    print(cancel_result)
    print("Restaurants after customer cancel:", restaurants)
    print("Purchase Orders:", purchase_orders)
    restaurant_cancel_result = restaurant_cancel({
        "restaurantId": "r2",
        "numberOfBags": 2
    })
    print("Restaurant Cancellation Result:")
    print(restaurant_cancel_result)
    print("Restaurants after restaurant cancel:", restaurants)

