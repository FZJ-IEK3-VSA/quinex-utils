import re
from quinex_utils.patterns.number_words import number_words
from quinex_utils.patterns.numeric_value import numeric_value
from quinex_utils.patterns.imprecise_quantities import imprecise_value_case_insensitive
from quinex_utils.patterns.order_of_magnitude import power, order_of_magnitude, num_with_order_of_magnitude_abbr
from text_processing_utils.regex import make_named_group_unique


# Pattern to identify expressions of numeric values with order of magnitude.
value = r"(" + numeric_value + r"|" + number_words + r")"
fraction = r"(" + value + r"( ?/ ?| per | devided by )" + value + r")"
NUMERIC_VALUE_WITH_ORDER_OF_MAGNITUDE_PATTERN = r"((?P<numeric_value>" + value + r")" + order_of_magnitude + r"|" +  num_with_order_of_magnitude_abbr + r")"
NUMERIC_VALUE_WITH_ORDER_OF_MAGNITUDE_PATTERN = re.compile(make_named_group_unique(NUMERIC_VALUE_WITH_ORDER_OF_MAGNITUDE_PATTERN, group_name="thousands_seperator"))

# Pattern to identify diverse expressions of numeric values.
value_representations = [
    imprecise_value_case_insensitive,
    number_words,
    value,
    fraction,
    power,
    value + order_of_magnitude,
    value + r"( ?| ?\+ ?)" + fraction,    
]
NUMERIC_VALUE_PATTERN = r"(?P<numeric_value>" +  "|".join(value_representations) + r")"
NUMERIC_VALUE_PATTERN = make_named_group_unique(NUMERIC_VALUE_PATTERN, group_name="base")
NUMERIC_VALUE_PATTERN = make_named_group_unique(NUMERIC_VALUE_PATTERN, group_name="power")
NUMERIC_VALUE_PATTERN = re.compile(make_named_group_unique(NUMERIC_VALUE_PATTERN, group_name="thousands_seperator"))