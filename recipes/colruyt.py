"""Match ingredients to Colruyt products and derive per-unit prices.

Product data comes from the public GCS bucket `colruyt-products`, filled
nightly by github.com/BelgianNoise/colruyt-products-scraper. We stick to the
Everyday/Boni house brands and convert store prices to our canonical units
(EUR per kg / liter / piece).
"""

import json
import logging
import re
import urllib.request
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from core.constants import IngredientCategory, Unit
from recipes.models import Ingredient

logger = logging.getLogger(__name__)

BUCKET_LIST_URL = (
    "https://storage.googleapis.com/storage/v1/b/colruyt-products/o"
    "?prefix=colruyt-products/&fields=items(name)"
)
BUCKET_FILE_URL = "https://storage.googleapis.com/colruyt-products/{name}"

PREFERRED_BRANDS = ("EVERYDAY", "BONI")
# Fresh produce/meat/bread mostly carries no brand (or COLRUYT) in the dump;
# used as fallback when no Everyday/Boni product matches.
FALLBACK_BRANDS = ("", "COLRUYT")

KG_UNITS = ("KG", "K")

# Ingredient name (lowercased, parenthetical stripped) -> search term used
# against Colruyt product names. Only needed where our Flemish shorthand
# differs from the store naming.
SEARCH_ALIASES: dict[str, str] = {
    "ajuin": "uien",
    "look": "look gepeld",
    "kersttomaten": "kerstomaten",
    "rijpe tomaten": "tomaten",
    "tomaat": "tomaten",
    "banaan": "bananen",
    "peer": "peren",
    "citroen": "citroenen",
    "courgette": "courgetten",
    "sla": "kropsla",
    "witte kool": "witte kool",
    "erwtjes": "erwten",
    "gele pudding": "puddingpoeder",
    "soepdiertjes": "soepvermicelli",
    "vermicelli": "soepvermicelli",
    "curry manna": "currysaus",
    "tomatensaus van zonn": "tomatensaus",
    "boter": "melkerijboter",
    "gehakt": "gehakt",
    "hamburgers": "hamburger rund",
    "pistolets": "pistolet",
    "suiker": "kristalsuiker",
    "bastaardsuiker": "cassonade",
    "kinnekessuiker": "parelsuiker",
    "bloem": "bloem tarwe",
    "platte kaas": "plattekaas",
    "choco": "chocopasta",
    "room": "culinaire room",
    "spek": "spekblokjes",
    "friet": "frieten",
    "kroketten": "aardappelkroketten",
    "mini-loempia's": "loempia",
    "zoetzure saus": "zoetzure",
    "spuitwater": "bruisend water",
    "diepvriesfruit": "fruitmix",
    "fruitsla": "fruitmix",
    "geraspte kaas": "kaas gemalen",
    "woknoedels": "noedels",
    "koffie": "koffie gemalen",
    "kippenbouillon": "bouillon kip",
    "groentenbouillon": "bouillon groenten",
    "vleesbouillon": "bouillon rund",
    "tuinkruidenbouillon": "bouillon tuinkruiden",
}

# Fresh food categories look in the unbranded fresh assortment first.
FRESH_FIRST_CATEGORIES = (
    IngredientCategory.PRODUCE,
    IngredientCategory.MEAT,
    IngredientCategory.BAKERY,
)

_PACK_COUNT_RE = re.compile(r"(\d+)\s*(?:st\b|stuks)|(\d+)\s*x\s*\d", re.IGNORECASE)


@dataclass(frozen=True)
class Product:
    product_id: str
    long_name: str
    brand: str
    content: str
    basic_price: Decimal
    measurement_unit: str  # "KG", "L", ... (uppercased)
    unit_price: Decimal  # EUR per measurement unit

    @property
    def pack_count(self) -> int | None:
        """Number of pieces in the package ('eieren 30st', 'pistolet 8x90g')."""
        for text in (self.content, self.long_name):
            match = _PACK_COUNT_RE.search(text)
            if match:
                return int(match.group(1) or match.group(2))
        return None


def parse_products(raw: list[dict]) -> list[Product]:
    products = []
    for item in raw:
        price = item.get("price") or {}
        if not item.get("isAvailable") or not item.get("isPriceAvailable"):
            continue
        if not price.get("basicPrice"):
            continue
        products.append(
            Product(
                product_id=str(item.get("productId", "")),
                long_name=item.get("LongName") or item.get("name", ""),
                brand=(item.get("brand") or "").upper(),
                content=item.get("content") or "",
                basic_price=Decimal(str(price["basicPrice"])),
                measurement_unit=(price.get("measurementUnit") or "").upper(),
                unit_price=Decimal(str(price.get("measurementUnitPrice") or 0)),
            )
        )
    return products


def load_products(path: Path) -> list[Product]:
    with open(path, encoding="utf-8") as handle:
        return parse_products(json.load(handle))


def download_latest_dump(target: Path) -> Path:
    """Fetch the most recent product dump from the public bucket."""
    with urllib.request.urlopen(BUCKET_LIST_URL, timeout=60) as response:
        names = [item["name"] for item in json.load(response).get("items", [])]
    if not names:
        raise RuntimeError("No product dumps found in the colruyt-products bucket")
    latest = sorted(names)[-1]
    logger.info("Downloading %s", latest)
    with urllib.request.urlopen(
        BUCKET_FILE_URL.format(name=latest), timeout=300
    ) as response:
        target.write_bytes(response.read())
    return target


def product_details(product: Product) -> str:
    """Display string: name, container volume and [brand] ([LOS] = loose)."""
    detail = product.long_name
    if product.content and product.content not in product.long_name:
        detail += f" {product.content}"
    return f"{detail} [{product.brand or 'LOS'}]"


def search_term(ingredient: Ingredient) -> str:
    base = re.sub(r"\s*\(.*\)", "", ingredient.name).strip().lower()
    return SEARCH_ALIASES.get(base, base)


def unit_price_for(ingredient: Ingredient, product: Product) -> Decimal | None:
    """EUR per the ingredient's canonical unit, or None if incompatible."""
    if ingredient.unit == Unit.KG:
        if product.measurement_unit in KG_UNITS and product.unit_price > 0:
            return product.unit_price
        return None
    if ingredient.unit == Unit.LITER:
        if product.measurement_unit == "L" and product.unit_price > 0:
            return product.unit_price
        return None
    # piece: price per package item when a pack count is stated, else the
    # package price itself (one package = one piece: a bread, a jar, ...).
    count = product.pack_count
    if count:
        return (product.basic_price / count).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )
    # Loose weight articles (no fixed package content, price per kg) have no
    # meaningful per-piece price — e.g. loose tomatoes for a piece ingredient.
    if product.measurement_unit in KG_UNITS and not product.content.strip():
        return None
    return product.basic_price


def _cheapest(
    ingredient: Ingredient,
    products: list[Product],
    term_re: re.Pattern,
    brands: tuple[str, ...] | None,
) -> tuple[Product, Decimal] | None:
    best: tuple[Product, Decimal] | None = None
    for product in products:
        if brands is not None and product.brand not in brands:
            continue
        if not term_re.search(product.long_name.lower()):
            continue
        price = unit_price_for(ingredient, product)
        if price is None or price <= 0:
            continue
        if best is None or price < best[1]:
            best = (product, price)
    return best


def find_match(
    ingredient: Ingredient,
    products: list[Product],
    brands: tuple[str, ...] = PREFERRED_BRANDS,
) -> tuple[Product, Decimal] | None:
    """Cheapest unit-compatible product, searched in tiers. Fresh categories
    (produce/meat/bakery) look in the unbranded fresh assortment first, the
    rest in the Everyday/Boni house brands; any brand is the last resort."""
    term = search_term(ingredient)
    term_re = re.compile(r"\b" + re.escape(term) + r"\b")
    if not brands:  # any-brand mode
        return _cheapest(ingredient, products, term_re, None)
    if ingredient.category in FRESH_FIRST_CATEGORIES:
        tiers: list[tuple[str, ...] | None] = [FALLBACK_BRANDS, brands, None]
    else:
        tiers = [brands, FALLBACK_BRANDS, None]
    for tier in tiers:
        match = _cheapest(ingredient, products, term_re, tier)
        if match:
            return match
    return None
