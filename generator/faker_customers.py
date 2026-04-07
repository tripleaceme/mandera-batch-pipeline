"""Generates synthetic customer records."""

import random
from datetime import datetime, timezone

from faker import Faker

from config.settings import CUSTOMERS_MIN, CUSTOMERS_MAX

fake = Faker()


def generate(batch_id: str) -> list[dict]:
    """Generate 10-20 customer documents."""
    count = random.randint(CUSTOMERS_MIN, CUSTOMERS_MAX)
    customers = []

    for _ in range(count):
        customers.append({
            "customer_id": f"CUST{random.randint(10000, 99999)}",
            "name": fake.name(),
            "email": fake.email(),
            "phone": fake.phone_number(),
            "city": fake.city(),
            "batch_id": batch_id,
            "created_at": datetime.now(timezone.utc),
        })

    return customers
