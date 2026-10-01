"""
Decision Brief Generator for grocery demand planning.

Design principle: Python computes every number; the LLM only interprets
the computed facts. The model never touches raw rows, so it cannot invent
or miscalculate figures, and every claim in the brief traces back to a
metric in the facts table.

Usage:
    python decision_brief.py grocery_demand_sample.csv
Set ANTHROPIC_API_KEY (in the environment or a .env file) to generate the
brief automatically; otherwise the script prints the facts and the full
prompt to paste into any LLM.
"""
import json
import os
import sys
from typing import Any

import pandas as pd
from dotenv import load_dotenv

PERISHABLE_MAX_COVER = 5    # days
SHELF_MAX_COVER = 21        # days
STOCKOUT_RISK_COVER = 2     # days
BIAS_FLAG = 0.15            # 15% systematic over/under forecast

def compute_facts(df: pd.DataFrame) -> dict[str, Any]:
    weeks = sorted(df.week.unique())
    latest, recent = weeks[-1], weeks[-2:]
    facts: dict[str, Any] = {"period": f"{weeks[0]} to {latest}"}

    # Forecast accuracy by category (WAPE) and bias
    g = df.groupby("category")
    acc = pd.DataFrame({
        "wape": g.apply(lambda x: (x.actual_units - x.forecast_units).abs().sum() / x.actual_units.sum()),
        "bias": g.apply(lambda x: (x.forecast_units.sum() - x.actual_units.sum()) / x.actual_units.sum()),
    }).round(3)
    facts["overall_wape"] = round(float((df.actual_units - df.forecast_units).abs().sum() / df.actual_units.sum()), 3)
    facts["category_accuracy"] = acc.reset_index().to_dict("records")

    # SKUs with systematic bias over the last two weeks
    r = df[df.week.isin(recent)].groupby("sku")[["forecast_units","actual_units"]].sum()
    r["bias"] = ((r.forecast_units - r.actual_units) / r.actual_units).round(3)
    facts["biased_skus_last_2_weeks"] = r[r.bias.abs() > BIAS_FLAG].reset_index()[["sku","bias"]].to_dict("records")

    # Promo lift the forecast missed
    p = df[df.promo == 1]
    if len(p):
        facts["promo_underforecast"] = (p.groupby("sku")[["forecast_units","actual_units"]].sum()
            .assign(missed_units=lambda x: x.actual_units - x.forecast_units).reset_index().to_dict("records"))

    # Days of cover at latest week
    last = df[df.week == latest].copy()
    last["daily_demand"] = last.actual_units / 7
    last["days_cover"] = (last.on_hand_units / last.daily_demand).round(1)
    risk = last[last.days_cover < STOCKOUT_RISK_COVER]
    over = last[(last.perishable & (last.days_cover > PERISHABLE_MAX_COVER)) |
                (~last.perishable & (last.days_cover > SHELF_MAX_COVER))]
    cols = ["store","sku","on_hand_units","daily_demand","days_cover"]
    facts["stockout_risk"] = risk[cols].round(1).to_dict("records")
    facts["overstock_risk"] = over[cols].round(1).to_dict("records")
    return facts

PROMPT = """You are a senior demand planner writing a weekly decision brief for a quick commerce grocery business.

Use ONLY the facts below. Do not calculate new numbers or assume anything not stated. If the facts do not support a conclusion, say so.

FACTS (computed in code, verified):
{facts}

Write the brief in this structure:
1. Headline: one sentence on the most important thing leadership should know this week.
2. Three key takeaways: each cites the specific metric it is based on.
3. Recommended actions: up to three, each with an owner (Commercial, Ops, or Planning), urgency (today, this week, next cycle), and the expected effect.
4. Confidence and caveats: what the data cannot tell us and what to check before acting.

Keep it under 250 words, plain language, written for a non technical VP."""

def main(path: str) -> None:
    df = pd.read_csv(path)
    facts = compute_facts(df)
    prompt = PROMPT.format(facts=json.dumps(facts, indent=2, default=str))
    if os.getenv("ANTHROPIC_API_KEY"):
        import anthropic
        msg = anthropic.Anthropic().messages.create(
            model="claude-sonnet-4-5", max_tokens=800,
            messages=[{"role": "user", "content": prompt}])

        # Filter and join only the text blocks
        response = "".join([block.text for block in msg.content if block.type == "text"])
        print(response)
    else:
        print(prompt)

if __name__ == "__main__":
    load_dotenv()
    main(sys.argv[1] if len(sys.argv) > 1 else "grocery_demand_sample.csv")
