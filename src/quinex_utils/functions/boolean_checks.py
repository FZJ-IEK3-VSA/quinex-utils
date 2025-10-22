from decimal import Decimal
from quinex_utils.patterns.contains import CONTAINS_NUMBER_PATTERN, CONTAINS_NUMBER_INCLUDING_IMPRECISE_ONES_PATTERN
from quinex_utils.patterns.imprecise_quantities import IMPRECISE_VALUE_PATTERN 
from quinex_utils.lookups.physical_constants import PHYSICAL_CONSTANTS_LOWERED 



def is_numeric(some_string, require_leading_zero=False) -> bool:
    """
    Checks if a string content is a numeric number (e.g., "3", "2.718", "1e3).
    Other representations of numbers like alphabetic numbers ("three") are not recognized.
    If require_leading_zero is True, then the string must start with a digit 
    and is not considered numeric if it starts with a decimal point.
    """
    if require_leading_zero and some_string.lstrip()[0] == ".":
        # '.8' should not be considered a number in 'Twin rear axle 49 ft 2+1.0⁄2.0 in.8 ft 4+3⁄8 in'
        return False

    try:
        float(some_string)
        return True
    except ValueError:
        return False


def contains_any_number(string: str, consider_imprecise_quantites=False) -> bool:
    """
    Quickly check if a string contains any number.
    """
    if consider_imprecise_quantites:
        return bool(CONTAINS_NUMBER_INCLUDING_IMPRECISE_ONES_PATTERN.search(string))
    else:
        return bool(CONTAINS_NUMBER_PATTERN.search(string))
    

def contains_any_physical_constant(string: str) -> bool:
    """
    Check if a string contains any physical constant.
    """
    if any(constant in string.lower() for constant in PHYSICAL_CONSTANTS_LOWERED):
        return True
    else:
        return False


def is_imprecise_quantity(string: str) -> bool:
    """
    Check if a string is an imprecise quantity.
    """
    # TODO: Not used right now. Remove if not needed.
    return bool(IMPRECISE_VALUE_PATTERN.search(string))


def is_relative_quantity(quantity_span, text):
    """
    Determine whether a quantity is absolute or relative 
    (e.g., "increased by", "twice as much as", etc.). 
    Both quantities with and without modifiers can be given.

    Args:
        quantity_span (dict): Quantity span with "start", "end, and "text" fields.
        text (str): Text from which the quantity span was extracted.
    Returns:
        is_relative (bool): True if the quantity is relative, False otherwise.
    """
    # TODO: Improve this function.

    # Per default, the quantity is assumed to be absolute.
    is_relative = False                    
    
    if quantity_span["start"] != quantity_span["end"]:
        # Quantity is likely to be relative if it is prefixed by "by".
        for prefix in ["by", "twice as much as", "half as much as", "by more than", "by less than"]: 
            if text[: quantity_span["start"]].strip().endswith(" " + prefix) or quantity_span["text"].startswith(prefix):
                is_relative = True
                break

        # Quantity is likely to be relative if it is suffixed by "above", "below", "higher than",  "lower than".
        if not is_relative:
            for suffix in ["above", "below", "higher than", "lower than"]:
                if text[quantity_span["end"]: ].strip().startswith(suffix + " ") or quantity_span["text"].endswith(prefix):
                    is_relative = True
                    break

    return is_relative


def is_small_int(value: Decimal, threshold: int = 10) -> bool:
    """
    Determine if a value is an integer below a certain threshold.
    """
    (numerator, denominator) = value.as_integer_ratio()
    if denominator == 1 and abs(numerator) < threshold:
        return True
    else:
        return False
