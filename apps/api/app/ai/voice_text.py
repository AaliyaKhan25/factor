"""Text helpers for voice commands: Devanagari to Latin, number words to digits, fuzzy item matching.

Speech to text can return Hindi script, Hinglish, or English, and spoken numbers often arrive as words.
Commands are matched on the cleaned-up Latin text so they work whichever form arrives.
"""
import re
import unicodedata
from difflib import SequenceMatcher

# ---------------------------------------------------------------- Devanagari -> Latin (rough, for matching only)
_CONS = {
    "क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "n", "च": "ch", "छ": "chh", "ज": "j", "झ": "jh", "ञ": "n",
    "ट": "t", "ठ": "th", "ड": "d", "ढ": "dh", "ण": "n", "त": "t", "थ": "th", "द": "d", "ध": "dh", "न": "n",
    "प": "p", "फ": "f", "ब": "b", "भ": "bh", "म": "m", "य": "y", "र": "r", "ल": "l", "व": "v", "श": "sh",
    "ष": "sh", "स": "s", "ह": "h", "ळ": "l",
}
_VOWELS = {
    "अ": "a", "आ": "a", "इ": "i", "ई": "i", "उ": "u", "ऊ": "u", "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au", "ऑ": "o", "ऋ": "ri",
}
_MATRAS = {"ा": "a", "ि": "i", "ी": "i", "ु": "u", "ू": "u", "े": "e", "ै": "ai", "ो": "o", "ौ": "au", "ॉ": "o", "ृ": "ri"}
_NUKTA = {"ज": "z", "फ": "f", "ड": "d", "ढ": "dh", "क": "q", "ख": "kh", "ग": "g"}
_DIGITS = {c: str(i) for i, c in enumerate("०१२३४५६७८९")}


def has_devanagari(text: str) -> bool:
    return any("\u0900" <= ch <= "\u097f" for ch in text)


def to_latin(text: str) -> str:
    """Rough phonetic Latin spelling. Text with no Devanagari is returned unchanged."""
    if not has_devanagari(text):
        return text
    text = unicodedata.normalize("NFC", text)
    out: list[str] = []
    i = 0
    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if ch in _CONS:
            base = _CONS[ch]
            skip = 0
            if nxt == "़":
                base = _NUKTA.get(ch, base)
                skip = 1
            after = text[i + 1 + skip] if i + 1 + skip < len(text) else ""
            if after in _MATRAS:
                out.append(base + _MATRAS[after])
                i += 2 + skip
                continue
            if after == "्":
                out.append(base)
                i += 2 + skip
                continue
            # inherent "a": dropped at the end of a word and before a nasal mark
            end_of_word = not ("\u0900" <= after <= "\u097f") or after in ("ं", "ँ", "ः")
            out.append(base if end_of_word else base + "a")
            i += 1 + skip
            continue
        if ch in _VOWELS:
            out.append(_VOWELS[ch])
        elif ch in ("ं", "ँ"):
            out.append("n")
        elif ch == "ः":
            out.append("h")
        elif ch in _DIGITS:
            out.append(_DIGITS[ch])
        elif ch == "।":
            out.append(".")
        elif ch in ("़", "्") or ch in _MATRAS:
            pass
        else:
            out.append(ch)
        i += 1
    return "".join(out)


# ---------------------------------------------------------------- number words
_UNITS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19,
    # Hindi. "do" (two) is left out on purpose: it is also the English word "do" ("how many do I have").
    "ek": 1, "teen": 3, "char": 4, "chaar": 4, "panch": 5, "paanch": 5, "chhe": 6, "chhah": 6, "che": 6, "saat": 7,
    "aath": 8, "nau": 9, "das": 10, "gyarah": 11, "barah": 12, "terah": 13, "chaudah": 14, "pandrah": 15,
    "solah": 16, "satrah": 17, "atharah": 18, "unnees": 19, "bees": 20, "pachees": 25, "tees": 30, "chalis": 40,
    "pachas": 50, "saath": 60, "sattar": 70, "assi": 80, "nabbe": 90,
}
_TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}
_BIG = {"hundred": 100, "sau": 100}


def word_to_int(token: str) -> int | None:
    t = token.casefold()
    if t.isdigit():
        return int(t)
    if t in _UNITS:
        return _UNITS[t]
    if t in _TENS:
        return _TENS[t]
    if t == "do":
        return 2
    return None


def _is_num_word(w: str) -> bool:
    w = w.casefold()
    return w in _UNITS or w in _TENS or w in _BIG


def numberize(text: str) -> str:
    """Replace spoken numbers with digits: 'twenty five' -> '25', 'char' -> '4'. Other text is untouched."""
    parts = re.findall(r"[A-Za-z]+|\d+|[^A-Za-z\d]+", text)
    out: list[str] = []
    i = 0
    while i < len(parts):
        if re.fullmatch(r"[A-Za-z]+", parts[i]) and _is_num_word(parts[i]):
            j, words = i, []
            while j < len(parts):
                if re.fullmatch(r"[A-Za-z]+", parts[j]) and _is_num_word(parts[j]):
                    words.append(parts[j].casefold())
                    j += 1
                elif re.fullmatch(r"[\s-]+", parts[j]) and j + 1 < len(parts) and re.fullmatch(r"[A-Za-z]+", parts[j + 1]) and _is_num_word(parts[j + 1]):
                    j += 1
                else:
                    break
            total = current = 0
            for w in words:
                if w in _BIG:
                    current = (current or 1) * _BIG[w]
                else:
                    current += _UNITS.get(w, _TENS.get(w, 0))
            out.append(str(total + current))
            i = j
        else:
            out.append(parts[i])
            i += 1
    return "".join(out)


# ---------------------------------------------------------------- matching catalog items in a sentence
def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.casefold())


def _same(a: str, b: str) -> bool:
    if a == b:
        return True
    sa, sb = a.rstrip("s"), b.rstrip("s")
    if len(sa) >= 3 and sa == sb:
        return True
    return len(a) >= 4 and len(b) >= 4 and SequenceMatcher(None, a, b).ratio() >= 0.8


def find_items(text: str, items: list) -> list:
    """Catalog items whose name words all appear in the sentence, tolerant of plurals and small spelling slips."""
    words = _tokens(text)
    hits: list[tuple[object, set[str]]] = []
    for it in items:
        name_tokens = _tokens(it.name)
        if name_tokens and all(any(_same(n, w) for w in words) for n in name_tokens):
            hits.append((it, set(name_tokens)))
    # "red rose" and "rose" both match "red rose": keep the more specific one
    keep = [it for it, toks in hits if not any(toks < other for _, other in hits)]
    return keep
