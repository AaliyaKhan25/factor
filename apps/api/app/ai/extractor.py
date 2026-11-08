"""Extract structured order details from spoken natural language or chat text.

Handles Indian English, Hindi, and Hinglish voice orders like:
- "rahul bought 80 roses , total price 1600"
- "rahul ne 80 roses khareede total 1600"
- "order for priya: 2 gulmohar sets, total price 24800"
- "customer sneha 9876543210 bought 5 scrunchies for 250"
"""
import re
from typing import Any, Dict, List, Optional

# Spoken number dictionary
WORD_NUMBERS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
    "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
    "eighty": 80, "ninety": 90, "hundred": 100, "thousand": 1000,
    # Indic words
    "ek": 1, "do": 2, "teen": 3, "char": 4, "chaar": 4, "paanch": 5,
    "chhe": 6, "saat": 7, "aath": 8, "nau": 9, "das": 10,
    "sau": 100, "hazar": 1000, "hazaar": 1000, "lakh": 100000,
}


def normalize_words(text: str) -> str:
    """Replace spoken number words with digits where appropriate."""
    tokens = text.split()
    res = []
    for t in tokens:
        clean = t.lower().strip(",.:")
        if clean in WORD_NUMBERS:
            res.append(str(WORD_NUMBERS[clean]))
        else:
            res.append(t)
    return " ".join(res)


def extract_phone(text: str) -> Optional[str]:
    """Extract a 10-digit Indian phone number if spoken."""
    m = re.search(r"(?:\+?91[\-\s]?)?([6-9]\d{9})\b", text)
    if m:
        return m.group(1)
    return None


def extract_handle(text: str) -> Optional[str]:
    """Extract social handle like @rahul."""
    m = re.search(r"@([a-zA-Z0-9_.]+)", text)
    if m:
        return f"@{m.group(1)}"
    return None


def extract_price_paise(text: str) -> Optional[int]:
    """Find the total price mentioned in rupees and convert to paise."""
    # Look for patterns like "total price 1600", "total 1600", "price 1600", "for 1600", "₹1600", "1600 rs"
    patterns = [
        r"(?:total\s*(?:price|amount|cost)?|price|amount|cost)\s*(?:is|was|of|:)?\s*(?:rs\.?|inr|₹)?\s*(\d+(?:\.\d+)?)",
        r"(?:for|worth|paying|paid)\s*(?:rs\.?|inr|₹)?\s*(\d+(?:\.\d+)?)",
        r"(?:rs\.?|inr|₹)\s*(\d+(?:\.\d+)?)",
        r"(\d+(?:\.\d+)?)\s*(?:rupees|rupaye|rupe|rs\.?|inr|₹)",
        r"(?:total)\s*:?\s*(\d+(?:\.\d+)?)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try:
                val = float(m.group(1))
                return int(round(val * 100))
            except ValueError:
                continue
    return None


def extract_customer_name(text: str) -> str:
    """Extract the customer name from common conversational structures."""
    # Pattern 1: "<name> bought / purchased / ordered / took / ne liye / ne khareede"
    m = re.match(
        r"^\s*(?:customer\s+)?([a-zA-Z\u0900-\u097F]+(?:\s+[a-zA-Z\u0900-\u097F]+)?)\s+(?:bought|ordered|purchased|took|wants|booked|ne|ko)\b",
        text,
        re.IGNORECASE,
    )
    if m:
        name = m.group(1).strip()
        if name.lower() not in ("order", "customer", "please", "can"):
            return name.title()

    # Pattern 2: "order for/from <name>:"
    m2 = re.search(
        r"(?:order\s+(?:for|from)|customer)\s+([a-zA-Z\u0900-\u097F]+(?:\s+[a-zA-Z\u0900-\u097F]+)?)",
        text,
        re.IGNORECASE,
    )
    if m2:
        return m2.group(1).strip().title()

    # Pattern 3: Fallback first word if followed by a number
    m3 = re.match(r"^\s*([a-zA-Z\u0900-\u097F]+)\s+\d+", text)
    if m3:
        return m3.group(1).strip().title()

    return "Walk-in Customer"


def extract_order_items(text: str, total_price_paise: Optional[int] = None) -> List[Dict[str, Any]]:
    """Extract item name and quantity."""
    # Pattern: "<quantity> <item_name>" e.g., "80 roses", "2 gulmohar sets", "5 silk sarees"
    # Stop before words like 'total', 'price', 'for', 'at', 'rupees', 'rs', ',', etc.
    patterns = [
        r"(?:bought|ordered|purchased|took|iye|khareede|book)?\s*(\d+)\s+([a-zA-Z\u0900-\u097F\s\-]+?)(?=\s*(?:,|total|price|cost|for|at|worth|rupees|rupaye|rs|inr|₹|$))",
    ]

    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            qty_str, item_name = m.group(1), m.group(2).strip()
            # Clean unwanted filler words
            clean_name = re.sub(r"^(?:of|pieces|pcs|pack|units|nos|items)\s+", "", item_name, flags=re.IGNORECASE).strip()
            clean_name = re.sub(r"\s+(?:of|pieces|pcs|pack|units|nos|items|khareede|kharida|liye|liya|ordered|bought)$", "", clean_name, flags=re.IGNORECASE).strip()

            if clean_name and clean_name.lower() not in ("total", "price", "rupees", "rs"):
                try:
                    qty = int(qty_str)
                    unit_price = (total_price_paise // qty) if (total_price_paise and qty > 0) else 0
                    return [{
                        "name": clean_name.capitalize(),
                        "quantity": max(qty, 1),
                        "unit_price_paise": unit_price,
                        "total_paise": total_price_paise or 0,
                    }]
                except ValueError:
                    pass

    # Fallback default item if not explicitly parsed
    return [{
        "name": "Custom Order Item",
        "quantity": 1,
        "unit_price_paise": total_price_paise or 0,
        "total_paise": total_price_paise or 0,
    }]


def parse_voice_order(text: str) -> Dict[str, Any]:
    """Parse complete natural language voice command into structured order draft."""
    raw_cleaned = text.strip()
    normalized = normalize_words(raw_cleaned)

    phone = extract_phone(normalized)
    handle = extract_handle(normalized)
    customer_name = extract_customer_name(normalized)
    total_price_paise = extract_price_paise(normalized)
    items = extract_order_items(normalized, total_price_paise)

    # If item has total price and multiple items exist, ensure consistency
    calculated_total = sum(i["unit_price_paise"] * i["quantity"] for i in items)
    final_total_paise = total_price_paise if total_price_paise is not None else calculated_total

    return {
        "raw_text": raw_cleaned,
        "customer": {
            "name": customer_name,
            "phone": phone,
            "handle": handle,
        },
        "items": items,
        "total_price_paise": final_total_paise,
        "source": "voice",
        "confidence": 0.95 if customer_name and items and final_total_paise else 0.75,
    }
