    

import re
import locale
from typing import Union
from fractions import Fraction
import numpy as np
import warnings
try:
    import numexpr as ne
except ImportError:
    ne = None
from decimal import *
from collections import defaultdict
from quinex_utils.lookups.number_words import ALL_NUMBER_WORDS_MAPPING, ORDER_OF_MAGNITUDE_WORDS_MAPPING, AMBIGOUS_FRACTION_WORDS, NUMBER_WORDS_THAT_CAN_BE_CONFUSED_WITH_UNITS
from quinex_utils.functions.normalize import normalize_quantity_span, normalize_num_span
from quinex_utils.patterns.numeric_value import INT_OR_FLOAT_PATTERN
from quinex_utils.patterns.number import NUMERIC_VALUE_WITH_ORDER_OF_MAGNITUDE_PATTERN
from quinex_utils.patterns.order_of_magnitude import POWER_PATTERN
from quinex_utils.patterns.split import SPLIT_DIGIT_AND_NUMBERWORD_COMBINATIONS



# Type aliases
Offset = tuple[int, int]
Annotations = Union[dict[str, list[Offset]], defaultdict[list[Offset]]]
Facts = dict[str, list[dict]]
Labels = dict[str, dict[str, list[str]]]
UnitConvData = dict[str, list[dict[str, str]]]
UnitFreqs = dict[str, Union[list[str], list[list[str, int]]]]


def num_word_to_num(num_word_candidate: str, only_consider_order_of_magnitude_words=False, only_consider_small_number_words=False) -> Union[float, int]:
    """
    Convert a number word like "five", "fith", "million", etc.

    Note that a billion has two distinct definitions,
    10^9 (short scale) and 10^12 (long scale), of which
    the former one is mostly used in English languages.
    Hence, the short scale is assumed here.

    Note that "hundreds", "millions", etc. will be interpreted as 100, 1000000,
    etc., respectively, and have to be marked as imprecise in post-processing.
    """
        
    if not only_consider_order_of_magnitude_words:
        # Check if number is a small number word (below hundred).
        number = ALL_NUMBER_WORDS_MAPPING.get(num_word_candidate)
        if number != None:
            return number # Success!
        elif num_word_candidate != "tens" and num_word_candidate.endswith("s"):
            # We exclude tens as it is imprecise meaning multiple tens.
            # Similarly, for higher magnitudes like "hundreds", "thousands", etc.
            # given in ORDER_OF_MAGNITUDE_WORDS_MAPPING we do not consider the plural form.
            number = ALL_NUMBER_WORDS_MAPPING.get(num_word_candidate.removesuffix("s"))
            if number != None:
                return number # Success!

    if not only_consider_small_number_words:
        # Check if number is an order of magnitude word.
        power_of_ten = ORDER_OF_MAGNITUDE_WORDS_MAPPING.get(num_word_candidate)
        if power_of_ten != None:
            return 10 ** power_of_ten # Success!

    return None  # Fail silently
    

def cast_str_as_int(num_str: str, considered_thousands_separators: list=["'", ",", "."]) -> int:
    """Cast string as integer."""
    # We do not simply use locale.atoi(num_str) since it would transform '0,378' to 378 without error.    
    try:
        num = int(num_str) # 1000000
    except:
        # Maybe the quantity is formatted with thousands separators.
        no_thousands_seperator_and_decimal_separator = sum(sep in num_str for sep in considered_thousands_separators) == 1
        if no_thousands_seperator_and_decimal_separator \
            and re.match(r"^[1-9]{1,3}(?:[',\.]\d{3})*$", num_str) \
                and (not "." in num_str or num_str.count(".") > 1):                                
                # The string contains only one type of thousands separator and matches
                # the pattern of three digits after each thousands separator.
                # [1-9] is used in the REGEX to not transform '0,378' to '0378' to 378.            
                # As dots are typically used as decimal separators in English, we consider 
                # them only as thousands separators if the string contains multiple dots.
                
                # Remove thousands separator
                num = int(num_str.replace(".", "").replace(",", "").replace("'", ""))
        else:
            raise ValueError("Could not cast string as integer.")            
                          
    return num


def cast_str_as_float(num_str: str) -> float:
    """Cast string as float."""    
    try:
        num = float(num_str)
    except:
        # Maybe number is formatted in German style with comma as decimal separator
        # or has thousands separators.
        match = INT_OR_FLOAT_PATTERN.fullmatch(num_str)
        if match != None:
            # If the string matches the pattern of an integer or float, we can
            # safely cast it to a float when removing the thousands separators
            # and ensuring English style with a dot as decimal separator.            
            
            # Remove thousands separator.
            th_sep = match.group("thousands_seperator")
            if th_sep != None:                
                num_str = num_str.replace(th_sep, "")
            
            # Cast to float using dot as decimal separator.
            num = float(num_str.replace(",", "."))
                 
        else:
            raise ValueError("Could not cast string as float.")

    return num

def cast_str_as_fraction_sum(num_str: str) -> float:
    """
    Cast string as sum of fractions (e.g., '9 3/4' to 9.75 or '9 -3/4' to 8.25).
    """
    if "/" in num_str and re.fullmatch(r"[0-9\/\-\+ ]+", num_str):            
        # Replace "//" with "/" and delete whitespace around "/"
        fract_string = re.sub(r"(?<=\d)(\s*/{1,2}\s*)(?=\d)", "/", num_str)
        fract_string = re.sub(r"(?<=\d)(\s+/\s+)(?=\d)", "/", num_str)

        # For seperation of values at whitespace convert
        # '-2-1/4' to '-2 -1/4' and '-2 + 1/4' to '-2 +1/4', etc.
        fract_string = re.sub(r"(?<=\d)(\s*-\s*)(?=\d)", " -", fract_string)
        fract_string = re.sub(r"(?<=\d)(\s*\+\s*)(?=\d)", " +", fract_string)
        
        return float(sum(Fraction(num) for num in fract_string.split()))
    else:
        raise ValueError("String cannot be interpreted as sum of fractions.")

def cast_str_as_number_words(num_str: str) -> Union[float, int]:
    """Cast string as special number words not coverd
    by below method like ordinals or plurals
    (e.g., 'fifth' and 'fives').

    Note that "hundreds", "millions", etc. will be interpreted as 100, 1000000,
    etc., respectively, and have to be marked as imprecise in post-processing.
    """
    parsed_num = num_word_to_num(num_str)
    if parsed_num is None:
        raise ValueError
    else:
        return parsed_num
    
def parse_value_and_order_of_magnitude_separately(value_span):

    value_match = NUMERIC_VALUE_WITH_ORDER_OF_MAGNITUDE_PATTERN.fullmatch(value_span)
    
    if value_match is None:
        raise ValueError(f"Seems like there is no order of magnitude expression in '{value_span}'.")                                    

    # Consider value and order of magnitude separately.
    value_match = value_match.groupdict()
    
    # Get order of magnitude. 
    order_of_magnitude = None               
    if value_match["order_of_magnitude_x"] != None:
        order_of_magnitude_str = value_match["order_of_magnitude_x"].strip().removeprefix("x").removeprefix("*").lstrip()
        if order_of_magnitude_str.startswith("10^"):
            order_of_magnitude_str = order_of_magnitude_str.removeprefix("10^")
            add_power_of_ten_flag = True
        else:
            add_power_of_ten_flag = False                    
    elif value_match["order_of_magnitude_e"] != None:
        order_of_magnitude_str = value_match["order_of_magnitude_e"].lower().strip().removeprefix("e").lstrip()
        add_power_of_ten_flag = True
    elif value_match["order_of_magnitude_a"] != None:
        order_of_magnitude_str = value_match["order_of_magnitude_a"].lower().strip()
        add_power_of_ten_flag = False
    elif value_match["order_of_magnitude_k"] != None:
        value_match["numeric_value"] = value_match["numeric_value_k"] # Different num value pattern as only simple numeric values are allowed here.
        order_of_magnitude_str = value_match["order_of_magnitude_k"].lower().strip()
        if order_of_magnitude_str == "k":
            order_of_magnitude = 3
            add_power_of_ten_flag = True
        elif order_of_magnitude_str == "m":
            order_of_magnitude = 6
            add_power_of_ten_flag = True
        elif order_of_magnitude_str == "b":
            order_of_magnitude = 9
            add_power_of_ten_flag = True
        else:
            raise ValueError(f"Unknown order of magnitude abbreviation '{order_of_magnitude_str}' in '{value_span}'.")
    else:
        ValueError("Regex must be ill-defined.")

    # Get value without suffixed order of magnitude.
    value = str2num(value_match["numeric_value"], normalize_chars=False)
    
    if order_of_magnitude is None:
        order_of_magnitude = str2num(order_of_magnitude_str, normalize_chars=False, skip_cast_as_num_and_order_of_magnitude=True)

    if add_power_of_ten_flag and order_of_magnitude is not None:
        order_of_magnitude = 10 ** order_of_magnitude

    return value, order_of_magnitude

def cast_str_as_num_with_order_of_magnitude(value_span: str) -> Union[float, int, None]:
    """
    Cast string as numeric value with order of magnitude (e.g., "3.5 million", "3.5e6", "3.5x10^6", etc.).
    """
            
    value, order_of_magnitude = parse_value_and_order_of_magnitude_separately(value_span)

    # Get value with suffixed order of magnitude. Because simply 
    # calculating the value as `value = value * order_of_magnitude`
    # can result in numerical errors, we use the following approach.
    product = float(Decimal(str(value)) * Decimal(str(order_of_magnitude)))

    return product

def cast_str_as_math_expr(num_str: str) -> float:
    """Cast string as mathematical expression."""

    if not any(char.isdigit() for char in num_str):        
        raise ValueError("String does not contain any digits, hence mathematical expression cannot be solved.")

    # First, change for example '7 10^2' to '7*10^2'
    math_string = re.sub(r"(?<=\d)(\s+)(?=10\^\d)", "*", num_str)
    math_string = math_string.replace("^", "**").replace("x", "*").replace("×", "*")

    with warnings.catch_warnings():
        # Surpress warnings like "SyntaxWarning: 'int' object is not callable;
        # perhaps you missed a comma?" for strings like "3 (number)", which
        # should just return None but not a warning.
        warnings.simplefilter("ignore", SyntaxWarning)
        if ne == None:
            raise ImportError("numexpr is not installed, cannot evaluate mathematical expression. Set allow_evaluating_str_as_python_expr=False when calling str2num or install numexpr.")        
        np_array = ne.evaluate(math_string)
        
        if isinstance(np_array, np.ndarray) and np_array.ndim == 0 and type(np_array.item()) != bool:
            # If the result is a 0-dimensional array, return the float
            # value of the array, if it is not a boolean value. We exclude
            # boolean values because otherwise expression like "a is b" or 
            # "this is not a" would return True or False and be considered
            # as a valid number.
            return float(np_array.item())
        else:
            raise ValueError

def cast_str_as_digits_and_number_words(num_str: str, normalize_chars: bool) -> Union[float, int]:
    """
    Cast string as a mix of digits and number words (e.g., five thousand or 1.2 million).

    Assumption: third, fourth, fifth, etc. are interpreted as ordinals and not as fractions 
                unless they are preceded by a number word smaller than twenty 
                (e.g., "one third" is 1/3 and "twenty third" is 23th).
    """

    if not any(char.isalpha() for char in num_str):
        # If the string does not contain any alphabetic characters, it is not a number word.
        raise ValueError("String does not contain any alphabetic characters, hence it cannot be a number word.")
    
    num_str = re.sub(r"(^|\s)(a|an)\s", " 1 ", num_str).strip()
    num_str = num_str.replace(" plus ", " and ").replace(", ", " and ")
    additive =num_str.split(" and ")

    is_number_word_candidate = lambda word: not any(char.isdigit() for char in word)
    
    total_sum = 0
    for num_str in additive:            
        digit_word_tokens = SPLIT_DIGIT_AND_NUMBERWORD_COMBINATIONS.split(num_str)        
        if len(digit_word_tokens) > 0 and digit_word_tokens[-1] in NUMBER_WORDS_THAT_CAN_BE_CONFUSED_WITH_UNITS and any(not is_number_word_candidate(t) for t in digit_word_tokens[:-1]):
            raise ValueError(
                f"""
                String is likely not a number, because it ends on a word that can refer to both a number and a unit (e.g., 'second') and is
                preceded by numbers expressed in digits, which hints at it being used as a unit. String: '{num_str}'
                """)

        num = 0
        for num_token_str in digit_word_tokens:
            
            num_token_value = None
            
            if is_number_word_candidate(num_token_str):
                # Treat number token as number word.
                num_token_value = num_word_to_num(num_token_str, only_consider_order_of_magnitude_words=True)
                if num_token_value is not None:
                    # Number is order of magnitude word (e.g., million, billion, etc.)
                    if num == 0:
                        num = num_token_value 
                    else:
                        # Magnitude words are multiplied with the previous number.
                        num *= num_token_value 
                else:
                    # Number is a number word smaller one hundred (e.g., one, fifty, third, etc.) or a fraction (e.g., third, millionth, etc.)
                    num_token_value = num_word_to_num(num_token_str, only_consider_small_number_words=True)
                    if num_token_value is not None:                                                
                        if num_token_str in AMBIGOUS_FRACTION_WORDS and abs(num) < 20 and num != 0:
                            # Heuristic: If the number word is an ambiguous fraction word and the previous number
                            # smaller than absolute 20, treat it as a fraction (e.g., "one third" is 1/3 and "twenty third" is 23th).
                            if num_token_value > 1: 
                                num /= num_token_value
                            else:
                                # Is already given as fraction.
                                num *= num_token_value
                        else:
                            num += num_token_value

            else:
                # Treat number token as number expressed with digits.
                num_token_value = str2num(num_token_str, consider_num_words=False, normalize_chars=normalize_chars)
                if num_token_value is not None:
                    num += num_token_value
            
            if num_token_value is None:
                raise ValueError(f"Could not parse number token '{num_token_str}' in string '{num_str}'.")

        total_sum += num

    return total_sum


def cast_str_as_power(clean_string: str) -> Union[float, int]:
    """Cast string as power of ten (e.g., '10^3' or '10**3' to 1000)."""
    match = POWER_PATTERN.fullmatch(clean_string.replace("**", "^"))
    if match is None:
        raise ValueError(f"String '{clean_string}' does not match power pattern.")
    else:
        base = str2num(match.group("base"), consider_num_words=False, normalize_chars=False)
        power = str2num(match.group("power"), consider_num_words=False, normalize_chars=False)
        if base == None or power == None:
            raise ValueError(f"Could not parse base '{match.group('base')}' or power '{match.group('power')}' in string '{clean_string}'.")
        else:
            # Success!
            return base ** power


def str2num(
        string: str,
        consider_num_words: bool=True,
        normalize_chars: bool=True,
        skip_cast_as_num_and_order_of_magnitude=False,        
        allow_evaluating_str_as_python_expr=False,
        lang: str="en"
    ) -> Union[float, int]:
    """
    Converts e.g. "12345.0" to float and 12345 to int.
    Locale.atoi and .atof are used in order to cope with
    language specific writing of numbers, e.g., commas as
    thousands delimiters for US English. In order to change
    language add:
        locale.setlocale(locale.LC_ALL, "en_US.UTF-8")

    Limitations:
        Roman numerals (e.g., 'XIII') are not supported.
        Multidim. values (e.g., '10x50x100') are not supported.

    Note setting `allow_evaluating_str_as_python_expr` to True can be dangerous,
    as it will evaluate the given string as Python code.

    A note on the order:
    The methods for casting strings as fractions, mathematical
    expression and mixture of digits and num words are slower
    than for integers, floats and number words. Additionally,
    the respective kinds of number strings occur probably much
    less frequent. Therefore, they are placed last.

    Note that "hundreds", "millions", etc. will be interpreted as 100, 1000000,
    etc., respectively, and have to be marked as imprecise in post-processing.
    """

    if string == "":
        return None
    
    # Setting localization could also be done once
    # importing this module, however, when using Spacy
    # in combination with benepar, it will change the
    # localization setting. Thus, to be certain about
    # the localization setting, it is defined here.
    if lang == "en":
        locale.setlocale(locale.LC_ALL, "en_US.UTF-8")        
    else:
        raise NotImplementedError(f"Localization for language '{lang}' is not implemented.")

    # Convert ordinals like '30th' to '30'
    string = re.sub(r"(?<=\d)(st|nd|rd|th)$", "", string)

    # Normalize.
    clean_string = normalize_quantity_span(string) if normalize_chars else string   
    clean_string = normalize_num_span(clean_string)

    if clean_string in ["an", "a"]:
        # Special case for 'an' and 'a', 
        # which are considered 1 here.
        return 1
    elif len(clean_string) == 1 and not clean_string.isdigit():
        # A single-character non-digit string is not a number.
        return None

    try:
        number = cast_str_as_int(clean_string)
    except:
        pass
    else:
        return number
    
    # '- 10' to '-10', '- 1.5' to '1.5' etc.
    clean_string = re.sub(r"(?<=^[-+])(\s+)(?=\d([.,]?\d)*$)", "", clean_string)

    try:
        number = cast_str_as_float(clean_string)
    except:
        pass
    else:
        return number

    if consider_num_words:
        try:
            number = cast_str_as_number_words(clean_string)
        except:
            pass
        else:
            return number

    try:
        number = cast_str_as_fraction_sum(clean_string)
    except:
        pass
    else:
        return number
    
    try:
        number = cast_str_as_power(clean_string)
    except:
        pass
    else:
        return number
    
    if not skip_cast_as_num_and_order_of_magnitude:
        try:
            number = cast_str_as_num_with_order_of_magnitude(clean_string)
        except:
            pass
        else:
            return number

    if consider_num_words:
        try:
            number = cast_str_as_digits_and_number_words(clean_string, normalize_chars)
        except:
            pass
        else:
            return number
        
    if allow_evaluating_str_as_python_expr:
        try:
            number = cast_str_as_math_expr(clean_string)
        except:
            return None  # Fail silently
        else:
            return number