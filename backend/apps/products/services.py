def calculate_gst_breakdown(price_inclusive_paise: int) -> dict:
    """
    Computes exact 18% GST breakdown from an inclusive price in paise.
    All monetary figures are computed and returned in both integer paise and INR.
    
    Mathematical formula:
      Base Taxable Amount = round(P_inclusive / 1.18)
      Total 18% GST       = P_inclusive - Base Taxable Amount
      CGST (9%)           = round(Total GST / 2)
      SGST (9%)           = Total GST - CGST
    """
    if price_inclusive_paise <= 0:
        return {
            "price_inclusive_paise": 0,
            "base_taxable_paise": 0,
            "total_gst_paise": 0,
            "cgst_paise": 0,
            "sgst_paise": 0,
            "gst_rate_percent": 18.0,
            "price_inclusive_inr": 0.0,
            "base_taxable_inr": 0.0,
            "total_gst_inr": 0.0,
            "cgst_inr": 0.0,
            "sgst_inr": 0.0,
        }

    base_taxable = round(price_inclusive_paise / 1.18)
    total_gst = price_inclusive_paise - base_taxable
    cgst = round(total_gst / 2)
    sgst = total_gst - cgst

    return {
        "price_inclusive_paise": price_inclusive_paise,
        "base_taxable_paise": base_taxable,
        "total_gst_paise": total_gst,
        "cgst_paise": cgst,
        "sgst_paise": sgst,
        "gst_rate_percent": 18.0,
        "price_inclusive_inr": price_inclusive_paise / 100.0,
        "base_taxable_inr": base_taxable / 100.0,
        "total_gst_inr": total_gst / 100.0,
        "cgst_inr": cgst / 100.0,
        "sgst_inr": sgst / 100.0,
    }
