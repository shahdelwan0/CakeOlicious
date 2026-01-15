from flask import Blueprint, request, jsonify, current_app
from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, IntegerField
from wtforms.validators import DataRequired, NumberRange
from datetime import datetime

import uuid
import os
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
import logging
from sqlalchemy import text

from backend.models.Product import Product
from backend.models.Category import Category
from backend.models.User import User
from backend.extensions import db
from backend.routes.auth import token_required

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__)

def check_admin(user):
    return user.user_role.lower() == 'admin'

class AddProductForm(FlaskForm):
    class Meta:
        csrf = False  

    product_name = StringField("Product Name", validators=[DataRequired()])
    description = StringField("Description")
    price = FloatField(
        "Price",
        validators=[
            DataRequired(),
            NumberRange(min=0.01, message="Price must be greater than 0"),
        ],
    )
    stock = IntegerField(
        "Stock",
        validators=[
            DataRequired(),
            NumberRange(min=0, message="Stock cannot be negative"),
        ],
    )
    category_id = IntegerField("Category ID", validators=[DataRequired()])
    image_url = StringField("Image URL")
    discount = FloatField(
        "Discount",
        validators=[
            NumberRange(min=0, max=100, message="Discount must be between 0 and 100"),
        ],
    )

class UpdatePriceForm(FlaskForm):
    class Meta:
        csrf = False

    new_price = FloatField(
        "New Price",
        validators=[
            DataRequired(),
            NumberRange(min=0.01, message="Price must be greater than 0"),
        ],
    )

class UpdateDiscountForm(FlaskForm):
    class Meta:
        csrf = False

    new_discount = FloatField(
        "New Discount",
        validators=[
            DataRequired(),
            NumberRange(min=0, max=100, message="Discount must be between 0 and 100"),
        ],
    )

@admin_bp.route("/admin/upload-image", methods=["POST"])
@token_required
def upload_image(current_user):
    if not check_admin(current_user):
        return jsonify({"message": "Unauthorized access"}), 403

    try:
        logger.info("Processing image upload request")

        if "image" not in request.files:
            logger.warning("No file part in request")
            return jsonify({"success": False, "message": "No file part"}), 400

        file = request.files["image"]

        if file.filename == "":
            logger.warning("No selected file")
            return jsonify({"success": False, "message": "No selected file"}), 400

        allowed_extensions = {"png", "jpg", "jpeg", "gif", "webp"}
        file_ext = (
            file.filename.rsplit(".", 1)[1].lower() if "." in file.filename else ""
        )
        if file_ext not in allowed_extensions:
            logger.warning(f"Invalid file type: {file_ext}")
            return (
                jsonify(
                    {
                        "success": False,
                        "message": f'Invalid file type. Allowed: {", ".join(allowed_extensions)}'
                    }
                ),
                400,
            )

        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        unique_filename = f"{timestamp}_{uuid.uuid4().hex[:8]}_{filename}"

        upload_folder = os.path.join(current_app.root_path, "static", "uploads")
        os.makedirs(upload_folder, exist_ok=True)

        file_path = os.path.join(upload_folder, unique_filename)
        file.save(file_path)

        logger.info(f"File saved to {file_path}")

        image_url = f"/static/uploads/{unique_filename}"
        full_url = f"http://localhost:5000{image_url}"

        logger.info(f"Image URL: {image_url}")
        logger.info(f"Full URL: {full_url}")

        return (
            jsonify(
                {
                    "success": True,
                    "message": "Image uploaded successfully",
                    "imageUrl": image_url,
                    "fullUrl": full_url,
                    "filename": unique_filename,
                }
            ),
            201,
        )

    except Exception as e:
        logger.error(f"Error uploading image: {str(e)}")
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500

@admin_bp.route("/admin/upload", methods=["POST"])
@token_required
def upload_product_image(current_user):
    if not check_admin(current_user):
        return jsonify({"message": "Unauthorized access"}), 403

    try:
        logger.info("Processing product image upload request")

        if "image" not in request.files:
            logger.warning("No file part in request")
            return jsonify({"success": False, "message": "No file part"}), 400

        file = request.files["image"]
        product_name = request.form.get("product_name", "unknown_product")

        if file.filename == "":
            logger.warning("No selected file")
            return jsonify({"success": False, "message": "No selected file"}), 400

        allowed_extensions = {"png", "jpg", "jpeg", "gif", "webp"}
        file_ext = (
            file.filename.rsplit(".", 1)[1].lower() if "." in file.filename else ""
        )
        if file_ext not in allowed_extensions:
            logger.warning(f"Invalid file type: {file_ext}")
            return (
                jsonify(
                    {
                        "success": False,
                        "message": f'Invalid file type. Allowed: {", ".join(allowed_extensions)}'
                    }
                ),
                400,
            )

        filename = secure_filename(file.filename)
        product_slug = secure_filename(product_name.lower().replace(" ", "-"))
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        unique_filename = (
            f"{product_slug}_{timestamp}_{uuid.uuid4().hex[:8]}.{file_ext}"
        )

        upload_folder = os.path.join("static", "uploads")
        os.makedirs(upload_folder, exist_ok=True)

        file_path = os.path.join(upload_folder, unique_filename)
        file.save(file_path)

        image_url = f"/static/uploads/{unique_filename}"
        full_url = f"http://localhost:5000{image_url}"

        return (
            jsonify(
                {
                    "success": True,
                    "message": "Image uploaded successfully",
                    "productName": product_name,
                    "imageUrl": full_url,
                    "relativePath": image_url,
                    "filename": unique_filename,
                }
            ),
            201,
        )

    except Exception as e:
        logger.error(f"Error uploading image: {str(e)}")
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500

@admin_bp.route("/admin", methods=["GET"])
@token_required
def admin_dashboard(current_user):
    if not check_admin(current_user):
        logger.warning(f"Unauthorized access attempt for user_id: {current_user.id}")
        return jsonify({"message": "Unauthorized access"}), 403
    
    try:

        product_count_query = text("SELECT COUNT(*) FROM products")
        product_count = db.session.execute(product_count_query).scalar() or 0
        
        user_count_query = text("SELECT COUNT(*) FROM users")
        user_count = db.session.execute(user_count_query).scalar() or 0
        
        order_stats_query = text("""
            SELECT COUNT(*) as order_count, COALESCE(SUM(total_amount), 0) as total_revenue 
            FROM orders
        """)
        order_stats = db.session.execute(order_stats_query).fetchone()
        order_count = order_stats.order_count if order_stats else 0
        total_revenue = float(order_stats.total_revenue) if order_stats and order_stats.total_revenue else 0
        
        recent_activity_query = text("""
            SELECT o.id, o.user_id, u.username, o.order_date, o.total_amount, o.status
            FROM orders o
            JOIN users u ON o.user_id = u.id
            ORDER BY o.order_date DESC
            LIMIT 5
        """)
        recent_activity_result = db.session.execute(recent_activity_query).fetchall()
        
        recent_activity = []
        for row in recent_activity_result:
            activity = {
                "id": row.id,
                "user_id": row.user_id,
                "username": row.username,
                "date": row.order_date.isoformat() if hasattr(row.order_date, 'isoformat') else str(row.order_date),
                "amount": float(row.total_amount) if row.total_amount else 0,
                "status": row.status
            }
            recent_activity.append(activity)
        
        return jsonify({
            "message": "Welcome to the admin dashboard",
            "stats": {
                "totalProducts": product_count,
                "totalUsers": user_count,
                "totalOrders": order_count,
                "totalRevenue": total_revenue
            },
            "recentActivity": recent_activity
        }), 200
        
    except Exception as e:
        logger.error(f"Error in admin dashboard: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"message": f"Error: {str(e)}"}), 500

@admin_bp.route("/admin/products", methods=["GET"])
@token_required
def admin_get_products(current_user):
    logger.info(f"Admin products request from user_id: {current_user.id}, role: {current_user.user_role}")
    
    if not check_admin(current_user):
        logger.warning(f"Unauthorized access attempt for user_id: {current_user.id}")
        return jsonify({"message": "Unauthorized access"}), 403
    
    try:

        products_query = text("""
            SELECT p.id, p.product_name, p.product_description, p.price, p.stock,
                   p.category_id, p.image_url, p.is_active, p.discount, c.category_name
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            ORDER BY p.id DESC""")
        
        products_result = db.session.execute(products_query).fetchall()
        logger.info(f"Found {len(products_result) if products_result else 0} products")
        
        products = []
        for row in products_result:
            try:
                logger.debug(f"Processing product row: {row}")
                product = {
                    "id": row.id,
                    "product_name": row.product_name,
                    "description": row.product_description,
                    "price": float(row.price) if row.price is not None else 0.0,
                    "stock": row.stock if row.stock is not None else 0,
                    "category_id": row.category_id,
                    "category_name": row.category_name,
                    "image_url": row.image_url,
                    "is_active": bool(row.is_active) if hasattr(row, 'is_active') else True,
                    "discount": float(row.discount) if hasattr(row, 'discount') and row.discount is not None else 0.0
                }
                products.append(product)
            except Exception as row_error:
                logger.error(f"Error processing product row: {str(row_error)}")

        logger.info(f"Returning {len(products)} products")
        return jsonify({"success": True, "products": products}), 200
        
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        logger.error(f"Error fetching products: {str(e)}")
        logger.error(error_traceback)

        return jsonify({
            "success": False, 
            "message": f"Error: {str(e)}",
            "traceback": error_traceback
        }), 500

@admin_bp.route("/admin/users", methods=["GET"])
@token_required
def admin_get_users(current_user):
    logger.info(f"Admin users request from user_id: {current_user.id}, role: {current_user.user_role}")
    
    if not check_admin(current_user):
        logger.warning(f"Unauthorized access attempt for user_id: {current_user.id}")
        return jsonify({"message": "Unauthorized access"}), 403
    
    try:

        result = db.session.execute(text("SELECT id, username, email, full_name, user_address, phone_number, user_role FROM users")).fetchall()
        
        users = []
        for row in result:
            try:
                user = {
                    "id": row[0],
                    "username": row[1],
                    "email": row[2],
                    "full_name": row[3],
                    "user_address": row[4],
                    "phone_number": row[5],
                    "user_role": row[6]
                }
                users.append(user)
            except Exception as row_error:
                logger.error(f"Error processing user row: {str(row_error)}")

        logger.info(f"Returning {len(users)} users")
        return jsonify({
            "success": True,
            "users": users
        }), 200
        
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        logger.error(f"Error fetching users: {str(e)}")
        logger.error(error_traceback)
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}",
            "traceback": error_traceback
        }), 500

@admin_bp.route("/admin/product/toggle-visibility/<int:product_id>", methods=["POST"])
@token_required
def toggle_product_visibility(current_user, product_id):
    if not check_admin(current_user):
        logger.warning(f"Unauthorized access attempt for user_id: {current_user.id}")
        return jsonify({"message": "Unauthorized access"}), 403
    
    if not request.is_json:
        logger.error("Invalid JSON format in request")
        return jsonify({"message": "Invalid JSON format"}), 400
    
    data = request.get_json()
    is_active = data.get('is_active')
    
    if is_active is None:
        return jsonify({"message": "is_active field is required"}), 400
    
    try:
        
        product_result = db.session.execute(
            text("SELECT product_name FROM products WHERE id = :product_id"),
            {"product_id": product_id}
        ).fetchone()
        
        if not product_result:
            logger.warning(f"Product not found for ID: {product_id}")
            return jsonify({"message": "Product not found"}), 404
        
        update_query = text("""
            UPDATE products 
            SET is_active = :is_active
            WHERE id = :product_id""")
        
        db.session.execute(
            update_query,
            {
                "product_id": product_id,
                "is_active": is_active
            }
        )
        
        db.session.commit()
        logger.info(f"Product {product_id} visibility updated to {is_active}")
        return jsonify({"message": "Product visibility updated successfully"}), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating product visibility: {str(e)}")
        return jsonify({"message": "Error updating product visibility", "error": str(e)}), 500

@admin_bp.route("/admin/product/update/<int:product_id>", methods=["POST"])
@token_required
def update_product(current_user, product_id):
    if not check_admin(current_user):
        logger.warning(f"Unauthorized access attempt for user_id: {current_user.id}")
        return jsonify({"message": "Unauthorized access"}), 403
    
    if not request.is_json:
        logger.error("Invalid JSON format in request")
        return jsonify({"message": "Invalid JSON format"}), 400
    
    data = request.get_json()
    
    required_fields = ['product_name', 'price', 'stock', 'category_id']
    for field in required_fields:
        if field not in data or data[field] is None or data[field] == '':
            logger.warning(f"Missing or invalid required field: {field}")
            return jsonify({"message": f"Missing or invalid required field: {field}"}), 400
    
    try:

        product_result = db.session.execute(
            text("SELECT * FROM products WHERE id = :product_id"),
            {"product_id": product_id}
        ).fetchone()
        
        if not product_result:
            logger.warning(f"Product not found for ID: {product_id}")
            return jsonify({"message": "Product not found"}), 404
        
        try:
            product_name = str(data.get("product_name", "")).strip()
            product_description = str(data.get("description", "")).strip()
            price = float(data.get("price")) if data.get("price") and data.get("price") != '' else None
            stock = int(data.get("stock")) if data.get("stock") and data.get("stock") != '' else None
            category_id = int(data.get("category_id")) if data.get("category_id") and data.get("category_id") != '' else None
            image_url = str(data.get("image_url", "")).strip() if data.get("image_url") else ""
            discount = float(data.get("discount", 0)) if data.get("discount") and data.get("discount") != '' else 0
            is_active = data.get("is_active", 1)
            
            if not product_name or not price or not stock or not category_id:
                return jsonify({"message": "Missing required fields or invalid values"}), 400
            
        except ValueError as ve:
            logger.error(f"Invalid data type in update: {str(ve)}")
            return jsonify({"message": f"Invalid data format: {str(ve)}"}), 400
        
        update_query = text("""
            UPDATE products
            SET product_name = :product_name,
                product_description = :product_description,
                price = :price,
                stock = :stock,
                category_id = :category_id,
                image_url = :image_url,
                discount = :discount,
                is_active = :is_active
            WHERE id = :product_id
        """)
        
        db.session.execute(update_query, {
            "product_id": product_id,
            "product_name": product_name,
            "product_description": product_description,
            "price": price,
            "stock": stock,
            "category_id": category_id,
            "image_url": image_url,
            "discount": discount,
            "is_active": is_active
        })
        
        db.session.commit()
        logger.info(f"Product {product_id} updated successfully")
        return jsonify({"success": True, "message": "Product updated successfully"}), 200
        
    except ValueError as ve:
        db.session.rollback()
        logger.error(f"Invalid data type: {str(ve)}")
        return jsonify({"success": False, "message": f"Invalid data type: {str(ve)}"}), 400
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating product: {str(e)}")
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500

@admin_bp.route("/admin/user/delete/<int:user_id>", methods=["DELETE"])
@token_required
def delete_user(current_user, user_id):
    logger.info(f"Delete user request for user_id: {user_id} from admin: {current_user.id}")
    
    if not check_admin(current_user):
        logger.warning(f"Unauthorized access attempt for user_id: {current_user.id}")
        return jsonify({"message": "Unauthorized access"}), 403
    
    try:

        user_check = db.session.execute(
            text("SELECT id FROM users WHERE id = :user_id"),
            {"user_id": user_id}
        ).fetchone()
        
        if not user_check:
            logger.warning(f"User not found for deletion: {user_id}")
            return jsonify({"success": False, "message": "User not found"}), 404
        
        delete_query = text("DELETE FROM users WHERE id = :user_id")
        db.session.execute(delete_query, {"user_id": user_id})
        db.session.commit()
        
        logger.info(f"User {user_id} deleted successfully")
        return jsonify({
            "success": True,
            "message": "User deleted successfully"
        }), 200
        
    except Exception as e:
        db.session.rollback()
        import traceback
        error_traceback = traceback.format_exc()
        logger.error(f"Error deleting user: {str(e)}")
        logger.error(error_traceback)
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}",
            "traceback": error_traceback}), 500

@admin_bp.route("/admin/user/update/<int:user_id>", methods=["PUT", "POST"])
@token_required
def update_user(current_user, user_id):
    logger.info(f"Update user request for user_id: {user_id} from admin: {current_user.id}")
    
    if not check_admin(current_user):
        logger.warning(f"Unauthorized access attempt for user_id: {current_user.id}")
        return jsonify({"message": "Unauthorized access"}), 403
    
    if not request.is_json:
        logger.error("Invalid JSON format in request")
        return jsonify({"message": "Invalid JSON format"}), 400
    
    data = request.get_json()
    
    try:

        user_check_query = text("SELECT id, username FROM users WHERE id = :user_id")
        user = db.session.execute(user_check_query, {"user_id": user_id}).fetchone()
        
        if not user:
            logger.warning(f"User not found: {user_id}")
            return jsonify({"success": False, "message": "User not found"}), 404
        
        update_fields = []
        params = {"user_id": user_id}
        
        if "username" in data and data["username"]:
            update_fields.append("username = :username")
            params["username"] = data["username"]
        
        if "email" in data and data["email"]:
            update_fields.append("email = :email")
            params["email"] = data["email"]
        
        if "full_name" in data and data["full_name"]:
            update_fields.append("full_name = :full_name")
            params["full_name"] = data["full_name"]
        
        if "user_address" in data:
            update_fields.append("user_address = :user_address")
            params["user_address"] = data["user_address"]
        
        if "phone_number" in data:
            update_fields.append("phone_number = :phone_number")
            params["phone_number"] = data["phone_number"]
        
        if "user_role" in data and data["user_role"]:
            update_fields.append("user_role = :user_role")
            params["user_role"] = data["user_role"]
        
        if "password" in data and data["password"]:

            hashed_password = generate_password_hash(data["password"])
            update_fields.append("password_hash = :password_hash")
            params["password_hash"] = hashed_password
        
        if not update_fields:
            return jsonify({"success": True, "message": "No changes to update"}), 200
        
        update_query = text(f"""
            UPDATE users 
            SET {', '.join(update_fields)}
            WHERE id = :user_id
        """)
        
        db.session.execute(update_query, params)
        db.session.commit()
        
        logger.info(f"User {user_id} ({user.username}) updated successfully")
        return jsonify({
            "success": True, 
            "message": f"User {user.username} updated successfully"
        }), 200
        
    except Exception as e:
        db.session.rollback()
        import traceback
        error_traceback = traceback.format_exc()
        logger.error(f"Error updating user: {str(e)}")
        logger.error(error_traceback)
        return jsonify({
            "success": False, 
            "message": f"Error: {str(e)}",
            "traceback": error_traceback
        }), 500

@admin_bp.route("/admin/product/add", methods=["POST"])
@token_required
def add_product(current_user):
    if not check_admin(current_user):
        logger.warning(f"Unauthorized access attempt for user_id: {current_user.id}")
        return jsonify({"success": False, "message": "Unauthorized access"}), 403
    
    try:
        if not request.is_json:
            logger.error("Invalid JSON format in request")
            return jsonify({"success": False, "message": "Invalid JSON format"}), 400
        
        data = request.get_json()
        logger.info(f"Received product data: {data}")
        
        required_fields = ['product_name', 'price', 'stock', 'category_id']
        for field in required_fields:
            if field not in data or data[field] is None or data[field] == '':
                logger.warning(f"Missing or empty required field: {field}")
                return jsonify({
                    "success": False, 
                    "message": f"Missing or empty required field: {field}"
                }), 400
        
        try:
            product_name = str(data.get("product_name", "")).strip()
            description = str(data.get("description", "")).strip()
            price_val = data.get("price")
            stock_val = data.get("stock")
            category_id_val = data.get("category_id")
            image_url = str(data.get("image_url", "")).strip()
            discount_val = data.get("discount", 0)
            
            if not price_val or price_val == '':
                return jsonify({"success": False, "message": "Price is required and must not be empty"}), 400
            price = float(price_val)
            
            if not stock_val or stock_val == '':
                return jsonify({"success": False, "message": "Stock is required and must not be empty"}), 400
            stock = int(stock_val)
            
            if not category_id_val or category_id_val == '':
                return jsonify({"success": False, "message": "Category is required and must not be empty"}), 400
            category_id = int(category_id_val)
            
            if not product_name:
                return jsonify({"success": False, "message": "Product name is required"}), 400
            
            discount = float(discount_val) if discount_val and discount_val != '' else 0
            
        except ValueError as ve:
            logger.error(f"Invalid data type: {str(ve)}")
            return jsonify({"success": False, "message": f"Invalid data format: {str(ve)}"}), 400
        
        existing = db.session.execute(
            text("SELECT id FROM products WHERE product_name = :product_name"),
            {"product_name": product_name}
        ).fetchone()
        
        if existing:
            logger.warning(f"Product already exists: {product_name}")
            return jsonify({"success": False, "message": "Product with this name already exists"}), 400
        
        insert_query = text("""
            INSERT INTO products (product_name, product_description, price, stock, category_id, image_url, discount, is_active)
            VALUES (:product_name, :description, :price, :stock, :category_id, :image_url, :discount, 1)
        """)
        
        db.session.execute(insert_query, {
            "product_name": product_name,
            "description": description,
            "price": price,
            "stock": stock,
            "category_id": category_id,
            "image_url": image_url,
            "discount": discount
        })
        
        db.session.commit()
        
        product_query = text("""
            SELECT id, product_name, product_description, price, stock, 
                   category_id, image_url, discount, is_active 
            FROM products 
            WHERE product_name = :product_name
        """)
        product = db.session.execute(
            product_query, {"product_name": product_name}
        ).fetchone()
        
        if not product:
            logger.error("Product not found after adding")
            return jsonify({"success": False, "message": "Product not found after operation"}), 500
        
        logger.info(f"Product added successfully: {product[0]}")
        return jsonify({
            "success": True,
            "message": "Product added successfully",
            "product": {
                "id": product[0],
                "product_name": product[1],
                "description": product[2],
                "price": float(product[3]),
                "stock": product[4],
                "category_id": product[5],
                "image_url": product[6],
                "discount": float(product[7]),
                "is_active": product[8]
            }
        }), 201
        
    except ValueError as ve:
        db.session.rollback()
        logger.error(f"Invalid data type: {str(ve)}")
        return jsonify({"success": False, "message": f"Invalid data type: {str(ve)}"}), 400
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding product: {str(e)}")
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500
