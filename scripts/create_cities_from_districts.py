#!/usr/bin/env python3
"""
Extract city information from district files and create a GeoJSON for economic simulation.
"""

import json
import random
import sys
from collections import defaultdict
from pathlib import Path

# Reason: the script lives in scripts/; put the repository root on the path for src.econgen.
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.econgen.paths import worldbuilder_dir

# Eno-Worldbuilder2 checkout ($ENO_WORLDBUILDER_DIR); outputs go to the repository root.
WORLDBUILDER_DIR = worldbuilder_dir()
OUTPUT_DIR = REPO_ROOT


def get_polygon_centroid(coordinates):
    """Calculate centroid of a polygon."""
    # Take the first ring (exterior)
    ring = coordinates[0]
    x_coords = [point[0] for point in ring]
    y_coords = [point[1] for point in ring]

    # Simple centroid calculation
    centroid_x = sum(x_coords) / len(x_coords)
    centroid_y = sum(y_coords) / len(y_coords)

    return [centroid_x, centroid_y]


def analyze_district_file(filepath):
    """Analyze a district file to extract city information."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        city_name = data.get("name", "")
        if not city_name:
            # Extract from filename
            city_name = Path(filepath).stem.split(".")[0]

        # Capitalize city name
        city_name = city_name.capitalize()

        districts = data.get("features", [])
        if not districts:
            return None

        # Calculate statistics
        total_districts = len(districts)
        district_types = defaultdict(int)
        eras = defaultdict(int)
        all_coords = []

        for district in districts:
            props = district.get("properties", {})
            district_types[props.get("Type", "Unknown")] += 1
            eras[props.get("Era", "Unknown")] += 1

            # Collect coordinates for centroid calculation
            geom = district.get("geometry", {})
            if geom.get("type") == "Polygon":
                coords = geom.get("coordinates", [])
                if coords:
                    all_coords.extend(coords[0])

        # Calculate city centroid
        if all_coords:
            x_coords = [point[0] for point in all_coords]
            y_coords = [point[1] for point in all_coords]
            city_center = [sum(x_coords) / len(x_coords), sum(y_coords) / len(y_coords)]
        else:
            return None

        # Determine dominant era
        dominant_era = max(eras.items(), key=lambda x: x[1])[0] if eras else "Medieval"

        # Map era to tech level
        tech_mapping = {
            "Ancient": "tribal",
            "Medieval": "medieval",
            "Renaissance": "medieval",
            "Industrial": "industrial",
            "Modern": "industrial",
        }
        tech_level = tech_mapping.get(dominant_era, "medieval")

        # Estimate population based on district count and types
        base_population = total_districts * 500  # Base per district

        # Adjust for district types
        residential_districts = district_types.get("Residential", 0)
        commercial_districts = district_types.get("Commercial", 0)
        industrial_districts = district_types.get("Industrial", 0)

        population = (
            base_population
            + residential_districts * 1000
            + commercial_districts * 300
            + industrial_districts * 200
        )

        # Add some randomness but keep it deterministic per city
        random.seed(hash(city_name) % 2147483647)
        population = int(population * random.uniform(0.7, 1.3))

        # Generate endowments based on geography and district types
        endowments = {}

        # Base resources
        endowments["food"] = random.randint(50, 200)
        endowments["wood"] = random.randint(30, 150)
        endowments["stone"] = random.randint(20, 100)

        # Special resources based on characteristics
        if commercial_districts > 2:
            endowments["luxury_goods"] = random.randint(10, 50)

        if industrial_districts > 1:
            endowments["iron_ore"] = random.randint(50, 200)
            endowments["tools"] = random.randint(20, 80)

        # Coastal determination (simplified - based on coordinate ranges)
        coastal = (
            min(x_coords) < 30
            and max(x_coords) > 25  # Coastal longitude ranges
            or abs(city_center[1] - 36) < 2  # Near latitude 36
        )

        # Mountainous determination (simplified - based on coordinate clustering)
        mountainous = len({round(coord, 1) for coord in x_coords}) > 5

        if coastal:
            endowments["fish"] = random.randint(100, 400)

        return {
            "name": city_name,
            "population": population,
            "tech": tech_level,
            "center": city_center,
            "districts": total_districts,
            "dominant_era": dominant_era,
            "district_types": dict(district_types),
            "endowments": endowments,
            "coastal": coastal,
            "mountainous": mountainous,
        }

    except Exception as e:  # noqa: BLE001 - skip unreadable files, keep processing the rest
        print(f"Error processing {filepath}: {e}")
        return None


def main():
    districts_dir = WORLDBUILDER_DIR / "GIS" / "districts"

    cities = []

    print("Analyzing district files...")
    for district_file in districts_dir.glob("*.geojson"):
        city_info = analyze_district_file(district_file)
        if city_info:
            cities.append(city_info)
            print(
                f"Processed: {city_info['name']} ({city_info['population']:,} pop, {city_info['districts']} districts)"
            )

    # Sort by population (largest first)
    cities.sort(key=lambda x: x["population"], reverse=True)

    # Create GeoJSON FeatureCollection
    features = []

    for i, city in enumerate(cities):
        feature = {
            "type": "Feature",
            "properties": {
                "Id": str(i + 1),
                "Burg": city["name"],
                "Population": city["population"],
                "type": "city",
                "tech": city["tech"],
                "endowments": city["endowments"],
                "Coastal": city["coastal"],
                "Mountainous": city["mountainous"],
                "districts_count": city["districts"],
                "dominant_era": city["dominant_era"],
                "district_types": city["district_types"],
            },
            "geometry": {"type": "Point", "coordinates": city["center"]},
        }
        features.append(feature)

    # Create final GeoJSON
    geojson = {"type": "FeatureCollection", "features": features}

    # Write to file
    output_path = OUTPUT_DIR / "worldbuilder_cities.geojson"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(geojson, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Created {output_path}")
    print(f"📊 Processed {len(cities)} cities")
    print(
        f"📈 Population range: {min(c['population'] for c in cities):,} - {max(c['population'] for c in cities):,}"
    )

    # Print top 10 cities
    print("\n🏙️ Top 10 Cities by Population:")
    for i, city in enumerate(cities[:10]):
        print(
            f"{i + 1:2d}. {city['name']:<15} {city['population']:>7,} pop ({city['tech']}, {city['districts']} districts)"
        )


if __name__ == "__main__":
    main()
