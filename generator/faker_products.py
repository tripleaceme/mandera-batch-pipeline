"""Generates synthetic product records."""

import random
from datetime import datetime, timezone

from config.settings import PRODUCTS_MIN, PRODUCTS_MAX, PRODUCT_CATEGORIES
from config.data_quality import DATA_QUALITY_PROFILE
from generator.data_quality import introduce_product_issues


def generate(batch_id: str) -> list[dict]:
    count = random.randint(PRODUCTS_MIN, PRODUCTS_MAX)
    products = []

    config = DATA_QUALITY_PROFILE["products"]

    all_categories = list(PRODUCT_CATEGORIES.keys())

    for _ in range(count):
        category = random.choice(all_categories)

        product = {
            "product_id": f"PROD{random.randint(1000, 9999)}",
            "product_name": random.choice(PRODUCT_CATEGORIES[category]),
            "category": category,
            "price": round(random.uniform(50, 15000), 2),
            "batch_id": batch_id,
            "created_at": datetime.now(timezone.utc),
        }

        product = introduce_product_issues(product, config, all_categories)
        products.append(product)

    return products
    
# def generate(batch_id: str) -> list[dict]:
#     """Generate 5-10 product documents."""
#     count = random.randint(PRODUCTS_MIN, PRODUCTS_MAX)
#     products = []

#     for _ in range(count):
#         category = random.choice(list(PRODUCT_CATEGORIES.keys()))
#         products.append({
#             "product_id": f"PROD{random.randint(1000, 9999)}",
#             "product_name": random.choice(PRODUCT_CATEGORIES[category]),
#             "category": category,
#             "price": round(random.uniform(50, 15000), 2),
#             "batch_id": batch_id,
#             "created_at": datetime.now(timezone.utc),
#         })

#     return products
