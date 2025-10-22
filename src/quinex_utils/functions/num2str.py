    

import itertools
from typing import Union
from fractions import Fraction
import math
from decimal import *
from collections import defaultdict


# Type aliases
Offset = tuple[int, int]
Annotations = Union[dict[str, list[Offset]], defaultdict[list[Offset]]]
Facts = dict[str, list[dict]]
Labels = dict[str, dict[str, list[str]]]
UnitConvData = dict[str, list[dict[str, str]]]
UnitFreqs = dict[str, Union[list[str], list[list[str, int]]]]


def get_fraction_str(number, fraction_line="/", thousands_sep=""):
    """Convert a numeric value into fraction string representation.
        For example, given 0.24 the string '6/25' is returned.

    :param number: input number
    :type number: float or int
    :param fraction_line: fraction line, defaults to "/"
    :type fraction_line: str, optional
    :param thousands_sep: thousands sperator, defaults to ""
    :type thousands_sep: str, optional
    :return: string representation of fraction
    :rtype: str
    """
    fraction = Fraction(number).limit_denominator(max_denominator=1000)
    numerator_str = f"{fraction.numerator:,}".replace(",", thousands_sep)
    denominator_str = f"{fraction.denominator:,}".replace(",", thousands_sep)
    fraction_str = numerator_str + fraction_line + denominator_str

    return fraction_str


def num2str(
    num,
    base="×10^",
    exp=0,
    spell_magn=False,
    thousands_sep="",
    prec=2,
    pad_exp=0,
    show_plus=False,
    fraction=False,
    fraction_sign="/",
    fraction_exp=False,
):
    # Some options validity checks
    # ...

    # Adapt precision, e.g., to not yield '0x10^+1' for '1' given the exponent 1.
    prec = prec + exp

    # Get string representation of the mantissa
    mantissa = num * 10 ** (-exp)

    if prec < 0:
        # round mantissa
        mantissa = round(mantissa, prec)
        prec = 0  # set precision for decimals to 0

    if fraction:
        mantissa_str = get_fraction_str(mantissa, fraction_sign, thousands_sep)
    else:
        mantissa_str = f"{mantissa:,.{prec}f}".replace(",", thousands_sep)

    # Get string representation of the order of magnitude
    if exp == 0:
        magn_str = ""  # 123×10^-0 etc. is not common
    else:
        if spell_magn and (exp > 0) and (exp % 3 == 0):            
            magn_word = number_words_lookup["magnitude_words"][(exp // 3) - 1]
            magn_str = " " + magn_word
        else:
            sign = ("+" if show_plus else "") if exp > 0 else "-"
            if fraction_exp:
                exp_str = get_fraction_str(abs(exp), fraction_sign, thousands_sep)
            else:
                exp_str = f"{abs(exp):0>{pad_exp}}"

            magn_str = base + sign + exp_str

    # Combine all
    num_str = mantissa_str + magn_str

    return num_str


def get_number_spellings(num: str, numerator: str, denominator: str):
    """Spell out a number using MediaWiki's ConvertNumeric module
        (https://en.wikipedia.org/wiki/Module:ConvertNumeric)

    :param num: number (None if no whole number before a fraction)
    :type num: str or None
    :param numerator: numerator of fraction (None if no fraction)
    :type numerator: str or None
    :param denominator: denominator of fraction (None if no fraction)
    :type denominator: str or None
    :return: unique English spellings of the given number
    :rtype: list
    """

    # Relavant option per argument of spell_number() in ConvertNumeric module
    capitalize = [False]
    use_and = [True, False]
    hyphenate = [True, False]
    ordinal = [True, False]
    plural = [True, False]
    links = [None]
    negative_word = [None]
    round = [None]  # [None, "up", "down"]
    zero = [None]  # [None, "nil", "null"]
    use_one = [True, False]

    # Explainational comments taken from source
    spelling_options = [
        [num],  # input number (nil if no whole number before a fraction)
        [numerator],  # numerator of input fraction (nil if no fraction)
        [denominator],  # denominator of input fraction (nil if no fraction)
        capitalize,  # whether to capitalize the result (e.g. 'One' instead of 'one') (boolean)
        use_and,  # whether to use the word 'and' between tens/ones place and higher places (boolean)
        hyphenate,  # whether to hyphenate all words in the result, useful as an adjective (boolean)
        ordinal,  # whether to produce an ordinal (e.g. 'first' instead of 'one') (boolean)
        plural,  # whether to pluralize the resulting number (boolean)
        links,  # nil: do not add any links; 'on': link "billion" and larger to Orders of magnitude article; any other text: list of numbers to link (e.g. "billion,quadrillion")
        negative_word,  # word to use for negative sign (typically 'negative' or 'minus'; nil to use default)
        round,  # nil or '': no rounding; 'on': round to nearest two-word number; 'up'/'down': round up/down to two-word number
        zero,  # word to use for value '0' (nil to use default)
        use_one,  # false: 2+1/2 → "two and a half"; true: "two and one-half" (boolean)
    ]
    permutation = list(itertools.product(*spelling_options))
    # Load MediaWiki modules written in Lua
    CONVERT_NUMERIC = lua.require(
        "./src/wikimeasurements/mediawiki_modules/mediawiki-extensions-Scribunto/includes/engines/LuaCommon/lualib/ConvertNumeric"
    )
    spellings = [CONVERT_NUMERIC[0].spell_number(*variant) for variant in permutation]
    unique_spellings = list(set(spellings))

    return unique_spellings


def MAPE(y_true: float, y_pred: float) -> float:
    """Calculate the Mean Absolute Percentage Error (MAPE)
    for a series of length 1. This implementation is
    similar to the implementation in scikit-learn.
    Epsilon is used in order to not devide by zero."""
    return abs(y_pred - y_true) / max(abs(y_true), np.finfo(np.float64).eps)


def get_digit_notations(number: str, threshold=0.03):
    # TODO: Check https://en.wikipedia.org/w/index.php?title=Orders_of_magnitude_(numbers)&action=edit
    #       Is 1000<sup>−10</sup> and 1.24{{e|−68}} parsed correctly?

    n = float(number)

    # Get base notation options
    # I expect "×" to be normalized to "x", do not expect dot
    ten_notations = [
        ["x", " x ", " ", ""],
        ["10"],  # base is always ten
        ["^", ""],
    ]
    e_notations = ["e", "E"]
    base_options = ["".join(b) for b in itertools.product(*ten_notations)] + e_notations

    # Get exponent options
    magnitude = 0 if n == 0 else math.floor(math.log10(abs(n)))
    exp_range = 2
    min_exp = 3 * math.floor((magnitude - exp_range) / 3)
    max_exp = 3 * math.ceil((magnitude + exp_range) / 3)
    exp_options = list(range(min_exp, max_exp + 1))

    spell_magn_options = [True, False]

    # Thousands seperator options
    # I do not expect thin space (" ") or underscore ("_")
    sep_options = ["", ",", " ", "'"]

    # Precision options
    n_dec = Decimal(number).as_tuple()
    decimal_places = -n_dec.exponent
    integer_places = len(n_dec.digits) - decimal_places
    all_prec_options = list(range(-integer_places, decimal_places + 1))
    all_prec_options.reverse()
    if n == 0:
        valid_prec_options = all_prec_options
    else:
        valid_prec_options = []
        for prec in all_prec_options:
            deviation = MAPE(n, round(n, prec))
            if deviation > threshold:
                break
            else:
                valid_prec_options.append(prec)

    # max_prec = decimal_places
    # # Leave the first three places untouched to limit deviation (1000 / 1009 > 0.99)
    # min_prec = min(0, -integer_places + 3)

    # Precision shall not be higher than precision of input number
    # prec_options = list(range(min_prec, max_prec + 1))

    pad_exp_options = [0, 1]

    # Sign options
    show_plus_options = [True, False]

    scientific_notation_options = [
        base_options,
        exp_options,
        spell_magn_options,
        sep_options,
        valid_prec_options,
        pad_exp_options,
        show_plus_options,
    ]

    permutation = list(itertools.product(*scientific_notation_options))
    notations = [num2str(n, *variant) for variant in permutation]

    return list(set(notations))