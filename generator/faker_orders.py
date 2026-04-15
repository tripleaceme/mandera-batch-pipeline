"""Generates synthetic order records."""

import random
from datetime import datetime, timezone

from config.settings import ORDERS_MIN, ORDERS_MAX, REGIONS, PAYMENT_STATUSES

from config.data_quality import DATA_QUALITY_PROFILE
from generator.data_quality import introduce_order_issues


def generate(customer_ids, product_ids, batch_id):
    count = random.randint(ORDERS_MIN, ORDERS_MAX)
    orders = []

    config = DATA_QUALITY_PROFILE["orders"]

    for _ in range(count):
        order = {
            "order_id": f"ORD{random.randint(10000, 99999)}",
            "customer_id": random.choice(customer_ids),
            "product_id": random.choice(product_ids),
            "region": random.choice(REGIONS),
            "amount": random.randint(1000, 50000),
            "payment_status": random.choice(PAYMENT_STATUSES),
            "batch_id": batch_id,
            "created_at": datetime.now(timezone.utc),
        }

        order = introduce_order_issues(order, config)
        orders.append(order)

    return orders
    
# def generate(customer_ids: list[str], product_ids: list[str], batch_id: str) -> list[dict]:
#     """Generate 2000-5000 order documents referencing existing customers and products."""
#     count = random.randint(ORDERS_MIN, ORDERS_MAX)
#     orders = []

#     for _ in range(count):
#         orders.append({
#             "order_id": f"ORD{random.randint(10000, 99999)}",
#             "customer_id": random.choice(customer_ids),
#             "product_id": random.choice(product_ids),
#             "region": random.choice(REGIONS),
#             "amount": random.randint(1000, 50000),
#             "payment_status": random.choice(PAYMENT_STATUSES),
#             "batch_id": batch_id,
#             "created_at": datetime.now(timezone.utc),
#         })

#     return orders
