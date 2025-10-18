from fastapi import APIRouter, Query
from backend.core.exceptions import db_error
from .schema import (
    CategoryIn, SupplierIn, IngredientIn, MenuItemIn, RecipeUpsert
)
from .service import (
    list_categories, create_category,
    list_suppliers, create_supplier, deactivate_supplier,
    ref_units, ref_locations, ref_users, ref_ingredients,
    create_ingredient, list_menu_items, create_menu_item,
    list_recipes, upsert_recipe, delete_recipe
)

router = APIRouter()

# ---- categories ----
@router.get("/categories")
def get_categories(type: str | None = Query(default=None, alias="type")):
    try:
        return list_categories(type)
    except Exception as e:
        raise db_error(e)

@router.post("/categories")
def post_category(body: CategoryIn):
    try:
        return create_category(body.name, body.type)
    except Exception as e:
        raise db_error(e)

# ---- suppliers ----
@router.get("/suppliers")
def get_suppliers(active_only: bool = False):
    try:
        return list_suppliers(active_only=active_only)
    except Exception as e:
        raise db_error(e)

@router.post("/suppliers")
def post_supplier(body: SupplierIn):
    try:
        return create_supplier(body.model_dump())
    except Exception as e:
        raise db_error(e)

@router.post("/suppliers/{supplier_id}/deactivate")
def post_supplier_deactivate(supplier_id: str):
    try:
        return deactivate_supplier(supplier_id)
    except Exception as e:
        raise db_error(e)

# ---- refs ----
@router.get("/ref/units")
def get_units():
    try:
        return ref_units()
    except Exception as e:
        raise db_error(e)

@router.get("/ref/locations")
def get_locations():
    try:
        return ref_locations()
    except Exception as e:
        raise db_error(e)

@router.get("/ref/users")
def get_users():
    try:
        return ref_users()
    except Exception as e:
        raise db_error(e)

@router.get("/ref/ingredients")
def get_ref_ingredients(active_only: bool = True):
    try:
        return ref_ingredients(active_only=active_only)
    except Exception as e:
        raise db_error(e)

# ---- ingredients ----
@router.post("/ingredients")
def post_ingredient(body: IngredientIn):
    try:
        return create_ingredient(body.model_dump())
    except Exception as e:
        raise db_error(e)

# ---- menu & recipes ----
@router.get("/menu_items")
def get_menu_items(active_only: bool = True):
    try:
        return list_menu_items(active_only=active_only)
    except Exception as e:
        raise db_error(e)

@router.post("/menu_items")
def post_menu_item(body: MenuItemIn):
    try:
        return create_menu_item(body.model_dump())
    except Exception as e:
        raise db_error(e)

@router.get("/recipes")
def get_recipes(menu_item_id: str):
    try:
        return list_recipes(menu_item_id)
    except Exception as e:
        raise db_error(e)

@router.post("/recipes")
def post_recipe(body: RecipeUpsert):
    try:
        return upsert_recipe(body.menu_item_id, body.ingredient_id, body.qty_required)
    except Exception as e:
        raise db_error(e)

@router.delete("/recipes/{menu_item_id}/{ingredient_id}")
def del_recipe(menu_item_id: str, ingredient_id: str):
    try:
        return delete_recipe(menu_item_id, ingredient_id)
    except Exception as e:
        raise db_error(e)
