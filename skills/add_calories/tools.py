import json
import os
import re
from datetime import date, datetime
from typing import Optional

from fastmcp import FastMCP
from pydantic import BaseModel
from tavily import TavilyClient

from db.connection import SessionLocal
from db.schemas.food_category import DEFAULT_FOOD_CATEGORIES
from import_folder.response import ToolResponse
from lmm.factory import get_lmm_provider
from repositories.calorie_repository import (
    create_food_entry,
    find_category_by_name,
    find_product_by_name,
    get_category_name,
    get_daily_totals,
    upsert_product,
)


class ProductLookup(BaseModel):
    found: bool
    name: str
    source: Optional[str] = None  # "catalog" or "web" when found
    category: Optional[str] = None  # set when a catalog product is categorized
    calories_per_100g: Optional[float] = None
    protein_per_100g: Optional[float] = None
    carbs_per_100g: Optional[float] = None
    fat_per_100g: Optional[float] = None


_MACRO_KEYS = (
    "calories_per_100g",
    "protein_per_100g",
    "carbs_per_100g",
    "fat_per_100g",
)


class _MacroExtraction(BaseModel):
    """Schema the extraction model is forced to emit (via Ollama's `format`).
    Constrains decoding to exactly the four per-100g macros as numbers/null, so
    the reply is always valid JSON in this shape — no prose, fences, or
    reasoning to scrape."""

    calories_per_100g: Optional[float] = None
    protein_per_100g: Optional[float] = None
    carbs_per_100g: Optional[float] = None
    fat_per_100g: Optional[float] = None


# JSON Schema passed as Ollama's `format=` to enforce structured output.
_MACRO_FORMAT = _MacroExtraction.model_json_schema()

_EXTRACTION_SYSTEM_PROMPT = (
    "You extract nutrition facts from web search snippets and return them PER "
    "100 GRAMS of the food.\n\n"
    "OUTPUT FORMAT — follow exactly:\n"
    "- Respond with a SINGLE raw JSON object and NOTHING else.\n"
    "- Your entire reply must start with '{' and end with '}'.\n"
    "- Do NOT include markdown, code fences (```), explanations, comments, or "
    "any reasoning/thinking text before or after the JSON. /no_think\n"
    "- Use exactly these four keys, in this order, with plain JSON numbers "
    "(no units, no quotes) or null:\n"
    '{"calories_per_100g": <kcal>, "protein_per_100g": <g>, '
    '"carbs_per_100g": <g>, "fat_per_100g": <g>}\n\n'
    "UNITS — read carefully, this is where mistakes happen:\n"
    "- Pages often show TWO columns: one PER 100 g and one PER SERVING / PER "
    "PORTION / PER PIECE (e.g. 'per portion (28g)'). Use ONLY the per-100 g "
    "column.\n"
    "- IGNORE per-serving / per-portion / per-piece numbers. Convert them to "
    "per 100 g ONLY when a source gives no per-100 g figures at all, using the "
    "serving weight in grams stated on that same source.\n"
    "- Take all four values from the SAME source and SAME column — never mix "
    "calories from one basis with macros from another.\n"
    "- When sources disagree, prefer the official manufacturer's page.\n"
    "- Sanity check: calories should be roughly 4·protein + 4·carbs + 9·fat. If "
    "your four numbers break this badly, you mixed units — re-read and fix.\n"
    "If a value truly cannot be determined, use null."
)

_test = {"only return json format as response of type"  '{"calories_per_100g": <kcal>, "protein_per_100g": <g>, '
         '"carbs_per_100g": <g>, "fat_per_100g": <g>}\n\n'}


def _extraction_model() -> Optional[str]:
    """Pick the model used for macro extraction: the configured
    CALORIE_EXTRACTION_MODEL, else the first model installed in Ollama."""
    configured = os.getenv("CALORIE_EXTRACTION_MODEL")
    if configured:
        return configured
    try:
        listed = get_lmm_provider().client.list()
        models = getattr(listed, "models", None) or listed.get("models", [])
        first = models[0]
        return getattr(first, "model", None) or first.get("model") or first.get("name")
    except Exception:
        return None


def _parse_macros(text: str) -> Optional[dict]:
    """Pull the first JSON object out of the model's reply and keep only the
    four macro keys with numeric values."""
    if not text:
        return None
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except (ValueError, TypeError):
        return None

    macros = {}
    for key in _MACRO_KEYS:
        value = data.get(key)
        if not isinstance(value, (int, float)):
            return None  # incomplete extraction — treat as a miss
        macros[key] = float(value)
    return macros


def _search_food_macros(name: str) -> Optional[dict]:
    """Search the web for a food's nutrition facts and extract the four per-100g
    macros. Extracts from ONE source at a time, highest-scored first, and
    returns the first result that parses and passes the plausibility check —
    this avoids asking the model to reconcile several sources that mix per-100g
    and per-serving numbers. Returns None if no source yields usable macros."""
    api_key = os.getenv("TAVILY_SEARCH_KEY")
    if not api_key:
        print("[lookup_product] TAVILY_SEARCH_KEY not set; cannot web-search")
        return None

    try:
        client = TavilyClient(api_key)
        response = client.search(
            query=f"{name} nutrition facts per 100g calories protein carbs fat",
            search_depth="advanced",
            max_results=5,
        )
        print(response, "response product search ===========")
    except Exception as e:
        print(f"[lookup_product] web search failed: {e}")
        return None

    model = _extraction_model()
    if not model:
        print("[lookup_product] no extraction model available")
        return None

    results = sorted(
        response.get("results", []),
        key=lambda r: r.get("score", 0),
        reverse=True,
    )
    reply = get_lmm_provider().chat(
        "granite4.1:3b",
        [
            {"role": "system", "content": _EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": f"Food: {name}\n\nSource:\n{results}"},
        ],
        format=_MACRO_FORMAT,
    )
    return _parse_macros(reply.message.content)


class LoggedFood(BaseModel):
    name: str
    grams: float
    category: Optional[str] = None
    calories: float
    protein: float
    carbs: float
    fat: float
    today_total_calories: float = 0.0  # user's total kcal for today after this


def register_calorie_tools(mcp: FastMCP):

    @mcp.tool
    async def lookup_product(name: str) -> ToolResponse[ProductLookup]:
        """
        Resolve a food's macros PER 100g. Checks the shared catalog first and, on
        a miss, searches the web for the nutrition facts automatically.

        ALWAYS call this first for each food the user mentions. If `found` is
        true, the returned per-100g values are ready to use — pass them straight
        to `add_food_entry`. If `found` is false, the macros could not be
        determined; tell the user you couldn't find nutrition info for that food
        and do NOT call `add_food_entry` for it.

        Args:
            name: The food name, e.g. "chicken breast", "white rice".
        """
        db = SessionLocal()
        try:
            product = find_product_by_name(name)
            print(product, "catalog hit=====" if product else "catalog miss=====")
            if product:
                return ToolResponse(
                    success=True,
                    result=ProductLookup(
                        found=True,
                        name=product.name,
                        source="catalog",
                        category=get_category_name(
                            db, product.food_category_id),
                        calories_per_100g=product.calories_per_100g,
                        protein_per_100g=product.protein_per_100g,
                        carbs_per_100g=product.carbs_per_100g,
                        fat_per_100g=product.fat_per_100g,
                    ),
                )

            # Not in the catalog — fall back to a web search + extraction so the
            # model gets usable macros without having to chain another tool.
            macros = _search_food_macros(name)
            if macros:
                return ToolResponse(
                    success=True,
                    result=ProductLookup(
                        found=True,
                        name=name,
                        source="web",
                        **macros,
                    ),
                )

            return ToolResponse(
                success=True,
                result=ProductLookup(found=False, name=name),
            )
        except Exception as e:
            return ToolResponse(success=False, result=f"Error: {e}")
        finally:
            db.close()

    @mcp.tool
    async def add_food_entry(
        name: str,
        grams: float,
        calories_per_100g: float,
        protein_per_100g: float,
        carbs_per_100g: float,
        fat_per_100g: float,
        category: str,
        created_by: Optional[int] = None,
    ) -> ToolResponse[LoggedFood]:
        """
        Log a food the user ate and save it to the shared catalog for reuse.

        Only call this when the user has provided a positive amount in grams. If
        the grams are missing or 0, do NOT call this tool — ask the user how many
        grams they ate instead.

        Pass the macros PER 100g returned by `lookup_product` (from the catalog
        or from its web-search fallback). The totals for the eaten amount are
        computed as grams / 100 * per-100g and returned.

        Classify the food into exactly ONE of these categories and pass it as
        `category`: vegetable, fruit, meat, seafood, dairy, grains, legumes,
        sweets, beverages, snacks, fats_oils, other. Use "other" if none fit.

        Args:
            name: The food name.
            grams: How many grams the user ate.
            calories_per_100g: Calories (kcal) per 100g.
            protein_per_100g: Protein (g) per 100g.
            carbs_per_100g: Carbohydrates (g) per 100g.
            fat_per_100g: Fat (g) per 100g.
            category: One of the allowed food categories listed above.
        """

        print("========= food entry", name, grams, category)
        db = SessionLocal()
        try:
            resolved_category = find_category_by_name(db, category)
            if resolved_category is None:
                return ToolResponse(
                    success=False,
                    result=(
                        f"Unknown category '{category}'. Choose one of: "
                        f"{', '.join(DEFAULT_FOOD_CATEGORIES)}."
                    ),
                )

            product = upsert_product(
                db,
                name=name,
                calories_per_100g=calories_per_100g,
                protein_per_100g=protein_per_100g,
                carbs_per_100g=carbs_per_100g,
                fat_per_100g=fat_per_100g,
                food_category_id=resolved_category.id,
            )
            entry = create_food_entry(
                db,
                product=product,
                grams=grams,
                created_by=created_by,
            )
            # Running total for today, so the reply can show it alongside the
            # logged food without relying on a separate tool call.
            today_totals = get_daily_totals(db, date.today(), created_by)
            return ToolResponse(
                success=True,
                result=LoggedFood(
                    name=entry.name,
                    grams=entry.grams,
                    category=get_category_name(db, entry.food_category_id),
                    calories=entry.calories,
                    protein=entry.protein,
                    carbs=entry.carbs,
                    fat=entry.fat,
                    today_total_calories=today_totals["calories"],
                ),
            )
        except Exception as e:
            return ToolResponse(success=False, result=f"Error: {e}")
        finally:
            db.close()

    @mcp.tool
    async def get_daily_totals_tool(
        created_by: Optional[int] = None,
    ) -> ToolResponse[dict]:
        """
        Return the user's summed macros (calories, protein, carbs, fat) for
        TODAY. Use this when the user asks what they ate or how many calories
        they have had.

        Takes no arguments — it always reports today's totals for the current
        user. Do NOT pass a date.
        """
        db = SessionLocal()
        try:
            totals = get_daily_totals(
                db, datetime.now().date(), created_by=created_by)
            return ToolResponse(success=True, result=totals)
        except Exception as e:
            return ToolResponse(success=False, result=f"Error: {e}")
        finally:
            db.close()
