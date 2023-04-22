from flask import Blueprint, request, jsonify
from app.models.product import Product
from app.external_services.file_service import create_product

product_api = Blueprint("product_api", __name__)

@product_api.route("/product", methods=["POST"])
def add_product():
    data = request.json
    product = Product(
        id=data["id"],
        name=data["name"],
        description=data["description"],
        price=data["price"],
        stock=data["stock"],
    )
    create_product(product)
    return jsonify({"message": "Product created"}), 201
