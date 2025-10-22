import re


WORD_BOUNDARY_TOKENIZATION_PATTERN = re.compile(r"\b")

sign = r"(?:[++\-−‐‑‒–—―] ?)?"
mantissa = r"(?:\d+(?:[., ']?\d{3})*(?:[,.]?\d+)?)"
power_of_n = r"(?:(?:[eE]|(?:(?: ?[x\W])? ?\d*[\^ ]?))? ?[+\-]? ?(?:\d+[., ']?)+)?"
num_regex = sign + mantissa + power_of_n
fraction_regex = num_regex + r"(?:[\/\⁄]" + num_regex + r")*"  # allow fractions
SPLIT_DIGITS_AND_WORDS = re.compile(r"([^\W\d_]+)|(" + fraction_regex + r")")

# Splits '123 million' or '123million' into '123' and 'million'.
SPLIT_DIGIT_AND_NUMBERWORD_COMBINATIONS = re.compile(r"(?:[\s-]|(?<=\d)(?=[a-zA-Z])|(?<=[a-zA-Z])(?=\d))")
