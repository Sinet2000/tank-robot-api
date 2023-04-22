import graphene
from graphene import ObjectType, String, Int, Float
from app.models.product import Product
from app.external_services.file_service import read_products_from_file

class ProductType(ObjectType):
    id = Int()
    name = String()
    description = String()
    price = Float()
    stock = Int()

class Query(ObjectType):
    products = graphene.List(ProductType)

    def resolve_products(self, info):
        products_data = read_products_from_file()
        products = [Product(**data) for data in products_data]
        return products

schema = graphene.Schema(query=Query)
