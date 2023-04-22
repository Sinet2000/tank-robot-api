import json
from app.shared.constants import JSON_FILE_PATH

def read_products_from_file():
    try:
        with open(JSON_FILE_PATH, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return []

def write_products_to_file(products):
    with open(JSON_FILE_PATH, "w") as file:
        json.dump(products, file)

def create_product(product):
    products = read_products_from_file()
    products.append(product.to_dict())
    write_products_to_file(products)
