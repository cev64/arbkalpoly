RISK_TERMS = ("regulation only", "postpon", "cancel", "minimum", "starting", "withdraw", "dead heat")

def validate_rules(kalshi_rules: str, polymarket_rules: str) -> tuple[bool, str]:
    left = kalshi_rules.lower()
    right = polymarket_rules.lower()
    for term in RISK_TERMS:
        if (term in left) != (term in right):
            return False, f"Rule wording differs for '{term}'."
    return True, "No obvious settlement-rule mismatch detected."
