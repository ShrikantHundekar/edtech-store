"""
Enterprise-grade 18% inclusive GST engine for EdTech Store.
Implements the exact statutory GST breakdown with zero rounding leakage.
"""


def calculate_inclusive_gst(price_inclusive_paise: int, is_interstate: bool = False) -> dict:
    """
    Computes exact 18% inclusive GST breakdown with ZERO rounding leakage.
    
    Standard Indian GST mathematical formula (Section 15 CGST Act):
      Inclusive Price = Base Taxable Amount * (1 + GST Rate)
      Base Taxable Amount = round(Inclusive Price / 1.18)
      Total GST Amount    = Inclusive Price - Base Taxable Amount
      
    Tax Split:
      Intra-State (default):
        CGST (9%) = round(Total GST / 2)
        SGST (9%) = Total GST - CGST (guarantees CGST + SGST == Total GST exactly)
        IGST      = 0
        
      Inter-State:
        IGST (18%) = Total GST
        CGST       = 0
        SGST       = 0
        
    Mathematical Invariants:
      1. base_taxable_paise + total_gst_paise == price_inclusive_paise (100% leak-proof)
      2. cgst_paise + sgst_paise + igst_paise == total_gst_paise (100% leak-proof)
      3. All paise fields are non-negative integers.
    """
    if price_inclusive_paise is None or price_inclusive_paise <= 0:
        return {
            "price_inclusive_paise": 0,
            "base_taxable_paise": 0,
            "total_gst_paise": 0,
            "cgst_paise": 0,
            "sgst_paise": 0,
            "igst_paise": 0,
            "is_interstate": is_interstate,
            "gst_rate_percent": 18.0,
            "price_inclusive_inr": 0.0,
            "base_taxable_inr": 0.0,
            "total_gst_inr": 0.0,
            "cgst_inr": 0.0,
            "sgst_inr": 0.0,
            "igst_inr": 0.0,
        }

    base_taxable_paise = round(price_inclusive_paise / 1.18)
    total_gst_paise = price_inclusive_paise - base_taxable_paise

    if is_interstate:
        igst_paise = total_gst_paise
        cgst_paise = 0
        sgst_paise = 0
    else:
        igst_paise = 0
        cgst_paise = round(total_gst_paise / 2)
        sgst_paise = total_gst_paise - cgst_paise

    return {
        "price_inclusive_paise": price_inclusive_paise,
        "base_taxable_paise": base_taxable_paise,
        "total_gst_paise": total_gst_paise,
        "cgst_paise": cgst_paise,
        "sgst_paise": sgst_paise,
        "igst_paise": igst_paise,
        "is_interstate": is_interstate,
        "gst_rate_percent": 18.0,
        "price_inclusive_inr": price_inclusive_paise / 100.0,
        "base_taxable_inr": base_taxable_paise / 100.0,
        "total_gst_inr": total_gst_paise / 100.0,
        "cgst_inr": cgst_paise / 100.0,
        "sgst_inr": sgst_paise / 100.0,
        "igst_inr": igst_paise / 100.0,
    }


def calculate_gst_breakdown(price_inclusive_paise: int) -> dict:
    """Alias for backwards compatibility with products and cart modules."""
    return calculate_inclusive_gst(price_inclusive_paise, is_interstate=False)


def verify_gst_split_integrity(max_price_paise: int = 100000, step: int = 100) -> bool:
    """
    Verifies that base_taxable_paise + total_gst_paise == price_inclusive_paise across price points
    with zero rounding leakage.
    """
    for price in range(0, max_price_paise + 1, step):
        res = calculate_inclusive_gst(price)
        if res['base_taxable_paise'] + res['total_gst_paise'] != price:
            return False
        if res['cgst_paise'] + res['sgst_paise'] != res['total_gst_paise']:
            return False
    return True

