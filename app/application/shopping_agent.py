# @spectra AG-002
# @spectra US-007
"""A bounded shopping policy. No language model or purchase tool is invoked."""
from decimal import Decimal
from app.domain.shopping import ShoppingProfile


def advise(profile: ShoppingProfile, comparison: dict) -> dict:
    plan, total, messages = [], Decimal(0), []
    baseline = Decimal(0)
    estimated = False
    for item in comparison["items"]:
        options = item["eligible_offers"]
        if not options:
            messages.append(f"{item['label']}: falta un precio local compatible y vigente.")
            continue
        best = min(options, key=lambda offer: (Decimal(offer["required_outlay"]), Decimal(offer["unit_price"]), offer["store"], offer["id"]))
        total += Decimal(best["required_outlay"])
        baseline += max(Decimal(offer["required_outlay"]) for offer in options)
        estimated = estimated or best["outlay_estimated"]
        plan.append({"key": item["key"], "label": item["label"], "offer": best})
        if Decimal(best["overbuy_quantity"]) > 0:
            messages.append(f"{item['label']}: el formato deja {best['overbuy_quantity']} {best['comparison_unit']} adicionales; comprueba si los consumirás.")
    complete = bool(profile.basket) and len(plan) == len(profile.basket)
    if not complete:
        messages.append("Cesta parcial: el importe solo incluye los productos con cobertura.")
    messages.append("No se han incluido transporte ni envío. El stock y el consumo doméstico no están verificados.")
    return {"mode": "bounded_rules", "llm_used": False, "plan": plan,
            "estimated_outlay": format(total, ".2f"), "variable_weight_estimate": estimated,
            "complete": complete,
            "within_budget": None if profile.max_budget is None or not complete else total <= profile.max_budget,
            "covered_items_within_budget": None if profile.max_budget is None else total <= profile.max_budget,
            "potential_difference": format(baseline - total, ".2f"),
            "difference_basis": "most_expensive_equivalent_fulfilment_among_eligible_observations_for_covered_items",
            "achieved_savings": None, "messages": messages,
            "purchases_executed": 0}
