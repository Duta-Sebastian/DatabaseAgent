from datetime import datetime, timedelta
from database.connection import SessionLocal, engine
import random

from database.models.order import Order
from database.models.order_item import OrderItem
from database.models.product import Product
from database.models.user import User


def create_sample_data():
    """Create sample data for testing the AI agent"""

    # Create a session
    db = SessionLocal()

    try:
        # Check if data already exists
        if db.query(User).count() > 0:
            print("Sample data already exists. Skipping seed.")
            return

        # Create sample users
        users = [
            User(name="John Doe", email="john@example.com", age=30),
            User(name="Jane Smith", email="jane@example.com", age=25),
            User(name="Bob Johnson", email="bob@example.com", age=35),
            User(name="Alice Wilson", email="alice@example.com", age=28),
            User(name="Charlie Brown", email="charlie@example.com", age=42),
        ]

        db.add_all(users)
        db.commit()

        # Create sample products
        products = [
            Product(name="Laptop", description="High-performance laptop", price=999.99, category="Electronics"),
            Product(name="Smartphone", description="Latest smartphone", price=699.99, category="Electronics"),
            Product(name="Coffee Mug", description="Ceramic coffee mug", price=12.99, category="Kitchen"),
            Product(name="Desk Chair", description="Ergonomic office chair", price=199.99, category="Furniture"),
            Product(name="Book", description="Programming guide", price=29.99, category="Books"),
            Product(name="Headphones", description="Noise-cancelling headphones", price=149.99, category="Electronics"),
            Product(name="Water Bottle", description="Stainless steel water bottle", price=19.99, category="Kitchen"),
            Product(name="Backpack", description="Travel backpack", price=79.99, category="Travel"),
        ]

        db.add_all(products)
        db.commit()

        # Create sample orders
        orders_data = [
            {"user_id": 1, "status": "completed", "days_ago": 5},
            {"user_id": 2, "status": "completed", "days_ago": 3},
            {"user_id": 1, "status": "pending", "days_ago": 1},
            {"user_id": 3, "status": "completed", "days_ago": 7},
            {"user_id": 4, "status": "completed", "days_ago": 2},
            {"user_id": 2, "status": "cancelled", "days_ago": 10},
            {"user_id": 5, "status": "pending", "days_ago": 0},
        ]

        orders = []
        for order_data in orders_data:
            created_date = datetime.now() - timedelta(days=order_data["days_ago"])
            order = Order(
                user_id=order_data["user_id"],
                total_amount=0,
                status=order_data["status"],
                created_at=created_date
            )
            orders.append(order)

        db.add_all(orders)
        db.commit()

        # Create order items and calculate totals
        order_items = []
        for i, order in enumerate(orders):
            # Add 1-3 random items to each order
            num_items = random.randint(1, 3)
            total = 0

            for _ in range(num_items):
                product = random.choice(products)
                quantity = random.randint(1, 2)
                price_per_item = product.price

                order_item = OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    quantity=quantity,
                    price_per_item=price_per_item
                )
                order_items.append(order_item)
                total += quantity * price_per_item

            # Update order total
            order.total_amount = round(total, 2)

        db.add_all(order_items)
        db.commit()

        print("Sample data created successfully!")
        print(f"Created {len(users)} users, {len(products)} products, {len(orders)} orders")

    except Exception as e:
        db.rollback()
        print(f"Error creating sample data: {e}")
        raise
    finally:
        db.close()


def clear_all_data():
    """Clear all data from the database"""
    db = SessionLocal()
    try:
        # Delete in order to respect foreign key constraints
        db.query(OrderItem).delete()
        db.query(Order).delete()
        db.query(Product).delete()
        db.query(User).delete()
        db.commit()
        print("All data cleared!")
    except Exception as e:
        db.rollback()
        print(f"Error clearing data: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    create_sample_data()