import os
import tempfile
import pytest
from app import create_app
import database


@pytest.fixture
def app_instance():
    """Create and configure a clean Flask application instance for testing."""
    db_fd, db_path = tempfile.mkstemp(suffix='_flask_test.db')
    os.close(db_fd)

    test_app = create_app({
        'TESTING': True,
        'DATABASE_PATH': db_path,
        'SECRET_KEY': 'test-secret-key'
    })

    # Seed with known test items
    with test_app.app_context():
        database.create_product("Test Laptop", "Computers", 1200.0, 10, 3, db_path=db_path)
        database.create_product("Test Cable", "Accessories", 15.0, 2, 5, db_path=db_path)  # Low stock

    yield test_app

    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture
def client(app_instance):
    """A test client for the app."""
    return app_instance.test_client()


def test_health_check(client):
    """Test the /health endpoint returns 200 and healthy JSON status."""
    response = client.get('/health')
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['status'] == 'healthy'
    assert json_data['database'] == 'connected'


def test_security_headers(client):
    """Test response contains standard production security headers."""
    response = client.get('/')
    assert response.headers.get('X-Content-Type-Options') == 'nosniff'
    assert response.headers.get('X-Frame-Options') == 'SAMEORIGIN'
    assert response.headers.get('X-XSS-Protection') == '1; mode=block'


def test_dashboard_route(client):
    """Test dashboard loads with status 200 and renders KPI metrics."""
    response = client.get('/')
    assert response.status_code == 200
    html = response.data.decode('utf-8')
    assert "Inventory Dashboard" in html
    assert "Test Laptop" in html
    assert "Total Products" in html


def test_products_list_and_search(client):
    """Test products listing, search query, and category filters."""
    # List all
    response = client.get('/products')
    assert response.status_code == 200
    assert "Test Laptop" in response.data.decode('utf-8')

    # Search
    search_res = client.get('/products?q=Laptop')
    assert "Test Laptop" in search_res.data.decode('utf-8')
    assert "Test Cable" not in search_res.data.decode('utf-8')

    # Category filter
    cat_res = client.get('/products?category=Accessories')
    assert "Test Cable" in cat_res.data.decode('utf-8')
    assert "Test Laptop" not in cat_res.data.decode('utf-8')


def test_add_product_route(client, app_instance):
    """Test adding a product via POST."""
    response = client.post('/products/add', data={
        'name': 'Wireless Keyboard',
        'category': 'Peripherals',
        'price': '79.99',
        'quantity': '15',
        'min_stock': '5'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert "Wireless Keyboard" in response.data.decode('utf-8')
    assert "added successfully" in response.data.decode('utf-8')


def test_edit_product_route(client):
    """Test editing an existing product."""
    response = client.post('/products/edit/1', data={
        'name': 'Test Laptop Ultra',
        'category': 'Computers',
        'price': '1350.00',
        'quantity': '12',
        'min_stock': '4'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert "Test Laptop Ultra" in response.data.decode('utf-8')
    assert "updated successfully" in response.data.decode('utf-8')


def test_delete_product_route(client):
    """Test deleting a product."""
    response = client.post('/products/delete/2', follow_redirects=True)
    assert response.status_code == 200
    assert "was deleted" in response.data.decode('utf-8')


def test_stock_in_and_out_route(client):
    """Test stock transaction routes."""
    # Stock IN
    res_in = client.post('/stock', data={
        'product_id': '1',
        'change_type': 'IN',
        'amount': '5',
        'notes': 'Supplier delivery'
    }, follow_redirects=True)
    assert res_in.status_code == 200
    assert "Stock IN successful" in res_in.data.decode('utf-8')

    # Stock OUT
    res_out = client.post('/stock', data={
        'product_id': '1',
        'change_type': 'OUT',
        'amount': '3',
        'notes': 'Customer order'
    }, follow_redirects=True)
    assert res_out.status_code == 200
    assert "Stock OUT successful" in res_out.data.decode('utf-8')


def test_negative_stock_rejection_route(client):
    """Test that attempting to withdraw more than available stock is rejected."""
    res_fail = client.post('/stock', data={
        'product_id': '1',
        'change_type': 'OUT',
        'amount': '9999',
        'notes': 'Over-dispatch attempt'
    }, follow_redirects=True)
    assert res_fail.status_code == 200
    assert "Stock transaction failed" in res_fail.data.decode('utf-8')
    assert "Stock cannot be negative" in res_fail.data.decode('utf-8')


def test_low_stock_route(client):
    """Test the low stock alerts page."""
    response = client.get('/low-stock')
    assert response.status_code == 200
    html = response.data.decode('utf-8')
    assert "Low Stock Alerts" in html
    assert "Test Cable" in html
