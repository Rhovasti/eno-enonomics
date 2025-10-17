# Economic Worldbuilding Analysis Report

**Generated:** 2025-09-20 14:19:47  
**Simulation Framework:** Economic Worldbuilding Generator v0.1.0

---

## Executive Summary

### Overview
The economic simulation analyzed **141** cities and settlements across a diverse technological landscape. The analysis reveals 45 active trade routes moving 41.81 units of goods, supported by 264 distinct production capabilities.

### Key Metrics
- **Total Population**: 1,481,480 inhabitants
- **Trade Volume**: 41.81 units
- **Active Trade Routes**: 45
- **Production Capabilities**: 264

### Technological Distribution
- **Tribal Era**: 24 settlements
- **Medieval Era**: 68 settlements  
- **Industrial Era**: 49 settlements

### Infrastructure
- **Capital Cities**: 0
- **Port Cities**: 0
- **Market Towns**: 0

## Settlement Overview

### Largest Cities by Population

| Rank | City | Population | Tech Level | Features |
|------|------|-----------|------------|----------|
| 1 | Guild | 79,193 | Industrial | None |
| 2 | Mahyapak | 71,912 | Industrial | None |
| 3 | Chingsan | 57,543 | Industrial | None |
| 4 | Pranos | 56,744 | Industrial | None |
| 5 | Jeong | 50,393 | Industrial | None |
| 6 | Palwede | 47,137 | Industrial | None |
| 7 | Zadardelen | 44,324 | Industrial | None |
| 8 | Engar | 42,312 | Industrial | None |
| 9 | Alebuo | 38,623 | Industrial | None |
| 10 | Phoelit | 32,245 | Industrial | None |

### Regional Distribution
- **Unknown**: 141 settlements, 1,481,480 total population (avg: 10,506)


## Production Analysis

### Top Production Centers

| City | Total Capacity | Primary Industries | Tech Level |
|------|---------------|-------------------|------------|
| Guild | 26.05 | Steel Making, Machinery Production | Industrial |
| Mahyapak | 24.82 | Steel Making, Machinery Production | Industrial |
| Chingsan | 22.21 | Steel Making, Machinery Production | Industrial |
| Pranos | 22.05 | Steel Making, Machinery Production | Industrial |
| Jeong | 20.78 | Steel Making, Machinery Production | Industrial |
| Palwede | 20.10 | Steel Making, Machinery Production | Industrial |
| Zadardelen | 19.49 | Steel Making, Machinery Production | Industrial |
| Engar | 19.04 | Steel Making, Machinery Production | Industrial |
| Alebuo | 18.19 | Steel Making, Machinery Production | Industrial |
| Phoelit | 16.62 | Steel Making, Machinery Production | Industrial |

### Production by Industry

- **Steel Making**: 386.62 total capacity across 117 producers
- **Machinery Production**: 99.59 total capacity across 11 producers
- **Weaving**: 87.90 total capacity across 30 producers
- **Jewelry Crafting**: 67.49 total capacity across 78 producers
- **Farming**: 4.27 total capacity across 14 producers
- **Toolmaking**: 3.07 total capacity across 14 producers


## Trade Analysis

### Trade Network Overview
- **Total Trade Volume**: 41.81 units
- **Active Trade Routes**: 45
- **Average Trade Distance**: 0.01 km
- **Unique Trading Partners**: 76

### Most Traded Resources

| Resource | Total Volume | Trade Routes |
|----------|-------------|--------------|
| Steel | 41.81 | 45 |

### Major Trade Routes

- **Bernala → Jinzhou**: 2.19 units, 0.02 km (steel)
- **Monte → Castri**: 2.05 units, 0.01 km (steel)
- **Shaxing → Jiafeng**: 1.92 units, 0.01 km (steel)
- **Mical → Uiaria**: 1.80 units, 0.02 km (steel)
- **Vialiranave → Reriro**: 1.73 units, 0.01 km (steel)
- **Jouy → Jargeroy**: 1.60 units, 0.01 km (steel)
- **Kushk → Ouiar**: 1.31 units, 0.00 km (steel)
- **Kushimaki → Vul**: 1.21 units, 0.00 km (steel)
- **Luquti → Uiaria**: 1.11 units, 0.01 km (steel)
- **Pogliaferte → Castri**: 1.09 units, 0.01 km (steel)


## Market Analysis

### Price Volatility by Resource

| Resource | Avg Price | Price Range | Volatility | Markets |
|----------|-----------|-------------|------------|---------|
| Steel | 59.33 | 14.40 - 120.00 | 178.0% | 117 |
| Jewelry | 452.87 | 72.45 - 500.00 | 94.4% | 127 |
| Machinery | 250.00 | 250.00 - 250.00 | 0.0% | 49 |
| Tools | 50.00 | 50.00 - 50.00 | 0.0% | 133 |
| Iron Ore | 30.00 | 30.00 - 30.00 | 0.0% | 113 |
| Fish | 25.00 | 25.00 - 25.00 | 0.0% | 133 |
| Stone | 8.00 | 8.00 - 8.00 | 0.0% | 133 |
| Wood | 10.00 | 10.00 - 10.00 | 0.0% | 133 |
| Textiles | 40.00 | 40.00 - 40.00 | 0.0% | 113 |
| Food | 20.00 | 20.00 - 20.00 | 0.0% | 133 |

### Market Insights

**High Price Volatility**: Steel, Jewelry show significant price variations across markets, indicating potential arbitrage opportunities.

**Stable Markets**: Machinery, Tools, Iron Ore, Fish, Stone demonstrate consistent pricing across multiple markets.



## Regional Analysis

### Economic Regions

#### Central Mixed
- **Settlements**: 141 (1,481,480 total population, avg: 10,506)
- **Infrastructure**: 0 ports, 0 capitals, 0 markets  
- **Dominant Tech**: Medieval
- **Notable Cities**: Guild, Mahyapak, Chingsan



## Appendices

### Methodology
This economic analysis uses a deterministic agent-based model to simulate production, consumption, and trade flows between settlements. Key factors include:

- **Production Capacity**: Based on population, technology level, and resource endowments
- **Demand Modeling**: Per-capita consumption adjusted for culture, infrastructure, and wealth
- **Trade Flows**: Greedy profit-maximization algorithm considering transport costs and distance
- **Price Discovery**: Supply/demand ratios with regional and local market effects

### Limitations
- Simplified cultural and technological assumptions
- Static analysis (no temporal dynamics)
- Limited resource complexity
- Approximated geographic relationships

### Technical Details
- **Coordinate System**: WGS84 (EPSG:4326)
- **Distance Calculation**: Great circle distance (Haversine formula)
- **Optimization**: Greedy algorithm for trade flow allocation

---

*Report generated by Economic Worldbuilding Generator v0.1.0*
*For technical support and methodology details, consult the project documentation.*