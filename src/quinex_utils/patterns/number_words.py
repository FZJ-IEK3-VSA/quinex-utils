import re
from quinex_utils.lookups.number_words import NUMBER_WORDS_PLUS_CAPITALIZED, STANDALONE_NUMBER_WORDS_PLUS_CAPITALIZED


number_words = r"((" + "|".join(NUMBER_WORDS_PLUS_CAPITALIZED) + r")((-| and | )(" + "|".join(NUMBER_WORDS_PLUS_CAPITALIZED) + r"))*|" + "|".join(STANDALONE_NUMBER_WORDS_PLUS_CAPITALIZED) + r")"
assert re.fullmatch(number_words, "two")
assert re.fullmatch(number_words, "two-thirds")

standalone_number_words = r"(" + "|".join(STANDALONE_NUMBER_WORDS_PLUS_CAPITALIZED) + r")"
STANDALONE_NUMBER_WORD_PATTERN = re.compile(standalone_number_words)