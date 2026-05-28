"""Test script to verify database models work correctly."""
import sys
sys.path.insert(0, '.')

from app.database import SessionLocal, engine, init_db
from app.models import Order, OrderItem, PackagingType, ProductKnowledge


def test_order_item_relationship():
    """Test that Order -> OrderItem relationship works correctly."""
    # Create all tables
    init_db()

    db = SessionLocal()
    try:
        # Create an Order with two OrderItems
        order = Order(
            order_no="TEST-ORDER-001",
            customer_code="TEST-CUST-001",
            customer_name="Test Customer",
            salesperson="Test Salesperson"
        )
        db.add(order)
        db.flush()

        item1 = OrderItem(
            order_id=order.id,
            internal_code="SKU-001",
            product_cn="Test Product 1",
            spec_kg=25.0,
            quantity_kg=1000.0,
            unit_price=29.5,
            total_amount=29500.0
        )
        item2 = OrderItem(
            order_id=order.id,
            internal_code="SKU-002",
            product_cn="Test Product 2",
            spec_kg=50.0,
            quantity_kg=500.0,
            unit_price=50.0,
            total_amount=25000.0
        )
        db.add(item1)
        db.add(item2)
        db.commit()

        # Query back and verify relationship
        fetched = db.query(Order).filter_by(order_no="TEST-ORDER-001").first()

        assert fetched is not None, "Order should be found"
        assert fetched.order_no == "TEST-ORDER-001"
        assert len(fetched.items) == 2, f"Expected 2 items, got {len(fetched.items)}"
        assert fetched.items[0].internal_code == "SKU-001"
        assert fetched.items[1].internal_code == "SKU-002"

        # Verify item -> order relationship
        item_fetched = db.query(OrderItem).filter_by(internal_code="SKU-001").first()
        assert item_fetched.order.order_no == "TEST-ORDER-001"

        print("All relationship tests passed!")

        # Clean up
        db.query(OrderItem).filter(OrderItem.internal_code.in_(["SKU-001", "SKU-002"])).delete()
        db.query(Order).filter(Order.order_no == "TEST-ORDER-001").delete()
        db.commit()

    finally:
        db.close()


if __name__ == "__main__":
    print("Testing database models...")
    test_order_item_relationship()
    print("Database model verification complete!")