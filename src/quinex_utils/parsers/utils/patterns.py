import re
from text_processing_utils.regex import make_named_group_unique
from quinex_utils.patterns.numeric_value import numeric_value
from quinex_utils.patterns.number_words import number_words
from quinex_utils.patterns.imprecise_quantities import imprecise_value_lower_case
from quinex_utils.lookups.number_words import NUMBER_WORDS, ORDER_OF_MAGNITUDE_WORDS, NUMBER_WORDS_PLUS_CAPITALIZED, ORDER_OF_MAGNITUDE_WORDS_PLUS_CAPITALIZED, STANDALONE_NUMBER_WORDS, STANDALONE_NUMBER_WORDS_PLUS_CAPITALIZED
from quinex_utils.lookups.quantity_modifiers import PREFIXED_QUANTITY_MODIFIERS, SUFFIXED_QUANTITY_MODIFIERS, PREFIXED_QMOD_MATH_SYMBOLS
from quinex_utils.lookups.physical_constants import PHYSICAL_CONSTANTS, PHYSICAL_CONSTANTS_LOWERED
from quinex_utils.lookups.imprecise_quantities import IMPRECISE_QUANTITIES, IMPRECISE_QUANTITIES_W_OPT_ARTICLE


###########################################
#             Unit patterns.              #
###########################################

split_at_parenthesis = r'(?<=[\]\)\}])|(?=[\[\(\{])' # warning: also used in QUANTITY_TOKENIZATION_PATTERN_2 
years = r'_?\{?\d{4}\}?'
split_between_exponents_and_units = r'(?<![\d\-])(?=\-?\d)'
UNIT_TOKENIZATION_PATTERN = re.compile(r'([\s\/\*\^]|' + years + r'|' + split_between_exponents_and_units + r'|' + split_at_parenthesis + r')(?![^()]*\))')
assert [s for s in UNIT_TOKENIZATION_PATTERN.split('$(kWh)-1') if s != ''] == ['$', '(kWh)', '-1']
assert [s for s in UNIT_TOKENIZATION_PATTERN.split('cents kWh-1') if s != ''] == ['cents', ' ', 'kWh', '-1']

IS_COMPOUND_ALPHA_UNIT = re.compile(r'^[a-zA-Z]{3,}([ \-][a-zA-Z]{3,})+$')
assert IS_COMPOUND_ALPHA_UNIT.fullmatch('kilometer') == None
assert IS_COMPOUND_ALPHA_UNIT.fullmatch('kWh') == None
assert IS_COMPOUND_ALPHA_UNIT.fullmatch('kilometer-per-hour') != None
assert IS_COMPOUND_ALPHA_UNIT.fullmatch('kWh per hour') != None
assert IS_COMPOUND_ALPHA_UNIT.fullmatch('meter^2 per hour') == None
assert IS_COMPOUND_ALPHA_UNIT.fullmatch('kWh-1 per day') == None

REMOVE_WHITESPACE_PATTERN = re.compile(r'\s+')
DIMENSION_VECTOR_PATTERN = re.compile(r"(?:A)(?P<amount_of_substance>-?\d*)(?:E)(?P<electric_current>-?\d*)(?:L)(?P<length>-?\d*)(?:I)(?P<luminous_intensity>-?\d*)(?:M)(?P<mass>-?\d*)(?:H)(?P<temperature>-?\d*)(?:T)(?P<time>-?\d*)(?:D)(?P<dimensionless>-?\d*)")
CURRENCY_YEAR_PATTERN = re.compile(r'_?{?(\d{4})}?')


###########################################
#          Uncertainty patterns.          #
###########################################
units_blacklist = ["and", "or", "to", "-", ",", ":", ";", "CI", " in"]
units_blacklist = [re.escape(unit) for unit in units_blacklist]
units_blacklist_regex = "|".join(units_blacklist)

unit_symbol = r"(?<=[\d\s\/])(?!" + units_blacklist_regex + r" )[^\d\s\/\^]{1,5}(?=[\d\s\/\^\-\)\]]|$)" # Only matches if preceded by digit, whitespace, or slash.
unit_symbol_w_exponent = unit_symbol + r"(?:(?:\^?\-?| \-?)[1-3])?"
unit_separator = r"(?:(?: ?\/ ?| per |\s)?"
unit_label = r"(?<=[\d\s\/])(?!" + units_blacklist_regex + r" )[^\d\s\/\^]{5,15}(?=[\d\s\/\^]|$)" 
unit_symbols = unit_separator + r")" + unit_symbol_w_exponent + unit_separator + unit_symbol_w_exponent + r"){0,10}"
compound_unit = unit_separator + r")" + r"(?:" + unit_label + r"|" + unit_symbol_w_exponent + r")" + unit_separator + r"(?:" + unit_label + r"|" + unit_symbol_w_exponent + r")" + r"){0,5}"

prefixed_units = r"(?:pH|USD|US dollar|dollar|\$|EUR|euro|€|GBP|pound|£|JPY|yen|¥|CNY|Chinese yuan|AUD|CAD|CHF)"
quantity = r"((?P<prefixed_unit>" + prefixed_units + r" ?)?(?P<numeric_value>" +  numeric_value + r")\s?(?P<suffixed_unit>" + compound_unit + r")?(?<![±\/\-\:\;\(]))"
quantity_w_opt_closing_parentheses = r"((?P<prefixed_unit>" + prefixed_units + r" ?)?(?P<numeric_value>" +  numeric_value + r")[\]\)\}]?\s?(?P<suffixed_unit>" + compound_unit + r")?(?<![±\/\-\:\;\(]))"
plus_minus = r"([±∓]|\+\/\-|\-\/\+)"

unc_num_divider = r"(, |,? ?[\(\[])"
tolerance = unc_num_divider + r"? ?(?P<uncertainty_type> ?" + plus_minus + " ?)" +  r"(?P<uncertainty>" + numeric_value + r")"
tolerance_w_units = r"(?P<uncertainty_type> ?[\(\[]?" + plus_minus + " ?)" +  r"(?P<uncertainty>" + quantity_w_opt_closing_parentheses + r")" 
TOLERANCE_W_UNITS_PATTERN = re.compile(make_named_group_unique(tolerance_w_units, group_name="thousands_seperator"))
tolerance_w_units = unc_num_divider + r"? ?" + tolerance_w_units

NUMERIC_VALUE_WITH_TOLERANCE_PATTERN  = r"(?P<numeric_value>" + numeric_value + r")" + tolerance
NUMERIC_VALUE_WITH_TOLERANCE_PATTERN  = re.compile(make_named_group_unique(NUMERIC_VALUE_WITH_TOLERANCE_PATTERN, group_name="thousands_seperator"))

standard_deviation_a = r",? ?\(?((SD|standard deviation)( |[,;:] ?))" + plus_minus + r"? ?" + r"(?P<uncertainty_a>" + numeric_value + r")" + r"\)?"
standard_deviation_a_w_units = r",? ?\(?((SD|standard deviation)( |[,;:] ?))" + plus_minus + r"? ?" + r"(?P<uncertainty_a>" + quantity + r")" + r"\)?"
standard_deviation_b = r",? ?\(?" + plus_minus + r"? ?" + r"(?P<uncertainty_b>" + numeric_value + r")" + r" ?(SD|standard deviation)" + r"\)?"
standard_deviation_b_w_units = r",? ?\(?" + plus_minus + r"? ?" + r"(?P<uncertainty_b>" + quantity + r")" + r" ?(SD|standard deviation)" + r"\)?"

STD_DEV_W_UNITS_PATTERN = r"(" + standard_deviation_a_w_units + "|" + standard_deviation_b_w_units + r")"
STD_DEV_W_UNITS_PATTERN = make_named_group_unique(STD_DEV_W_UNITS_PATTERN, group_name="prefixed_unit")
STD_DEV_W_UNITS_PATTERN = make_named_group_unique(STD_DEV_W_UNITS_PATTERN, group_name="numeric_value")
STD_DEV_W_UNITS_PATTERN = make_named_group_unique(STD_DEV_W_UNITS_PATTERN, group_name="suffixed_unit")
STD_DEV_W_UNITS_PATTERN = re.compile(make_named_group_unique(STD_DEV_W_UNITS_PATTERN, group_name="thousands_seperator"))

NUMERIC_VALUE_WITH_STD_DEV_PATTERN = r"(?P<numeric_value>" + numeric_value + r")" + r"(" + standard_deviation_a + "|" + standard_deviation_b + r")"
NUMERIC_VALUE_WITH_STD_DEV_PATTERN = re.compile(make_named_group_unique(NUMERIC_VALUE_WITH_STD_DEV_PATTERN, group_name="thousands_seperator"))

uncertainty_range = unc_num_divider + r"(?P<uncertainty_lb>" + numeric_value + r")" + r"( | ?- ?|[,;:] ?| to )"  r"(?P<uncertainty_ub>" + numeric_value + r")[\)\]]?"
uncertainty_range_standalone = unc_num_divider + uncertainty_range
uncertainty_range_w_units = r"[\(\[]?(?P<uncertainty_lb>" + quantity + r")" + r"( | ?- ?|[,;:] ?| to )"  r"(?P<uncertainty_ub>" + quantity + r")[\)\]]?"
uncertainty_range_w_units_standalone = r"((?P<comma_sep>, )|,? ?[\(\[])" + r"(?P<uncertainty_lb>" + quantity + r")" + r"( | ?- ?|(?(comma_sep)[;:] ?|[;:,] ?)| to )"  r"(?P<uncertainty_ub>" + quantity + r")[\)\]]?"
UNCERTAINTY_INTERVAL_WO_TYPE_W_UNITS_PATTERN = make_named_group_unique(uncertainty_range_w_units, group_name="prefixed_unit")
UNCERTAINTY_INTERVAL_WO_TYPE_W_UNITS_PATTERN = make_named_group_unique(UNCERTAINTY_INTERVAL_WO_TYPE_W_UNITS_PATTERN, group_name="numeric_value")
UNCERTAINTY_INTERVAL_WO_TYPE_W_UNITS_PATTERN = make_named_group_unique(UNCERTAINTY_INTERVAL_WO_TYPE_W_UNITS_PATTERN, group_name="suffixed_unit")
UNCERTAINTY_INTERVAL_WO_TYPE_W_UNITS_PATTERN = re.compile(make_named_group_unique(UNCERTAINTY_INTERVAL_WO_TYPE_W_UNITS_PATTERN, group_name="thousands_seperator"))

NUMERIC_VALUE_WITH_UNCERTAINTY_INTERVAL_WO_TYPE_PATTERN = r"(?P<numeric_value>" + numeric_value + r")" + r" " + uncertainty_range
NUMERIC_VALUE_WITH_UNCERTAINTY_INTERVAL_WO_TYPE_PATTERN = re.compile(make_named_group_unique(NUMERIC_VALUE_WITH_UNCERTAINTY_INTERVAL_WO_TYPE_PATTERN, group_name="thousands_seperator"))

uncertainty_interval_expressions = [
    "CI", "confidence intervals?", "confidence intervals? \[CI\]", "confidence intervals? \(CI\)", "confidence intervals?-CI",
    "UI", "uncertainty intervals?", "uncertainty intervals? \[UI\]", "uncertainty intervals? \(UI\)", "uncertainty intervals?-UI",
    "CrI", "credible intervals?", "credible intervals? \[CrI\]", "credible intervals? \(CrI\)", "credible intervals?-CrI",
]

uncertainty_interval = r"[\(\[]?(?P<uncertainty_type>([98765][509]% ?)?(" + "|".join(uncertainty_interval_expressions) + ")) ?([,:] ?| of | ?= ?)?" + uncertainty_range + r"[\)\]]?"
uncertainty_interval_w_units = r"[\(\[]?(?P<uncertainty_type>([98765][509]% ?)?(" + "|".join(uncertainty_interval_expressions) + ")) ?([,:] ?| of | ?= ?)?" + uncertainty_range_w_units + r"[\)\]]?"
UNCERTAINTY_INTERVAL_W_UNITS_PATTERN = make_named_group_unique(uncertainty_interval_w_units, group_name="prefixed_unit")
UNCERTAINTY_INTERVAL_W_UNITS_PATTERN = make_named_group_unique(UNCERTAINTY_INTERVAL_W_UNITS_PATTERN, group_name="numeric_value")
UNCERTAINTY_INTERVAL_W_UNITS_PATTERN = make_named_group_unique(UNCERTAINTY_INTERVAL_W_UNITS_PATTERN, group_name="suffixed_unit")
UNCERTAINTY_INTERVAL_W_UNITS_PATTERN = re.compile(make_named_group_unique(UNCERTAINTY_INTERVAL_W_UNITS_PATTERN, group_name="thousands_seperator"))
uncertainty_interval_w_units = unc_num_divider + uncertainty_interval_w_units.removeprefix(r"[\(\[]?")

NUMERIC_VALUE_WITH_UNCERTAINTY_INTERVAL_PATTERN = r"(?P<numeric_value>" + numeric_value + r")" + uncertainty_interval
NUMERIC_VALUE_WITH_UNCERTAINTY_INTERVAL_PATTERN  = re.compile(make_named_group_unique(NUMERIC_VALUE_WITH_UNCERTAINTY_INTERVAL_PATTERN, group_name="thousands_seperator"))

NUMERIC_VALUE_WITH_UNCERTAINTY_INTERVAL_W_UNITS_PATTERN = r"(?P<quantity>" + quantity + r")" + uncertainty_interval_w_units
NUMERIC_VALUE_WITH_UNCERTAINTY_INTERVAL_W_UNITS_PATTERN = make_named_group_unique(NUMERIC_VALUE_WITH_UNCERTAINTY_INTERVAL_W_UNITS_PATTERN, group_name="prefixed_unit")
NUMERIC_VALUE_WITH_UNCERTAINTY_INTERVAL_W_UNITS_PATTERN = make_named_group_unique(NUMERIC_VALUE_WITH_UNCERTAINTY_INTERVAL_W_UNITS_PATTERN, group_name="numeric_value")
NUMERIC_VALUE_WITH_UNCERTAINTY_INTERVAL_W_UNITS_PATTERN = make_named_group_unique(NUMERIC_VALUE_WITH_UNCERTAINTY_INTERVAL_W_UNITS_PATTERN, group_name="suffixed_unit")
NUMERIC_VALUE_WITH_UNCERTAINTY_INTERVAL_W_UNITS_PATTERN  = re.compile(make_named_group_unique(NUMERIC_VALUE_WITH_UNCERTAINTY_INTERVAL_W_UNITS_PATTERN, group_name="thousands_seperator"))

UNCERTAINTY_EXPRESSION_PATTERN =                  r"(?P<protected_expression>" + uncertainty_interval + r"|" + uncertainty_range_standalone + r"|" + standard_deviation_a  + r"|" + standard_deviation_b + r"|" + tolerance + r")"
UNCERTAINTY_EXPRESSION_W_UNITS_PATTERN =  r"(?P<protected_expression>" + uncertainty_interval_w_units + r"|" + uncertainty_range_w_units_standalone + r"|" + standard_deviation_a_w_units + r"|" + standard_deviation_b_w_units + r"|" + tolerance_w_units + r")"

UNCERTAINTY_EXPRESSION_PATTERN = make_named_group_unique(UNCERTAINTY_EXPRESSION_PATTERN, group_name="uncertainty_lb")
UNCERTAINTY_EXPRESSION_PATTERN = make_named_group_unique(UNCERTAINTY_EXPRESSION_PATTERN, group_name="uncertainty_ub")
UNCERTAINTY_EXPRESSION_PATTERN = make_named_group_unique(UNCERTAINTY_EXPRESSION_PATTERN, group_name="uncertainty")
UNCERTAINTY_EXPRESSION_PATTERN = make_named_group_unique(UNCERTAINTY_EXPRESSION_PATTERN, group_name="uncertainty_type")

UNCERTAINTY_EXPRESSION_W_UNITS_PATTERN = make_named_group_unique(UNCERTAINTY_EXPRESSION_W_UNITS_PATTERN, group_name="uncertainty_lb")
UNCERTAINTY_EXPRESSION_W_UNITS_PATTERN = make_named_group_unique(UNCERTAINTY_EXPRESSION_W_UNITS_PATTERN, group_name="uncertainty_ub")
UNCERTAINTY_EXPRESSION_W_UNITS_PATTERN = make_named_group_unique(UNCERTAINTY_EXPRESSION_W_UNITS_PATTERN, group_name="uncertainty")
UNCERTAINTY_EXPRESSION_W_UNITS_PATTERN = make_named_group_unique(UNCERTAINTY_EXPRESSION_W_UNITS_PATTERN, group_name="uncertainty_type")

NUMERIC_VALUE_WITH_UNCERTAINTY_EXPRESSION_PATTERN = r"(?P<numeric_value>" + numeric_value + r")" + UNCERTAINTY_EXPRESSION_PATTERN
NUMERIC_VALUE_WITH_UNCERTAINTY_EXPRESSION_W_UNITS_PATTERN = r"(?P<quantity>" + quantity + r")" + UNCERTAINTY_EXPRESSION_W_UNITS_PATTERN
NUMERIC_VALUE_WITH_UNCERTAINTY_EXPRESSION_PATTERN = make_named_group_unique(NUMERIC_VALUE_WITH_UNCERTAINTY_EXPRESSION_PATTERN, group_name="thousands_seperator")
NUMERIC_VALUE_WITH_UNCERTAINTY_EXPRESSION_PATTERN = re.compile(NUMERIC_VALUE_WITH_UNCERTAINTY_EXPRESSION_PATTERN)

NUMERIC_VALUE_WITH_UNCERTAINTY_EXPRESSION_W_UNITS_PATTERN = make_named_group_unique(NUMERIC_VALUE_WITH_UNCERTAINTY_EXPRESSION_W_UNITS_PATTERN, group_name="prefixed_unit")
NUMERIC_VALUE_WITH_UNCERTAINTY_EXPRESSION_W_UNITS_PATTERN = make_named_group_unique(NUMERIC_VALUE_WITH_UNCERTAINTY_EXPRESSION_W_UNITS_PATTERN, group_name="numeric_value")
NUMERIC_VALUE_WITH_UNCERTAINTY_EXPRESSION_W_UNITS_PATTERN = make_named_group_unique(NUMERIC_VALUE_WITH_UNCERTAINTY_EXPRESSION_W_UNITS_PATTERN, group_name="suffixed_unit")
NUMERIC_VALUE_WITH_UNCERTAINTY_EXPRESSION_W_UNITS_PATTERN = make_named_group_unique(NUMERIC_VALUE_WITH_UNCERTAINTY_EXPRESSION_W_UNITS_PATTERN, group_name="thousands_seperator")
NUMERIC_VALUE_WITH_UNCERTAINTY_EXPRESSION_W_UNITS_PATTERN = re.compile(NUMERIC_VALUE_WITH_UNCERTAINTY_EXPRESSION_W_UNITS_PATTERN)

UNCERTAINTY_EXPRESSION_PATTERN = make_named_group_unique(UNCERTAINTY_EXPRESSION_PATTERN, group_name="thousands_seperator")
UNCERTAINTY_EXPRESSION_PATTERN = re.compile(UNCERTAINTY_EXPRESSION_PATTERN)

# UNCERTAINTY_EXPRESSION_W_UNITS_PATTERN is used to assign a token the uncertainty expression role
UNCERTAINTY_EXPRESSION_W_UNITS_PATTERN = make_named_group_unique(UNCERTAINTY_EXPRESSION_W_UNITS_PATTERN, group_name="prefixed_unit")
UNCERTAINTY_EXPRESSION_W_UNITS_PATTERN = make_named_group_unique(UNCERTAINTY_EXPRESSION_W_UNITS_PATTERN, group_name="numeric_value")
UNCERTAINTY_EXPRESSION_W_UNITS_PATTERN = make_named_group_unique(UNCERTAINTY_EXPRESSION_W_UNITS_PATTERN, group_name="suffixed_unit")
UNCERTAINTY_EXPRESSION_W_UNITS_PATTERN = make_named_group_unique(UNCERTAINTY_EXPRESSION_W_UNITS_PATTERN, group_name="thousands_seperator")
UNCERTAINTY_EXPRESSION_W_UNITS_PATTERN = re.compile(UNCERTAINTY_EXPRESSION_W_UNITS_PATTERN)

# TODO: Debug list(NUMERIC_VALUE_WITH_UNCERTAINTY_EXPRESSION_PATTERN.finditer('2.30, 95% CI 1.03-5.13'))

###########################################
#            Quantity patterns.           #
###########################################

# Split at combination of prefixed and suffixed quantity modifier phrases and imprecise quantities but not if preceded or followed by an alphabetic character.
MULTIWORD_SEPARATORS = ["of the", "out of", "out of the"]
PROTECTED_QUANTITY_PHRASES = PREFIXED_QUANTITY_MODIFIERS + SUFFIXED_QUANTITY_MODIFIERS + IMPRECISE_QUANTITIES_W_OPT_ARTICLE + MULTIWORD_SEPARATORS
PROTECTED_QUANTITY_PHRASES = sorted(PROTECTED_QUANTITY_PHRASES, key=lambda x: len(x), reverse=True)
PROTECTED_QUANTITY_PHRASES = [re.escape(phrase) for phrase in PROTECTED_QUANTITY_PHRASES]

# QUANTITY_TOKENIZATION_PATTERN_1 = re.compile(r"((?<![a-zA-Z])(?P<protected_expression>" + "|".join(PROTECTED_QUANTITY_PHRASES) + "|" + number_words + r")+(?![a-zA-Z]))", re.IGNORECASE)
QUANTITY_TOKENIZATION_PATTERN_1 = re.compile(r"((?<![a-zA-Z])(?P<protected_expression>" + "|".join(PROTECTED_QUANTITY_PHRASES) + "|" + number_words + r")((?![a-zA-Z])|(?<=\-)))", re.IGNORECASE)
assert len(list(QUANTITY_TOKENIZATION_PATTERN_1.finditer('1 - 2 km '))) == 0
assert len(list(QUANTITY_TOKENIZATION_PATTERN_1.finditer('a few hundred hours'))) == 1
assert len(list(QUANTITY_TOKENIZATION_PATTERN_1.finditer('non-zero'))) == 2

# Split quantity string at whitespace, comma or semicolon with whitespace, boundaries between digits and letters,
# and at hyphens if they denote ranges (e.g., '5-10' or '5%-10%' but not 'three-dimensional'), 
# whilst respecting special currency symbols (such as '₽', '₦',  '₭', '฿', '₡', etc.) and special unit symbols (such as '%', '‰', '‱', 'µ', etc.).
special_symbols_to_consider_alpha = r"€$%‰‱°µμ₽₦₺лвč₭฿₡₮₹₼₨₫₩﷼Дин៛؋łدден£¢ƒ₴₱¥₪¢⊄￠′′"  # Add more special symbols if needed 

split_at_modifier_followed_by_special_symbol = r'(?<=' + '|'.join([re.escape(mod) for mod in PREFIXED_QMOD_MATH_SYMBOLS]) + r')(?=[' +special_symbols_to_consider_alpha + r'])'
split_at_digit_followed_by_alpha_or_special_symbol = r'(?<=\d|[\]\)\}])[,;\.]?(?=[a-zA-Z' + special_symbols_to_consider_alpha + r']|[\[\(\{])'
split_at_digit_preceded_by_alpha_or_special_symbol = r'(?<=[a-zA-Z' + special_symbols_to_consider_alpha + r']|[\]\)\}])[,;\.]?(?=\d|[\[\(\{])'
split_at_whitespace_comma_or_semicolon = r'[,;]?\s'
split_at_range_hypen_a = r'(?<!^)(?<![\^ ,;\.])\-(?![a-zA-Z])' 
split_at_range_hypen_b = r'(?<=\d)\-(?=[a-zA-Z' + special_symbols_to_consider_alpha + r'])' # e.g., US$0.031–US$0.039/kWh
split_at_ratio_colon = r'(?<!^)(?<=\d)\:(?=\d)' 
split_at_fraction_between_digit_and_alpha = r'(?<=\d)[\/] ?(?=[a-zA-Z' + special_symbols_to_consider_alpha + r'])'
split_at_fraction_between_alpha_and_digit = r'(?<=[a-zA-Z' + special_symbols_to_consider_alpha + r'])[\/] ?(?=\d)'
QUANTITY_TOKENIZATION_PATTERN_2 = re.compile(r'(' + split_at_modifier_followed_by_special_symbol + r"|" + split_at_digit_followed_by_alpha_or_special_symbol + r'|' + split_at_digit_preceded_by_alpha_or_special_symbol + r'|' + split_at_whitespace_comma_or_semicolon + r'|' + split_at_range_hypen_a + r'|' + split_at_range_hypen_b + r'|' + split_at_fraction_between_digit_and_alpha + r'|' + split_at_fraction_between_alpha_and_digit + r'|' + split_at_parenthesis + r'|' + split_at_ratio_colon + r')')

assert [s for s in QUANTITY_TOKENIZATION_PATTERN_2.split("-$100million")   if s != ''] == ['-', '$', '100', 'million']
assert [s for s in QUANTITY_TOKENIZATION_PATTERN_2.split("1:7.5")   if s != ''] == ['1', ':', '7.5']                                                                        
assert [s for s in QUANTITY_TOKENIZATION_PATTERN_2.split("-0.6 to -1.2 V") if s != ''] == ['-0.6', ' ', 'to', ' ', '-1.2', ' ', 'V']
assert [s for s in QUANTITY_TOKENIZATION_PATTERN_2.split("−0.6 to −1.2 V") if s != ''] == ['−0.6', ' ', 'to', ' ', '−1.2', ' ', 'V']
assert [s for s in QUANTITY_TOKENIZATION_PATTERN_2.split("1.32 m")   if s != ''] == ['1.32', ' ', 'm']
assert [s for s in QUANTITY_TOKENIZATION_PATTERN_2.split("1 to 2 m") if s != ''] == ['1', ' ', 'to', ' ', '2', ' ', 'm']
assert [s for s in QUANTITY_TOKENIZATION_PATTERN_2.split("1/5")      if s != ''] == ['1/5']
assert [s for s in QUANTITY_TOKENIZATION_PATTERN_2.split("$5/kWh")   if s != ''] == ['$', '5', '/', 'kWh']
assert [s for s in QUANTITY_TOKENIZATION_PATTERN_2.split("2-3")      if s != ''] == ['2', '-', '3']
assert [s for s in QUANTITY_TOKENIZATION_PATTERN_2.split("2%-3%")    if s != ''] == ['2', '%', '-', '3', '%']
assert [s for s in QUANTITY_TOKENIZATION_PATTERN_2.split("2%/3%")    if s != ''] == ['2', '%', '/', '3', '%']
assert [s for s in QUANTITY_TOKENIZATION_PATTERN_2.split("2-3%")     if s != ''] == ['2', '-', '3', '%']
assert [s for s in QUANTITY_TOKENIZATION_PATTERN_2.split("three-dimensional") if s != ''] == ['three-dimensional']
assert [s for s in QUANTITY_TOKENIZATION_PATTERN_2.split("5.2*10⁻³ m") if s != ''] == ['5.2*10⁻³', ' ', 'm']
result = [s for s in QUANTITY_TOKENIZATION_PATTERN_2.split('$1.2, $1.2, $0.51, $0.21,$ 1.2, and $0.8 kg À1') if s not in ['', ' ']]
assert result == ['$', '1.2', ', ', '$', '1.2', ', ', '$', '0.51', ', ', '$', '0.21', ',', '$', '1.2', ', ', 'and', '$', '0.8', 'kg', 'À1']

for test_str in [
    "-0.6 to -1.2 V",
    "−0.6 to −1.2 V",
    "1.32 m",
    "1 to 2 m",
    "1/5",
    "$5/kWh",
    "2-3",
    "2%-3%",
    "2%/3%",
    "2-3%",
    "three-dimensional",
    "5.2*10⁻³ m",
    "$1.2, $1.2, $0.51, $0.21,$ 1.2, and $0.8 kg À1",
]:
    result = [s for s in QUANTITY_TOKENIZATION_PATTERN_2.split(test_str) if s not in ['', ' ']]
    assert "".join(result).replace(" ","") == test_str.replace(" ","")    


IS_NON_PHYSICAL_UNIT_PATTERN = re.compile(r"^[a-zA-Z \-]{3,}$") # assumes at least 3 characters long string that only contains alphabetic characters, whitespace, and hyphens.

# Pattern for validating a quantity string by matching abstract components of a quantity.
ABSTRACT_QUANTITY_PATTERN =  re.compile(
                r"(?P<prefixed_quantity_modifier>" +      r"((_whitespace_)?(_prefixed_quantity_modifier_))+)?" # prefixed modifiers
                r"(?P<prefixed_unit>" +                   r"((_whitespace_)?(_unit_)(_year_)?))?"
                r"(?P<numeric_value>" +                   r"((_whitespace_)?(_number_)((_whitespace_)?(_math_operator_)?(_whitespace_)?(_number_))*))"
                r"(?P<uncertainty_expression_pre_unit>" + r"((_list_separator_)?(_whitespace_)?_uncertainty_expression_))?"
                r"(?P<suffixed_unit>" +                   r"((_whitespace_)?(_math_operator_)?(_whitespace_)?(_unit_)" + r"((_whitespace_)?(_year_))?" + r"((_whitespace_)?(_math_operator_)?(_whitespace_)?(_number_))?" + r"((_whitespace_)?(_math_operator_))?" + r")*)?"
                r"(?P<uncertainty_expression_post_unit>" + r"((_list_separator_)?(_whitespace_)?_uncertainty_expression_))?"
                r"(?P<suffixed_quantity_modifier>" +      r"((_whitespace_)?(_suffixed_quantity_modifier_))+(_whitespace_)?)?" # suffixed modifiers
                r"(_whitespace_)?" # trailing whitespace
            )
