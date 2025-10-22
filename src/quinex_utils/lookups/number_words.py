description = """
NUMBER_WORDS_MAPPING is a mapping of number words to their corresponding integer values. The number words include cardinal numbers, ordinal numbers, and common fractions.

ORDER_OF_MAGNITUDE_WORDS_MAPPING is a mapping of order of magnitude words to the corresponding power of ten in the short scale (that is n for 10^n). The short scale is used as it is used in most English variants today (https://en.wikipedia.org/wiki/Names_of_large_numbers)
"""

ORDER_OF_MAGNITUDE_WORDS_MAPPING = {
    "hundred": 2,
	'thousand': 3,
	'million': 6,
	'billion': 9,
	'trillion': 12,
	'quadrillion': 15,
	'quintillion': 18,
	'sextillion': 21,
	'septillion': 24,
	'octillion': 27,
	'nonillion': 30,
	'decillion': 11*3,
	'undecillion': 12*3,
	'duodecillion': 13*3,
	'tredecillion': 14*3,
	'quattuordecillion': 15*3,
	'quindecillion': 16*3,
	'sexdecillion': 17*3,
	'septendecillion': 18*3,
	'octodecillion': 19*3,
	'novemdecillion': 20*3,
	'vigintillion': 21*3,
	'unvigintillion': 22*3,
	'duovigintillion': 23*3,
	'tresvigintillion': 24*3,
	'quattuorvigintillion': 25*3,
	'quinquavigintillion': 26*3,
	'sesvigintillion': 27*3,
	'septemvigintillion': 28*3,
	'octovigintillion': 29*3,
	'novemvigintillion': 30*3,
	'trigintillion': 31*3,
	'untrigintillion': 32*3,
	'duotrigintillion': 33*3,
	'trestrigintillion': 34*3,
	'quattuortrigintillion': 35*3,
	'quinquatrigintillion': 36*3,
	'sestrigintillion': 37*3,
	'septentrigintillion': 38*3,
	'octotrigintillion': 39*3,
	'noventrigintillion': 40*3,
	'quadragintillion': 41*3,
	'quinquagintillion': 51*3,
	'sexagintillion': 61*3,
	'septuagintillion': 71*3,
	'octogintillion': 81*3,
	'nonagintillion': 91*3,
	'centillion': 101*3,
	'uncentillion': 102*3,
	'duocentillion': 103*3,
	'trescentillion': 104*3,
	'decicentillion': 111*3,
	'undecicentillion': 112*3,
	'viginticentillion': 121*3,
	'unviginticentillion': 122*3,
	'trigintacentillion': 131*3,
	'quadragintacentillion': 141*3,
	'quinquagintacentillion': 151*3,
	'sexagintacentillion': 161*3,
	'septuagintacentillion': 171*3,
	'octogintacentillion': 181*3,
	'nonagintacentillion': 191*3,
	'ducentillion': 201*3,
	'trecentillion': 301*3,
	'quadringentillion': 401*3,
	'quingentillion': 501*3,
	'sescentillion': 601*3,
	'septingentillion': 701*3,
	'octingentillion': 801*3,
	'nongentillion': 901*3,
	'millinillion': 1001*3,
}

NUMBER_WORDS_MAPPING = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,    
    "first": 1,
    "second": 2,
    "third": 3,    
    "fourth": 4,
    "fifth": 5,
    "sixth": 6,
    "seventh": 7,
    "eighth": 8,
    "ninth": 9, 
    "ones": 1,
    "twos": 2,
    "threes": 3,
    "fours": 4,
    "fives": 5,
    "sixes": 6,
    "sevens": 7,
    "eights": 8,
    "nines": 9,
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
    "twentieth": 20,
    "thirtieth": 30,
    "fortieth": 40,
    "fiftieth": 50,
    "sixtieth": 60,
    "seventieth": 70,
    "eightieth": 80,
    "ninetieth": 90,
    "twenties": 20,
    "thirties": 30,
    "forties": 40,
    "fifties": 50,
    "sixties": 60,
    "seventies": 70,
    "eighties": 80,
    "nineties": 90,
    "twentieth": 20,
    "tenth": 10,
    "eleventh": 11,
    "twelfth": 12,
    "thirteenth": 13,
    "fourteenth": 14,
    "fifteenth": 15,
    "sixteenth": 16,
    "seventeenth": 17,
    "eighteenth": 18,
    "nineteenth": 19,
    "tens": 10,
    "elevens": 11,
    "twelves": 12,
    "thirteens": 13,
    "fourteens": 14,
    "fifteens": 15,
    "sixteens": 16,
    "seventeens": 17,
    "eighteens": 18,
    "nineteens": 19,
    "half": 0.5,
    "halves": 0.5,   
    "thirds": 1/3,
    "quarter": 0.25,    
    "dozen": 12,
    "dozens": 12,
    "gross": 144,
    "great gross": 1728,
    "small gross": 120,
    "twelfty": 120,
    "great hundred": 120,
    "long hundred": 120, 
    "long thousand": 1200,
    "hundredth": 100,
    "thousandth": 1000,
    "millionth": 1000000,
    "billionth": 1000000000,
}


NUMBER_WORDS_THAT_CAN_BE_CONFUSED_WITH_UNITS = ["second", "quarter"]

# Number words that are unlikely to be used in combinations with other number words.
STANDALONE_NUMBER_WORDS_MAPPING = {
    "a third": 1/3,  # 'a' distinguishes it from 3rd
    "a quarter": 0.25,  # 'a' distinguishes it from 4th
    "once": 1,
    "twice": 2,
    "thrice": 3,
    "single": 1,
    "double": 2,
    "triple": 3,
    "quadruple": 4,
    "quintuple": 5,
    "zeroth": 0,
    "zeros": 0,
    # TODO: check the following numbers are not confused
    # "one third": 1/3, # added 'one' to distinguish from 3rd
    # "one fourth": 0.25, # added 'one' to distinguish from 4th     
    # "fifth": 0.2,
    # "sixth": 1/6,
    # "eighth": 0.125,
    # "one ninth": 1/9,
    # "one tenth": 0.1, # added 'one' to distinguish from 10th
    # "one sixteenth": 0.0625, # added 'one' to distinguish from 16th
}

AMBIGOUS_FRACTION_WORDS = [
    "third",  # can be 1/3 or 3rd    
    "thirds",  # can be 1/3 or 3rd
    # Not really ambiguous, but added to have a consistent list of fraction words for str2num.
    "half",
    "halves",
    "quarter",
    # ... # all fraction words ending on "th" are added below.
]

# Add further standalone number words that are fractions 
# (e.g., "a fifth", "a sixth", "a eighth", "a ninth", "a tenth", "a sixteenth",
# ( and "fifths", "sixths", "eighths", "ninths", "tenths", "sixteenths")
# Also, add themm to AMBIGOUS_FRACTION_WORDS used by str2num
fractions_to_add = {}
for word, value in NUMBER_WORDS_MAPPING.items():
    if word.endswith("th"):
        AMBIGOUS_FRACTION_WORDS.append(word)
        AMBIGOUS_FRACTION_WORDS.append(word + "s")
        fractions_to_add[word + "s"] = 1/value
        STANDALONE_NUMBER_WORDS_MAPPING["a " + word] = 1/value

NUMBER_WORDS_MAPPING.update(fractions_to_add)

ALL_NUMBER_WORDS_MAPPING = NUMBER_WORDS_MAPPING | STANDALONE_NUMBER_WORDS_MAPPING

ORDER_OF_MAGNITUDE_WORDS = list(ORDER_OF_MAGNITUDE_WORDS_MAPPING.keys())
NUMBER_WORDS = list(NUMBER_WORDS_MAPPING.keys()) + ORDER_OF_MAGNITUDE_WORDS
STANDALONE_NUMBER_WORDS = list(STANDALONE_NUMBER_WORDS_MAPPING.keys())

# Sort from longest to shortest to ensure that longer phrases are matched first in regex patterns.
NUMBER_WORDS = sorted(NUMBER_WORDS, key=lambda x: len(x), reverse=True)
STANDALONE_NUMBER_WORDS = sorted(STANDALONE_NUMBER_WORDS, key=lambda x: len(x), reverse=True)
ORDER_OF_MAGNITUDE_WORDS = sorted(ORDER_OF_MAGNITUDE_WORDS, key=lambda x: len(x), reverse=True)

# Add capitalized versions.
NUMBER_WORDS_PLUS_CAPITALIZED = NUMBER_WORDS + [w.capitalize() for w in NUMBER_WORDS]
STANDALONE_NUMBER_WORDS_PLUS_CAPITALIZED = STANDALONE_NUMBER_WORDS + [w.capitalize() for w in STANDALONE_NUMBER_WORDS]
ORDER_OF_MAGNITUDE_WORDS_PLUS_CAPITALIZED = ORDER_OF_MAGNITUDE_WORDS + [w.capitalize() for w in ORDER_OF_MAGNITUDE_WORDS]

