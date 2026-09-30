#!/usr/bin/env python3
"""Generate a large GeoJSON file for performance testing."""

import json
import random
from pathlib import Path


def generate_large_geojson(
    num_cities: int = 140, output_path: str = "data/large_test.geojson"
) -> None:
    """Generate a GeoJSON file with many cities for performance testing.

    Args:
        num_cities: Number of cities to generate
        output_path: Output file path
    """

    # City name components for variety
    prefixes = ["North", "South", "East", "West", "New", "Old", "Upper", "Lower", "Great", "Little"]
    bases = [
        "Haven",
        "Port",
        "City",
        "Town",
        "Bridge",
        "Hill",
        "Valley",
        "Grove",
        "Field",
        "Springs",
        "Mills",
        "Falls",
        "Cross",
        "Gate",
        "Ford",
        "Bay",
        "Point",
        "Ridge",
        "Dale",
        "Burg",
    ]
    suffixes = ["ton", "ville", "stead", "ford", "holm", "by", "thorpe", "wick", "ham", "bury"]

    cultures = ["noon", "dawn", "night", "dusk"]
    religions = ["asta", "aumir", "dayar", "none"]
    tech_levels = ["tribal", "medieval", "industrial"]

    features = []

    # Generate cities across a realistic geographic region (roughly 10x10 degree area)
    base_lat, base_lon = 45.0, -75.0  # Somewhere in temperate zone

    for i in range(num_cities):
        # Generate coordinates (in EPSG:3857 Web Mercator for consistency with test data)
        lat_offset = random.uniform(-5, 5)  # +/- 5 degrees
        lon_offset = random.uniform(-5, 5)  # +/- 5 degrees

        lat = base_lat + lat_offset
        lon = base_lon + lon_offset

        # Convert to EPSG:3857 (rough approximation)
        # Web Mercator projection: x = lon * 111319.49, y = lat * 111319.49 (simplified)
        x = (lon + 180) * 111319.49
        y = lat * 111319.49

        # Generate city properties
        name_parts = []
        if random.random() < 0.3:  # 30% chance of prefix
            name_parts.append(random.choice(prefixes))
        name_parts.append(random.choice(bases))
        if random.random() < 0.2:  # 20% chance of suffix
            name_parts[-1] += random.choice(suffixes)

        city_name = "".join(name_parts)

        # Population distribution: mostly small towns, some cities, few large cities
        pop_type = random.choices(
            ["small", "medium", "large", "mega"],
            weights=[60, 30, 9, 1],  # 60% small, 30% medium, 9% large, 1% mega
            k=1,
        )[0]

        if pop_type == "small":
            population = random.randint(1000, 10000)
        elif pop_type == "medium":
            population = random.randint(10000, 50000)
        elif pop_type == "large":
            population = random.randint(50000, 200000)
        else:  # mega
            population = random.randint(200000, 1000000)

        # Tech level biased by population
        if population > 100000:
            tech = random.choices(tech_levels, weights=[5, 25, 70], k=1)[0]
        elif population > 30000:
            tech = random.choices(tech_levels, weights=[10, 60, 30], k=1)[0]
        else:
            tech = random.choices(tech_levels, weights=[40, 50, 10], k=1)[0]

        # Infrastructure features based on population and random chance
        is_capital = random.random() < 0.02  # 2% chance of capital
        is_port = random.random() < 0.15  # 15% chance of port
        has_plaza = random.random() < 0.25  # 25% chance of market
        has_temple = random.random() < 0.20  # 20% chance of temple
        has_citadel = random.random() < 0.10  # 10% chance of citadel
        has_walls = random.random() < 0.15  # 15% chance of walls
        is_shanty = population < 5000 and random.random() < 0.05  # 5% chance for small towns

        # Elevation for mining potential (simplified)
        elevation = random.randint(0, 2000)

        properties = {
            "Id": str(i + 1),
            "Burg": city_name,
            "Population": population,
            "tech": tech,
            "Culture": random.choice(cultures),
            "Religion": random.choice(religions),
            "Elevation (m)": elevation,
            "Capital": "capital" if is_capital else None,
            "Port": "port" if is_port else None,
            "Plaza": "plaza" if has_plaza else None,
            "Temple": "temple" if has_temple else None,
            "Citadel": "citadel" if has_citadel else None,
            "Walls": "walls" if has_walls else None,
            "Shanty Town": "shanty town" if is_shanty else None,
        }

        # Remove None values
        properties = {k: v for k, v in properties.items() if v is not None}

        feature = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [x, y]},
            "properties": properties,
        }

        features.append(feature)

    # Create FeatureCollection
    geojson_data = {"type": "FeatureCollection", "features": features}

    # Write to file
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(geojson_data, f, indent=2)

    print(f"Generated {num_cities} cities in {output_file}")
    print(f"File size: {output_file.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    generate_large_geojson(140, "data/performance_test.geojson")
