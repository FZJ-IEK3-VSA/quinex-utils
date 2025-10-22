import re


# Regex patterns.
integer_part = r"\d+(?:(?<!^0)(?P<thousands_seperator>[\.\,' ])\d{3}(?:(?P=thousands_seperator)\d{3})*)*"
decimal_seperator = r"(?:(?:(?<![\.\,]\d{3})[\,\.]|(?<=\.\d{3})\,|(?<=\,\d{3})\.))"
fractional_part = r"\d+"
numeric_value = r"(?:[-+]? ?" + integer_part + r"(?:" + decimal_seperator + fractional_part + r")?" + r")"

# Pre-compiled regex for matching integer or float values.
INT_OR_FLOAT_PATTERN = re.compile(numeric_value)

# Tests.
assert INT_OR_FLOAT_PATTERN.fullmatch('123')
assert INT_OR_FLOAT_PATTERN.fullmatch('12.3')
assert INT_OR_FLOAT_PATTERN.fullmatch('12,3')
assert INT_OR_FLOAT_PATTERN.fullmatch('1,22,33') == None
assert INT_OR_FLOAT_PATTERN.fullmatch('1.22.33') == None
assert INT_OR_FLOAT_PATTERN.fullmatch('1,331.4')
assert INT_OR_FLOAT_PATTERN.fullmatch('1.234.567,890')
assert INT_OR_FLOAT_PATTERN.fullmatch('0.234.567,890') == None
assert INT_OR_FLOAT_PATTERN.fullmatch('10.234.567,890')