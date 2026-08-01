"""Fill ingredient prices from the Colruyt product dump (Everyday/Boni).

Ingredients with a pinned `colruyt_product_id` follow that product; others
get the cheapest matching house-brand product. Unmatched ingredients are
listed for manual pricing in the admin.
"""

from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.constants import Shop
from recipes.colruyt import (
    download_latest_dump,
    find_match,
    load_products,
    product_details,
    unit_price_for,
)
from recipes.models import Ingredient


class Command(BaseCommand):
    help = "Update ingredient prices from the latest Colruyt product dump."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--file",
            help="Use a local dump JSON instead of downloading the latest",
        )
        parser.add_argument(
            "--any-brand",
            action="store_true",
            help="Also match products outside the Everyday/Boni house brands",
        )
        parser.add_argument(
            "--rematch",
            action="store_true",
            help="Clear existing product pins first and match from scratch",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        if options["file"]:
            path = Path(options["file"])
        else:
            path = Path(settings.BASE_DIR) / "colruyt-products.json"
            self.stdout.write("Downloading latest product dump…")
            download_latest_dump(path)
        products = load_products(path)
        self.stdout.write(f"{len(products)} available products loaded.")

        if options["rematch"]:
            cleared = Ingredient.objects.exclude(colruyt_product_id="").update(
                colruyt_product_id=""
            )
            self.stdout.write(f"Cleared {cleared} product pin(s).")

        by_id = {p.product_id: p for p in products}
        brands = () if options["any_brand"] else ("EVERYDAY", "BONI")
        now = timezone.now()
        matched, pinned, unmatched = [], [], []

        skipped_shops = 0
        for ingredient in Ingredient.objects.all():
            if ingredient.shop != Shop.COLRUYT:
                skipped_shops += 1
                continue
            if ingredient.colruyt_product_id:
                product = by_id.get(ingredient.colruyt_product_id)
                price = product and unit_price_for(ingredient, product)
                if product and price:
                    ingredient.price_per_unit = price
                    ingredient.product_details = product_details(product)
                    ingredient.price_updated = now
                    ingredient.save()
                    pinned.append(ingredient)
                else:
                    unmatched.append((ingredient, "pinned product gone"))
                continue

            result = find_match(ingredient, products, brands)
            if result is None:
                unmatched.append((ingredient, "no house-brand match"))
                continue
            product, price = result
            ingredient.price_per_unit = price
            ingredient.product_details = product_details(product)
            ingredient.colruyt_product_id = product.product_id
            ingredient.price_updated = now
            ingredient.save()
            matched.append((ingredient, product, price))
        if skipped_shops:
            self.stdout.write(
                f"{skipped_shops} non-Colruyt ingredient(s) left untouched."
            )

        for ingredient, product, price in matched:
            self.stdout.write(
                f"  {ingredient.name}: EUR {price}/{ingredient.unit} "
                f"<- {product.long_name} [{product.brand}]"
            )
        if pinned:
            self.stdout.write(f"{len(pinned)} pinned ingredient(s) refreshed.")
        if unmatched:
            self.stdout.write(self.style.WARNING("No price for:"))
            for ingredient, reason in unmatched:
                self.stdout.write(f"  - {ingredient.name} ({reason})")
        self.stdout.write(
            self.style.SUCCESS(
                f"Done: {len(matched)} matched, {len(pinned)} pinned, "
                f"{len(unmatched)} without price."
            )
        )
