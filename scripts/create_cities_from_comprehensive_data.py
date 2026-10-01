#!/usr/bin/env python3
"""
Create accurate city GeoJSON from comprehensive city analysis data.
"""

import json
import random
import sys
from pathlib import Path

# Reason: the script lives in scripts/; put the repository root on the path for src.econgen.
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.econgen.paths import worldbuilder_dir

# Eno-Worldbuilder2 checkout ($ENO_WORLDBUILDER_DIR); outputs go to the repository root.
WORLDBUILDER_DIR = worldbuilder_dir()
OUTPUT_DIR = REPO_ROOT


def determine_tech_level(city_data):
    """Determine tech level based on city characteristics."""
    # Factors that influence tech level
    population = city_data.get("population", 0)
    building_count = city_data.get("building_count", 0)
    founded = city_data.get("founded_in", 0)
    is_capital = city_data.get("capital", False)
    has_plaza = city_data.get("plaza", False)

    # Calculate tech score
    tech_score = 0

    # Population influence (bigger cities = more advanced)
    if population > 8000:
        tech_score += 3
    elif population > 3000:
        tech_score += 2
    elif population > 1000:
        tech_score += 1

    # Building density influence
    if building_count > 500:
        tech_score += 2
    elif building_count > 200:
        tech_score += 1

    # Infrastructure influence
    if is_capital:
        tech_score += 2
    if has_plaza:
        tech_score += 1

    # Age influence (older cities might be more established)
    if founded < 50:  # Very old
        tech_score += 1

    # Assign tech level based on score
    if tech_score >= 6:
        return "industrial"
    elif tech_score >= 3:
        return "medieval"
    else:
        return "tribal"


def generate_endowments(city_data):
    """Generate resource endowments based on city characteristics."""
    endowments = {}

    # Set random seed based on city name for consistency
    random.seed(hash(city_data["name"]) % 2147483647)

    # Base resources for all cities
    population = city_data.get("population", 0)
    elevation = city_data.get("elevation", 0)
    valley = (city_data.get("valley") or "").lower()

    # Basic resources scaled by city size
    size_factor = max(0.5, min(2.0, population / 2000))

    endowments["food"] = int(50 + random.randint(20, 80) * size_factor)
    endowments["wood"] = int(30 + random.randint(15, 60) * size_factor)
    endowments["stone"] = int(20 + random.randint(10, 50) * size_factor)

    # Elevation-based resources
    if elevation > 2000:  # High mountains
        endowments["iron_ore"] = int(random.randint(100, 200))
        endowments["stone"] = int(endowments["stone"] * 1.5)
    elif elevation > 1000:  # Hills
        endowments["iron_ore"] = int(random.randint(50, 120))

    # Valley-based specializations
    if "night" in valley:
        endowments["luxury_goods"] = random.randint(20, 60)
    elif "day" in valley or "noon" in valley:
        endowments["food"] = int(endowments["food"] * 1.5)
    elif "dawn" in valley or "dusk" in valley:
        endowments["tools"] = random.randint(30, 80)

    # Port cities get fishing
    if city_data.get("port", False):
        endowments["fish"] = random.randint(200, 500)

    # Infrastructure influences
    if city_data.get("capital", False):
        endowments["luxury_goods"] = random.randint(40, 100)

    if city_data.get("plaza", False):
        # Markets boost trade goods
        for resource in ["tools", "luxury_goods"]:
            if resource in endowments:
                endowments[resource] = int(endowments[resource] * 1.3)

    return endowments


def determine_geographic_flags(city_data):
    """Determine coastal and mountainous flags."""
    elevation = city_data.get("elevation", 0)
    latitude = city_data.get("latitude", 0)
    port = city_data.get("port", False)

    # Coastal determination
    coastal = port or (
        elevation < 500 and abs(latitude - 36) < 3
    )  # Near sea level and reasonable latitude

    # Mountainous determination
    mountainous = elevation > 1500

    return coastal, mountainous


def main():
    # Load comprehensive city data
    data_path = (
        WORLDBUILDER_DIR / "GIS" / "comprehensive_city_analysis_results_updated_manually.json"
    )

    with open(data_path, "r", encoding="utf-8") as f:
        cities_data = json.load(f)

    print(f"Processing {len(cities_data)} cities from comprehensive data...")

    # Create GeoJSON features
    features = []

    for i, city_data in enumerate(cities_data):
        # Determine characteristics
        tech_level = determine_tech_level(city_data)
        endowments = generate_endowments(city_data)
        coastal, mountainous = determine_geographic_flags(city_data)

        # Create feature
        feature = {
            "type": "Feature",
            "properties": {
                "Id": str(i + 1),
                "Burg": city_data["name"].title(),
                "Population": city_data.get("population", 0),
                "type": "city" if city_data.get("population", 0) > 1000 else "village",
                "tech": tech_level,
                "endowments": endowments,
                "Coastal": coastal,
                "Mountainous": mountainous,
                # Additional city characteristics
                "capital": city_data.get("capital", False),
                "port": city_data.get("port", False),
                "citadel": city_data.get("citadel", False),
                "walls": city_data.get("walls", False),
                "plaza": city_data.get("plaza", False),
                "temple": city_data.get("temple", False),
                "shanty_town": city_data.get("shanty_town", False),
                # Geographic and infrastructure data
                "elevation": city_data.get("elevation", 0),
                "valley": city_data.get("valley", ""),
                "founded_in": city_data.get("founded_in", 0),
                "building_count": city_data.get("building_count", 0),
                "district_count": city_data.get("district_count", 0),
                "districts": city_data.get("districts", []),
            },
            "geometry": {
                "type": "Point",
                "coordinates": [city_data.get("longitude", 0), city_data.get("latitude", 0)],
            },
        }

        features.append(feature)

        # Debug output for first few cities
        if i < 5:
            print(
                f"{city_data['name']}: {city_data['population']} pop, {tech_level}, {len(city_data.get('districts', []))} districts"
            )

    # Sort by population (largest first)
    features.sort(key=lambda x: x["properties"]["Population"], reverse=True)

    # Create final GeoJSON
    geojson = {"type": "FeatureCollection", "features": features}

    # Write to file
    output_path = OUTPUT_DIR / "accurate_cities.geojson"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(geojson, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Created {output_path}")
    print(f"📊 Processed {len(features)} cities")

    # Statistics
    populations = [f["properties"]["Population"] for f in features]
    tech_levels = {}
    for f in features:
        tech = f["properties"]["tech"]
        tech_levels[tech] = tech_levels.get(tech, 0) + 1

    print(f"📈 Population range: {min(populations):,} - {max(populations):,}")
    print(f"🏭 Tech distribution: {dict(tech_levels)}")

    # Print top 10 cities
    print("\n🏙️ Top 10 Cities by Population:")
    for i, feature in enumerate(features[:10]):
        props = feature["properties"]
        print(
            f"{i + 1:2d}. {props['Burg']:<20} {props['Population']:>6,} pop ({props['tech']:<10}, {props['district_count']} districts)"
        )

    return output_path


if __name__ == "__main__":
    main()
