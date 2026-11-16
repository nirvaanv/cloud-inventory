import os
import tempfile
import pytest
import database


@pytest.fixture
def temp_db():
    """Provides a fresh, isolated temporary SQLite database for each test."""
    db_fd, db_path = tempfile.mkstemp(suffix='_test.db')
    os.close(db_fd)
    database.init_db(db_path)
    yield db_path
    if os.path.exists(db_path):
        os.remove(db_path)


def test_init_db(temp_db):
    """Test that database tables and indexes are created successfully."""
    conn = database.get_db_connection(temp_db)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row['name'] for row in cursor.fetchall()]
    conn.close()

    assert 'products' in tables
    assert 'stock_history' in tables


def test_create_and_get_product(temp_db):
    """Test creating a product and fetching it by ID."""
    prod_id = database.create_product(
        name="Logitech Mouse",
        category="Accessories",
        price=49.99,
        quantity=20,
        min_stock=5,
        db_path=temp_db
    )
    assert prod_id > 0

    product = database.get_product_by_id(prod_id, temp_db)
    assert product is not None
    assert product['name'] == "Logitech Mouse"
    assert product['category'] == "Accessories"
    assert product['price'] == 49.99
    assert product['quantity'] == 20
    assert product['min_stock'] == 5


def test_product_validation(temp_db):
    """Test that invalid product inputs raise ValueError."""
    with pytest.raises(ValueError, match="Product name cannot be empty"):
        database.create_product("", "Category", 10.0, 5, 2, db_path=temp_db)

    with pytest.raises(ValueError, match="Price must be greater than or equal to 0"):
        database.create_product("Item", "Category", -5.0, 5, 2, db_path=temp_db)

    with pytest.raises(ValueError, match="Quantity cannot be negative"):
        database.create_product("Item", "Category", 10.0, -2, 2, db_path=temp_db)


def test_update_product(temp_db):
    """Test updating product details and quantity adjustment."""
    prod_id = database.create_product("Desk", "Furniture", 150.0, 10, 3, db_path=temp_db)
    database.update_product(prod_id, "Standing Desk", "Office Furniture", 299.0, 15, 4, db_path=temp_db)

    updated = database.get_product_by_id(prod_id, temp_db)
    assert updated['name'] == "Standing Desk"
    assert updated['category'] == "Office Furniture"
    assert updated['price'] == 299.0
    assert updated['quantity'] == 15
    assert updated['min_stock'] == 4


def test_delete_product(temp_db):
    """Test deleting a product."""
    prod_id = database.create_product("Old Item", "Misc", 5.0, 1, 1, db_path=temp_db)
    success = database.delete_product(prod_id, temp_db)
    assert success is True

    deleted = database.get_product_by_id(prod_id, temp_db)
    assert deleted is None


def test_stock_in(temp_db):
    """Test Stock In increases quantity and records transaction."""
    prod_id = database.create_product("Widget", "Hardware", 10.0, 10, 5, db_path=temp_db)
    new_qty = database.stock_transaction(prod_id, 'IN', 15, notes="Received shipment", db_path=temp_db)

    assert new_qty == 25
    product = database.get_product_by_id(prod_id, temp_db)
    assert product['quantity'] == 25

    history = database.get_stock_history(product_id=prod_id, db_path=temp_db)
    assert len(history) == 2  # 1 initial + 1 stock in
    assert history[0]['change_type'] == 'IN'
    assert history[0]['quantity'] == 15
    assert history[0]['previous_stock'] == 10
    assert history[0]['new_stock'] == 25


def test_stock_out(temp_db):
    """Test Stock Out decreases quantity."""
    prod_id = database.create_product("Gadget", "Electronics", 20.0, 30, 5, db_path=temp_db)
    new_qty = database.stock_transaction(prod_id, 'OUT', 10, notes="Dispatched order", db_path=temp_db)

    assert new_qty == 20
    product = database.get_product_by_id(prod_id, temp_db)
    assert product['quantity'] == 20


def test_negative_quantity_prevention(temp_db):
    """Test that Stock Out preventing negative inventory throws ValueError."""
    prod_id = database.create_product("Limited Item", "Electronics", 100.0, 5, 2, db_path=temp_db)
    with pytest.raises(ValueError, match="Insufficient stock"):
        database.stock_transaction(prod_id, 'OUT', 10, db_path=temp_db)

    # Quantity remains unchanged
    product = database.get_product_by_id(prod_id, temp_db)
    assert product['quantity'] == 5


def test_low_stock_detection(temp_db):
    """Test low-stock detection when quantity <= min_stock."""
    database.create_product("Item Adequate", "Cat", 10.0, 20, 5, db_path=temp_db)
    p2 = database.create_product("Item Equal", "Cat", 10.0, 5, 5, db_path=temp_db)
    p3 = database.create_product("Item Below", "Cat", 10.0, 2, 5, db_path=temp_db)
    p4 = database.create_product("Item Out", "Cat", 10.0, 0, 5, db_path=temp_db)

    low_items = database.get_low_stock_products(temp_db)
    low_ids = [item['id'] for item in low_items]

    assert len(low_items) == 3
    assert p2 in low_ids
    assert p3 in low_ids
    assert p4 in low_ids


def test_search_and_filter(temp_db):
    """Test search query, category filter and sorting."""
    p1 = database.create_product("MacBook Air", "Computers", 999.0, 10, 2, db_path=temp_db)
    p2 = database.create_product("MacBook Pro", "Computers", 1999.0, 5, 2, db_path=temp_db)
    p3 = database.create_product("Wireless Headset", "Audio", 150.0, 15, 3, db_path=temp_db)

    # Search by text
    results = database.get_all_products(db_path=temp_db, search="MacBook")
    assert len(results) == 2

    # Search by ID
    results_id = database.get_all_products(db_path=temp_db, search=str(p1))
    assert len(results_id) == 1
    assert results_id[0]['id'] == p1

    # Search by ID with hash prefix (#)
    results_hash = database.get_all_products(db_path=temp_db, search=f"#{p2}")
    assert len(results_hash) == 1
    assert results_hash[0]['id'] == p2

    # Category
    results_cat = database.get_all_products(db_path=temp_db, category="Audio")
    assert len(results_cat) == 1
    assert results_cat[0]['name'] == "Wireless Headset"

    # Sort
    results_sorted = database.get_all_products(db_path=temp_db, sort_by='price', sort_order='desc')
    assert results_sorted[0]['name'] == "MacBook Pro"
