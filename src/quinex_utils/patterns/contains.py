import re
from quinex_utils.lookups.number_words import NUMBER_WORDS
from quinex_utils.lookups.imprecise_quantities  import IMPRECISE_QUANTITIES


# Patterns for checking if a string contains a number.
CONTAINS_DIGIT_REGEX = re.compile(r".*\d.*")
CONTAINS_DECIMAL_NUMBER_PATTERN = re.compile(r"(.*\d+\.\d+.*)")
contains_num_pattern = r"\d|" + "|".join(NUMBER_WORDS)
contains_num_pattern_incl_imprecise_ones = contains_num_pattern + r"|" + "|".join(IMPRECISE_QUANTITIES)
CONTAINS_NUMBER_PATTERN = re.compile(contains_num_pattern, re.IGNORECASE)
CONTAINS_NUMBER_INCLUDING_IMPRECISE_ONES_PATTERN = re.compile(contains_num_pattern_incl_imprecise_ones, re.IGNORECASE)
CONTAINS_NUMBER_WORD_OR_IMPRECISE_QUANTITY_REGEX = re.compile(r"(" + "|".join(NUMBER_WORDS + IMPRECISE_QUANTITIES) + r")")
