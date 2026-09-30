"""Deterministic, illustrative route comparisons; no LLM arithmetic."""
from decimal import Decimal, ROUND_HALF_UP

EXTERNAL_CONTEXT = [
    {"id": "food_transport", "finding": "Food transport is only a small part of food-system emissions; local origin alone does not prove a lower footprint.",
     "source_url": "https://ourworldindata.org/faqs-environmental-impacts-food"},
    {"id": "conversion_factors", "finding": "Published transport conversion factors depend on vehicle type and assumptions. This demo uses its own illustrative 160 g/km car factor, not a verified customer footprint.",
     "source_url": "https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2025"},
]

def kg_from_grams(grams):
    return float((Decimal(grams) / Decimal(1000)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

def options(scenario):
    """Four weeks/month; bicycle has zero direct tailpipe emissions in this limited comparison."""
    car_g = scenario["car_g_per_km"]
    commute_days = min(2, scenario["commute_car_days"])
    bike_savings_g = 2 * scenario["commute_one_way_m"] * commute_days * 4 * car_g // 1000
    grocery_savings_g = 2 * scenario["grocery_current_one_way_m"] * scenario["grocery_trips_month"] * car_g // 1000
    return [
        {"id": "BIKE_COMMUTE", "title": "Cycle two commute days each week",
         "description": f"Try a {scenario['commute_one_way_m']/1000:g} km one-way bike route on two of your five example driving days.",
         "monthly_kg_co2e_avoided": kg_from_grams(bike_savings_g),
         "calculation": f"2 × {scenario['commute_one_way_m']/1000:g} km × {commute_days} days/week × 4 weeks × {car_g} g/km",
         "condition": "Only if the route is safe, practical and you currently drive those trips. Direct car emissions only; cycling lifecycle and extra food energy are excluded.",
         "route_kind": "illustrative route, not a verified map"},
        {"id": "NEARBY_GROCERY", "title": "Try a nearby grocery trip by bike",
         "description": f"Compare a {scenario['grocery_nearby_one_way_m']/1000:g} km one-way neighborhood shop with a {scenario['grocery_current_one_way_m']/1000:g} km one-way car trip, once a week. Look for seasonal, locally sourced items if they are available; this estimate covers only travel.",
         "monthly_kg_co2e_avoided": kg_from_grams(grocery_savings_g),
         "calculation": f"2 × {scenario['grocery_current_one_way_m']/1000:g} km × {scenario['grocery_trips_month']} trips × {car_g} g/km",
         "condition": "Only if the original trip is by car and the shop/stock and bike route work for you. Product emissions, price and availability are not estimated; local origin alone is not a lower-carbon guarantee.",
         "route_kind": "illustrative store scenario, not a real merchant recommendation"},
    ]
