import os
import sqlite3
from datetime import datetime

DEFAULT_DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
DEFAULT_DB_PATH = os.path.join(DEFAULT_DB_DIR, 'inventory.db')


def get_db_path(custom_path=None):
    """
    Returns the resolved database path.
    Priority:
    1. custom_path parameter (e.g. from test fixture)
    2. DATABASE_PATH environment variable
    3. Production container path (/data/inventory.db) if /data directory exists
    4. Local fallback: instance/inventory.db
    """
    if custom_path:
        db_path = custom_path
    elif os.environ.get('DATABASE_PATH'):
        db_path = os.environ.get('DATABASE_PATH')
    elif os.path.exists('/data') and os.access('/data', os.W_OK):
        db_path = '/data/inventory.db'
    else:
        db_path = DEFAULT_DB_PATH

    # Ensure parent directory exists
    parent_dir = os.path.dirname(os.path.abspath(db_path))
    if parent_dir and not os.path.exists(parent_dir):
        os.makedirs(parent_dir, exist_ok=True)

    return db_path


def get_db_connection(db_path=None):
    """Creates a sqlite3 connection with Row factory and foreign keys enabled."""
    target_path = get_db_path(db_path)
    conn = sqlite3.connect(target_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path=None):
    """Initializes tables and indexes if they do not exist."""
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    price REAL NOT NULL CHECK(price >= 0),
                    quantity INTEGER NOT NULL DEFAULT 0 CHECK(quantity >= 0),
                    min_stock INTEGER NOT NULL DEFAULT 5 CHECK(min_stock >= 0),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS stock_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL,
                    change_type TEXT NOT NULL CHECK(change_type IN ('IN', 'OUT', 'INITIAL', 'ADJUSTMENT')),
                    quantity INTEGER NOT NULL,
                    previous_stock INTEGER NOT NULL,
                    new_stock INTEGER NOT NULL,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
                );
            """)

            conn.execute("CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_products_quantity ON products(quantity);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_stock_history_product_id ON stock_history(product_id);")
    finally:
        conn.close()


def seed_sample_data(db_path=None):
    """Seeds initial sample products if database is completely empty."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS count FROM products;")
        count = cursor.fetchone()['count']
        if count == 0:
            sample_products = [
                ("Apple MacBook Pro M3", "Electronics", 169900.00, 15, 5),
                ("Dell UltraSharp 27 4K Monitor", "Electronics", 42500.00, 8, 3),
                ("Logitech MX Master 3S Mouse", "Accessories", 8995.00, 25, 10),
                ("Keychron K2 Mechanical Keyboard", "Accessories", 7499.00, 4, 6),  # Low stock
                ("Ergonomic Mesh Executive Chair", "Furniture", 18500.00, 6, 2),
                ("Motorized Height-Adjustable Desk", "Furniture", 34999.00, 2, 4),    # Low stock
                ("Anker USB-C 10-in-1 Power Hub", "Accessories", 4999.00, 30, 8),
                ("Sony WH-1000XM5 Wireless Headphones", "Audio", 26990.00, 0, 5),     # Out of stock
                ("Logitech Brio 4K Ultra Webcam", "Electronics", 14500.00, 12, 4),
                ("D-Link Cat-6 High Speed Cable (10m)", "Networking", 899.00, 50, 15),
            ]
            with conn:
                for item in sample_products:
                    cur = conn.execute(
                        "INSERT INTO products (name, category, price, quantity, min_stock) VALUES (?, ?, ?, ?, ?);",
                        item
                    )
                    prod_id = cur.lastrowid
                    conn.execute(
                        """INSERT INTO stock_history 
                           (product_id, change_type, quantity, previous_stock, new_stock, notes) 
                           VALUES (?, 'INITIAL', ?, 0, ?, 'Initial inventory load');""",
                        (prod_id, item[3], item[3])
                    )
    finally:
        conn.close()


def get_all_products(db_path=None, search=None, category=None, sort_by='name', sort_order='asc'):
    """Retrieves products with optional search, category filter, and sorting."""
    conn = get_db_connection(db_path)
    try:
        query = "SELECT * FROM products WHERE 1=1"
        params = []

        if search and search.strip():
            cleaned_search = search.strip().lstrip('#')
            query += " AND (name LIKE ? OR category LIKE ? OR CAST(id AS TEXT) LIKE ?)"
            search_term = f"%{cleaned_search}%"
            params.extend([search_term, search_term, search_term])

        if category and category.strip() and category.strip() != 'All':
            query += " AND category = ?"
            params.append(category.strip())

        # Allowed sorting fields with case-insensitive string collation
        allowed_sort_fields = {
            'id': 'id',
            'name': 'LOWER(name)',
            'category': 'LOWER(category)',
            'price': 'price',
            'quantity': 'quantity',
            'created_at': 'created_at'
        }
        sort_column = allowed_sort_fields.get(sort_by, 'LOWER(name)')
        order_direction = 'DESC' if str(sort_order).lower() == 'desc' else 'ASC'

        query += f" ORDER BY {sort_column} {order_direction};"

        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return rows
    finally:
        conn.close()


def get_product_by_id(product_id, db_path=None):
    """Retrieves a single product by its ID."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE id = ?;", (product_id,))
        product = cursor.fetchone()
        return product
    finally:
        conn.close()


def create_product(name, category, price, quantity=0, min_stock=5, db_path=None):
    """Creates a new product record and records initial stock entry."""
    name = str(name).strip()
    category = str(category).strip()
    price = float(price)
    quantity = int(quantity)
    min_stock = int(min_stock)

    if not name:
        raise ValueError("Product name cannot be empty.")
    if not category:
        raise ValueError("Category cannot be empty.")
    if price < 0:
        raise ValueError("Price must be greater than or equal to 0.")
    if quantity < 0:
        raise ValueError("Quantity cannot be negative.")
    if min_stock < 0:
        raise ValueError("Minimum stock threshold cannot be negative.")

    conn = get_db_connection(db_path)
    try:
        with conn:
            cursor = conn.execute(
                """INSERT INTO products (name, category, price, quantity, min_stock)
                   VALUES (?, ?, ?, ?, ?);""",
                (name, category, price, quantity, min_stock)
            )
            product_id = cursor.lastrowid

            conn.execute(
                """INSERT INTO stock_history
                   (product_id, change_type, quantity, previous_stock, new_stock, notes)
                   VALUES (?, 'INITIAL', ?, 0, ?, 'Product registered in system');""",
                (product_id, quantity, quantity)
            )
        return product_id
    finally:
        conn.close()


def update_product(product_id, name, category, price, quantity, min_stock, db_path=None):
    """Updates product details and logs stock adjustment if quantity changed."""
    name = str(name).strip()
    category = str(category).strip()
    price = float(price)
    new_qty = int(quantity)
    min_stock = int(min_stock)

    if not name:
        raise ValueError("Product name cannot be empty.")
    if not category:
        raise ValueError("Category cannot be empty.")
    if price < 0:
        raise ValueError("Price must be greater than or equal to 0.")
    if new_qty < 0:
        raise ValueError("Quantity cannot be negative.")
    if min_stock < 0:
        raise ValueError("Minimum stock threshold cannot be negative.")

    conn = get_db_connection(db_path)
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT quantity FROM products WHERE id = ?;", (product_id,))
            current = cursor.fetchone()
            if not current:
                raise ValueError(f"Product with ID {product_id} not found.")

            old_qty = current['quantity']

            cursor.execute(
                """UPDATE products 
                   SET name = ?, category = ?, price = ?, quantity = ?, min_stock = ?
                   WHERE id = ?;""",
                (name, category, price, new_qty, min_stock, product_id)
            )

            if old_qty != new_qty:
                diff = new_qty - old_qty
                change_type = 'IN' if diff > 0 else 'OUT'
                conn.execute(
                    """INSERT INTO stock_history
                       (product_id, change_type, quantity, previous_stock, new_stock, notes)
                       VALUES (?, ?, ?, ?, ?, 'Manual quantity adjustment in product edit');""",
                    (product_id, change_type, abs(diff), old_qty, new_qty)
                )
        return True
    finally:
        conn.close()


def delete_product(product_id, db_path=None):
    """Deletes product and its stock history."""
    conn = get_db_connection(db_path)
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM products WHERE id = ?;", (product_id,))
            deleted_count = cursor.rowcount
        return deleted_count > 0
    finally:
        conn.close()


def stock_transaction(product_id, change_type, amount, notes='', db_path=None):
    """
    Executes Stock In or Stock Out.
    Validates that:
    - amount > 0
    - change_type is 'IN' or 'OUT'
    - Stock Out does not cause quantity to fall below 0.
    """
    amount = int(amount)
    if amount <= 0:
        raise ValueError("Transaction amount must be a positive integer greater than zero.")

    change_type = change_type.upper()
    if change_type not in ('IN', 'OUT'):
        raise ValueError("Change type must be 'IN' or 'OUT'.")

    conn = get_db_connection(db_path)
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT quantity, name FROM products WHERE id = ?;", (product_id,))
            product = cursor.fetchone()
            if not product:
                raise ValueError(f"Product with ID {product_id} not found.")

            current_qty = product['quantity']

            if change_type == 'IN':
                new_qty = current_qty + amount
            else:  # 'OUT'
                if current_qty < amount:
                    raise ValueError(
                        f"Insufficient stock for '{product['name']}'. "
                        f"Available: {current_qty}, Requested: {amount}. Stock cannot be negative."
                    )
                new_qty = current_qty - amount

            cursor.execute("UPDATE products SET quantity = ? WHERE id = ?;", (new_qty, product_id))
            cursor.execute(
                """INSERT INTO stock_history
                   (product_id, change_type, quantity, previous_stock, new_stock, notes)
                   VALUES (?, ?, ?, ?, ?, ?);""",
                (product_id, change_type, amount, current_qty, new_qty, notes.strip() or f"Stock {change_type} operation")
            )
        return new_qty
    finally:
        conn.close()


def get_stock_history(product_id=None, limit=50, db_path=None):
    """Retrieves stock history joined with product details."""
    conn = get_db_connection(db_path)
    try:
        query = """
            SELECT sh.*, p.name AS product_name, p.category AS product_category
            FROM stock_history sh
            JOIN products p ON sh.product_id = p.id
        """
        params = []
        if product_id:
            query += " WHERE sh.product_id = ?"
            params.append(product_id)

        query += " ORDER BY sh.created_at DESC, sh.id DESC LIMIT ?;"
        params.append(limit)

        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return rows
    finally:
        conn.close()


def get_low_stock_products(db_path=None):
    """Retrieves all products where current quantity is less than or equal to minimum stock."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT *, (min_stock - quantity) AS stock_deficit
            FROM products
            WHERE quantity <= min_stock
            ORDER BY quantity ASC, min_stock DESC;
        """)
        rows = cursor.fetchall()
        return rows
    finally:
        conn.close()


def get_dashboard_stats(db_path=None):
    """Retrieves aggregated statistics for the dashboard."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) AS total_products FROM products;")
        total_products = cursor.fetchone()['total_products']

        cursor.execute("SELECT COALESCE(SUM(quantity), 0) AS total_stock FROM products;")
        total_stock = cursor.fetchone()['total_stock']

        cursor.execute("SELECT COUNT(*) AS low_stock_count FROM products WHERE quantity <= min_stock;")
        low_stock_count = cursor.fetchone()['low_stock_count']

        cursor.execute("SELECT COALESCE(SUM(price * quantity), 0.0) AS total_value FROM products;")
        total_value = cursor.fetchone()['total_value']

        cursor.execute("SELECT COUNT(DISTINCT category) AS total_categories FROM products;")
        total_categories = cursor.fetchone()['total_categories']

        cursor.execute("SELECT * FROM products ORDER BY created_at DESC, id DESC LIMIT 5;")
        recent_products = cursor.fetchall()

        cursor.execute("""
            SELECT category, COUNT(*) AS count, SUM(quantity) AS total_qty, SUM(price * quantity) AS cat_value
            FROM products
            GROUP BY category
            ORDER BY count DESC;
        """)
        category_summary = cursor.fetchall()

        return {
            'total_products': total_products,
            'total_stock': total_stock,
            'low_stock_count': low_stock_count,
            'total_value': round(total_value, 2),
            'total_categories': total_categories,
            'recent_products': recent_products,
            'category_summary': category_summary
        }
    finally:
        conn.close()


def get_distinct_categories(db_path=None):
    """Retrieves list of distinct categories currently in use."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT category FROM products ORDER BY category ASC;")
        rows = [r['category'] for r in cursor.fetchall() if r['category']]
        return rows
    finally:
        conn.close()
