import re
from quinex_utils.lookups.imprecise_quantities import IMPRECISE_QUANTITIES


# Imprecise quantitities
imprecise_value_lower_case = r"(((a|an|the) )?(" + "|".join(IMPRECISE_QUANTITIES) + r"))" 
IMPRECISE_VALUE_PATTERN = re.compile(imprecise_value_lower_case, re.IGNORECASE) 

# Note that although we ignore case here, we add capitalized versions of the imprecise quantities 
# to the regex to avoid having to use re.IGNORECASE in the rest of the code.
imprecise_value_case_insensitive = r"(((a|an|the) )?(" + "|".join(IMPRECISE_QUANTITIES + [impq.capitalize() for impq in IMPRECISE_QUANTITIES]) + r"))" 


