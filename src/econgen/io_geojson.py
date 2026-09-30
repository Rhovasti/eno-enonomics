"""GeoJSON loading and validation for economic operators."""

import json
from pathlib import Path
from typing import List, Dict, Any, Sequence, Union
import geojson_pydantic as geojson
from pyproj import Transformer
from pydantic import ValidationError
from decimal import Decimal

from .models import Operator, TechLevel
import logging

logger = logging.getLogger(__name__)


class GeoJSONLoader:
    """Load and validate GeoJSON data, converting to economic operators."""

    def __init__(self, strict: bool = True):
        """Initialize GeoJSON loader.

        Args:
            strict: If True, raise exceptions on validation errors.
                   If False, log warnings and skip invalid features.
        """
        self.strict = strict
        # Transform from Web Mercator (EPSG:3857) to WGS84 (EPSG:4326)
        self.transformer = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)
        logger.info(f"Initialized GeoJSON loader (strict={strict})")

    def load_operators(self, paths: Sequence[Union[Path, str]]) -> List[Operator]:
        """Load operators from GeoJSON files.

        Args:
            paths: List of file paths to load

        Returns:
            List of validated Operator instances

        Raises:
            ValueError: If strict=True and validation fails
        """
        operators = []

        for path_input in paths:
            path = Path(path_input)
            logger.info(f"Loading GeoJSON from {path}")

            if not path.exists():
                error_msg = f"File not found: {path}"
                if self.strict:
                    raise FileNotFoundError(error_msg)
                logger.warning(error_msg)
                continue

            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                error_msg = f"Failed to parse JSON from {path}: {e}"
                if self.strict:
                    raise ValueError(error_msg)
                logger.warning(error_msg)
                continue

            # Validate GeoJSON structure
            try:
                if data.get("type") == "FeatureCollection":
                    fc = geojson.FeatureCollection(**data)
                    features = fc.features
                elif data.get("type") == "Feature":
                    features = [geojson.Feature(**data)]
                else:
                    error_msg = f"Invalid GeoJSON type in {path}: {data.get('type')}"
                    if self.strict:
                        raise ValueError(error_msg)
                    logger.warning(error_msg)
                    continue
            except ValidationError as e:
                error_msg = f"Invalid GeoJSON structure in {path}: {e}"
                if self.strict:
                    raise ValueError(error_msg)
                logger.warning(error_msg)
                continue

            # Convert features to operators
            for i, feature in enumerate(features):
                try:
                    feature_dict = (
                        feature.model_dump() if hasattr(feature, "model_dump") else feature
                    )
                    op = self._feature_to_operator(feature_dict, f"{path.stem}_{i}")
                    operators.append(op)
                except Exception as e:
                    error_msg = f"Failed to convert feature {i} from {path}: {e}"
                    if self.strict:
                        raise ValueError(error_msg)
                    logger.warning(error_msg)

        logger.info(f"Successfully loaded {len(operators)} operators from {len(paths)} files")
        return operators

    def _feature_to_operator(self, feature: Dict[str, Any], fallback_id: str) -> Operator:
        """Convert GeoJSON feature to Operator instance.

        Args:
            feature: GeoJSON feature dictionary
            fallback_id: Fallback ID if none found in feature

        Returns:
            Operator instance

        Raises:
            ValueError: If feature cannot be converted
        """
        props = feature.get("properties", {})
        geom = feature.get("geometry", {})

        # Extract coordinates and convert projection
        coords = geom.get("coordinates", [0, 0])
        if len(coords) >= 2:
            # Transform from Web Mercator (EPSG:3857) to WGS84 (EPSG:4326)
            lon, lat = self.transformer.transform(coords[0], coords[1])
        else:
            raise ValueError(f"Invalid coordinates in feature: {coords}")

        # Extract operator ID
        operator_id = str(props.get("Id", props.get("fid", fallback_id)))

        # Extract name
        name = props.get("Burg", props.get("name", f"Unknown_{operator_id}"))

        # Infer technology level
        tech = self._infer_tech_level(props)

        # Extract population
        population = int(props.get("Population", 0))

        # Extract tags
        tags = self._extract_tags(props)

        # Extract endowments
        endowments = self._extract_endowments(props)
        self._infer_fantastical_endowments(props, endowments, operator_id, lon)

        # Create operator
        return Operator(
            operator_id=operator_id,
            name=name,
            kind="city",  # Default - could be extended for other types
            tech=tech,
            coord=(lat, lon),
            population=population,
            tags=tags,
            endowments=endowments,
            capital=props.get("Capital") == "capital",
            port=props.get("Port") == "port",
            citadel=props.get("Citadel") == "citadel",
            walls=props.get("Walls") == "walls",
            plaza=props.get("Plaza") == "plaza",
            temple=props.get("Temple") == "temple",
            shanty_town=props.get("Shanty Town") == "shanty town",
        )

    def _infer_tech_level(self, props: Dict[str, Any]) -> TechLevel:
        """Infer technology level from feature properties.

        Args:
            props: Feature properties dictionary

        Returns:
            Inferred TechLevel
        """
        # Check for explicit tech field
        if "tech" in props:
            tech_str = str(props["tech"]).lower()
            try:
                return TechLevel(tech_str)
            except ValueError:
                logger.warning(f"Invalid tech level '{tech_str}', falling back to inference")

        # Infer from population size
        pop = props.get("Population", 0)
        if pop > 50000:
            return TechLevel.INDUSTRIAL
        elif pop > 10000:
            return TechLevel.MEDIEVAL
        else:
            return TechLevel.TRIBAL

    def _extract_tags(self, props: Dict[str, Any]) -> List[str]:
        """Extract tags from feature properties.

        Args:
            props: Feature properties dictionary

        Returns:
            List of tags
        """
        tags = []

        # Infrastructure tags
        if props.get("Port") == "port":
            tags.append("port")
        if props.get("Capital") == "capital":
            tags.append("capital")
        if props.get("Plaza") == "plaza":
            tags.append("market")
        if props.get("Temple") == "temple":
            tags.append("religious")
        if props.get("Citadel") == "citadel":
            tags.append("fortified")
        if props.get("Walls") == "walls":
            tags.append("walled")
        if props.get("Shanty Town") == "shanty town":
            tags.append("poor")

        # Culture/religion tags
        culture = props.get("Culture", "")
        if culture:
            tags.append(f"culture_{culture.lower()}")

        religion = props.get("Religion", "")
        if religion and religion != "No religion":
            tags.append(f"religion_{religion.lower()}")

        return tags

    def _extract_endowments(self, props: Dict[str, Any]) -> Dict[str, Decimal]:
        """Extract resource endowments from feature properties.

        Args:
            props: Feature properties dictionary

        Returns:
            Dictionary of resource endowments
        """
        endowments = {}

        # Check for explicit endowments
        if "endowments" in props and isinstance(props["endowments"], dict):
            for resource_id, value in props["endowments"].items():
                try:
                    endowments[resource_id] = Decimal(str(value))
                except (ValueError, TypeError):
                    logger.warning(f"Invalid endowment value for {resource_id}: {value}")

        # Derive capacity drivers from the resource stocks the worldbuilder
        # emits (wood/stone/iron_ore/fish), so extraction rules (forestry,
        # quarrying, mining, fishing) fire for cities holding those stocks even
        # when geographic signals (Culture/Elevation/Mountainous) are absent.
        wood = endowments.get("wood", Decimal("0"))
        if wood > 0:
            endowments["forestry"] = max(
                endowments.get("forestry", Decimal("0")), _stock_driver(wood)
            )
        ore = max(endowments.get("stone", Decimal("0")), endowments.get("iron_ore", Decimal("0")))
        if ore > 0:
            endowments["mining_potential"] = max(
                endowments.get("mining_potential", Decimal("0")), _stock_driver(ore)
            )
        if endowments.get("fish", Decimal("0")) > 0:
            endowments["fishing"] = max(endowments.get("fishing", Decimal("0")), Decimal("0.6"))

        # Infer endowments from features
        if props.get("Port") == "port":
            endowments["fishing"] = Decimal("0.8")
            endowments["trade_access"] = Decimal("0.9")

        # Handle boolean geographic flags
        if props.get("Coastal", False):
            endowments["fishing"] = Decimal("0.8")
            endowments["trade_access"] = Decimal("0.7")

        if props.get("Mountainous", False):
            endowments["mining_potential"] = Decimal("0.6")

        # Infer from elevation (mountains = mining potential)
        elevation = props.get("Elevation (m)", 0)
        if elevation > 500:
            endowments["mining_potential"] = Decimal("0.6")
        elif elevation > 200:
            endowments["mining_potential"] = Decimal("0.3")

        # Infer from culture (crude but deterministic)
        culture = props.get("Culture", "").lower()
        if "forest" in culture or "wild" in culture:
            endowments["forestry"] = Decimal("0.7")
        if "noon" in culture or "day" in culture:
            endowments["agriculture"] = Decimal("0.8")
        if "night" in culture or "dawn" in culture:
            endowments["craftsmanship"] = Decimal("0.6")

        # Population density affects labor endowments
        pop = props.get("Population", 0)
        if pop > 30000:
            endowments["skilled_labor"] = Decimal("0.7")
        elif pop > 10000:
            endowments["general_labor"] = Decimal("0.8")
        elif pop > 5000:
            endowments["general_labor"] = Decimal("0.6")
        elif pop > 1000:
            endowments["general_labor"] = Decimal("0.4")

        # Add basic endowments for all settlements without overriding specializations
        if pop > 1000:
            for driver, baseline in (("agriculture", "0.5"), ("craftsmanship", "0.4")):
                endowments[driver] = max(endowments.get(driver, Decimal("0")), Decimal(baseline))

        # Tech-based industrial capacity
        # Reason: use the inferred tech level; most datasets have no explicit "tech" field
        tech_level = self._infer_tech_level(props)
        if tech_level == TechLevel.MEDIEVAL:
            endowments["industrial_capacity"] = Decimal("0.3")
        elif tech_level == TechLevel.INDUSTRIAL:
            endowments["industrial_capacity"] = Decimal("0.7")

        return endowments

    def _infer_fantastical_endowments(
        self,
        props: Dict[str, Any],
        endowments: Dict[str, Decimal],
        operator_id: str,
        lon: float,
    ) -> None:
        """Infer Eno alchemical endowments (Periodical System) from geography.

        Adds the capacity drivers that fantastical gathering/mining rules gate on
        (see ``fantastical.py``). Distribution is lore-faithful and deterministic
        so a given city always specializes the same way:
        - Sap where there is vegetation (wood stock, or forestry/agriculture in
          datasets without worldbuilder stocks) — common.
        - Rime on the dark side (lon < 0), Ash on the sun side (lon >= 0).
        - Pitch at coastal/deep-sea sites.
        - Phos at industrial (energy) sites.
        - 1-2 element deposits per mining/precious city (varied, by stable hash);
          mining means an iron_ore stock, or mining potential without stocks.
        - Mucus glands and Mold deposits rare (a handful of cities).

        Args:
            props: Feature properties dictionary
            endowments: Endowment dict to extend in place
            operator_id: Operator id (used for deterministic specialization)
            lon: Longitude (dark vs sun side of Eno)
        """
        h = _stable_hash(operator_id)
        zero = Decimal("0")

        # Reason: worldbuilder exports carry resource stocks; plain geographic
        # datasets (e.g. kaupungit) do not, so fall back to the derived drivers.
        if isinstance(props.get("endowments"), dict):
            has_vegetation = endowments.get("wood", zero) > 0
            has_mining = endowments.get("iron_ore", zero) > 0
        else:
            has_vegetation = (
                endowments.get("forestry", zero) > 0 or endowments.get("agriculture", zero) > 0
            )
            has_mining = endowments.get("mining_potential", zero) > 0

        # Sap: ubiquitous where vegetation exists — a common component.
        if has_vegetation:
            endowments.setdefault("sap_harvest", Decimal("0.5"))

        # Dark vs sun side of Eno -> Rime vs Ash pilgrimage (each city picks one).
        if lon < 0:
            endowments["rime_collection"] = Decimal("0.4")
        else:
            endowments["ash_pilgrimage"] = Decimal("0.4")

        # Pitch: dredged from the deep sea by coastal / trading cities.
        if (
            endowments.get("fish", Decimal("0")) > 0
            or endowments.get("trade_access", Decimal("0")) > 0
        ):
            endowments["pitch_depth"] = Decimal("0.5")

        # Phos: raw energy gathered at industrial sites.
        if self._infer_tech_level(props) == TechLevel.INDUSTRIAL:
            endowments["phos_vent"] = Decimal("0.4")

        # Element deposits: cities with a mining or precious signal specialize
        # in 1-2 periodic elements (deterministic per city, so specialization is
        # stable but varied across the map).
        has_precious = endowments.get("luxury_goods", Decimal("0")) > 0
        if has_mining or has_precious:
            pool = ["feron", "cunu", "charon", "plon", "suhra", "sirael"]
            if has_precious:
                pool += ["aru", "sira"]
            count = 1 + (h % 2)
            chosen: List[str] = []
            seed = h
            while len(chosen) < count:
                seed = (seed * 1103515245 + 12345) % 2147483647
                element = pool[seed % len(pool)]
                if element not in chosen:
                    chosen.append(element)
            for element in chosen:
                endowments[f"{element}_deposit"] = Decimal("0.6")

        # Rare components: Mucus glands (Norian populations), Mold (meteor sites).
        if h % 7 == 0:
            endowments["mucus_gland"] = Decimal("0.5")
        if h % 23 == 0:
            endowments["mold_deposit"] = Decimal("0.4")


def _stable_hash(text: str) -> int:
    """Deterministic 31-bit hash of a string (Python's hash() is salted)."""
    h = 0
    for ch in text:
        h = (h * 31 + ord(ch)) % 0x80000000
    return h


def _stock_driver(stock: Any) -> Decimal:
    """Map a raw resource-stock magnitude to a sub-1 capacity-driver value.

    ``_calculate_endowment_capacity`` expects drivers in roughly [0, 1] (it
    computes ``1 + clamp(value*3, 0, 3)``); raw worldbuilder stocks are large
    integers (e.g. wood ~ 40-160), so scale them into a graded [0.2, 0.9] band.
    """
    value = Decimal(str(stock))
    return min(Decimal("0.9"), Decimal("0.2") + value / Decimal("250"))


# Export main class
__all__ = ["GeoJSONLoader"]
