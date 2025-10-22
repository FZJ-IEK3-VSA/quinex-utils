import re
from quinex_utils.patterns.numeric_value import numeric_value
from quinex_utils.lookups.number_words import ORDER_OF_MAGNITUDE_WORDS_PLUS_CAPITALIZED
from text_processing_utils.regex import make_named_group_unique


power = r"(?P<base>" + numeric_value + r")\^(?P<power>" + numeric_value + r"( ?\/ ?" + numeric_value + r" ?\^?-?\d)*)"
POWER_PATTERN = re.compile(make_named_group_unique(power, group_name="thousands_seperator"))

order_of_magnitude_words = r"(" + "|".join(ORDER_OF_MAGNITUDE_WORDS_PLUS_CAPITALIZED) + r")((-| and | )(" + "|".join(ORDER_OF_MAGNITUDE_WORDS_PLUS_CAPITALIZED) + r"))*"
ORDER_OF_MAGNITUDE_WORD_PATTERN = re.compile(order_of_magnitude_words)

order_of_magnitude_numeric_x = r"(?P<order_of_magnitude_x>( ?[x×∙⋅·•\* ] ?)" + power + r")"
order_of_magnitude_numeric_e = r"(?P<order_of_magnitude_e> ?[eE]" + numeric_value + r")"
order_of_magnitude_alpha = r"(?P<order_of_magnitude_a> (hundred|thousand|million|billion|trillion))"
order_of_magnitude = r"(" + order_of_magnitude_numeric_x + r"|" + order_of_magnitude_numeric_e + r"|" + order_of_magnitude_alpha + r")"
num_with_order_of_magnitude_abbr = r"(?P<numeric_value_k>" + numeric_value + r")" + r"(?P<order_of_magnitude_k> ?[kKMB])"
