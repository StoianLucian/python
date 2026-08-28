from fastapi import APIRouter, Depends, Query

from repositories import *
from repositories.calorie_repository import find_product_by_name
from skills.add_calories.tools import ProductLookup, _search_food_macros

router = APIRouter(
    prefix="/calories",
    tags=["calories"],
)


@router.get("/lookup")
def lookup_food_macros(
    name: str = Query(..., min_length=1, description="Food name, e.g. 'chicken breast'"),
    user=Depends(check_token),
):
    """Look up a food's per-100g macros via web search + extraction.

    Wraps `_search_food_macros`: searches the web for the food and returns the
    first source whose extracted macros pass the plausibility check. Returns
    `found: false` when no source yields usable macros.

    This is a plain (non-async) handler on purpose — `_search_food_macros` does
    blocking network + model calls, so FastAPI runs it in a threadpool and the
    event loop is not blocked.
    """
    # product = find_product_by_name(name)
    # print(product, "-===========")
    macros = _search_food_macros(name)
    if macros is None:
        return ProductLookup(found=False, name=name)
    return macros
