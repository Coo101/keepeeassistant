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
    "Rijpe tomaten": (KG, PRODUCE),
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
    "Room (culinair)": (L, DAIRY),
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
    "Chipolata": (P, MEAT),
    "Baksaucis": (P, MEAT),
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
    "Vleesbouillon": (L, DRY),
    "Erwten (diepvries)": (KG, PRODUCE),
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
        "steps": [
            (
                "Melk opwarmen; chocomelk aanmaken met cacaopoeder en "
                "suiker; koffie zetten.",
                20,
            ),
            ("Brood snijden en in manden verdelen.", 15),
            (
                "Afdelingsbakken klaarzetten: boter, choco, confituur, "
                "smeerkaas en al het gerief per bak.",
                15,
            ),
        ],
        "notes": "Afgeleid uit aankopen Klein Kamp (58 pers. ~ 50 porties, "
        "~10 melk/beleg-maaltijden per kamp), geschaald naar 71 pers. "
        "Boter/choco/confituur/suiker/koffie: schatting volgens richtlijnen "
        "koken-voor-groepen — nazicht gewenst.",
    },
    {
        "name": "Beleg (kaas, hesp, saucis)",
        "dish_type": DishType.BREAD_MEAL_EXTRA,
        "steps": [
            (
                "Kaas, hesp en saucis openen/snijden en verdelen over de "
                "afdelingsbakken.",
                10,
            ),
        ],
        "notes": "Extra bij standaardontbijt; hoeveelheden nog aan te vullen.",
    },
    {
        "name": "Cornflakes",
        "dish_type": DishType.BREAD_MEAL_EXTRA,
        "ingredients": [("Cornflakes (doos)", "8")],
        "steps": [
            (
                "Cornflakes, yoghurtpotjes en (koud gezet) fruitsap "
                "verdelen over de afdelingsbakken.",
                10,
            ),
        ],
        "notes": "Extra bij standaardontbijt. Ook: fruitsap en yoghurtpotjes "
        "(aantallen aan te vullen).",
    },
    {
        "name": "Speculaas & hagelslag",
        "dish_type": DishType.BREAD_MEAL_EXTRA,
        "steps": [
            (
                "Hagelslag in confituurpotten met lepel; samen met de "
                "speculaas verdelen over de afdelingsbakken.",
                10,
            ),
        ],
        "notes": "Extra bij standaardontbijt; hagelslag in confituurpotten "
        "+ lepel. Hoeveelheden nog aan te vullen.",
    },
    {
        "name": "Eieren (ontbijt)",
        "dish_type": DishType.BREAD_MEAL_EXTRA,
        "ingredients": [("Eieren", "130")],
        "steps": [
            ("Eieren hard koken of in porties bakken.", 30),
            ("Met kaas en hesp verdelen over de afdelingsbakken.", 10),
        ],
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
        "steps": [
            (
                "Pancakebeslag maken: bloem, bakpoeder en suiker mengen; "
                "eieren en melk erdoor kloppen.",
                20,
            ),
            ("American pancakes in porties bakken en warmhouden.", 45),
            ("Spek krokant bakken; roereieren bakken.", 40),
            (
                "Buffet klaarzetten: yoghurt, fruitsla, beleg, speculaas en " "siroop.",
                20,
            ),
            ("Afdelingsbakken klaarzetten met al het gerief.", 15),
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
        "steps": [
            ("Spek krokant bakken; eieren in porties bakken.", 40),
            ("Verdelen over de afdelingsbakken.", 10),
        ],
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
            (
                "Spek in reepjes snijden en krokant uitbakken; een deel apart "
                "houden als garnituur.",
                15,
            ),
            ("Ajuin schillen, grof snijden en stoven in het spekvet.", 15),
            ("Courgette in stukken snijden en kort meebakken.", 15),
            ("Aardappelen in blokjes snijden en toevoegen.", 10),
            ("Kippenbouillon toevoegen en alles gaar koken.", 20),
            ("Soep mixen en aanlengen met heet water tot 11 l.", 10),
            (
                "Proeven, bijkruiden met peper en zout; krokante spekjes er "
                "bovenop bij het serveren.",
                5,
            ),
        ],
        "notes": "11 liter soep voor 71 personen.",
        "source": "2025 dag 1",
    },
    {
        "name": "Preisoep",
        "dish_type": DishType.SOUP,
        "ingredients": [
            ("Ajuin", "1.1"),
            ("Selder (struik)", "1.5"),
            ("Prei (stronk)", "6"),
            ("Wortelen", "1.6"),
            ("Aardappelen", "1"),
            ("Look (teen)", "6"),
            ("Witte bonen (bokaal)", "3"),
            ("Soepdiertjes", "1"),
        ],
        "steps": [
            (
                "Verse bouillon: wortelen, ajuin, selder en look grof snijden, "
                "aanstoven en met 5,5 l water 30 min zachtjes laten trekken.",
                40,
            ),
            ("Prei in grote stukken snijden en goed wassen.", 15),
            ("Prei en aardappel toevoegen en gaar koken.", 20),
            ("Soep mixen; bonen en diertjes kort meekoken.", 15),
            ("Brood in blokjes snijden en bakken in boter (croutons).", 15),
        ],
        "notes": "11 liter soep voor 71 personen. Verse groentebouillon "
        "(per liter: 100 g wortel, 100 g ajuin, 1/10 struik selder, 1 teen "
        "look) vervangt 5,5 l groentenbouillon en wordt meegemixt.",
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
            ("Ajuin", "1.8"),
            ("Selder (struik)", "2.8"),
            ("Prei (stronk)", "3"),
            ("Wortelen", "2.8"),
            ("Aardappelen", "1"),
            ("Look (teen)", "8"),
            ("Witte bonen (bokaal)", "3"),
            ("Soepdiertjes", "1"),
        ],
        "steps": [
            (
                "Verse bouillon: wortelen, ajuin, selder en look grof snijden, "
                "aanstoven en met 8 l water 30 min zachtjes laten trekken.",
                40,
            ),
            (
                "Soepgroenten in kleine stukjes snijden; selderblaadjes en enkel "
                "heel dunne steeltjes.",
                30,
            ),
            ("Groenten gaar koken in de bouillon en mixen.", 25),
            (
                "Diertjes ~10 min meekoken; bonen pas aan het einde toevoegen, "
                "niet mee laten doorkoken.",
                15,
            ),
        ],
        "notes": "16 liter soep voor 71 personen. Verse groentebouillon "
        "(per liter: 100 g wortel, 100 g ajuin, 1/10 struik selder, 1 teen "
        "look) vervangt 8 l groentenbouillon en wordt meegemixt.",
        "source": "2025 dag 3",
    },
    {
        "name": "Tomatensoep met balletjes",
        "dish_type": DishType.SOUP,
        "ingredients": [
            ("Rijpe tomaten", "14"),
            ("Ajuin", "1.5"),
            ("Look (teen)", "8"),
            ("Wortelen", "0.5"),
            ("Boter", "0.2"),
            ("Kippenbouillon", "4"),
            ("Room (culinair)", "2"),
            ("Suiker", "0.1"),
        ],
        "steps": [
            (
                "Tomaten wassen en in kwarten snijden (ontvellen hoeft niet, "
                "alles wordt gemixt).",
                25,
            ),
            ("Ajuin, look en wortel fijnsnijden en aanstoven in de boter.", 15),
            ("Tomaten toevoegen en ~10 min mee stoven tot ze loslaten.", 15),
            ("Kippenbouillon toevoegen en 25 min zachtjes laten koken.", 25),
            (
                "Soep glad mixen; op smaak brengen met een snuf suiker, peper "
                "en zout.",
                10,
            ),
            ("Balletjes toevoegen en laten garen.", 10),
            ("Room erdoor roeren en niet meer laten koken.", 5),
            (
                "Proeven: te weinig tomatensmaak? Lepel per lepel "
                "tomatenpuree uit de voorraad toevoegen — vers heeft "
                "voorrang.",
                None,
            ),
        ],
        "notes": "16 liter soep voor 71 personen, op verse rijpe tomaten en "
        "room (geen bloem/melk meer). Tomatenpuree staat bewust niet op de "
        "boodschappenlijst: enkel bijsturen met voorraadpuree als de smaak "
        "te vlak is. Soepballetjes: hoeveelheid nog aan te vullen.",
        "source": "2025 dag 5",
    },
    {
        "name": "Paprikasoep",
        "dish_type": DishType.SOUP,
        "ingredients": [
            ("Paprika", "4"),
            ("Ajuin", "2.3"),
            ("Wortelen", "0.8"),
            ("Selder (struik)", "0.8"),
            ("Look (teen)", "8"),
            ("Kruidenkaas (potje)", "3"),
            ("Tomatenpuree (blik/potje)", "4"),
        ],
        "steps": [
            (
                "Verse bouillon: wortelen, ajuin, selder en look grof snijden, "
                "aanstoven en met 8 l water 30 min zachtjes laten trekken.",
                40,
            ),
            (
                "Paprika's snijden en aanstoven; tomatenpuree kort meebakken.",
                20,
            ),
            ("Alles gaar koken in de bouillon, kruidenkaas toevoegen en mixen.", 25),
            ("Afwerken met paprikapoeder, peper en zout.", 5),
        ],
        "notes": "16 liter soep voor 71 personen. 20 rode paprika's ≈ 4 kg. "
        "Verse groentebouillon (per liter: 100 g wortel, 100 g ajuin, 1/10 "
        "struik selder, 1 teen look) vervangt 8 l groentenbouillon én de 36 "
        "tuinkruidenblokjes. Extra: paprikapoeder (potje).",
        "source": "2025 dag 8",
    },
    {
        "name": "Heldere zomergroentesoep",
        "dish_type": DishType.SOUP,
        "ingredients": [
            ("Wortelen", "3.1"),
            ("Ajuin", "1.6"),
            ("Selder (struik)", "1.6"),
            ("Look (teen)", "16"),
            ("Courgette", "3"),
            ("Prei (stronk)", "2"),
            ("Kersttomaten", "1.5"),
            ("Erwtjes (potje)", "2"),
            ("Verse peterselie (bussel)", "1"),
        ],
        "steps": [
            (
                "Verse bouillon: wortelen (1,6 kg), ajuin, selder en look grof "
                "snijden, aanstoven en met 16 l water 45 min zachtjes laten "
                "trekken.",
                55,
            ),
            ("Bouillon zeven zodat hij helder blijft.", 10),
            (
                "Courgette, resterende wortelen (1,5 kg) en prei in fijne "
                "brunoise snijden.",
                30,
            ),
            (
                "Brunoise beetgaar koken in de heldere bouillon; erwtjes en "
                "gehalveerde kerstomaten de laatste minuten toevoegen.",
                15,
            ),
            ("Afwerken met verse peterselie, peper en zout.", 5),
        ],
        "notes": "Heldere (niet-gemixte) frisse zomersoep op verse "
        "groentebouillon. 16 liter voor 71 personen.",
    },
    {
        "name": "Komkommersoep (koud)",
        "dish_type": DishType.SOUP,
        "ingredients": [
            ("Komkommer", "24"),
            ("Yoghurt", "3"),
            ("Look (teen)", "4"),
        ],
        "steps": [
            ("Komkommers wassen, schillen en zaadlijsten verwijderen.", 20),
            (
                "Komkommers grof snijden en glad mixen met de yoghurt en de " "look.",
                15,
            ),
            (
                "Op smaak brengen met peper, zout en (optioneel) verse munt "
                "of dille.",
                5,
            ),
            ("Minstens 2 uur goed koud zetten en koud serveren.", None),
        ],
        "notes": "Koude gemixte zomersoep. Yoghurt en look zijn een "
        "schatting — nazicht gewenst; verse munt of dille apart voorzien.",
        "source": "2025 dag 10",
    },
    {
        "name": "Minestrone op vleesbouillon",
        "dish_type": DishType.SOUP,
        "ingredients": [
            ("Vleesbouillon", "6"),
            ("Ajuin", "1"),
            ("Look (teen)", "8"),
            ("Wortelen", "1.5"),
            ("Courgette", "3"),
            ("Selder (struik)", "1"),
            ("Kersttomaten", "1.5"),
            ("Tomatenpuree (blik/potje)", "2"),
            ("Witte bonen (bokaal)", "3"),
            ("Soepdiertjes", "1"),
            ("Verse peterselie (bussel)", "1"),
        ],
        "steps": [
            (
                "Bewaard kookvocht van de balletjes opkoken en aanvullen met "
                "vleesbouillon/water tot 12 l.",
                15,
            ),
            (
                "Ajuin, look, selder en wortelen fijnsnijden en aanstoven; "
                "tomatenpuree kort meebakken.",
                25,
            ),
            (
                "Groenten zacht laten koken in de bouillon; courgette in "
                "blokjes en gehalveerde kerstomaten toevoegen.",
                20,
            ),
            ("Soepdiertjes ~10 min meekoken; bonen op het einde toevoegen.", 15),
            ("Niet mixen; afwerken met peterselie, peper en zout.", 5),
        ],
        "notes": "16 liter voor 71 personen. Basis: het gezeefde kookvocht van "
        "'Balletjes in tomatensaus met puree' (plan die de dag ervoor); "
        "aanvullen met vleesbouillon. Niet mixen — dit is naast de "
        "kippensoep een tweede heldere soep.",
    },
    {
        "name": "Zomerse erwtensoep met spek",
        "dish_type": DishType.SOUP,
        "ingredients": [
            ("Erwten (diepvries)", "4"),
            ("Spek", "1.5"),
            ("Ajuin", "1"),
            ("Look (teen)", "6"),
            ("Prei (stronk)", "2"),
            ("Aardappelen", "1"),
            ("Vleesbouillon", "5.5"),
        ],
        "steps": [
            ("Spek uitbakken; ajuin, look en prei toevoegen en aanstoven.", 20),
            (
                "Aardappelen in blokjes en de bouillon (of balletjes-kookvocht) "
                "toevoegen; gaar koken.",
                25,
            ),
            (
                "Erwten toevoegen en maar 5 min meekoken, zo blijft de soep "
                "frisgroen.",
                10,
            ),
            (
                "Mixen; proeven en bijkruiden; een deel krokante spekjes als "
                "garnituur bovenop.",
                10,
            ),
        ],
        "notes": "11 liter voor 71 personen. Frisgroene gemixte zomersoep op "
        "varkens-/vleesbouillon; het balletjes-kookvocht mag de bouillon "
        "(deels) vervangen.",
    },
    {
        "name": "Ajuinsoep op rundsbouillon",
        "dish_type": DishType.SOUP,
        "ingredients": [
            ("Ajuin", "5"),
            ("Boter", "0.3"),
            ("Look (teen)", "6"),
            ("Vleesbouillon", "8"),
            ("Wit brood", "2"),
            ("Geraspte kaas", "1"),
        ],
        "steps": [
            (
                "Ajuin in halve ringen snijden en heel traag goudbruin stoven "
                "in de boter (niet laten aanbranden).",
                45,
            ),
            (
                "Look toevoegen; bouillon (of balletjes-kookvocht) toevoegen "
                "en 20 min zacht laten koken.",
                25,
            ),
            ("Brood in blokjes bakken tot croutons.", 15),
            (
                "Serveren met croutons en geraspte kaas; desgewenst mixen "
                "voor de kleinsten.",
                10,
            ),
        ],
        "notes": "11 liter voor 71 personen. Rundsbouillon of het kookvocht "
        "van de balletjes als basis.",
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
            (
                "Balletjes rollen van het gehakt en gaar koken in licht "
                "gezouten water; daarna in de tomatensaus opwarmen met een "
                "paar blaadjes laurier en wat oregano; bijkruiden met peper "
                "en zout.",
                45,
            ),
            (
                "Kookvocht van de balletjes zeven en in de koelkast bewaren "
                "als verse vleesbouillon voor de soep (cf. kippensoep).",
                10,
            ),
            (
                "Melk en boter opwarmen met nootmuskaat/peper/zout; eieren "
                "loskloppen; aardappelen stoempen met het mengsel.",
                30,
            ),
        ],
        "notes": "Puree-extra's (melk, ei, boter, nootmuskaat): hoeveelheden "
        "nog aan te vullen. 5 uien ≈ 0.8 kg. Het gezeefde kookvocht van de "
        "balletjes is de basis voor de vleesbouillonsoepen (minestrone, "
        "erwtensoep, ajuinsoep) — plan die er de dag na.",
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
        "steps": [
            ("Aardappelen schillen en gaar koken.", 45),
            (
                "Tartaarsaus: sjalot, peterselie en bieslook fijnsnijden en "
                "onder de mayonaise mengen met een scheut citroensap; koud "
                "zetten.",
                15,
            ),
            ("Spinazie laten ontdooien en het vocht goed laten uitdampen.", 20),
            (
                "Aardappelen stoempen met de boter en wat melk; kruiden met "
                "nootmuskaat, peper en zout; spinazie eronder mengen.",
                25,
            ),
            (
                "Visburgers in porties bakken en warmhouden in de oven; "
                "serveren met citroen en tartaar.",
                30,
            ),
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
        "steps": [
            ("Paprika's in reepjes snijden en grillen.", 20),
            (
                "IJsbergsla in reepjes, wortelen raspen, witte kool "
                "fijnschaven, kerstomaten halveren.",
                30,
            ),
            (
                "Kipschnitzels bakken en in reepjes snijden; kruiden met "
                "paprikapoeder en kippenkruiden.",
                30,
            ),
            (
                "Wraps kort opwarmen; alles in schalen op tafel zetten en "
                "zelf laten vullen met looksaus.",
                15,
            ),
        ],
        "notes": "Paprika's grillen. Looksaus nog aan te vullen. Kruiden uit "
        "de voorraad.",
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
        "steps": [
            (
                "Ajuin en look snipperen en aanstoven; gehakt toevoegen en "
                "rul bakken.",
                20,
            ),
            (
                "Paprika in blokjes meebakken; tomatenpuree kort meebakken.",
                10,
            ),
            (
                "Passata, rode bonen, mais en Mexicaanse kruiden toevoegen; "
                "15 min laten sudderen en bijkruiden met peper en zout.",
                20,
            ),
            (
                "Wraps kort opwarmen en vullen; eventueel oprollen in "
                "aluminiumfolie om warm te houden.",
                15,
            ),
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
            (
                "Kipfilets koken met laurier en tijm; kookwater bijhouden en "
                "kip in blokjes snijden.",
                30,
            ),
            ("Soepballetjes even koken; champignons in schijfjes bakken.", 25),
            ("Sla, komkommer en tomaat snijden voor de salade erbij.", 20),
            ("Videe in 2 keer maken: boter smelten, vloeiende bloem toevoegen.", 15),
            (
                "Melk en kipkookvocht al roerend toevoegen; op smaak brengen "
                "met bouillon en een scheut citroensap.",
                20,
            ),
            ("Kip, balletjes en champignons als laatste toevoegen.", 10),
            ("Kroketten bakken en warmhouden in de oven.", 45),
        ],
        "notes": "Extra: 12 kippenbouillonblokjes om de kipfilet in te koken; "
        "1,5 l kipkookwater voor de smaak. Laurier en tijm uit de "
        "kruidenvoorraad.",
        "source": "2025 dag 5",
    },
    {
        "name": "Calamaris en mini-loempia's",
        "dish_type": DishType.HOT_MEAL,
        "ingredients": [
            ("Calamaris (pak)", "4"),
            ("Mini-loempia's", "30"),
        ],
        "steps": [
            ("Frituur voorverwarmen op 180 °C.", 10),
            (
                "Calamaris en mini-loempia's in porties frituren en "
                "warmhouden in de oven.",
                40,
            ),
            (
                "Serveren met citroen en zoetzure of cocktailsaus uit de " "voorraad.",
                5,
            ),
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
        "steps": [
            (
                "Kipfilet in reepjes snijden, kruiden met kippenkruiden en "
                "in porties roerbakken.",
                25,
            ),
            ("Woknoedels koken volgens de verpakking en laten uitlekken.", 15),
            (
                "Wokgroenten in de grote wok roerbakken; kip en noedels " "toevoegen.",
                20,
            ),
            (
                "Afblussen met de sojasaus; op smaak brengen met look- en "
                "gemberpoeder uit de voorraad.",
                10,
            ),
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
            ("Vleesbouillon", "5"),
            ("Sla (krop)", "4"),
            ("Komkommer", "10"),
            ("Tomaat", "25"),
        ],
        "steps": [
            (
                "Stoofvlees (liefst daags op voorhand) in porties aanbraden.",
                30,
            ),
            ("Ajuin en look snijden en aanstoven; vlees terug toevoegen.", 15),
            (
                "Vleesbouillon toevoegen met laurier, tijm en een scheut "
                "azijn of bruin bier; 2 à 3 uur zachtjes laten stoven tot "
                "het vlees uit elkaar valt.",
                150,
            ),
            ("Sla, komkommer en tomaat snijden voor de salade.", 20),
            (
                "Friet in porties frituren; stoofvlees opwarmen en indien "
                "te dun licht binden.",
                60,
            ),
        ],
        "notes": "7 ajuinen ≈ 1,1 kg. Vleesbouillon i.p.v. groentenbouillon "
        "(stoofpot); laurier en tijm uit de kruidenvoorraad.",
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
        "steps": [
            (
                "Macaroni koken, afgieten en mengen met een klont boter "
                "zodat hij niet plakt.",
                25,
            ),
            (
                "Kaassaus: boter smelten, vloeiende bloem toevoegen en al "
                "roerend de melk toevoegen.",
                20,
            ),
            (
                "Geraspte kaas onder de saus roeren; kruiden met "
                "nootmuskaat, peper en zout.",
                10,
            ),
            (
                "Hespenblokjes en macaroni door de saus mengen; eventueel "
                "afwerken onder de grill met extra kaas.",
                15,
            ),
        ],
        "notes": "Hoeveelheid macaroni controleren (opmerking draaiboek).",
        "source": "2025 dag 10",
    },
    {
        "name": "Wortelpuree met worst",
        "dish_type": DishType.HOT_MEAL,
        "ingredients": [
            ("Wortelen", "8"),
            ("Aardappelen", "8"),
            ("Boter", "0.5"),
            ("Melk", "1"),
            ("Chipolata", "80"),
        ],
        "steps": [
            (
                "Aardappelen en wortelen schillen, in stukken snijden en "
                "samen gaar koken.",
                40,
            ),
            (
                "Stoempen met de boter en melk; kruiden met nootmuskaat, "
                "peper en zout.",
                20,
            ),
            (
                "Worsten in porties bakken; het braadvocht als jus over de " "puree.",
                30,
            ),
        ],
        "notes": "Uit menu 2026 dag 7. Hoeveelheden zijn een schatting — "
        "nazicht gewenst.",
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
            (
                "Bouillon in water smelten en toevoegen met 2 blaadjes "
                "laurier; 10 minuten laten stoven.",
                15,
            ),
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
        "steps": [
            (
                "Groenten snijden: sla in reepjes, komkommer in schijfjes, "
                "tomaten in partjes, wortelen raspen; mais en erwtjes laten "
                "uitlekken.",
                40,
            ),
            ("Pitavlees in porties bakken in bakboter.", 40),
            ("Turkse broden opwarmen in de oven.", 15),
            (
                "Alles in schalen op tafel zetten; zelf laten vullen met "
                "pitasaus, mayo of ketchup.",
                10,
            ),
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
        "steps": [
            ("Ajuin in ringen snijden en goudbruin stoven.", 25),
            (
                "Hamburgers in porties bakken op het kampvuur of de " "bakplaat.",
                45,
            ),
            (
                "Pistolets opensnijden; serveren met gebakken ajuin, mayo "
                "en ketchup.",
                15,
            ),
        ],
        "notes": "Extra: mayo en ketchup. 2026 rekende 70 stuks voor 58 man.",
        "source": "2025 dag 10",
    },
    # ---------- Broodmaaltijden ----------
    {
        "name": "Broodmaaltijd",
        "dish_type": DishType.BREAD_MEAL,
        "steps": [
            ("Brood snijden en in manden verdelen.", 15),
            ("Chocomelk aanmaken en koffie zetten.", 20),
            (
                "Afdelingsbakken klaarzetten: boter en al het beleg per bak.",
                15,
            ),
        ],
        "notes": "Brood van de bakker + choco, confituur, smeerkaas, boter, "
        "cacaopoeder, suiker, melk, koffie. Hoeveelheden nog aan te vullen.",
    },
    {
        "name": "Baksaucis",
        "dish_type": DishType.BREAD_MEAL_EXTRA,
        "ingredients": [("Baksaucis", "85")],
        "steps": [("Baksaucissen in porties bakken.", 40)],
        "notes": "Extra bij een broodmaaltijd. ~1,2 per persoon (zoals de 70 "
        "hamburgers voor 58 man in 2026).",
    },
    {
        "name": "Pannenkoeken",
        "dish_type": DishType.BREAD_MEAL_EXTRA,
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
        "steps": [
            ("Melk aan de kook brengen.", 15),
            (
                "Puddingzakjes aanmaken volgens de verpakking en al roerend "
                "laten binden.",
                15,
            ),
            (
                "In kommen/trays gieten en laten opstijven in de koeling; "
                "afwerken met fijne suiker en hagelslag.",
                15,
            ),
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
        "steps": [
            ("Eieren splitsen; eiwitten stijfkloppen.", 20),
            (
                "Platte kaas mengen met de dooiers, suiker en vanillesuiker.",
                15,
            ),
            (
                "Ananas laten uitlekken, in stukjes snijden en eronder "
                "mengen; eiwit voorzichtig eronder spatelen.",
                15,
            ),
            ("Minstens 2 uur koud zetten.", None),
        ],
        "source": "2025 dag 3",
    },
    {
        "name": "Chocomousse",
        "dish_type": DishType.DESSERT,
        "ingredients": [("Chocomousse (zak)", "4")],
        "steps": [
            ("Chocomousse aanmaken volgens de verpakking en opkloppen.", 20),
            ("In kommen verdelen en koud zetten.", 10),
        ],
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
        "steps": [
            (
                "Melk met een snuifje zout aan de kook brengen; rijst "
                "toevoegen en op zacht vuur gaar laten koken, regelmatig "
                "roeren.",
                60,
            ),
            ("Suiker en vanillesuiker toevoegen.", 10),
            (
                "In kommen gieten; serveren met kinnekes- en " "bastaardsuiker.",
                15,
            ),
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
        "steps": [
            ("Diepvries pas openen bij het uitdelen.", 5),
        ],
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
        "steps": [
            (
                "Fruit wassen; appels en peren in partjes, watermeloen in "
                "schijven snijden.",
                30,
            ),
            ("Verdelen over schalen per afdeling.", 10),
        ],
        "source": "2025 dag 2",
    },
    {
        "name": "Nectarines",
        "dish_type": DishType.SNACK_FRUITVEG,
        "ingredients": [("Nectarine", "60")],
        "steps": [
            ("Nectarines wassen en uitdelen.", 10),
        ],
        "source": "2025 dag 9",
    },
    {
        "name": "Koude groenten",
        "dish_type": DishType.SNACK_FRUITVEG,
        "steps": [
            (
                "Groenten wassen en in dipstukjes snijden; goed koud "
                "zetten tot het vieruurtje.",
                30,
            ),
        ],
        "notes": "Uit menu 2026; invulling nog te kiezen.",
    },
    {
        "name": "Prinskoeken",
        "dish_type": DishType.SNACK_SWEET,
        "ingredients": [("Prinskoeken (pak)", "4")],
        "steps": [
            ("Koeken uitdelen per afdeling.", 5),
        ],
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
        "steps": [
            (
                "Bananen pellen en in porties mixen met melk, "
                "vanillesuiker en vanille-ijs.",
                30,
            ),
            ("Direct koud serveren in bekers.", 10),
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
        "steps": [
            ("Yoghurt en diepvriesfruit in porties glad mixen.", 25),
            ("Direct serveren in bekers.", 10),
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
        "steps": [
            ("Ice tea op voorhand goed koud zetten.", 5),
            ("Uitschenken en uitdelen met een biscuit.", 15),
        ],
        "notes": "Uit menu 2026; hoeveelheden nog aan te vullen.",
    },
    {
        "name": "Bruschetta's",
        "dish_type": DishType.SNACK_SAVORY,
        "steps": [
            (
                "Tomaten in blokjes snijden en mengen met look, olijfolie, "
                "peper, zout en gedroogde basilicum.",
                20,
            ),
            ("Brood in sneetjes roosteren en beleggen.", 30),
        ],
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
