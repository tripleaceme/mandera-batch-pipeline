# generator/data_quality.py

import random

def safe_int(value):
    try:
        if value in ("NaN", None, "", "null"):
            return None
        return int(float(value))
    except (ValueError, TypeError):
        return None


def maybe(probability: float) -> bool:
    return random.random() < probability


def introduce_customer_issues(customer: dict, config: dict) -> dict:
    if maybe(config["missing_email_rate"]):
        customer["email"] = None

    if maybe(config["invalid_email_rate"]):
        customer["email"] = "invalid_email@@"

    if maybe(config["missing_city_rate"]):
        customer["city"] = ""

    return customer


def introduce_order_issues(order: dict, config: dict) -> dict:
    if maybe(config["missing_product_rate"]):
        order["product_id"] = None

    if maybe(config["invalid_amount_rate"]):
        order["amount"] = "NaN"

    if maybe(config["negative_amount_rate"]):
        amount = safe_int(order["amount"])

        if amount is None:
            return order["amount"]

        order["amount"] = -abs(amount)

    if maybe(config["invalid_status_rate"]):
        order["payment_status"] = "UNKNOWN_STATUS"

    return order



def introduce_product_issues(product: dict, config: dict, all_categories: list) -> dict:

    # Missing name
    if maybe(config["missing_name_rate"]):
        product["product_name"] = None

    # Invalid price (extreme values)
    if maybe(config["invalid_price_rate"]):
        product["price"] = round(random.uniform(100000, 999999), 2)

    # Zero price bug
    if maybe(config["zero_price_rate"]):
        product["price"] = 0

    # Category mismatch
    if maybe(config["category_mismatch_rate"]):
        product["category"] = random.choice(all_categories)

    # Schema drift
    if maybe(config["schema_drift_rate"]):
        product["brand"] = random.choice(["Nike", "Apple", "Samsung", "Sony", "Generic"])
        product["is_active"] = random.choice([True, False])

    return product
