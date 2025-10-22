import re
import unicodedata
from quinex_utils.lookups.character_mapping import UNICODE_POWERS_MAPPING
  

ADD_WHITESPACE_BETWEEN_CERTAIN_ALPHA_SPECIAL_CHARS = re.compile(r'([a-zA-Z])([%‰])')
REMOVE_TRAILING_DOT_FROM_UNITS = re.compile(r"(?<![a-zA-Z])\.$")
CORRECT_DEGREE_CELSIUS_FAHRENHEIT_PARSING_ERRORS = re.compile(r"[∘•] ?(?=[CcFf]\b)")
NORMALIZE_SUPERSCRIPTS_HELPER = re.compile(r"(?<![⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼ⁿⁱ⁽⁾])(?=[⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼ⁿⁱ⁽⁾])")

# Recover likely powers of 10 (e.g., '10-3' to '10^-3' and '10 3' to '10^3' but not '^10 3').
NORMALIZE_POWERS_OF_TEN_1 = re.compile(r"(^|[^\^0-9])(10)(?: ?(\-(?!\d{2,}))| )(?=\d)")
assert NORMALIZE_POWERS_OF_TEN_1.sub(r"\1\2^\3", "10-3") == "10^-3"
assert NORMALIZE_POWERS_OF_TEN_1.sub(r"\1\2^\3", "10 15") == "10^15"
assert NORMALIZE_POWERS_OF_TEN_1.sub(r"\1\2^\3", "10-15") == "10-15" # Rather a range than a power of ten.
assert NORMALIZE_POWERS_OF_TEN_1.sub(r"\1\2^\3", "10 -3") == "10^-3"
assert NORMALIZE_POWERS_OF_TEN_1.sub(r"\1\2^\3", "10 3") == "10^3"
assert NORMALIZE_POWERS_OF_TEN_1.sub(r"\1\2^\3", "103") == "103"
assert NORMALIZE_POWERS_OF_TEN_1.sub(r"\1\2^\3", '8.75*10 -2 $/kW-h') == '8.75*10^-2 $/kW-h'
assert NORMALIZE_POWERS_OF_TEN_1.sub(r"\1\2^\3", '8.75*10 2 $/kW-h') == '8.75*10^2 $/kW-h'
assert NORMALIZE_POWERS_OF_TEN_1.sub(r"\1\2^\3", '8.75*102 $/kW-h') == '8.75*102 $/kW-h'

# Recover likely powers of 10 with no whitespace or dash between 10 and the exponent but leading multiplication sign
NORMALIZE_POWERS_OF_TEN_2 = re.compile(r"(?<=\* )(10)(?=[1-9]\d{0,2}([\D]|$))")
assert NORMALIZE_POWERS_OF_TEN_2.sub(r"\1^", "1.0 * 107") == "1.0 * 10^7"
assert NORMALIZE_POWERS_OF_TEN_2.sub(r"\1^", "1.0 * 1070") == "1.0 * 10^70"
assert NORMALIZE_POWERS_OF_TEN_2.sub(r"\1^", "1.0 * 107000") == "1.0 * 107000"
assert NORMALIZE_POWERS_OF_TEN_2.sub(r"\1^", "1.0 * 10") == "1.0 * 10"
assert NORMALIZE_POWERS_OF_TEN_2.sub(r"\1^", "1.0 * 100") == "1.0 * 100"
assert NORMALIZE_POWERS_OF_TEN_2.sub(r"\1^", "1.0 * 1000") == "1.0 * 1000"

def normalize_unicode_string(string: str) -> str:
    """
    Normalize unicode string using NFKC while preserving the original meaning
    (e.g., '¼' to '1⁄4',  '¹/₇₉₈' to '1/798', and '10²³' to '10^23').
    """

    # Add "^" before superscript letters (e.g., '10²³' to '10^23').
    string = NORMALIZE_SUPERSCRIPTS_HELPER.sub("^", string)
    return unicodedata.normalize("NFKC", string)


def normalize_unit_span(unit_str: str, quantity_normalization_already_done: bool=False) -> str:

    # Remove trailing dot and leading dash from unit string.
    # (e.g., 'kWh.' to 'kWh' and '-hours' to 'hours').
    display_unit_str = unit_str.strip().removesuffix('.').removeprefix('-').strip()
    
    if not quantity_normalization_already_done:
        unit_str = normalize_quantity_span(display_unit_str)
    else:
        unit_str = display_unit_str

    # Normalize power signs.
    unit_str = unit_str.replace('**', '^')

    # Remove multiplication signs.    
    unit_str = re.sub(r"[\*\.∙·⋅]", " ", unit_str)
    # unit_str = re.sub(r"[∙·⋅](?! ?[CcFf]\b)", " ", unit_str) # replace '∙' etc. if not meant as degree
    unit_str = re.sub(r"(^| )[x×] ", r"\1 ", unit_str)

    # Normalize division signs.
    unit_str = re.sub(r"(^| )per ", r"\1/ ", unit_str)

    # Correct potential degree celsius or fahrenheit parsing errors
    # (e.g., '∘ C' or '•C' to '°C').    
    unit_str = CORRECT_DEGREE_CELSIUS_FAHRENHEIT_PARSING_ERRORS.sub(r"°", unit_str)

    # Add whitespace between certain alphabetic characters and
    # '%' and '‰' (e.g., 'mol%' to 'mol %').
    unit_str = ADD_WHITESPACE_BETWEEN_CERTAIN_ALPHA_SPECIAL_CHARS.sub(r'\1 \2', unit_str)    

    # Remove trailing "." if not preceded by alphabetic character
    # (e.g., '%.' to %', but not 'wt.%' or perc.)    
    # unit_str = REMOVE_TRAILING_DOT_FROM_UNITS.sub(r"", unit_str)

    # Remove trailing ":" from unit string.
    # (e.g., to only get '%' '%: 95').
    unit_str = unit_str.removesuffix(':').removesuffix(';').removesuffix(',')

    return unit_str.strip(), display_unit_str


def normalize_num_span(num_span: str) -> str:
    num_span = num_span.removeprefix("+")
    num_span = num_span.lower()
    return num_span


def normalize_quantity_span(string: str) -> str:
    """
    Normalize quantity span to be parsed by the parser.
    """

    # Correct encoding errors.
    string = string.replace("\xa0", " ").strip()

    # Normalize unicode string-
    # Note that '−' will not be normalized to '-' etc. 
    # and has to be done separately.
    string = normalize_unicode_string(string)

    # Trim whitespace.
    string = re.sub(r"\s+", " ", string).strip()

    # Normalize signs.
    string = re.sub(r"[-−‐‑‒–—―]", "-", string)
    string = string.replace("+/-", "±").replace("+-", "±")
    string = string.replace("-/+", "∓").replace("-+", "∓")

    # Normalize comparision operators.
    string = string.replace("!=", "≠")
    string = string.replace("<=>", "⇔")
    string = string.replace(">=", "≥")
    string = string.replace("<=", "≤")
    string = string.replace("<<", "≪")
    string = string.replace(">>", "≫")

    # Normalize multiplication and division symbols.
    string = re.sub(r"(?<=\d)( ?[x×∙⋅·•] ?)(?=[\d\-+])", " * ", string)
    string = string.replace("⁄", "/").replace("÷", "/")

    # Correct spelling errors, e.g., '0. 0273 US$/kWh' to '0.0273 US$/kWh'.
    # Patterns to correct are: '1. 0273', '1 .0273', '1 . 0273' or '> 0. 0 5' to '> 0.05'.    
    # string = re.sub(r"(?<=\d)( ?\.\s+)(?=\d)", ".", string)
    match = re.search(r"(\d ?\.(\s+\d)+)", string)
    if match:
         string = string.replace(match.group(0), match.group(0).replace(" ", ""))

    # Normalize different powers of 10.
    # Normalize 10**3 to 10^3.
    string = re.sub(r"(?<=\d)(\*\*)(?=[\d\-+])", "^", string)

    # Recover likely powers of 10
    # (e.g., '10-3' to '10^-3' and '10 3' to '10^3' but not '^10 3').
    string = NORMALIZE_POWERS_OF_TEN_1.sub(r"\1\2^\3", string)

    # Recover likely powers of 10 with no whitespace or dash between 10
    # and the exponent but leading multiplication sign
    string = NORMALIZE_POWERS_OF_TEN_2.sub(r"\1^", string)

    # Normalize e3 to 10^3 and e-3 to 10^-3.
    string = re.sub(r"(?<=\d)([eE])(?=[\d\-+])", "*10^", string)

    # Normalize ', and ' to ' and '.
    string = string.replace(", and ", " and ")

    # Remove garbage.
    string = string.removesuffix('respectively').removesuffix(', ')

    # If string endswith "fold" preceded by alphabetic character, 
    # add a dash before "fold" (e.g., 'twofold' to 'two-fold').
    string = re.sub(r"([a-zA-Z]+)fold\b", r"\1-fold", string)

    # TODO: To not confuse, multidimensional quantities with x10^3 etc.
    # add whitespace around x if multiple x's are present.
                            
    # Remove trailing "." if not preceded by alphabetic character
    # (e.g., '%.' to %' and '%).' to %)', but not 'wt.%' or perc.)  
    string = REMOVE_TRAILING_DOT_FROM_UNITS.sub(r"", string)

    # Remove unnecessary parentheses.
    string = string.strip()
    open_count = string.count("(")
    close_count = string.count(")")
    if open_count == 1 and close_count == 1 \
        and string.startswith("(") and string.endswith(")"):
        # If there is an opening and closing parenthesis, remove them.
            string = string[1:-1].strip()
    elif open_count == 1 and close_count == 0 \
        and string.startswith("("):
            # If there is an opening parenthesis but no closing one, remove it.
            string = string[1:].strip()
    elif open_count == 0 and close_count == 1 \
        and string.endswith(")"):
            # If there is a closing parenthesis but no opening one, remove it.
            string = string[:-1].strip()

    # Add leading whitespace to opening parentheses.
    # (e.g., '5.71(95% credible interval: 4.08-7.55)' to '5.71 (95% credible interval: 4.08-7.55)')
    string = re.sub(r"(?<=\S)(\()", r" (", string)

    # Add leading whitespace to dash that is followed by a space.
    # (e.g., '6- 10%' to '6 - 10%')
    string = re.sub(r"(?<=\S)(-)(?=\s)", r" -", string)

    # Add ommited zero before decimal point.
    # (e.g., '$.27/kWh' to '$0.27/kWh', but not '$.27.21/kWh' to '$0.27.21/kWh')
    # That is, add a zero before decimal point if it is not preceded by a digit 
    # and is followed by digits that are not divided by a dot.
    string = re.sub(r"(?<!\d)(\.\d+)(?![\d\.])", r"0\1", string)    
    
    # Trim whitespace.
    string = string.strip()

    return string


def rectify_quantity_annotation(quantity_span):
    """Rectify common mistakes of quantity span taggers."""
    
    # Remove known prefixes which do not belong to the quantity.
    KNOWN_PREFIXES = ["with a", "with an", "from", "of"]
    for prefix in KNOWN_PREFIXES:
        if quantity_span.startswith(prefix + " "):
            quantity_span = quantity_span.removeprefix(
                prefix
            )
            break        

    # Remove punctuation marks and more from end of quantity span.
    KNOWN_SUFFIXES = [".", ":", ",", ";", "?", "!", " of"]
    for suffix in KNOWN_SUFFIXES:
        if quantity_span.endswith(suffix):
            quantity_span = quantity_span.removesuffix(
                suffix
            )
            break        

    return quantity_span