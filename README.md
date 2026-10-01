# Decision Brief Generator

Turns raw grocery demand data into a short weekly decision brief: a headline, three key takeaways, and recommended actions with owners and urgency.

## How it works

Python computes every number; the LLM only interprets them.

1. `compute_facts()` reads the CSV and calculates:
   - Forecast accuracy (WAPE) and bias, overall and by category
   - SKUs with more than 15% forecast bias over the last two weeks
   - Promo demand the forecast missed
   - Stockout and overstock risk from days of cover in the latest week
2. The facts are inserted into a prompt that tells the model to use only those facts and to cite the metric behind each claim.
3. The prompt is sent to Claude, or printed so you can paste it into any LLM.

The model never sees raw rows, so it can't invent or miscalculate figures, and every claim in the brief traces back to a computed metric.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

```bash
python decision_brief.py grocery_demand_sample.csv
```

- **With `ANTHROPIC_API_KEY` set:** prints the generated brief.
- **Without it:** prints the facts and full prompt for use with any LLM.

## Data

`grocery_demand_sample.csv` is a synthetic dataset: 8 weeks, 3 stores, 10 SKUs across 6 categories. Columns:

| Column | Description |
| --- | --- |
| `week` | ISO week, e.g. `2026-W01` |
| `store` | Store name |
| `sku` | Product name |
| `category` | Product category |
| `perishable` | `True` / `False` |
| `promo` | `1` if on promotion that week, else `0` |
| `forecast_units` | Forecast weekly units |
| `actual_units` | Actual weekly units sold |
| `on_hand_units` | Stock on hand (only needed for the latest week) |

## Configuration

Thresholds are constants at the top of `decision_brief.py`:

| Constant | Default | Meaning |
| --- | --- | --- |
| `PERISHABLE_MAX_COVER` | 5 | Days of cover above which perishables are overstocked |
| `SHELF_MAX_COVER` | 21 | Days of cover above which shelf-stable items are overstocked |
| `STOCKOUT_RISK_COVER` | 2 | Days of cover below which an item is at stockout risk |
| `BIAS_FLAG` | 0.15 | Forecast bias that flags a SKU |

## License

[MIT](LICENSE)
