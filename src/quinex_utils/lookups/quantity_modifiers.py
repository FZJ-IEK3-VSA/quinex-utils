
# All symbols that quantity modifiers are normalized to:
ALL_NORMALIZED_QMOD_SYMBOLS = ["", "=", "!=", "±", "<", ">",  "<=", ">=", ">>", "<<", "~", "~<", "~>=", "<~", ">~", ">~=", "<~=", "<>", "><", "<>=", "∝", "mean", "median"]

# Symbols that are not considered as quantity modifiers, but as part of the quantity span itself:
MATH_SYMBOLS_CONSIDERED_AS_PART_OF_QUANTITY_SPAN = ["+", "-", "−"] 

# A mapping of quantity modifiers to their normalized forms.
# This mapping is used to create the PREFIXED_QUANTITY_MODIFIERS list and 
# SUFFIXED_QUANTITY_MODIFIERS list for identifying quantity modifiers and
# the QUANTITY_MODIFIER_MAPPING dict to normalize identified quantity modifiers.
# Set the mapping values to None if the modifier should not be used in the QUANTITY_MODIFIER_MAPPING.
# For suffixed modifiers, a version with parentheses is created automatically.
QMODS = {
    "statistical_modifiers_prefixed": {
        "average": "mean",
        "average of": "mean",
        "average over": "mean",
        "average value of": "mean",
        "averaging": "mean",
        "on average": "mean",
        "median": "median",
        "median over": "median",
        "median value of": "median",
        "a median of": "median",
        "mean": "mean",
        "mean over": "mean",
        "mean value of": "mean",
    },
    "statistical_modifiers_suffixed": {
        "on average,": "mean",
        "on average": "mean",        
        "average": "mean",
        "median": "median",
        "mean": "mean",
    },
    "words_prefixed": {
        # Already normalized.
        "=": "=",
        "!=": "!=",
        "±": "±",
        "<": "<",
        ">": ">",
        "<=": "<=",
        ">=": ">=",
        ">>": ">>",
        "<<": "<<",
        "~": "~",
        "~<": "~<",
        "~>=": "~>=",
        "<~": "<~",
        ">~": ">~",
        ">~=": ">~=",
        "<~=": "<~=",
        "<>": "<>",
        "><": "><",
        "<>=": "<>=",
        "∝": "∝",
        # Negations.
        "not": "!=",  
        "not equal": "!=",
        "not equals": "!=",
        "not equal to": "!=",
        "minus": "-",
        "negative": "-",
        "∓": "±",
        "∼": "~",
        "≥": ">=",
        "≤": "<=",
        "≃": "~",
        "≪": "<<",
        "≫": ">>",
        "much greater than": ">>",
        "much less than": "<<",
        "≠": "!=",
        "≈": "~",
        "¬": "!=",
        "<or=": "<=",
        ">or=": ">=",
        "approximately": "~",
        "approx.": "~",
        "approx": "~",
        "around": "~",
        "about": "~",
        "some": "~",
        "close to": "~",
        "circa": "~",
        "ca.": "~",
        "ca": "~",
        "almost": "~<",
        "of around": "~",
        "higher than": ">",
        "up to": "<=",
        "min.": ">=",
        "min": ">=",
        "minimum": ">=",
        "max.": "<=",
        "max": "<=",
        "maximum": "<=",
        "below": "<",
        "well below": "<",
        "just below": "<",
        "as low as": ">=",
        "as high as": "<=",
        "above": ">",
        "just above": ">",
        "well above": ">>",
        "over": ">",
        "just over": ">",
        "well over": ">>",
        "near the": "~",
        "near": "~",
        "nearly": "~",
        "as much as": "<=",
        "at least": ">=",
        "at most": "<=",
        "less than": "<",
        "more than": ">",
        "roughly": "~",
        "between": "",
        "lower limit of": ">=",
        "upper limit of": "<=",
        "order of": "~",
        "not more than": "<=",
        "not less than": ">=",
        "beyond": ">",        
        "less than": "<",
        "greater than": ">",
        "smaller than": "<",
        "equal to": "=",
        "equals": "=",
        "could drop to": ">=",
        "at around": "~",
        "or below": "<",
        "exceed": ">",
        "not exceed": "<=",
        "in the order of": "~",
        "possibly be made as high as": "<=",
        "at about": "~",
        "uppermost": "<=",
        "⩽": "<=",
        "a minimum of": ">=",
        "minimum": ">=",
        "about ±": "",
        "≳": ">~=",
        "become as low as": ">=", 
        "initially around": "~",
        "after about": "~",
        "less than ∼": "<~",
        "upto": "<=",
        "of the order of": "~",
        "on the order of": "~",
        "from approximately": ">~",
        "varied widely from": ">",
        "values as high as ~": "<~=",
        "slightly above the critical value of": "~>=",
        "up to around": ">~=",
        "still above": ">",
        "lower than": "<",
        "up to at least": "<>=",
        "significantly higher than": ">>",
        "below around": "<~",
        "exceeded": ">",
        "over more than": ">",
        "approximate": "~",
        "up to approximately": "<~=",
        "from ∼": ">~",
        "over the": ">",
        "stabilized at a value of": "=", 
        "reached a maximum of": "<=",
        "a maximum of": "<=",
        "a minimum of": ">=",
        "above ∼": ">~",
        "below ∼": "<~",
        "far more than": ">>",
        "way more than": ">>",
        "slightly less": "~<",
        "over <": "><",        
        "as low as": ">=",
        "non-": "!=",
        "proportional to": "∝",        
        # From modifers list
        'inbetween': None,
        'appro.': "~",        
        'was obtained as': None,
        'estimated': None,
        'up to exceed': None,
        'is identified to be': None,
        'within <': None,
        'evaluated to be': None,
        'range of': None,
        'ranging from': None,
        'until': None,
        'top': None,
        'within the top': None,
        'before': None,
        'past': None,
        'between ∼': None,
        'range': None,
        'after': None,
        'ranged between': None,
        'approximately every': None,
        'low as': None,
        'increases from': None,
        'decreased from the initial': None,
        'decreased from': None,
        'toward': None,
        'approached': None,
        'ranges': None,
        'calculated to': None,
        'increased from': None,
        'lower': None,
        'ranged from': None,
        'found to be': None,
        'was as high as': None,
        'between the ages of': None,
        'starts on': None,
        'from': None,
        'average maximum': None,
        '‡': None,
        'better than': None,
        'the range between': None,
        'every': None,
        'in the range of': None,
        'comes to': None,
        'within': None,
        'an initial value between': None,
        'last': None,
        'between about': None,
        'upper': None,
        'increases from ∼': None,
        'down to': None,
        'declined from': None,
        'reach': None,
        'mean and 2sd of': None,
        'decreased below': None,
        'range from': None,
        'decrease to': None,
        'worse than': None,
        'in the amount of': None,
        'fallen from': None,
        'were revealed to be': None,        
    },    
    "words_suffixed": {
        "or lower": "<=",
        "or higher": ">=",
        "or less": "<=",
        "or more": ">=",        
        "at least": ">=",
        "at minimum": ">=",
        "at maximum": "<=",
        'at most' : None, # TODO: why no mapping?
        "at best": "<=",  # Assumption: higher is better
        "at worst": ">=",  # Assumption: higher is better                
        "seems to be the ultimate lower limit": ">=",
        "seems to be the ultimate upper limit": "<=",
        "approximately": "~",
        "approx.": "~",
        "approx": "~",
        "range": "~",
        "higher": None,
        "nominally" : None,        
        "larger" : None,
    },
}

# Add " a" to prefixed quantity modifiers.
prefixed_mods_w_a = {}
omit_adding_a = ["non-", "negative"]
for k, v in QMODS["words_prefixed"].items():
    if not k.endswith(" a") and k not in omit_adding_a:
        prefixed_mods_w_a[k + " a"] = v
QMODS["words_prefixed"].update(prefixed_mods_w_a)

add_parentheses_to_dict_values = lambda d: {"(" + k + ")": v for k, v in d.items() if not k.endswith(",") and not k.endswith(")")}

# Allow suffixed modifiers to be in parentheses.
suffixed_qmods_in_parentheses = add_parentheses_to_dict_values(QMODS["words_suffixed"])
QMODS["words_suffixed"].update(suffixed_qmods_in_parentheses)

# Allow suffixed statistical modifiers to be in parentheses.
suffixed_statistical_qmods_in_parentheses = add_parentheses_to_dict_values(QMODS["statistical_modifiers_suffixed"])
QMODS["statistical_modifiers_suffixed"].update(suffixed_statistical_qmods_in_parentheses)

# Create lists used to identify quantity modifiers in text.
PREFIXED_QUANTITY_MODIFIERS = list(QMODS["words_prefixed"] | QMODS["statistical_modifiers_prefixed"])
SUFFIXED_QUANTITY_MODIFIERS = list(QMODS["words_suffixed"] | QMODS["statistical_modifiers_suffixed"])

# Create list of math symbols that are prefixed modifiers or considered as part of the quantity span.
PREFIXED_QMOD_MATH_SYMBOLS = [m for m in PREFIXED_QUANTITY_MODIFIERS if len(m) == 1] + MATH_SYMBOLS_CONSIDERED_AS_PART_OF_QUANTITY_SPAN

# Create dict used to map identified quantity modifiers to their normalized forms.
remove_none_values_from_dict = lambda d: {k: v for k, v in d.items() if v != None}
QUANTITY_MODIFIER_MAPPING = {}
QUANTITY_MODIFIER_MAPPING['statistical_modifiers'] = remove_none_values_from_dict(QMODS['statistical_modifiers_prefixed']) | remove_none_values_from_dict(QMODS['statistical_modifiers_suffixed'])
QUANTITY_MODIFIER_MAPPING['words_prefixed'] = remove_none_values_from_dict(QMODS['words_prefixed'])
QUANTITY_MODIFIER_MAPPING['words_suffixed'] = remove_none_values_from_dict(QMODS['words_suffixed'])

# Sort from longest to shortest to ensure that longer phrases are matched first in regex patterns.
PREFIXED_QUANTITY_MODIFIERS = sorted(PREFIXED_QUANTITY_MODIFIERS, key=lambda x: len(x), reverse=True)
SUFFIXED_QUANTITY_MODIFIERS = sorted(SUFFIXED_QUANTITY_MODIFIERS, key=lambda x: len(x), reverse=True)

