import os
from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, jsonify
)
import database


def create_app(test_config=None):
    """Create and configure the Cloud Inventory Flask application."""
    app = Flask(__name__, instance_relative_config=True)

    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY') or os.urandom(32),
        DATABASE_PATH=database.get_db_path()
    )

    if test_config:
        app.config.update(test_config)
        # If test_config provides DATABASE_PATH, set it
        if 'DATABASE_PATH' in test_config:
            os.environ['DATABASE_PATH'] = test_config['DATABASE_PATH']

    # Ensure the instance directory exists
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        pass

    # Initialize the database schema and sample data on startup
    with app.app_context():
        target_db = app.config.get('DATABASE_PATH')
        database.init_db(target_db)
        # Seed sample data if not in test mode or if requested
        if not app.config.get('TESTING'):
            database.seed_sample_data(target_db)

    # -------------------------------------------------------------
    # Production Security Headers
    # -------------------------------------------------------------
    @app.after_request
    def set_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        return response

    # -------------------------------------------------------------
    # Context Processor for common navbar badges / stats
    # -------------------------------------------------------------
    @app.context_processor
    def inject_global_data():
        try:
            target_db = app.config.get('DATABASE_PATH')
            low_stock_items = database.get_low_stock_products(target_db)
            return {'global_low_stock_count': len(low_stock_items)}
        except Exception:
            return {'global_low_stock_count': 0}

    # -------------------------------------------------------------
    # Module 1: Dashboard
    # -------------------------------------------------------------
    @app.route('/')
    def dashboard():
        target_db = app.config.get('DATABASE_PATH')
        stats = database.get_dashboard_stats(target_db)
        recent_transactions = database.get_stock_history(limit=5, db_path=target_db)
        return render_template(
            'dashboard.html',
            stats=stats,
            recent_transactions=recent_transactions
        )

    # -------------------------------------------------------------
    # Module 2: Product Management & Module 5: Search & Filtering
    # -------------------------------------------------------------
    @app.route('/products')
    def products():
        target_db = app.config.get('DATABASE_PATH')
        search_query = request.args.get('q', '').strip()
        category_filter = request.args.get('category', '').strip()
        sort_by = request.args.get('sort', 'name')
        sort_order = request.args.get('order', 'asc')

        product_list = database.get_all_products(
            db_path=target_db,
            search=search_query,
            category=category_filter,
            sort_by=sort_by,
            sort_order=sort_order
        )
        categories = database.get_distinct_categories(target_db)

        return render_template(
            'products.html',
            products=product_list,
            categories=categories,
            search_query=search_query,
            category_filter=category_filter,
            sort_by=sort_by,
            sort_order=sort_order
        )

    @app.route('/products/add', methods=['GET', 'POST'])
    def add_product():
        target_db = app.config.get('DATABASE_PATH')
        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            category = request.form.get('category', '').strip()
            price_str = request.form.get('price', '').strip()
            quantity_str = request.form.get('quantity', '0').strip()
            min_stock_str = request.form.get('min_stock', '5').strip()

            errors = []
            if not name:
                errors.append("Product name is required.")
            if not category:
                errors.append("Category is required.")

            try:
                price = float(price_str)
                if price < 0:
                    errors.append("Price cannot be negative.")
            except (ValueError, TypeError):
                errors.append("Valid price number is required.")

            try:
                quantity = int(quantity_str)
                if quantity < 0:
                    errors.append("Quantity cannot be negative.")
            except (ValueError, TypeError):
                errors.append("Quantity must be a non-negative integer.")

            try:
                min_stock = int(min_stock_str)
                if min_stock < 0:
                    errors.append("Minimum stock threshold cannot be negative.")
            except (ValueError, TypeError):
                errors.append("Minimum stock must be a non-negative integer.")

            if errors:
                for error in errors:
                    flash(error, 'danger')
                categories = database.get_distinct_categories(target_db)
                return render_template('add_product.html', categories=categories, form=request.form)

            try:
                new_id = database.create_product(
                    name=name,
                    category=category,
                    price=price,
                    quantity=quantity,
                    min_stock=min_stock,
                    db_path=target_db
                )
                flash(f"Product '{name}' added successfully (ID: #{new_id})!", 'success')
                return redirect(url_for('products'))
            except Exception as e:
                flash(f"Error creating product: {str(e)}", 'danger')

        categories = database.get_distinct_categories(target_db)
        return render_template('add_product.html', categories=categories, form={})

    @app.route('/products/edit/<int:product_id>', methods=['GET', 'POST'])
    def edit_product(product_id):
        target_db = app.config.get('DATABASE_PATH')
        product = database.get_product_by_id(product_id, target_db)
        if not product:
            flash(f"Product with ID #{product_id} not found.", 'warning')
            return redirect(url_for('products'))

        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            category = request.form.get('category', '').strip()
            price_str = request.form.get('price', '').strip()
            quantity_str = request.form.get('quantity', '0').strip()
            min_stock_str = request.form.get('min_stock', '5').strip()

            errors = []
            if not name:
                errors.append("Product name is required.")
            if not category:
                errors.append("Category is required.")

            try:
                price = float(price_str)
                if price < 0:
                    errors.append("Price cannot be negative.")
            except (ValueError, TypeError):
                errors.append("Valid price number is required.")

            try:
                quantity = int(quantity_str)
                if quantity < 0:
                    errors.append("Quantity cannot be negative.")
            except (ValueError, TypeError):
                errors.append("Quantity must be a non-negative integer.")

            try:
                min_stock = int(min_stock_str)
                if min_stock < 0:
                    errors.append("Minimum stock threshold cannot be negative.")
            except (ValueError, TypeError):
                errors.append("Minimum stock must be a non-negative integer.")

            if errors:
                for error in errors:
                    flash(error, 'danger')
                categories = database.get_distinct_categories(target_db)
                return render_template(
                    'edit_product.html',
                    product=product,
                    categories=categories,
                    form=request.form
                )

            try:
                database.update_product(
                    product_id=product_id,
                    name=name,
                    category=category,
                    price=price,
                    quantity=quantity,
                    min_stock=min_stock,
                    db_path=target_db
                )
                flash(f"Product #{product_id} ('{name}') updated successfully!", 'success')
                return redirect(url_for('products'))
            except Exception as e:
                flash(f"Error updating product: {str(e)}", 'danger')

        categories = database.get_distinct_categories(target_db)
        return render_template('edit_product.html', product=product, categories=categories, form=product)

    @app.route('/products/delete/<int:product_id>', methods=['POST'])
    def delete_product(product_id):
        target_db = app.config.get('DATABASE_PATH')
        product = database.get_product_by_id(product_id, target_db)
        if not product:
            flash(f"Product #{product_id} does not exist.", 'warning')
            return redirect(url_for('products'))

        success = database.delete_product(product_id, target_db)
        if success:
            flash(f"Product '{product['name']}' (ID #{product_id}) was deleted.", 'info')
        else:
            flash(f"Could not delete product #{product_id}.", 'danger')

        return redirect(url_for('products'))

    # -------------------------------------------------------------
    # Module 3: Stock Management
    # -------------------------------------------------------------
    @app.route('/stock', methods=['GET', 'POST'])
    def stock():
        target_db = app.config.get('DATABASE_PATH')
        if request.method == 'POST':
            product_id_str = request.form.get('product_id', '').strip()
            change_type = request.form.get('change_type', '').strip().upper()
            amount_str = request.form.get('amount', '').strip()
            notes = request.form.get('notes', '').strip()

            try:
                product_id = int(product_id_str)
                amount = int(amount_str)
                if amount <= 0:
                    flash("Stock quantity amount must be greater than zero.", 'danger')
                    return redirect(url_for('stock'))

                new_quantity = database.stock_transaction(
                    product_id=product_id,
                    change_type=change_type,
                    amount=amount,
                    notes=notes,
                    db_path=target_db
                )
                product = database.get_product_by_id(product_id, target_db)
                flash(
                    f"Stock {change_type} successful for '{product['name']}'. "
                    f"New available stock: {new_quantity} units.",
                    'success'
                )
            except ValueError as ve:
                flash(f"Stock transaction failed: {str(ve)}", 'danger')
            except Exception as e:
                flash(f"Unexpected error processing stock: {str(e)}", 'danger')

            return redirect(url_for('stock'))

        product_list = database.get_all_products(db_path=target_db, sort_by='name')
        history = database.get_stock_history(limit=50, db_path=target_db)
        return render_template('stock.html', products=product_list, history=history)

    # -------------------------------------------------------------
    # Module 4: Low Stock Alerts
    # -------------------------------------------------------------
    @app.route('/low-stock')
    def low_stock():
        target_db = app.config.get('DATABASE_PATH')
        low_stock_items = database.get_low_stock_products(target_db)
        return render_template('low_stock.html', items=low_stock_items)

    # -------------------------------------------------------------
    # Health endpoint used by deployment checks.
    # -------------------------------------------------------------
    @app.route('/health')
    def health():
        target_db = app.config.get('DATABASE_PATH')
        try:
            # Verify database connectivity
            conn = database.get_db_connection(target_db)
            cursor = conn.cursor()
            cursor.execute("SELECT 1;")
            cursor.fetchone()
            conn.close()
            return jsonify({
                "status": "healthy",
                "service": "cloud-inventory",
                "database": "connected"
            }), 200
        except Exception as e:
            return jsonify({
                "status": "unhealthy",
                "service": "cloud-inventory",
                "error": str(e)
            }), 500

    # -------------------------------------------------------------
    # Error Handlers
    # -------------------------------------------------------------
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('base.html', error_code=404, error_message="Page Not Found"), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('base.html', error_code=500, error_message="Internal Server Error"), 500

    return app


# Application instance for Gunicorn / WSGI
app = create_app()

if __name__ == '__main__':
    # Local development server
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() in ('true', '1')
    app.run(host='0.0.0.0', port=port, debug=debug_mode)

