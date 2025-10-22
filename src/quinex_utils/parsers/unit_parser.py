import os
import json
from decimal import *
import numpy as np
from copy import deepcopy
from datetime import datetime
from collections import defaultdict
from thefuzz import process

try:
    from types import NoneType
except ImportError:
    NoneType = type(None)

try:
    from cucopy import Currency
except ImportError:
    Currency = None

from quinex_utils.parsers.utils.patterns import (
    IS_COMPOUND_ALPHA_UNIT,
    CURRENCY_YEAR_PATTERN,
    UNIT_TOKENIZATION_PATTERN,
    REMOVE_WHITESPACE_PATTERN,
    DIMENSION_VECTOR_PATTERN,
)
from quinex_utils import CONFIG
from quinex_utils.functions import str2num, normalize_unit_span, remove_exponent_from_ucum_code_of_single_unit



# TODO: Add C code wrapper.
class FastSymbolicUnitParser:
    """A fast and simple rule-based unit parser which links QUDT units to unit strings."""

    def __init__(self, load_ucum_codes: bool=False, verbose: bool=False):

        self.verbose = verbose

        # Load symbol lookup.            
        with open(os.path.join(CONFIG["static_resources_dir"], "unit_symbol_lookup.json"), 'r') as f:
            self.unit_symbol_lookup = json.load(f)

        # Load label lookup.
        with open(os.path.join(CONFIG["static_resources_dir"], "unit_label_lookup.json"), 'r') as f:
            self.unit_label_lookup = json.load(f)

        # Load priority lookup for ambiguous units.
        with open(os.path.join(CONFIG["static_resources_dir"], "ambiguous_unit_priorities_curated.json"), 'r') as f:
            unit_priorities_ = json.load(f)

        # Remove all units with None as priority as well as remaining empty dicts.
        self.unit_priorities = {}
        for unit_expr, prios in unit_priorities_.items():
            remaining_after_curation = {unit: prio for unit, prio in prios.items() if prio is not None}
            if len(remaining_after_curation) > 0:
                self.unit_priorities[unit_expr] = remaining_after_curation
        
        del unit_priorities_

        # Load unit dimension and kind lookup.
        with open(os.path.join(CONFIG["static_resources_dir"], "unit_dimensions_and_kinds.json"), 'r') as f:
            self.unit_dimensions_and_kinds = json.load(f)

        # Load ucum code lookup.
        if load_ucum_codes:
            with open(os.path.join(CONFIG["static_resources_dir"], "ucum_codes.json"), 'r') as f:
                self.ucum_code_lookup = json.load(f)
        else:
            self.ucum_code_lookup = None
        
        self.conversion_lookup = defaultdict(dict)
        for uri, info in self.unit_dimensions_and_kinds.items():
            if info['conversion_multiplier'] in self.conversion_lookup[info['dimension_vector']]:
                self.conversion_lookup[info['dimension_vector']][info['conversion_multiplier']].append(uri)            
            else:
                self.conversion_lookup[info['dimension_vector']].update({info['conversion_multiplier']: [uri]})

        self.reverse_symbol_label_lookup = defaultdict(list)
        for symbol, uris in self.unit_symbol_lookup.items():
            for uri in uris:
                self.reverse_symbol_label_lookup[uri].append(symbol)        
        for label, uris in self.unit_label_lookup.items():
            for uri in uris:
                self.reverse_symbol_label_lookup[uri].append(label)
        
        self.ERROR_LOG = defaultdict(list)
        
        if Currency == None:
            self.cc = None
        else:
            self.cc = Currency(ignore_cache=False, normalize_to="USD", aggregate_from="A")
    

    def get_exponent(self, unit_string_parts, min_i, max_i, exponent):
        """Gets the exponent of a unit string part 
        based on preceding and succeeding unit string parts.
        """
        if min_i == max_i:
            used_indices = [min_i]
        else:
            used_indices = [min_i, max_i]

        # Process preceding information.
        if min_i > 0:
            if unit_string_parts[min_i-1] ==  '/':
                exponent *= -1
                used_indices.append(min_i-1)
        
        # Process succeeding information.
        if max_i < len(unit_string_parts) - 1:
            # Note: We could have just used int(...) but maybe the exponent is a fraction.            
            exponent_candidate = str2num(unit_string_parts[max_i+1], normalize_chars=False)
            if exponent_candidate is not None:
                # Next token is a number!
                exponent *= exponent_candidate
                used_indices.append(max_i+1)
            elif unit_string_parts[max_i+1] ==  '^' and max_i < len(unit_string_parts) - 2:
                # Check for "^" "some number" pattern.
                exponent_candidate = str2num(unit_string_parts[max_i+2], normalize_chars=False)
                if exponent_candidate is not None:                                                       
                    exponent *= exponent_candidate 
                    used_indices += [max_i+1,max_i+2]
                
        return exponent, used_indices


    def qudt_unit_linking(self, unit_string_part):
        """Links a unit string part to a QUDT unit class. 
        In case of ambiguity, the unit with the highest priority is returned.
        """

        symbol_matches = self.unit_symbol_lookup.get(unit_string_part, [])
        label_matches = self.unit_label_lookup.get(unit_string_part.lower(), [])

        # As the label lookup mostly includes singular units, 
        # we also check for plural units if no match was found.
        if len(label_matches) == 0 and unit_string_part.endswith("s"):
             # Remove trailing 's' from unit string part.
             label_matches = self.unit_label_lookup.get(unit_string_part.lower()[:-1], [])
        
        matches = set(symbol_matches + label_matches)

        if len(matches) == 0:   
            # No match.             
            qudt_unit_class = None
        elif len(matches) == 1:
            # One match.
            qudt_unit_class = matches.pop()
        else:
            # Get priorities for unit.
            priorities = self.unit_priorities.get(unit_string_part, {})
            if len(priorities) == 0:
                priorities = self.unit_priorities.get(unit_string_part.lower(), {})
                if len(priorities) == 0 and unit_string_part.endswith("s"):
                    # Remove trailing 's' from unit string part.
                    priorities = self.unit_priorities.get(unit_string_part[:-1], {})
                    if len(priorities) == 0:
                        priorities = self.unit_priorities.get(unit_string_part.lower()[:-1], {})

            prios = []
            for match in matches:
                prio = priorities.get(match)
                if prio is not None:
                    prios.append(prio)

            if len(prios) > 0:                
                # Get unit with lowest value for prio.
                min_prio = min(prios)
                if prios.count(min_prio) != 1:
                    qudt_unit_class = None
                    if self.verbose:
                        print('Warning: Multiple units with same priority found for unit "{}".'.format(unit_string_part))                    
                else:
                    # Get index of unit with lowest prio.
                    min_prio_index = prios.index(min_prio)
                    # Get unit with lowest prio.
                    qudt_unit_class = list(matches)[min_prio_index]
            else:
                # Maybe a lowered unit label was matched that is actually a unit symbol and should be treated case-sensitive.
                if unit_string_part.startswith('M'):
                    # If unit starts with a capital 'M', remove units containing 'Milli' from matches.
                    matches = [match for match in matches if "Milli" not in match]
                elif unit_string_part.startswith('m') and unit_string_part[1].isupper():                    
                    # If unit starts with a small 'm' and is not followed by a lowercase letter,
                    # and there is only one QUDT unit with 'Milli' in its URI, take that one.
                    matches = [match for match in matches if "Milli" in match]

                if len(matches) == 1:
                    qudt_unit_class = matches.pop()
                else: # TODO: raised error for "/hr"
                    qudt_unit_class = None
                    if self.verbose:
                        print('Warning: Number of priorities does not match number of matches for unit "{}".'.format(unit_string_part))                    

        return qudt_unit_class
    

    def get_compound_unit_conversion_info(self, units, break_if_conversion_not_allowed=False):
        """
        Aggregates conversion information from compound unit parts.
        
        Assumption: 
            a)  **Following common practice in the QUDT, conversion offsets are set to None for compound units.**                    
                The reason to set the conversion offset to None for compound units is explained in the following examples:
                - 200 K * 5 °C  = 1000 K C°  = ??? K K
                - 200 km * 5 °C = 1000 km C° = ??? m K
            b) For currencies and other units without conversion multipier in compound units, the conversion
               multiplier of the compound unit is not effected (that is, default conv. multiplier is 1).
            c) For currencies and other units without defined applicable systems, 
               the applicable system of the compound unit is not effected.
        """

        if len(units) <= 1:
            raise ValueError("At least two units are required to get compound unit conversion information.")

        def dim_vector_str_to_num(dimension_vector_str):      
            dimension_vector_matches = DIMENSION_VECTOR_PATTERN.match(dimension_vector_str)
            dimension_vector_dict = dimension_vector_matches.groupdict()          
            dimension_vector = np.array([int(d) for d in dimension_vector_dict.values()])

            return dimension_vector
        
        allow_conversion = True    
        superordinate_dimension_vector = np.zeros(8)
        superordinate_conversion_multiplier = Decimal(1)
        superordinate_applicable_system = set()
        for i, (_, exponent, qudt_unit_class, _) in enumerate(units):

            conversion_info = self.unit_dimensions_and_kinds.get(qudt_unit_class)
                        
            # Get superordinate applicable system.
            if len(conversion_info["applicable_system"]) == 0:
                # Convention here: If no applicable system is defined, the unit is applicable to all systems.
                # However, this can lead to wrong unit conversions. Therefore, we set allow_conversion to False.
                allow_conversion = False
                pass
            elif len(superordinate_applicable_system) == 0:
                # Init applicable systems.
                superordinate_applicable_system = set(conversion_info["applicable_system"])            
            else:
                # Get intersection of previous and current applicable systems.
                superordinate_applicable_system = superordinate_applicable_system & set(conversion_info["applicable_system"])

            # Get dimension vector.
            dimension_vector_str = conversion_info["dimension_vector"]            
            dimension_vector = dim_vector_str_to_num(dimension_vector_str)
            if sum(dimension_vector[0:7]) == 0 and dimension_vector[7] != 0:
                # Conversion of dimensionless units can lead to wrong unit conversions. 
                allow_conversion = False

            dimension_vector = dimension_vector * exponent
            superordinate_dimension_vector += dimension_vector
            
            # Get conversion multiplier.
            if conversion_info["conversion_multiplier"] is not None:
                # Treat currencies and other units without conversion multipier 
                # in compound units according to common practice in QUDT.
                conversion_multiplier = Decimal(conversion_info["conversion_multiplier"])
                superordinate_conversion_multiplier *= conversion_multiplier**Decimal(exponent)
            else:
                # Coversion of compound units involving units without conversion multiplier 
                # may lead wrong unit conversions.
                allow_conversion = False

            if break_if_conversion_not_allowed and not allow_conversion:
                # If conversion is not allowed, break the loop.
                break

        if superordinate_dimension_vector[-1] != 0 and any(v != 0 for v in superordinate_dimension_vector[:-1]):
            # If the compound quantity is not dimensionless anymore, adapt the dimension vector accordingly.
            superordinate_dimension_vector[-1] = 0

        dimension_vector_to_str = lambda sodv: f"A{int(sodv[0])}E{int(sodv[1])}L{int(sodv[2])}I{int(sodv[3])}M{int(sodv[4])}H{int(sodv[5])}T{int(sodv[6])}D{int(sodv[7])}"
        superordinate_dimension_vector_str = dimension_vector_to_str(superordinate_dimension_vector)

        return superordinate_dimension_vector, superordinate_dimension_vector_str, float(superordinate_conversion_multiplier), superordinate_applicable_system, allow_conversion


    def unit_conversion(self, value: float, from_compound_unit: str, to_compound_unit: str , from_default_year: int=None, to_default_year: int=None) -> float:
        """Converts a value from one unit to another unit. Symbol/label is ignored. Year is ignored.

        Args:
            to_unit (tuple): (symbol/label, exponent, URI, year (optional)) of the target unit.
            from_unit (tuple):  (symbol/label, exponent, URI, year (optional)) of the source unit.
            value (float): Value to convert.            

        Returns:
            converted_value (float): Converted value.
        """
        # TODO: Start with dimensional analysis?

        current_year = datetime.now().year

        if len(from_compound_unit) == 0 and len(to_compound_unit) == 0:
            # No conversion needed.
            return value, from_compound_unit
        elif len(to_compound_unit) == 0:
            # Conversion is not possible.
            return None, None
        
        from_compound_unit_ = deepcopy(from_compound_unit)
        for i, from_unit in enumerate(from_compound_unit_):
            # TODO: Implement handling of cents properly.
            # Hot fix to support conversion of compound units with "PLACEHOLDER_CENT" unit.
            if from_unit[2] == "http://qudt.org/PLACEHOLDER_CENT":                
                value = value / (100 ** from_unit[1])
                if not any("/currency/" in unit[2] or "/CCY_" in unit[2] for unit in from_compound_unit):
                    # If there is no other currency in the from_compound_unit, return conversion is not possible,
                    # because we do not yet distinguish between cents in different currencies.
                    return None, None
                else:
                    # Assume cent modifies the currency in the compound unit.
                    from_compound_unit.pop(i)


        def compund_unit_to_str(compound_unit):            
            unit_str = ""
            for unit in compound_unit:
                if len(unit_str) > 0:
                    unit_str += "·"
                unit_str += unit[0]
                if unit[3] != None:
                    unit_str += f"_{str(unit[3])}"
                if unit[1] != 1:
                    unit_str += "^" + str(unit[1])

            return unit_str
        
        if self.verbose:
            print("\nConvert units:")
            print(f"From: {round(value, 10)} {compund_unit_to_str(from_compound_unit)}")                    
        
        to_compound_unit_ = to_compound_unit.copy()
        conv_value = value
        conv_unit = []        
        for from_unit in from_compound_unit:
                        
            _, from_exponent, from_qudt_unit_class, from_year = from_unit
            
            # Check if there is a unit in to_compound_unit, that, from_unit can be converted to. 
            success = False
            for to_unit in to_compound_unit_:

                _, to_exponent, to_qudt_unit_class, to_year = to_unit

                if from_exponent != to_exponent:                
                    # Not implemented.
                    # TODO: Implement conversion for different exponents.
                    continue
                else:
                    # Check if conversion is theoretically possible.
                    from_conversion_info = self.unit_dimensions_and_kinds.get(from_qudt_unit_class)
                    to_conversion_info = self.unit_dimensions_and_kinds.get(to_qudt_unit_class)

                    if from_conversion_info["is_currency"] != to_conversion_info["is_currency"]:
                        # Conversion between currency and physical unit is not possible.
                        continue
                    elif from_conversion_info["is_currency"] and to_conversion_info["is_currency"]:
                        ##########################################################################
                        #                        Conversion of currencies                        #
                        ##########################################################################
                        if self.cc == None:
                            raise ImportError("cucopy is not installed. Currency conversion is not available.")
                        
                        currency_conversion = True
                        if None in [from_year, to_year] and None in [from_default_year, to_default_year]:
                            # Currency conversion is not possible without a year.
                            raise ValueError('Currency conversion is not possible without specifying the years. Either the given units must contain a year or default years must be provided.')
                                                
                        from_y = from_year if from_year is not None else from_default_year
                        to_y = to_year if to_year is not None else to_default_year                        
                        
                        if from_y == to_y and from_qudt_unit_class == to_qudt_unit_class:
                            # No conversion needed.
                            pass
                        elif from_y >= current_year or to_y >= current_year:
                            print(f"Conversion from {from_y} to {to_y} is not possible, because economic data in annual resolution is not available for the current year or future years.")
                            continue
                        else:                            
                            # Get ISO currency codes.                                                                   
                            from_curreny_iso_code = from_qudt_unit_class.removeprefix("http://qudt.org/vocab/currency/").removeprefix("http://qudt.org/vocab/unit/CCY_")
                            to_curreny_iso_code = to_qudt_unit_class.removeprefix("http://qudt.org/vocab/currency/").removeprefix("http://qudt.org/vocab/unit/CCY_")
                            assert len(from_curreny_iso_code) == 3 and len(to_curreny_iso_code) == 3, f"Currency ISO codes must be 3 characters long, but got '{from_curreny_iso_code}' and '{to_curreny_iso_code}'."
                                                        
                            # Adjust for inflation and exchange rate.
                            conv_value = self.cc.convert_currency(
                                value=conv_value, 
                                base_year=str(from_y), 
                                base_currency=from_curreny_iso_code, 
                                target_year=str(to_y), 
                                target_currency=to_curreny_iso_code,
                                operation_order="inflation_first"
                            )              

                        # Success, proceed.
                        success = True

                    else:
                        ##########################################################################
                        #                      Conversion of physical units                      #
                        ##########################################################################                        
                        currency_conversion = False 
                        if from_qudt_unit_class == to_qudt_unit_class:
                            # No conversion needed.
                            pass
                        elif not from_conversion_info["conversion_offset"] in [None, 0] or not to_conversion_info["conversion_offset"] in [None, 0]:
                            # Conversion offset is not zero. For this case, unit conversion is not implemented.
                            continue
                        elif from_conversion_info["conversion_multiplier"] is None or to_conversion_info["conversion_multiplier"] is None:
                            # If no conversion multiplier is defined, unit conversion is not possible.
                            continue
                        elif len(from_conversion_info["applicable_system"]) == 0 or len(to_conversion_info["applicable_system"]) == 0:
                            # If no applicable system is defined, unit conversion is not possible.
                            continue
                        else:
                            # Get dimension vectors.
                            from_dimension_vector = from_conversion_info["dimension_vector"]
                            to_dimension_vector = to_conversion_info["dimension_vector"]

                            # Get conversion multipliers.
                            from_conversion_multiplier = from_conversion_info["conversion_multiplier"]
                            to_conversion_multiplier = to_conversion_info["conversion_multiplier"]

                            # Check if conversion is theoretically possible.
                            if from_dimension_vector == to_dimension_vector:                            
                                # Conversion is theoretically possible.
                                if from_conversion_multiplier != to_conversion_multiplier:
                                    assert from_exponent == to_exponent
                                    conversion_factor = from_conversion_multiplier / to_conversion_multiplier
                                    conv_value = conv_value * conversion_factor**from_exponent                                
                            else:
                                # Conversion is not possible.
                                continue
                                
                        success = True
                
                if success:
                    break

            if success:
                # Remove to_unit from to_compound_unit_.
                conv_unit.append((to_unit[0], to_unit[1], to_unit[2], to_y if currency_conversion else to_unit[3]))
                to_compound_unit_.remove(to_unit)
            else:
                # Conversion was not successful.
                break

        if len(to_compound_unit_) == 0:
            # Conversion was successful.
            if self.verbose:
                print(f"To:   {round(conv_value, 10)} {compund_unit_to_str(conv_unit)}")
            return conv_value, conv_unit
        else:
            # Conversion was not successful.
            if self.verbose:
                print("Conversion failed.")
            return None, None


    def get_single_class_for_compound_unit(self, units: list[tuple], unit_string: str) -> str:             
        """
        Attempts to find a single QUDT unit class that is equivalent to the given individual compound unit parts
        using dimensional analysis (https://en.wikipedia.org/wiki/Dimensional_analysis).

        Args:
            units (list): List of tuples of the form (unit_string_part, exponent, qudt_unit_class, used_indices).
        
        Returns:
            qudt_unit_class (str) or None: URI of a QUDT unit class. If no matching unit is found, None is returned.
        """
        
        unit = None # Default value.

        if any(u[3] is not None for u in units):
            # Unit conversion is not implemented for currency units.
            # If a unit has a year associated with it, it is a currency unit.            
            return unit

        # If any unit is a currency we cannot convert it.
        if any(self.unit_dimensions_and_kinds[u[2]]["is_currency"] for u in units):
            # Unit conversion based on dimensional analysis and conversion factors is not implemented for currencies
            # Currently, for example, cent/kWh and EUR/kWh would be considered equivalent, but they are not.
            return unit

        sodv, dimension_vector_str, superordinate_conversion_multiplier, superordinate_applicable_system, allow_unit_conversion = self.get_compound_unit_conversion_info(units, break_if_conversion_not_allowed=True)
        if allow_unit_conversion:
            # Unit conversion is theoretically possible.            
            unit_candidates = self.conversion_lookup.get(dimension_vector_str,{}).get(superordinate_conversion_multiplier)
            
            if unit_candidates is not None:                
                # Check if both the unit candidate and target unit are applicable to the same system.
                valid_unit_candidates = []
                for unit_candidate in unit_candidates:
                    # Get intesection of applicable systems.
                    applicable_systems = superordinate_applicable_system & set(self.unit_dimensions_and_kinds[unit_candidate]["applicable_system"])
                    if len(applicable_systems) > 0:
                        # Unit conversion is possible.
                        valid_unit_candidates.append(unit_candidate)

                if len(valid_unit_candidates) == 1:
                    # Exactly one match.
                    unit = valid_unit_candidates[0]
                elif len(valid_unit_candidates) > 1:
                    # Multiple matches. Choose one based on string similarity.
                    similarity_scores = []
                    for valid_unit_candidate in valid_unit_candidates:
                        # Get lowest Levenshtein distance between unit string and surface forms.
                        surface_forms = self.reverse_symbol_label_lookup.get(valid_unit_candidate)
                        _, similarity_score = process.extractOne(unit_string.replace(" ",""), surface_forms)
                        similarity_scores.append(similarity_score)

                    # Choose unit with highest similartiy score. In case of a tie, choose the first one.
                    unit = valid_unit_candidates[np.argmax(similarity_scores)]
                                    
        return unit


    def parse(self, unit_string: str, group_exponent: int=1, quantity_normalization_already_done: bool=False) -> list[tuple]:
        """
        Parses a unit string into a list of tuples of the form (unit_string_part, exponent, qudt_unit_class, used_indices).
        The aim is not to divide the units into their smallest parts but to return as little compund unit parts as possible, 
        ideally a single QUDT class is equivalent to the given unit.

        Args:
            unit_string (str): Unit string to parse.
            group_exponent (int, optional): Exponent of the group. Defaults to 1. Used for recursive calls.
            quantity_normalization_already_done (bool, optional): If True, the standard normalization procedure for quantities is skipped to save time.

        Returns:
            units (list): List of tuples of the form (unit_string_part, exponent, qudt_unit_class, used_indices).
    
        Examples:
            >>> parse("%")    
            [('%', 1, 'http://qudt.org/vocab/unit/PERCENT', None)]
            >>> parse("TWh/a")    
            [('TWh', 1, 'http://qudt.org/vocab/unit/TeraW-HR', None), ('a', -1, 'http://qudt.org/vocab/unit/YR', None)]
            >>> parse("$2021/kWh")
            [('$', 1, 'http://qudt.org/vocab/unit/CCY_USD', 2021), ('kWh', -1, 'http://qudt.org/vocab/unit/KiloW-HR', None)]
            >>> parse("km / s")           
            [('km / s', 1, 'http://qudt.org/vocab/unit/KiloM-PER-SEC', None)]

        """

        # Assumption: Each unit of a compound unit is part of the QUDT including the unit prefix. 
        # This assumptions allows us to not deal with unit prefixes (e.g. 'k' for kilo) separately.
        # Assumption: All unit labels are lowercase.
        
        if unit_string == "" or unit_string.count('(') != unit_string.count(')'):
            # Unit string cannot be zero width and number of opening and closing brackets must be equal.
            return None
        
        # First, try direct match.        
        qudt_unit_class = self.qudt_unit_linking(unit_string)
        if qudt_unit_class is not None:
            ###########################################
            #            Got direct match.            #
            ###########################################
            # Note: Although matching on the full unit string will potentially leave more ambiguity 
            # undetected, because the more complex a compound unit, the more likely it is that there 
            # are multiple spellings and that they are not part of the QUDT, also because they are 
            # less used. However, we assume that if a direct match is possible, it is more likely
            # that the matching unit is th correct one compared to potential unknown matches, just 
            # because it is modeled in the QUDT, and therefore seems to be more common.        
            return [(unit_string, group_exponent, qudt_unit_class, None)]

        
        ###########################################
        #           Normalize unit span.          #
        ###########################################
        # Try direct match with different postprocessed forms of the unit string.
        normalized_unit_string, display_unit_str = normalize_unit_span(unit_string, quantity_normalization_already_done=quantity_normalization_already_done)
        normalized_unit_string_wo_parentheses = normalized_unit_string.removeprefix('(').removesuffix(')')
        postprocessed_forms = [normalized_unit_string, normalized_unit_string_wo_parentheses]
        if IS_COMPOUND_ALPHA_UNIT.fullmatch(normalized_unit_string_wo_parentheses):
            postprocessed_forms.append(normalized_unit_string_wo_parentheses.replace("-", " "))

        for postprocessed_form in set(postprocessed_forms):
            if postprocessed_form != unit_string:
                qudt_unit_class = self.qudt_unit_linking(postprocessed_form)
                if qudt_unit_class is not None:
                    ###########################################
                    #            Got direct match.            #
                    ###########################################
                    return [(display_unit_str, group_exponent, qudt_unit_class, None)]

        ###########################################
        #        Decompose compound unit.         #
        ###########################################
        # No match. Try to decompose compound unit.
        units = self.parse_compound_unit_str(normalized_unit_string, group_exponent=group_exponent)
                  
        if units != None:
            if len(units) == 1:
                # Adapt displayed unit string if it is a single unit too match other matching approaches.
                units[0] = (display_unit_str, units[0][1], units[0][2], units[0][3])
            if len(units) > 1:                    
                ########################################################
                #    Aggregate compund unit back to a single class.    #
                ########################################################   
                unit = self.get_single_class_for_compound_unit(units, normalized_unit_string)
                if unit is not None:
                    units = [(display_unit_str, 1, unit, None)]
            
            return units
        else:        
            # Last fallback: Remove all whitespace and check again.
            # Note that this can lead to false positives (e.g., "m s -1" -> "ms-1").
            normalized_unit_string_wo_parentheses_and_whitespace = REMOVE_WHITESPACE_PATTERN.sub('', normalized_unit_string_wo_parentheses)
            qudt_unit_class = self.qudt_unit_linking(normalized_unit_string_wo_parentheses_and_whitespace)
            if qudt_unit_class is not None:
                ###########################################
                #            Got direct match.            #
                ###########################################
                return [(display_unit_str, group_exponent, qudt_unit_class, None)]
            else:
                return None


    def parse_compound_unit_str(self, normalized_unit_string: str, group_exponent: int=1) -> list[tuple]:
        """
        Decopmpose a compound unit string into its individual parts and parse 
        each part individually whilst keeping track of the exponents.
        """

        # Splits a unit string at whitespace, '/', "*", "^", and 4-digit numbers (optionally 
        # within curly braces and preceded by an underscore), which are likely to be years,  
        # but keep strings inside parantheses intact.
        unit_string_parts = UNIT_TOKENIZATION_PATTERN.split(normalized_unit_string)
        
        # Remove empty strings from list.
        unit_string_parts = [part for part in unit_string_parts if part not in ['', ' ']]

        # Loop through the individual parts of the unit string.
        units = []
        all_used_indices = []
        for i, unit_string_part in enumerate(unit_string_parts):

            if i in all_used_indices:
                # Unit string part has already been used.
                continue
            elif unit_string_part[0] == '(' and unit_string_part[-1] == ')':             
                # Deal with nested parantheses.
                group_exponent, used_indices = self.get_exponent(unit_string_parts, i, i, group_exponent)
                unit_group = self.parse(unit_string_part[1:-1], group_exponent=group_exponent)
                if unit_group is not None:                        
                    units += unit_group                
            else:

                # Try to match unit string part to QUDT class.
                qudt_unit_class = self.qudt_unit_linking(unit_string_part)
            
                if qudt_unit_class is not None:
                    # Unit string part appears to be a unit.
                        
                    currency_year = None
                    max_i = i
                    if self.unit_dimensions_and_kinds.get(qudt_unit_class, {}).get("is_currency"):
                        # Unit is a currency. Often a year is given after the 
                        # currency (e.g., 0.03 $2021/kWh). Try to find the year.
                        if i < len(unit_string_parts) - 1:
                            currency_year_matches = CURRENCY_YEAR_PATTERN.match(unit_string_parts[i+1])
                            if currency_year_matches is not None:
                                currency_year = int(currency_year_matches.group(1))
                                max_i = i+1
                        
                    exponent, used_indices = self.get_exponent(unit_string_parts, i, max_i, group_exponent)
                    units.append((unit_string_part, exponent, qudt_unit_class, currency_year))
                else:
                    # Maybe the unit string part is a "/" or "per" and will be used 
                    # to determine the exponent of the next unit.
                    continue

            all_used_indices += used_indices

            # Early abort condition: Check if no part of the unit string has been used more than once.
            if len(set(all_used_indices)) != len(all_used_indices):
                # Unit string could not be parsed.
                return None

        # Final check: Check if all parts of the unit string have been used exactly once.
        if len(set(all_used_indices)) != len(unit_string_parts):
            # Unit string could not be parsed.
            return None
        
        return units


    def get_compound_ucum_codes(self, units) -> list[str]:
        """
        Get compound UCUM codes for a list of units.

        Assumptions:
            - If a currency unit is part of the compound unit, an empty list
              is returned to reflect common practice in QUDT.

        Limitations: 
            No use of parantheses such as in "erg/(cm2.s)".        

        Args:
            units (list[str, str]): List of units in the form of a tuple of (exponent, qudt_unit_uri).            

        Returns:
            ucum_codes (list[str]): List of compound UCUM codes.
        """

        if self.ucum_code_lookup is None:
            raise ValueError("UCUM code lookup not loaded. Initialize FastSymbolicUnitParser class with load_ucum_codes=True.")
        
        if any(qudt_unit_uri.startswith("http://qudt.org/vocab/currency/") or qudt_unit_uri.startswith("http://qudt.org/vocab/unit/CCY_") for _, qudt_unit_uri in units):
            return [] 

        ucum_code_parts = {"/": [], "-1": []}
        for i, (exponent, qudt_unit_uri) in enumerate(units):

            if exponent == 0:
                raise ValueError("Exponent of 0 not allowed.")

            ucum_codes = self.ucum_code_lookup.get(qudt_unit_uri, [])
            
            if len(ucum_codes) == 0:
                raise ValueError(f"UCUM code for {qudt_unit_uri} not found.")                    

            for ucum_code in ucum_codes:
                
                # Get UCUM code variant.
                ucum_code, included_exponent = remove_exponent_from_ucum_code_of_single_unit(ucum_code)
                exponent *= included_exponent

                if exponent != 1:
                    ucum_code_num = ucum_code + str(exponent)    
                else:
                    ucum_code_num = ucum_code

                # Get UCUM code variant.
                if i == 0 or exponent > 0:
                    ucum_code_per = ucum_code_num
                elif exponent == -1:
                    ucum_code_per = "/" + ucum_code
                else:
                    ucum_code_per = "/" + ucum_code + str(abs(exponent))                    

                # Choose UCUM code variant.
                if "/" in ucum_code:
                    # Add to "/" list       
                    ucum_code_parts["/"].append(ucum_code_per)
                elif "-" in ucum_code:
                    # Add to "-1" list
                    ucum_code_parts["-1"].append(ucum_code_num)
                else:
                    # Add to both.       
                    ucum_code_parts["/"].append(ucum_code_per)
                    ucum_code_parts["-1"].append(ucum_code_num)
        
        
        generated_ucum_codes = {"/": [], "-1": []}
        if len(ucum_code_parts["-1"]) > 0:
            generated_ucum_codes["-1"] = ".".join(ucum_code_parts["-1"])
        
        already_used_indices = []
        if len(ucum_code_parts["/"]) > 0:
            # Enclose groups of ucum code parts starting with "/" in parantheses
            # and only join parts with "." if they are not starting with "/".
            generated_ucum_codes["/"] = ""            
            for i, part in enumerate(ucum_code_parts["/"]):
                if i == 0:
                    generated_ucum_codes["/"] += part
                elif i in already_used_indices:
                    continue
                elif part[0] == "/" and len(ucum_code_parts["/"]) > i + 1 and ucum_code_parts["/"][i+1][0] == "/":
                    # Start group in parantheses.
                    generated_ucum_codes["/"] += f'/({part[1:]}.{ucum_code_parts["/"][i+1][1:]}'
                    already_used_indices.append(i+1)
                    for j in range(i+2, len(ucum_code_parts["/"])):
                        if ucum_code_parts["/"][j][0] == "/":
                            already_used_indices.append(j)
                            generated_ucum_codes["/"] += "." + ucum_code_parts["/"][j][1:]
                        else:                            
                            break

                    generated_ucum_codes["/"] += ")"
                elif part[0] == "/":
                    generated_ucum_codes["/"] += part
                else:
                    generated_ucum_codes["/"] += "." + part

                already_used_indices.append(i)

        return generated_ucum_codes