"""Import recipes from the 2025/2026 draaiboek kookploeg documents.

Base headcount for every recipe = camp 2025: 27 under-12 + 44 twelve-plus
(Toppers/Kerels/Aspi's + leiding/kookploeg/technische ploeg), 71 people total.
Quantities prefer the 2025 draaiboek ("as cooked"); pack/jar counts are mapped
to piece with the pack size in the ingredient name. Items without usable
quantities are listed in the recipe notes for later review.

Idempotent: existing recipes (matched by name) are left untouched.
"""

import logging
from decimal import Decimal
from typing import Any

from django.core.management.base import BaseCommand

from core.constants import DishType, IngredientCategory, Unit
from recipes.models import Ingredient, Recipe, RecipeIngredient, RecipeStep

logger = logging.getLogger(__name__)

BASE_CHILDREN = 27
BASE_TEENS = 44

P = Unit.PIECE
KG = Unit.KG
L = Unit.LITER

PRODUCE = IngredientCategory.PRODUCE
DAIRY = IngredientCategory.DAIRY
MEAT = IngredientCategory.MEAT
BAKERY = IngredientCategory.BAKERY
DRY = IngredientCategory.DRY_GOODS
OTHER = IngredientCategory.OTHER

# name -> (unit, category)
INGREDIENTS: dict[str, tuple[str, str]] = {
    # Produce
    "Appel": (P, PRODUCE),
    "Peer": (P, PRODUCE),
    "Watermeloen": (P, PRODUCE),
    "Banaan": (P, PRODUCE),
    "Nectarine": (P, PRODUCE),
    "Courgette": (P, PRODUCE),
    "Prei (stronk)": (P, PRODUCE),
    "Ajuin": (KG, PRODUCE),
    "Aardappelen": (KG, PRODUCE),
    "Wortelen": (KG, PRODUCE),
    "Selder (struik)": (P, PRODUCE),
    "Komkommer": (P, PRODUCE),
    "Tomaat": (P, PRODUCE),
    "Kersttomaten": (KG, PRODUCE),
    "Sla (krop)": (P, PRODUCE),
    "IJsbergsla (krop)": (P, PRODUCE),
    "Paprika": (KG, PRODUCE),
    "Champignons": (KG, PRODUCE),
    "Spinazie (diepvries)": (KG, PRODUCE),
    "Citroen": (P, PRODUCE),
    "Look (teen)": (P, PRODUCE),
    "Verse peterselie (bussel)": (P, PRODUCE),
    "Sjalot": (P, PRODUCE),
    "Witte kool": (KG, PRODUCE),
    "Diepvriesfruit": (KG, PRODUCE),
    "Fruitsla (diepvries)": (KG, PRODUCE),
    "Mais": (KG, PRODUCE),
    "Erwtjes (potje)": (P, PRODUCE),
    # Dairy
    "Melk": (L, DAIRY),
    "Boter": (KG, DAIRY),
    "Geraspte kaas": (KG, DAIRY),
    "Platte kaas (vol)": (KG, DAIRY),
    "Kruidenkaas (potje)": (P, DAIRY),
    "Eieren": (P, DAIRY),
    "Yoghurt": (KG, DAIRY),
    "Vanille-ijs": (L, DAIRY),
    "Spuitwater": (L, OTHER),
    # Meat & fish
    "Kipfilet": (KG, MEAT),
    "Gehakt": (KG, MEAT),
    "Spek": (KG, MEAT),
    "Soepballetjes": (KG, MEAT),
    "Hespenblokjes": (KG, MEAT),
    "Pitavlees": (KG, MEAT),
    "Stoofvlees": (KG, MEAT),
    "BBQ-vlees (pak)": (P, MEAT),
    "Hamburgers": (P, MEAT),
    "Kipschnitzel": (P, MEAT),
    "Visburgers (groot)": (P, MEAT),
    "Calamaris (pak)": (P, MEAT),
    # Bakery
    "Pistolets": (P, BAKERY),
    "Turks brood": (P, BAKERY),
    "Wit brood": (P, BAKERY),
    "Grijs brood": (P, BAKERY),
    "Wraps": (P, BAKERY),
    "Prinskoeken (pak)": (P, BAKERY),
    "Smeerkaas": (KG, DAIRY),
    # Dry goods & rest
    "Rijst": (KG, DRY),
    "Spaghetti": (KG, DRY),
    "Macaroni": (KG, DRY),
    "Spirelli": (KG, DRY),
    "Woknoedels": (KG, DRY),
    "Vermicelli": (KG, DRY),
    "Soepdiertjes": (KG, DRY),
    "Bloem": (KG, DRY),
    "Zelfrijzende bloem": (KG, DRY),
    "Vloeiende bloem": (KG, DRY),
    "Suiker": (KG, DRY),
    "Vanillesuiker (pakje)": (P, DRY),
    "Kinnekessuiker (pak)": (P, DRY),
    "Bastaardsuiker (pak)": (P, DRY),
    "Bakpoeder (zakje)": (P, DRY),
    "Cornflakes (doos)": (P, DRY),
    "Kroketten": (KG, DRY),
    "Friet": (KG, DRY),
    "Curry Manna (bokaal 355 g)": (P, DRY),
    "Zoetzure saus (fles 500 g)": (P, DRY),
    "Tomatensaus Van Zonn (zak)": (P, DRY),
    "Tomatenpuree (blik/potje)": (P, DRY),
    "Passata": (L, DRY),
    "Kippenbouillon": (L, DRY),
    "Groentenbouillon": (L, DRY),
    "Tuinkruidenbouillon (blokje)": (P, DRY),
    "Gele pudding (zakje)": (P, DRY),
    "Chocomousse (zak)": (P, DRY),
    "Witte bonen (bokaal)": (P, DRY),
    "Rode bonen": (KG, DRY),
    "Mayonaise": (L, DRY),
    "Mexicaanse kruiden": (KG, DRY),
    "Sojasaus": (L, DRY),
    "Ahornsiroop (bus)": (P, DRY),
    "Choco": (KG, DRY),
    "Confituur": (KG, DRY),
    "Cacaopoeder": (KG, DRY),
    "Koffie (gemalen)": (KG, DRY),
    "Mini-loempia's": (P, DRY),
    "Wokgroenten (diepvries)": (KG, PRODUCE),
    "Julienne soepgroenten (zak)": (P, PRODUCE),
    "Pitasaus (bus)": (P, DRY),
    "Calippo": (P, OTHER),
    "Ananas (groot blik)": (P, DRY),
    "Citroensap (fles)": (P, DRY),
}

STANDARD_BREAKFAST_NOTE = (
    "Standaard: brood van de bakker, choco, confituur, smeerkaas, boter, melk, "
    "cacaopoeder, suiker, koffie. Hoeveelheden nog aan te vullen."
)

# Recipe spec: name, dish_type, ingredients [(name, qty)], steps [(text, min)],
# notes. Source marks the draaiboek day it came from.
RECIPES: list[dict[str, Any]] = [
    # ---------- Ontbijt ----------
    {
        "name": "Standaardontbijt",
        "dish_type": DishType.BREAD_MEAL,
        "ingredients": [
            ("Wit brood", "8"),
            ("Grijs brood", "6"),
            ("Melk", "13"),
            ("Cacaopoeder", "0.6"),
            ("Smeerkaas", "0.4"),
            ("Boter", "1.5"),
            ("Choco", "1.2"),
            ("Confituur", "0.6"),
            ("Suiker", "0.3"),
            ("Koffie (gemalen)", "0.2"),
        ],
        "notes": "Afgeleid uit aankopen Klein Kamp (58 pers. ~ 50 porties, "
        "~10 melk/beleg-maaltijden per kamp), geschaald naar 71 pers. "
        "Boter/choco/confituur/suiker/koffie: schatting volgens richtlijnen "
        "koken-voor-groepen — nazicht gewenst.",
    },
    {
        "name": "Beleg (kaas, hesp, saucis)",
        "dish_type": DishType.BREAD_MEAL_EXTRA,
        "notes": "Extra bij standaardontbijt; hoeveelheden nog aan te vullen.",
    },
    {
        "name": "Cornflakes",
        "dish_type": DishType.BREAD_MEAL_EXTRA,
        "ingredients": [("Cornflakes (doos)", "8")],
        "notes": "Extra bij standaardontbijt. Ook: fruitsap en yoghurtpotjes "
        "(aantallen aan te vullen).",
    },
    {
        "name": "Speculaas & hagelslag",
        "dish_type": DishType.BREAD_MEAL_EXTRA,
        "notes": "Extra bij standaardontbijt; hagelslag in confituurpotten "
        "+ lepel. Hoeveelheden nog aan te vullen.",
    },
    {
        "name": "Eieren (ontbijt)",
        "dish_type": DishType.BREAD_MEAL_EXTRA,
        "ingredients": [("Eieren", "130")],
        "notes": "Extra bij standaardontbijt, met kaas en hesp.",
    },
    {
        "name": "Brunch",
        "dish_type": DishType.BREAD_MEAL,
        "ingredients": [
            ("Eieren", "132"),
            ("Spek", "4"),
            ("Ahornsiroop (bus)", "2"),
            ("Bloem", "1.4"),
            ("Bakpoeder (zakje)", "7"),
            ("Melk", "1.8"),
            ("Fruitsla (diepvries)", "1"),
        ],
        "notes": STANDARD_BREAKFAST_NOTE
        + " Brunch-extra's: speculaas, kaas en hesp, salami, hagelslag, "
        "yoghurtpotjes, American pancakes (bloem/bakpoeder/melk/12 eieren "
        "zitten in de aantallen).",
        "source": "2025 dag 8",
    },
    {
        "name": "Spek & ei",
        "dish_type": DishType.BREAD_MEAL_EXTRA,
        "notes": "Extra bij standaardontbijt. Uit menu 2026; hoeveelheden "
        "nog aan te vullen.",
    },
    # ---------- Soepen ----------
    {
        "name": "Courgettesoep",
        "dish_type": DishType.SOUP,
        "ingredients": [
            ("Courgette", "4"),
            ("Ajuin", "1.5"),
            ("Aardappelen", "1"),
            ("Kippenbouillon", "5.5"),
            ("Spek", "3"),
        ],
        "steps": [
            ("2 ketels water koken.", 15),
            ("Uien schillen en in grote stukken snijden; boter in ketel smelten.", 15),
            ("Ajuin stoven, courgette afbakken.", 15),
            ("Aardappelen in blokjes snijden en toevoegen met de courgettes.", 10),
            ("Bouillon smelten in kom en toevoegen.", 5),
            ("Als groenten gaar zijn: soep mixen, heet water toevoegen tot 11 l.", 15),
            ("Proeven en bijkruiden met peper en zout.", 5),
        ],
        "notes": "11 liter soep voor 71 personen.",
        "source": "2025 dag 1",
    },
    {
        "name": "Preisoep",
        "dish_type": DishType.SOUP,
        "ingredients": [
            ("Ajuin", "0.5"),
            ("Selder (struik)", "1"),
            ("Prei (stronk)", "6"),
            ("Wortelen", "1"),
            ("Aardappelen", "1"),
            ("Witte bonen (bokaal)", "3"),
            ("Soepdiertjes", "1"),
            ("Groentenbouillon", "5.5"),
        ],
        "steps": [
            ("Prei in grote stukken snijden en goed wassen.", 15),
            ("Ajuin schillen, grote stukken snijden en aanstoven.", 15),
            ("Prei en aardappel toevoegen.", 5),
            ("Bouillon smelten, soep koken en mixen.", 30),
            ("Brood in blokjes snijden en bakken in boter (croutons).", 15),
        ],
        "notes": "11 liter soep voor 71 personen.",
        "source": "2025 dag 6",
    },
    {
        "name": "Kippensoep met vermicelli",
        "dish_type": DishType.SOUP,
        "ingredients": [
            ("Julienne soepgroenten (zak)", "2"),
            ("Vermicelli", "1"),
            ("Kippenbouillon", "5.5"),
            ("Kipfilet", "1.2"),
            ("Verse peterselie (bussel)", "1"),
        ],
        "steps": [
            ("Kookvocht van de kipfilets opwarmen; kookt -> groenten toevoegen.", 10),
            ("Water toevoegen tot 11 l.", 5),
            (
                "Kipfilets toevoegen; kookt -> vermicelli toevoegen en "
                "+-5 minuten laten koken, daarna afzetten.",
                10,
            ),
            ("Peterselie spoelen, knippen en als afwerking toevoegen.", 10),
        ],
        "notes": "11 liter soep voor 71 personen. Kipfilet = 6 filets (~200 g/stuk).",
        "source": "2025 dag 2",
    },
    {
        "name": "Groentesoep met diertjes",
        "dish_type": DishType.SOUP,
        "ingredients": [
            ("Ajuin", "1"),
            ("Selder (struik)", "2"),
            ("Prei (stronk)", "3"),
            ("Wortelen", "2"),
            ("Aardappelen", "1"),
            ("Witte bonen (bokaal)", "3"),
            ("Soepdiertjes", "1"),
            ("Groentenbouillon", "8"),
        ],
        "steps": [
            (
                "Soepgroenten in kleine stukjes snijden; selderblaadjes en enkel "
                "heel dunne steeltjes.",
                30,
            ),
            ("Bonen pas aan het einde toevoegen, niet mee laten doorkoken.", 5),
        ],
        "notes": "16 liter soep voor 71 personen.",
        "source": "2025 dag 3",
    },
    {
        "name": "Tomatensoep met balletjes",
        "dish_type": DishType.SOUP,
        "ingredients": [
            ("Melk", "4"),
            ("Vloeiende bloem", "0.5"),
            ("Tomatenpuree (blik/potje)", "8"),
            ("Kippenbouillon", "8"),
            ("Tuinkruidenbouillon (blokje)", "5"),
            ("Ajuin", "1.5"),
        ],
        "steps": [
            (
                "Bloem met volle melk oproeren zodat de bloem weg is "
                "(nog niet op het vuur).",
                10,
            ),
            ("Vuur opzetten; tomatenpuree en passata toevoegen.", 10),
            ("Water bijvoegen (12 l).", 5),
            ("Balletjes als laatste toevoegen.", 10),
            (
                "Indien te lopend: soep in aparte kom met extra bloem oproeren en "
                "terug toevoegen.",
                None,
            ),
        ],
        "notes": "16 liter soep voor 71 personen. Soepballetjes: "
        "hoeveelheid nog aan te vullen.",
        "source": "2025 dag 5",
    },
    {
        "name": "Paprikasoep",
        "dish_type": DishType.SOUP,
        "ingredients": [
            ("Paprika", "4"),
            ("Ajuin", "1.5"),
            ("Kruidenkaas (potje)", "3"),
            ("Tuinkruidenbouillon (blokje)", "36"),
            ("Groentenbouillon", "8"),
            ("Tomatenpuree (blik/potje)", "4"),
        ],
        "notes": "16 liter soep voor 71 personen. 20 rode paprika's ≈ 4 kg. "
        "Extra: paprikapoeder (potje).",
        "source": "2025 dag 8",
    },
    {
        "name": "Komkommersoep (koud)",
        "dish_type": DishType.SOUP,
        "ingredients": [("Komkommer", "24")],
        "notes": "Koud serveren; verdere ingrediënten nog aan te vullen.",
        "source": "2025 dag 10",
    },
    # ---------- Middag (hoofdgerechten) ----------
    {
        "name": "Balletjes in tomatensaus met puree",
        "dish_type": DishType.HOT_MEAL,
        "ingredients": [
            ("Aardappelen", "17"),
            ("Gehakt", "9"),
            ("Ajuin", "0.8"),
            ("Tomatensaus Van Zonn (zak)", "3"),
        ],
        "steps": [
            ("Aardappelen schillen met dunschiller.", 45),
            ("Aardappelen opzetten en gaar laten koken.", 30),
            ("Ajuin snijden en aanstoven.", 15),
            ("Gehaktballen langzaam opwarmen, bijkruiden met peper en zout.", 30),
            (
                "Melk en boter opwarmen met nootmuskaat/peper/zout; eieren "
                "loskloppen; aardappelen stoempen met het mengsel.",
                30,
            ),
        ],
        "notes": "Puree-extra's (melk, ei, boter, nootmuskaat): hoeveelheden "
        "nog aan te vullen. 5 uien ≈ 0.8 kg.",
        "source": "2025 dag 2",
    },
    {
        "name": "Visburgers met spinaziepuree",
        "dish_type": DishType.HOT_MEAL,
        "ingredients": [
            ("Visburgers (groot)", "56"),
            ("Citroensap (fles)", "1"),
            ("Aardappelen", "11"),
            ("Spinazie (diepvries)", "3"),
            ("Boter", "1"),
            ("Mayonaise", "1"),
            ("Sjalot", "2"),
            ("Verse peterselie (bussel)", "1"),
        ],
        "notes": "Tartaarsaus = mayonaise + sjalot + peterselie + bieslook. "
        "Puree-extra's (melk, ei, nootmuskaat) nog aan te vullen. "
        "Spinazie: 2 pakken diepvries van 1,5 kg.",
        "source": "2025 dag 6",
    },
    {
        "name": "Wraps kip-kebab",
        "dish_type": DishType.HOT_MEAL,
        "ingredients": [
            ("Wraps", "50"),
            ("Kipschnitzel", "30"),
            ("IJsbergsla (krop)", "3"),
            ("Kersttomaten", "3"),
            ("Paprika", "3"),
            ("Wortelen", "1.5"),
            ("Witte kool", "0.5"),
        ],
        "notes": "Paprika's grillen. Looksaus nog aan te vullen.",
        "source": "2026 dag 3",
    },
    {
        "name": "Wraps burrito",
        "dish_type": DishType.HOT_MEAL,
        "ingredients": [
            ("Wraps", "50"),
            ("Gehakt", "5"),
            ("Passata", "3"),
            ("Rode bonen", "2"),
            ("Mais", "0.8"),
            ("Ajuin", "1.5"),
            ("Paprika", "2"),
            ("Look (teen)", "9"),
            ("Tomatenpuree (blik/potje)", "1"),
            ("Mexicaanse kruiden", "0.2"),
        ],
        "notes": "Tomatenpuree: 500 g. Look: 8 à 10 teentjes naar smaak.",
        "source": "2026 dag 3",
    },
    {
        "name": "Kroketten met videe",
        "dish_type": DishType.HOT_MEAL,
        "ingredients": [
            ("Kroketten", "15"),
            ("Vloeiende bloem", "2"),
            ("Melk", "8"),
            ("Tuinkruidenbouillon (blokje)", "12"),
            ("Soepballetjes", "5"),
            ("Kipfilet", "7"),
            ("Citroen", "2"),
            ("Sla (krop)", "4"),
            ("Komkommer", "8"),
            ("Tomaat", "18"),
            ("Champignons", "5"),
        ],
        "steps": [
            ("Kipfilets koken, kookwater bijhouden; kip in blokjes snijden.", 30),
            ("Soepballetjes even koken; groenten snijden.", 30),
            ("Videe in 2 keer maken: boter smelten, vloeiende bloem toevoegen.", 15),
            (
                "Melk en vocht al roerend toevoegen; op smaak brengen met " "bouillon.",
                20,
            ),
            ("Kip en balletjes als laatste toevoegen.", 10),
            ("Kroketten bakken en warmhouden in de oven.", 45),
        ],
        "notes": "Extra: 12 kippenbouillonblokjes om de kipfilet in te koken; "
        "1,5 l kipkookwater voor de smaak.",
        "source": "2025 dag 5",
    },
    {
        "name": "Calamaris en mini-loempia's",
        "dish_type": DishType.HOT_MEAL,
        "ingredients": [
            ("Calamaris (pak)", "4"),
            ("Mini-loempia's", "30"),
        ],
        "source": "2025 dag 4",
    },
    {
        "name": "Wokmie met kip",
        "dish_type": DishType.HOT_MEAL,
        "ingredients": [
            ("Kipfilet", "8"),
            ("Woknoedels", "6.2"),
            ("Wokgroenten (diepvries)", "10"),
            ("Sojasaus", "2.5"),
        ],
        "source": "2025 dag 4",
    },
    {
        "name": "Friet met stoofvlees",
        "dish_type": DishType.HOT_MEAL,
        "ingredients": [
            ("Friet", "30"),
            ("Stoofvlees", "15"),
            ("Ajuin", "1.1"),
            ("Look (teen)", "3"),
            ("Groentenbouillon", "5"),
            ("Sla (krop)", "4"),
            ("Komkommer", "10"),
            ("Tomaat", "25"),
        ],
        "notes": "7 ajuinen ≈ 1,1 kg. Bouillon mag ook vleesbouillon zijn.",
        "source": "2025 dag 9",
    },
    {
        "name": "Macaroni met kaas en hesp",
        "dish_type": DishType.HOT_MEAL,
        "ingredients": [
            ("Macaroni", "8.5"),
            ("Melk", "9"),
            ("Boter", "1.5"),
            ("Vloeiende bloem", "2"),
            ("Geraspte kaas", "2"),
            ("Hespenblokjes", "4"),
        ],
        "notes": "Hoeveelheid macaroni controleren (opmerking draaiboek).",
        "source": "2025 dag 10",
    },
    {
        "name": "Wortelpuree met worst",
        "dish_type": DishType.HOT_MEAL,
        "notes": "Uit menu 2026 dag 7; hoeveelheden nog aan te vullen.",
    },
    # ---------- Avond (warme maaltijden) ----------
    {
        "name": "Rijst met kip, curry en zoetzure saus",
        "dish_type": DishType.HOT_MEAL,
        "ingredients": [
            ("Kipfilet", "11"),
            ("Rijst", "6"),
            ("Curry Manna (bokaal 355 g)", "10"),
            ("Zoetzure saus (fles 500 g)", "7"),
        ],
        "steps": [
            ("Kipfilets koken (+-20 minuten).", 20),
            (
                "Warm houden: kipfilets in ketel tussen aluminiumfolie; "
                "bestrooien met kippenkruiden en bakken.",
                20,
            ),
            ("Kookvocht bewaren in emmer en in koelkast voor kippensoep.", 5),
            ("Saus opwarmen, regelmatig roeren zodat niets aanbrandt.", 15),
            ("Rijstzakjes in kokend water tot ze helemaal gezwollen zijn.", 20),
        ],
        "notes": "55 kipfilets van 200 g = 11 kg. Rijst: 120 g per persoon. "
        "Opmerking 2026: 'te veel kiek' — hoeveelheid kip herbekijken.",
        "source": "2025 dag 1",
    },
    {
        "name": "BBQ met groenten",
        "dish_type": DishType.HOT_MEAL,
        "ingredients": [
            ("BBQ-vlees (pak)", "7"),
            ("Tomaat", "30"),
            ("Komkommer", "10"),
            ("Sla (krop)", "5"),
            ("Wortelen", "3"),
            ("Eieren", "51"),
            ("Aardappelen", "9"),
            ("Spirelli", "3"),
        ],
        "steps": [
            ("Sla wassen en uitzwieren, bewaren in emmer in koelkast.", 20),
            ("Komkommer in dunne schijfjes; tomaten in 6 partjes.", 20),
            ("Aardappelen schillen en heel koken (niet plat koken).", 40),
            ("Eieren hard koken.", 15),
            ("Spirelli koken met 2 blokjes tuinkruiden.", 20),
            ("Wortelen raspen en besprenkelen met citroensap.", 15),
            ("BBQ aanmaken; aardappelsla en pasta afwerken.", 45),
        ],
        "notes": "Aardappelsla: mayo, zout, bieslook, uien. Koude pasta: mayo. "
        "Saus: mayo en ketchup. Hoeveelheden sauzen aan te vullen.",
        "source": "2025 dag 3",
    },
    {
        "name": "Spaghetti",
        "dish_type": DishType.HOT_MEAL,
        "ingredients": [
            ("Spaghetti", "10"),
            ("Gehakt", "8"),
            ("Geraspte kaas", "2"),
            ("Paprika", "2.4"),
            ("Courgette", "5"),
            ("Wortelen", "3.5"),
            ("Ajuin", "1.7"),
            ("Passata", "6"),
            ("Tomatenpuree (blik/potje)", "16"),
            ("Tuinkruidenbouillon (blokje)", "13"),
            ("Look (teen)", "15"),
        ],
        "steps": [
            ("Gehakt bakken voor de saus.", 20),
            ("Ajuin en look aanstoven; wortelen, paprika en courgette toevoegen.", 20),
            ("Bouillon in water smelten en toevoegen; 10 minuten laten stoven.", 15),
            ("Passata en tomatenpuree toevoegen.", 10),
            (
                "Vlees toevoegen; afwerken met oregano, basilicum, peper en zout.",
                10,
            ),
            ("Indien te dun: vloeiende bloem; te veel puree-smaak: melk.", None),
        ],
        "notes": "12 gele paprika's ≈ 2,4 kg; 11 ajuinen ≈ 1,7 kg; 12 brikken "
        "passata ≈ 6 l; 1,5 bol look ≈ 15 tenen. Extra: tabasco, oregano, "
        "basilicum, spaghettikruiden. Gehakt 2026: 5 kg i.p.v. 8 kg.",
        "source": "2025 dag 7",
    },
    {
        "name": "Pita",
        "dish_type": DishType.HOT_MEAL,
        "ingredients": [
            ("Turks brood", "38"),
            ("Pitavlees", "15"),
            ("Komkommer", "10"),
            ("Tomaat", "28"),
            ("Wortelen", "2"),
            ("Sla (krop)", "3"),
            ("Mais", "0.6"),
            ("Erwtjes (potje)", "2"),
            ("Pitasaus (bus)", "4"),
        ],
        "notes": "Extra: mayo, ketchup, bakboter. 2 potjes mais ≈ 0,6 kg.",
        "source": "2025 dag 8",
    },
    {
        "name": "Hamburgers (kampvuur)",
        "dish_type": DishType.HOT_MEAL,
        "ingredients": [
            ("Hamburgers", "115"),
            ("Pistolets", "115"),
            ("Ajuin", "5"),
        ],
        "notes": "Extra: mayo en ketchup. 2026 rekende 70 stuks voor 58 man.",
        "source": "2025 dag 10",
    },
    # ---------- Broodmaaltijden ----------
    {
        "name": "Broodmaaltijd",
        "dish_type": DishType.BREAD_MEAL,
        "notes": "Brood van de bakker + choco, confituur, smeerkaas, boter, "
        "cacaopoeder, suiker, melk, koffie. Hoeveelheden nog aan te vullen.",
    },
    {
        "name": "Broodmaaltijd + baksaucis",
        "dish_type": DishType.BREAD_MEAL,
        "notes": "Broodmaaltijd + baksaucis; hoeveelheden nog aan te vullen.",
    },
    {
        "name": "Broodmaaltijd + pannenkoeken",
        "dish_type": DishType.BREAD_MEAL,
        "ingredients": [
            ("Bloem", "4"),
            ("Bakpoeder (zakje)", "8"),
            ("Vanillesuiker (pakje)", "32"),
            ("Suiker", "0.64"),
            ("Eieren", "32"),
            ("Boter", "2.4"),
            ("Melk", "4"),
            ("Spuitwater", "4"),
        ],
        "steps": [
            ("Bloem, bakpoeder, suiker en vanillesuiker mengen.", 10),
            ("Melk toevoegen en mengen.", 5),
            ("Eierdooiers toevoegen; eiwit apart stijfkloppen.", 15),
            ("Water toevoegen; gesmolten boter (niet gekookt) toevoegen.", 10),
            ("Als laatste het eiwit eronder mengen; pannenkoeken bakken.", 60),
        ],
        "notes": "Bij zelfrijzende bloem geen bakpoeder. Toppings: overschot "
        "suiker, siroop, choco.",
        "source": "2025 dag 6",
    },
    # ---------- Desserts ----------
    {
        "name": "Gele pudding",
        "dish_type": DishType.DESSERT,
        "ingredients": [
            ("Gele pudding (zakje)", "12"),
            ("Melk", "9"),
        ],
        "notes": "Afwerken met fijne witte suiker en hagelslag.",
        "source": "2025 dag 2",
    },
    {
        "name": "Messinaroom",
        "dish_type": DishType.DESSERT,
        "ingredients": [
            ("Platte kaas (vol)", "4"),
            ("Eieren", "17"),
            ("Suiker", "1.3"),
            ("Vanillesuiker (pakje)", "17"),
            ("Ananas (groot blik)", "4"),
        ],
        "source": "2025 dag 3",
    },
    {
        "name": "Chocomousse",
        "dish_type": DishType.DESSERT,
        "ingredients": [("Chocomousse (zak)", "4")],
        "source": "2025 dag 7",
    },
    {
        "name": "Rijstpap",
        "dish_type": DishType.DESSERT,
        "ingredients": [
            ("Rijst", "1.5"),
            ("Melk", "12"),
            ("Suiker", "0.6"),
            ("Vanillesuiker (pakje)", "12"),
            ("Kinnekessuiker (pak)", "1"),
            ("Bastaardsuiker (pak)", "1"),
        ],
        "notes": "Bosto-rijst; klein beetje zout in de melk.",
        "source": "2025 dag 8",
    },
    {
        "name": "Appelcake",
        "dish_type": DishType.DESSERT,
        "notes": "Gemaakt/meegebracht door Mia. Aankoop niet nodig?",
    },
    {
        "name": "Flan",
        "dish_type": DishType.DESSERT,
        "notes": "Gekocht; hoeveelheden nog aan te vullen.",
    },
    {
        "name": "Koekjestaart",
        "dish_type": DishType.DESSERT,
        "notes": "Die Patrick maakt. Hoeveelheden nog aan te vullen.",
    },
    {
        "name": "Cornetto",
        "dish_type": DishType.DESSERT,
        "notes": "Gekocht ijs. Draaiboek: 'nooit genoeg' — aantal zelf kiezen "
        "(72 calippo's als referentie).",
    },
    {
        "name": "Waterijsjes (Calippo)",
        "dish_type": DishType.DESSERT,
        "ingredients": [("Calippo", "72")],
        "source": "2025 dag 4",
    },
    # ---------- Vieruurtjes ----------
    {
        "name": "Fruit (appel, peer, watermeloen)",
        "dish_type": DishType.SNACK_FRUITVEG,
        "ingredients": [
            ("Appel", "40"),
            ("Peer", "40"),
            ("Watermeloen", "3"),
        ],
        "source": "2025 dag 2",
    },
    {
        "name": "Nectarines",
        "dish_type": DishType.SNACK_FRUITVEG,
        "ingredients": [("Nectarine", "60")],
        "source": "2025 dag 9",
    },
    {
        "name": "Koude groenten",
        "dish_type": DishType.SNACK_FRUITVEG,
        "notes": "Uit menu 2026; invulling nog te kiezen.",
    },
    {
        "name": "Prinskoeken",
        "dish_type": DishType.SNACK_SWEET,
        "ingredients": [("Prinskoeken (pak)", "4")],
        "notes": "2 pakken wit / 2 pakken bruin.",
        "source": "2025 dag 1",
    },
    {
        "name": "Bananenmilkshake",
        "dish_type": DishType.SNACK_SWEET,
        "ingredients": [
            ("Banaan", "50"),
            ("Melk", "8"),
            ("Vanillesuiker (pakje)", "8"),
            ("Vanille-ijs", "5.5"),
        ],
        "source": "2025 dag 8",
    },
    {
        "name": "Smoothie",
        "dish_type": DishType.SNACK_SWEET,
        "ingredients": [
            ("Yoghurt", "7.5"),
            ("Diepvriesfruit", "7.5"),
        ],
        "source": "2025 dag 5",
    },
    {
        "name": "Hartjeswafels",
        "dish_type": DishType.SNACK_SWEET,
        "ingredients": [
            ("Boter", "2"),
            ("Zelfrijzende bloem", "2"),
            ("Suiker", "1.2"),
            ("Eieren", "36"),
            ("Vanillesuiker (pakje)", "8"),
        ],
        "steps": [
            ("Boter zacht laten worden en smelten.", 30),
            (
                "Eieren splitsen; dooiers onder het boter-suikermengsel; "
                "eiwit opkloppen.",
                20,
            ),
            ("Bloem onder het botermengsel roeren; eiwit eronder spatelen.", 15),
            ("Wafelijzer heet inboteren en goudgele wafels bakken.", 60),
        ],
        "source": "2025 dag 3",
    },
    {
        "name": "Ice tea met biscuit",
        "dish_type": DishType.SNACK_SWEET,
        "notes": "Uit menu 2026; hoeveelheden nog aan te vullen.",
    },
    {
        "name": "Bruschetta's",
        "dish_type": DishType.SNACK_SAVORY,
        "notes": "Uit menu 2026; hoeveelheden nog aan te vullen.",
    },
]


class Command(BaseCommand):
    help = "Import recipes from the draaiboek kookploeg 2025/2026 documents."

    def handle(self, *args: Any, **options: Any) -> None:
        for name, (unit, category) in INGREDIENTS.items():
            Ingredient.objects.get_or_create(
                name=name, defaults={"unit": unit, "category": category}
            )

        created_count = 0
        for spec in RECIPES:
            notes = spec.get("notes", "")
            source = spec.get("source")
            if source:
                notes = (notes + f"\nBron: draaiboek {source}.").strip()
            notes = (
                notes + "\nBasis: kamp 2025, 71 personen (27 -12j, 44 12+)."
            ).strip()

            recipe, created = Recipe.objects.get_or_create(
                name=spec["name"],
                defaults={
                    "dish_type": spec["dish_type"],
                    "base_children": BASE_CHILDREN,
                    "base_teens": BASE_TEENS,
                    "notes": notes,
                },
            )
            if not created:
                continue
            created_count += 1

            for ing_name, qty in spec.get("ingredients", []):
                ingredient = Ingredient.objects.get(name=ing_name)
                RecipeIngredient.objects.create(
                    recipe=recipe,
                    ingredient=ingredient,
                    quantity=Decimal(qty),
                    unit=ingredient.unit,
                )
            for order, (instruction, minutes) in enumerate(
                spec.get("steps", []), start=1
            ):
                RecipeStep.objects.create(
                    recipe=recipe,
                    order=order,
                    instruction=instruction,
                    duration_minutes=minutes,
                )

        logger.info("Imported %d new recipes", created_count)
        self.stdout.write(
            self.style.SUCCESS(
                f"Done: {created_count} new recipes "
                f"({len(RECIPES)} in import set, existing ones untouched)."
            )
        )
