from flask import Blueprint, jsonify, request
from backend.extensions import db
import logging
from sqlalchemy.exc import SQLAlchemyError
from backend.routes.auth import token_required
from sqlalchemy import text
from decimal import Decimal
from backend.models import ProductReview

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
product_bp = Blueprint('product', __name__)

@product_bp.route('/products', methods=['GET'])
def get_products():
    try:

        category_id = request.args.get('category_id', default=None, type=int)

        if category_id:
            query = text("""
                SELECT p.id, p.product_name, p.product_description, p.price, p.stock, 
                       c.id as category_id, c.category_name, p.image_url, p.discount
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                WHERE p.category_id = :category_id AND p.is_active = 1
            """)
            result = db.session.execute(query, {'category_id': category_id})
        else:
            query = text("""
                SELECT p.id, p.product_name, p.product_description, p.price, p.stock, 
                       c.id as category_id, c.category_name, p.image_url, p.discount
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                WHERE p.is_active = 1
            """)
            result = db.session.execute(query)
        
        products = result.fetchall()

        formatted_products = []
        for row in products:
            formatted_products.append({
                "id": row[0],
                "product_name": row[1],
                "product_description": row[2],
                "price": float(row[3]) if isinstance(row[3], Decimal) else row[3],
                "stock": row[4],
                "category_id": row[5],
                "category_name": row[6],
                "image_url": row[7],
                "discount": float(row[8]) if isinstance(row[8], Decimal) else row[8]
            })
        
        logger.info(f"Retrieved {len(formatted_products)} products for category_id {category_id if category_id else 'all'}")
        return jsonify({'products': formatted_products}), 200

    except SQLAlchemyError as e:
        logger.error(f"SQLAlchemy error fetching products: {str(e)}")
        return jsonify({'message': 'Error fetching products', 'error': str(e)}), 500
    except Exception as e:
        logger.error(f"General error fetching products: {str(e)}")
        return jsonify({'message': 'Error flowing products', 'error': str(e)}), 500

@product_bp.route('/product/<string:product_name>', methods=['GET'])
@token_required
def get_product_details(current_user, product_name):
    try:

        page = request.args.get('page', default=1, type=int)
        per_page = request.args.get('per_page', default=10, type=int)

        if page < 1 or per_page < 1:
            logger.warning(f"Invalid pagination parameters for product {product_name}: page={page}, per_page={per_page}")
            return jsonify({
                'status': 'fail',
                'message': 'Invalid pagination parameters',
                'status_code': 4
            }), 400

        logger.debug(f"Fetching product details for: {product_name}")
        product_result = db.session.execute(text("""
            SELECT p.id as product_id, p.product_name, p.product_description, p.price, 
                   p.stock, c.category_name, p.image_url, p.discount
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            WHERE p.product_name = :product_name
        """), {'product_name': product_name})
        product_row = product_result.fetchone()

        if not product_row:
            logger.warning(f"Product not found: {product_name}")
            return jsonify({
                'status': 'fail',
                'message': 'Product not found',
                'status_code': 2
            }), 404

        product_id = product_row[0]
        price = product_row[3]
        discount = product_row[7]
        discounted_price = float(price) * (1 - float(discount) / 100)
        product_details = {
            'product_id': product_id,
            'product_name': product_row[1],
            'description': product_row[2],
            'price': float(price) if isinstance(price, Decimal) else price,
            'discounted_price': round(discounted_price, 2),
            'stock': product_row[4],
            'stock_status': 'In Stock' if product_row[4] > 0 else 'Out of Stock',
            'category_name': product_row[5],
            'image_url': product_row[6],
            'discount': float(discount) if isinstance(discount, Decimal) else discount
        }

        logger.debug(f"Fetching reviews for product: {product_name}, page: {page}, per_page: {per_page}")
        offset = (page - 1) * per_page
        reviews_result = db.session.execute(text("""
            SELECT pr.id as review_id, p.id as product_id, p.product_name, u.id as user_id, 
                   u.username, pr.rating, pr.review_text, pr.created_at, pr.image_url
            FROM product_reviews pr
            JOIN products p ON pr.product_id = p.id
            JOIN users u ON pr.user_id = u.id
            WHERE p.product_name = :product_name
            ORDER BY pr.created_at DESC
            LIMIT :per_page OFFSET :offset
        """), {'product_name': product_name, 'per_page': per_page, 'offset': offset})

        reviews = []
        for row in reviews_result:
            reviews.append({
                'review_id': row[0],
                'product_id': row[1],
                'product_name': row[2],
                'user_id': row[3],
                'username': row[4],
                'rating': float(row[5]) if isinstance(row[5], Decimal) else row[5],
                'review_text': row[6],
                'review_date': str(row[7]) if row[7] else '',
                'photo_url': row[8]
            })

        avg_rating_result = db.session.execute(text("""
            SELECT 
                AVG(CAST(rating AS FLOAT)) AS average_rating,
                COUNT(rating) AS total_reviews
            FROM product_reviews
            WHERE product_id = :product_id
        """), {'product_id': product_id}).fetchone()

        product_details['average_rating'] = round(float(avg_rating_result[0]), 1) if avg_rating_result[0] else 0
        product_details['total_reviews'] = avg_rating_result[1] if avg_rating_result[1] else 0

        existing_review = db.session.execute(
            text("SELECT 1 FROM product_reviews WHERE product_id = :product_id AND user_id = :user_id"),
            {'product_id': product_id, 'user_id': current_user.id}
        ).fetchone()
        can_review = not existing_review

        total_reviews = product_details['total_reviews']
        total_pages = (total_reviews + per_page - 1) // per_page if total_reviews > 0 else 1

        logger.info(f"Retrieved product details and {len(reviews)} reviews for product: {product_name}, page: {page}")
        return jsonify({
            'status': 'success',
            'message': 'Product details and reviews retrieved successfully.',
            'status_code': 0,
            'product': product_details,
            'reviews': reviews,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total_reviews': total_reviews,
                'total_pages': total_pages
            },
            'can_review': can_review
        }), 200

    except SQLAlchemyError as e:
        logger.error(f"SQLAlchemy error fetching product details for {product_name}: {str(e)}")
        return jsonify({'status': 'fail', 'message': f'Database error: {str(e)}'}), 500
    except Exception as e:
        logger.error(f"General error fetching product details for {product_name}: {str(e)}")
        return jsonify({'status': 'fail', 'message': f'Server error: {str(e)}'}), 500

@product_bp.route('/product/<string:product_name>/review', methods=['POST'])
@token_required
def add_product_review(current_user, product_name):

        try:

            data = request.get_json()
            rating = data.get('rating')
            review_text = data.get('review_text', '')
            username = current_user.username

            product = db.session.execute(
                text("SELECT id FROM products WHERE product_name = :product_name"),
                {'product_name': product_name}
            ).fetchone()
            
            if not product:
                return jsonify({'status': 'fail', 'message': 'Product not found'}), 404
            
            product_id = product[0]

            from datetime import datetime
            new_review = ProductReview(
                product_id=product_id,
                user_id=current_user.id,
                rating=rating,
                review_text=review_text,
                created_at=datetime.utcnow()
            )
            
            db.session.add(new_review)
            db.session.commit()
            
            logger.info(f"Review added by user {current_user.id} for product {product_name}")
            return jsonify({
                'status': 'success',
                'message': 'Review added successfully',
                'status_code': 0,
                'review': {
                    'review_id': new_review.id,
                    'product_id': product_id,
                    'user_id': current_user.id,
                    'rating': rating,
                    'review_text': review_text,
                    'review_date': new_review.created_at.isoformat()
                }
            }), 201

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"SQLAlchemy error adding review for product {product_name}: {str(e)}")
            return jsonify({'status': 'fail', 'message': f'Database error: {str(e)}'}), 500
        except Exception as e:
            db.session.rollback()
            logger.error(f"General error adding review for product {product_name}: {str(e)}")
            return jsonify({'status': 'fail', 'message': f'Server error: {str(e)}'}), 500
    
@product_bp.route('/product/<string:product_name>/review', methods=['DELETE'])
@token_required
def delete_review(current_user, product_name):
    try:

        product = db.session.execute(
            text("SELECT id FROM products WHERE product_name = :product_name"),
            {'product_name': product_name}
        ).fetchone()
        
        if not product:
            return jsonify({'message': 'Product not found'}), 404
        
        product_id = product[0]
        
        review = db.session.query(ProductReview).filter_by(
            product_id=product_id,
            user_id=current_user.id
        ).first()
        
        if not review:
            logger.warning(f"No review found for product {product_name} by user {current_user.username}")
            return jsonify({'message': 'No review found to delete'}), 404
        
        db.session.delete(review)
        db.session.commit()
        logger.info(f"Review deleted for product {product_name} by user {current_user.username}")
        return jsonify({'message': 'Review deleted successfully'}), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"SQLAlchemy error deleting review: {str(e)}")
        return jsonify({'message': 'Error deleting review', 'error': str(e)}), 500
    except Exception as e:
        db.session.rollback()
        logger.error(f"General error deleting review: {str(e)}")
        return jsonify({'message': 'Error deleting review', 'error': str(e)}), 500
    
@product_bp.route('/categories', methods=['GET'])
def get_categories():
    """Get all categories"""
    try:
        logger.info("Fetching all categories")
        
        result = db.session.execute(text("SELECT id, category_name FROM categories"))
        categories = result.fetchall()
        
        formatted_categories = []
        for row in categories:
            formatted_categories.append({
                "id": row[0],
                "category_name": row[1]
            })
        
        logger.info(f"Retrieved {len(formatted_categories)} categories")
        return jsonify({'categories': formatted_categories}), 200
        
    except Exception as e:
        logger.error(f"Error fetching categories: {str(e)}")
        return jsonify({'message': 'Error fetching categories', 'error': str(e)}), 500
