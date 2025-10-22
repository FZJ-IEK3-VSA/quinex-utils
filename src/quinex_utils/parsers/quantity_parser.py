import itertools
from decimal import *
from typing import Union
from copy import deepcopy
from text_processing_utils.char_offsets import is_inside
from quinex_utils.parsers.unit_parser import FastSymbolicUnitParser
from quinex_utils.functions import normalize_quantity_span
from quinex_utils.functions.str2num import str2num, parse_value_and_order_of_magnitude_separately
from quinex_utils.lookups.quantity_modifiers import PREFIXED_QUANTITY_MODIFIERS, SUFFIXED_QUANTITY_MODIFIERS, PREFIXED_QMOD_MATH_SYMBOLS, QUANTITY_MODIFIER_MAPPING, MATH_SYMBOLS_CONSIDERED_AS_PART_OF_QUANTITY_SPAN
from quinex_utils.lookups.number_words import AMBIGOUS_FRACTION_WORDS
from quinex_utils.patterns.contains import CONTAINS_DECIMAL_NUMBER_PATTERN
from quinex_utils.patterns.split import WORD_BOUNDARY_TOKENIZATION_PATTERN
from quinex_utils.patterns.imprecise_quantities import IMPRECISE_VALUE_PATTERN
from quinex_utils.patterns.order_of_magnitude import ORDER_OF_MAGNITUDE_WORD_PATTERN
from quinex_utils.patterns.number_words import STANDALONE_NUMBER_WORD_PATTERN
from quinex_utils.patterns.number import NUMERIC_VALUE_PATTERN
from quinex_utils.parsers.utils.patterns import (
    QUANTITY_TOKENIZATION_PATTERN_1,
    QUANTITY_TOKENIZATION_PATTERN_2,
    UNCERTAINTY_EXPRESSION_W_UNITS_PATTERN,
    NUMERIC_VALUE_WITH_UNCERTAINTY_EXPRESSION_W_UNITS_PATTERN, 
    CURRENCY_YEAR_PATTERN,
    TOLERANCE_W_UNITS_PATTERN,
    UNCERTAINTY_INTERVAL_W_UNITS_PATTERN,
    UNCERTAINTY_INTERVAL_WO_TYPE_W_UNITS_PATTERN,
    STD_DEV_W_UNITS_PATTERN,
    ABSTRACT_QUANTITY_PATTERN,
    IS_NON_PHYSICAL_UNIT_PATTERN,
) 
from quinex_utils.parsers.utils.ambigous_candidate_filters import (
    ignore_duplicates_and_prioritize_successful_matches,
    filter_false_positve_ranges,
    filter_false_positive_single_quantities,
    filter_none_in_quanity_parts,
    filter_reverse_ranges,    
    filter_multidim,
    take_simplest_option,
)



class FastSymbolicQuantityParser:
    """A fast and simple rule-based quantity parser."""

    def __init__(self, error_if_no_success: bool=False, allow_evaluating_str_as_python_expr: bool=False, verbose: bool=False):              
        self.unit_parser = FastSymbolicUnitParser(verbose=verbose)
        self.verbose = verbose
        self.RANGE_SEPARATORS = ["-", "to"]
        self.LIST_SEPARATORS = ["and", "or", ";", ",", ", and", ", or", "vs.", "vs", "versus"]        
        self.RATIO_SEPARTORS = [":", "of the", "out of", "out of the", "of", "per"]
        self.MULTIDIM_SEPARATORS = ["x", "*", "times", "by"]
        self.MATH_OPERATORS = ["+", "-", "*", "/", "^", "(", ")", "±", "∓","(", ")", "[", "]", "{", "}"]
        self.PREFIXED_QUANTITY_MODIFIER_MAPPING = (
            QUANTITY_MODIFIER_MAPPING["words_prefixed"]           
            | QUANTITY_MODIFIER_MAPPING["statistical_modifiers"]
        )
        self.SUFFIXED_QUANTITY_MODIFIER_MAPPING = (
            QUANTITY_MODIFIER_MAPPING["words_suffixed"]
            | QUANTITY_MODIFIER_MAPPING["statistical_modifiers"]
        )
        self.QMODS_IN_UNITS = ["min", "min.", "max", "max."]
        self.error_if_no_success = error_if_no_success
        self.allow_evaluating_str_as_python_expr = allow_evaluating_str_as_python_expr


    def parse(self, quantity_span_agglomerate: str, simplify_results: bool=False) -> dict:
        """Dissect quantity span into value and unit, link unit class to unit and parse value to float.
        The parser fails silently, returning `'success': False`.

        Features:
            1. Dissects quantity span into value, units and modifiers.
            2. Determines the type of quantity span (single quantity, range, list, multidimensional).
            3. Normalizes values, units and modifiers.    

        Examples:
            >>> from quinex_utils.parsers.quantity_parser import FastSymbolicQuantityParser
            >>> quantity_parser = FastSymbolicQuantityParser()
            >>> quantity_parser.parse("around 344 million €")        
            {'nbr_quantities': 1,
            'normalized_quantities': [{'modifiers': {'prefixed': {'normalized': '~',
                                                                'text': 'around'},
                                                    'suffixed': {}},
                                        'prefixed_unit': {'normalized': None,
                                                        'text': None},
                                        'suffixed_unit': {'normalized': [('€',
                                                                        1,
                                                                        'http://qudt.org/vocab/unit/CCY_EUR',
                                                                        None)],
                                                        'text': '€'},
                                        'value': {'imprecise': False,
                                                'normalized': 344000000,
                                                'text': '344 million'}}],
            'separators': [],
            'text': 'around 344 million €',
            'type': 'single_quantity'}

            >>> quantity_parser.parse("above -120.123/-5 to 10.3 * 10^5 TWh kg*s^2/(m^2 per year)^3 at least")
            {'nbr_quantities': 2,
            'normalized_quantities': [{'modifiers': {'prefixed': {'normalized': '>', 'text': 'above'}, 'suffixed': {}},
                                        'prefixed_unit': {'normalized': {'normalized': None, 'text': None}, 'text': None},
                                        'suffixed_unit': {'normalized': {'normalized': [
                                            ('TWh', 1, 'http://qudt.org/vocab/unit/TeraW-HR', None),
                                            ('kg', 1, 'http://qudt.org/vocab/unit/KiloGM', None),
                                            ('s', 2, 'http://qudt.org/vocab/unit/SEC', None),
                                            ('m', -6, 'http://qudt.org/vocab/unit/M', None),
                                            ('year', 3,  'http://qudt.org/vocab/unit/YR', None)],
                                        ...}, {...}]
            'type': 'range'}
        """

        ###########################################
        #      Normalize quantity span.           #
        ###########################################
        quantity_span_agglomerate_clean = normalize_quantity_span(quantity_span_agglomerate)

        # Remove blacklisted suffixes.        
        quantity_span_agglomerate_clean = quantity_span_agglomerate_clean.removesuffix(" and").removesuffix(",")    

        ###########################################
        #              Tokenization.              #
        ###########################################
        quantity_span_parts = self.tokenize_quantity_str(quantity_span_agglomerate_clean)

        ###########################################
        #      Get roles of quanitity tokens.     #
        ###########################################
        role_set_permutation = self.get_token_roles(quantity_span_parts)
        
        if len(quantity_span_parts) == 1 and not any("number" in rs for rs in role_set_permutation):
            # Tokenize more aggressively if there is only one token and it is not a number.
            
            # Re-tokenize the quantity span parts.
            quantity_span_parts = WORD_BOUNDARY_TOKENIZATION_PATTERN.split(quantity_span_agglomerate_clean)
            
            # Remove zero-width matches.
            quantity_span_parts = [part for part in quantity_span_parts if part != '']

            # Determine roles of the quantity tokens again.
            role_set_permutation = self.get_token_roles(quantity_span_parts)        

        #####################################################################################
        #    Split superstructure into individual quantities and their meaningful parts.    #
        #####################################################################################              
        all_quantities = []
        superstructure_types = []
        superstructure_quantity_parts_ = []        
        for role_set in role_set_permutation:
            quantities, quantities_roles, separators = self.split_superstructure_into_individual_quantities(role_set, quantity_span_parts)
            all_quantities.append(quantities)
            superstructure_type = self.get_superstructure_type(separators)
            superstructure_quantity_parts = self.split_quantities_into_parts(quantities, quantities_roles)
            superstructure_types.append(superstructure_type)
            superstructure_quantity_parts_.append(superstructure_quantity_parts)

        ################################################    
        #    Choose the most likely superstructure.    #
        ################################################
        if len(all_quantities) > 1:
            all_quantities, superstructure_types, superstructure_quantity_parts_ = self.filter_ambigous_candidates(all_quantities, superstructure_types, superstructure_quantity_parts_, quantity_span_parts, role_set_permutation, quantity_span_agglomerate)

        # Now that we have a single interpretation, prepare for normalization.
        is_pre_segmented = False if None in superstructure_quantity_parts_[0] else True    
        quantities = superstructure_quantity_parts_[0] if is_pre_segmented else all_quantities[0]
        superstructure_type = superstructure_types[0]

        ##########################################################
        #    Normalize each part of each identified quantity.    #
        ##########################################################
        # Note: We loop through the quantities in reverse order to directly
        # add ellipsed units and orders of magnitude to the first quantities.                    
        failed_flag = False
        ellipsed = {}
        normalized_quantities = []                
        for i, quantity in enumerate(quantities[::-1]):

            if self.verbose and quantity == [] and len(quantities) > 0 and superstructure_type == "list":
                print("Warning: Empty quantity in lists either parsing error or list with ommited quantities given (e.g., in '1, 2, , 4, and 5 km')")

            # TODO: deal with relative values

            # Normalize modifiers, units and values.
            if is_pre_segmented:
                if quantity["suffixed_unit"] == "-":
                    # Dash is used to indicate same unit as last one. 
                    # Set suffixed_unit to None to trigger parsing of unit ellipses.
                    quantity["suffixed_unit"] = None
                normalized_quantity = self.normalize_segmented_quantity(quantity) 
                formally_valid = self.validate_normalized_quantity(normalized_quantity)
                if not formally_valid:
                    # Try sliding window parser instead.
                    quantity = all_quantities[0][i]
                    normalized_quantity = self.sliding_window_parser(quantity)
            else:                
                normalized_quantity = self.sliding_window_parser(quantity) 
            

            # If the center has no unit but the uncertainty expression has, move the unit from the uncertainty expression and to the center.
            if normalized_quantity["suffixed_unit"] == None \
                and normalized_quantity["uncertainty_expression_pre_unit"] != None \
                    and normalized_quantity["uncertainty_expression_pre_unit"]["normalized"] != None \
                        and not normalized_quantity["uncertainty_expression_pre_unit"]["normalized"]["unit"]["is_same_as_mean"]:
                            
                
                unc_unit_normalized = normalized_quantity["uncertainty_expression_pre_unit"]["normalized"]["unit"]["normalized"]
                if unc_unit_normalized.get("suffixed") != None or unc_unit_normalized.get("suffixed_ub") != None:
                    
                    # Add unit from uncertainty expression to center suffixed unit.
                    unit_key = "suffixed" if unc_unit_normalized.get("suffixed") != None else "suffixed_ub"                    
                    normalized_quantity["suffixed_unit"] = unc_unit_normalized[unit_key]
                    
                    # Remove unit from uncertainty expression.
                    moved_unit_surface = unc_unit_normalized[unit_key]["text"]
                    normalized_quantity["uncertainty_expression_pre_unit"]["text"] = normalized_quantity["uncertainty_expression_pre_unit"]["text"].removesuffix(moved_unit_surface)
                    normalized_quantity["uncertainty_expression_pre_unit"]["normalized"]["unit"]["is_same_as_mean"] = True
                    normalized_quantity["uncertainty_expression_pre_unit"]["normalized"]["unit"]["normalized"] = {}

            
            # Validate individual normalized quantity.
            formally_valid = self.validate_normalized_quantity(normalized_quantity)
            if not formally_valid: 
                # Failed to parse quantity span.
                failed_flag = True
                break
            else:
                # Could successfully parse an individual quantity.            
                # Deal with ellipsed units and orders of magnitude.
                if normalized_quantity["value"]["normalized"] == None:
                    order_of_magnitude = None
                else:
                    order_of_magnitude = normalized_quantity["value"]["normalized"].pop("order_of_magnitude")
                normalized_quantity, ellipsed = self.resolve_ellipses(i, normalized_quantity, ellipsed, order_of_magnitude)

                normalized_quantities.append(normalized_quantity)

        normalized_quantities.reverse()

        # Validate the normalization results.
        if failed_flag:
            if self.error_if_no_success:
                raise ValueError(f"Failed to parse quantity span: {quantity_span_agglomerate}.")
            
            # Reset normalized_quantities if parsing of an individual quantity failed.
            normalized_quantities = []
        else:
            formally_valid, unlikely_score = self.validate_normalized_quantity_superstructure(normalized_quantities, superstructure_type, skip_individual_validation=True)            
            # TODO: implement better heuristics for unlikely_score threshold once more checks are implemented.
            if not formally_valid or unlikely_score > 2: 
                # Note that we keep normalized_quantities as the quantity superstructure 
                # was fully parsed and the output may still be useful.
                failed_flag = True
            elif unlikely_score > 0:
                # Superstructure has some unlikely parts, but may still be correct.
                failed_flag = None


        if simplify_results:
            for normalized_quantity in normalized_quantities:

                # Summarize modifiers.
                # ...

                # Summarize units.
                # ...

                # Summarize uncertainty expressions.
                if normalized_quantity["uncertainty_expression_pre_unit"] != None:
                    normalized_quantity["uncertainty"] = normalized_quantity.pop("uncertainty_expression_pre_unit")
                    assert normalized_quantity.pop("uncertainty_expression_post_unit") == None, "Cannot have uncertainty expression before and after unit."
                elif normalized_quantity["uncertainty_expression_post_unit"] != None:
                    normalized_quantity["uncertainty"] = normalized_quantity.pop("uncertainty_expression_post_unit")
                    del normalized_quantity["uncertainty_expression_pre_unit"]

        normalization_dict = {
            "text": quantity_span_agglomerate,
            "type": superstructure_type,
            "nbr_quantities":  len(quantities),
            "normalized_quantities": normalized_quantities,
            "separators": separators,
            "success": not failed_flag if failed_flag != None else None
        }
        
        if len(normalization_dict["normalized_quantities"]) > 0 and normalization_dict["type"] == "list":
            # If a quantity starts with between it is likely to be a range although we 
            # defined "and" as a list seperator (e.g., 'between 1.23 and 1.24 million').
            first_modifier = normalization_dict["normalized_quantities"][0]["prefixed_modifier"]
            if first_modifier != None and first_modifier["text"] is not None and "between" in first_modifier["text"]:
                normalization_dict["type"] = "range"

        return normalization_dict
    

    def filter_ambigous_candidates(self, all_quantities, superstructure_types, superstructure_quantity_parts_, quantity_span_parts, role_set_permutation, quantity_span_agglomerate):
        """
        Filter out ambiguous candidates from the parsed quantities by removing common false positives.
        """
        
        if len(all_quantities) > 1:
            # Ignore duplicates and prioritize successful matches.
            all_quantities, superstructure_types, superstructure_quantity_parts_ = ignore_duplicates_and_prioritize_successful_matches(all_quantities, superstructure_types, superstructure_quantity_parts_)
            if len(all_quantities) > 1:
                # Heuristic: a range is unlikely to have a unit for the first quantity but not for the last one (e.g., '472 cm − 1' is not a range).
                all_quantities, superstructure_types, superstructure_quantity_parts_ = filter_false_positve_ranges(all_quantities, superstructure_types, superstructure_quantity_parts_)
                if len(all_quantities) > 1:
                    # Heuristic: if one option is a range with a dash as separator, it is more likely a range than a subtraction.
                    all_quantities, superstructure_types, superstructure_quantity_parts_ = filter_false_positive_single_quantities(all_quantities, superstructure_types, superstructure_quantity_parts_, role_set_permutation, quantity_span_parts)
                    if len(all_quantities) > 1:
                        # Heuristic: if one option could be successfully segmented, but others not, it is likely the correct one.
                        all_quantities, superstructure_types, superstructure_quantity_parts_ = filter_none_in_quanity_parts(all_quantities, superstructure_types, superstructure_quantity_parts_)
                        if len(all_quantities) > 1:
                            # Heuristic: ranges go from a smaller to a larger value.
                            all_quantities, superstructure_types, superstructure_quantity_parts_ = filter_reverse_ranges(all_quantities, superstructure_types, superstructure_quantity_parts_)
                            if len(all_quantities) > 1:
                                # Heristic: if one option is a multidimensional quantity and it has two or three dimensions, it is likely the correct one.                                                                        
                                all_quantities, superstructure_types, superstructure_quantity_parts_ = filter_multidim(all_quantities, superstructure_types, superstructure_quantity_parts_)                                
                                if len(all_quantities) > 1:
                                    # Heuristic: the simplest option is most likely the correct one.
                                    all_quantities, superstructure_types, superstructure_quantity_parts_ = take_simplest_option(all_quantities, superstructure_types, superstructure_quantity_parts_, quantity_span_agglomerate, verbose=self.verbose)
        
        return all_quantities, superstructure_types, superstructure_quantity_parts_


    def validate_normalized_quantity_superstructure(self, normalized_quantities, superstructure_type, skip_individual_validation=False):
        """
        Validate a normalized quantity agglomerate.
        
        Returns:
            - formally_valid (bool): Whether the normalized quantity is considered valid or not.
            - unlikely_score (int): A score indicating how likely the superstructure is not correctly parsed.
        """

        def check_if_superstructure_is_formally_valid(normalized_quantities, superstructure_type, skip_individual_validation):            
            if superstructure_type == "single_quantity" and len(normalized_quantities) != 1:
                # A single quantity consists of exactly one quantity.
                return False
            elif superstructure_type == "range" and len(normalized_quantities) != 2:
                # A range consists of two quantities.
                return False
            elif superstructure_type in ["list", "multidim", "ratio"] and len(normalized_quantities) < 2:
                # A list and multidimensional quantity consist of at least two quantities.
                return False
            
            # The individual quantities must be formally valid.
            if not skip_individual_validation:
                if any(not self.validate_normalized_quantity(q) for q in normalized_quantities):
                    return False

            # All good.
            return True

        def check_if_superstructure_is_likely_correct(normalized_quantities, superstructure_type):
            # TODO: Include in score whether there is ambiguity in the unit linking.            
            unlikely_score = 0
            
            for normalized_quantity in normalized_quantities:
                # Values that cannot be normalized are more likely not correct than those that can be normalized.            
                if normalized_quantity["value"]["normalized"] == None:
                    unlikely_score += 3
                    
                # Units that cannot be normalized are more likely not correct than those that can be normalized.
                # Note that we ignore ellipsed units here, to not count them multiple times.
                if normalized_quantity["prefixed_unit"] != None and normalized_quantity["prefixed_unit"]["text"] != None \
                    and normalized_quantity["prefixed_unit"]["normalized"] == None:                
                    unlikely_score += 1
                if normalized_quantity["suffixed_unit"] != None and normalized_quantity["suffixed_unit"]["text"] != None \
                    and normalized_quantity["suffixed_unit"]["normalized"] == None:
                    unlikely_score += 1                

                # Uncertainty expressions that cannot be normalized are more likely not correct than those that can be normalized.
                if normalized_quantity["uncertainty_expression_pre_unit"] != None and normalized_quantity["uncertainty_expression_pre_unit"]["normalized"] == None:
                    unlikely_score += 1
                if normalized_quantity["uncertainty_expression_post_unit"] != None and normalized_quantity["uncertainty_expression_post_unit"]["normalized"] == None:
                    unlikely_score += 1

            if superstructure_type == "range":
                # Intervals contain two quantities.
                assert len(normalized_quantities) == 2
          
                units_match = lambda unit_lb, unit_ub: (unit_lb == None and unit_ub == None) or ((unit_lb != None and unit_ub != None) \
                and ((unit_lb["text"] == unit_ub["text"]) \
                    or (unit_lb["ellipsed_text"] == unit_ub["text"]) \
                        or (unit_lb["normalized"] == unit_ub["normalized"])))

                unit_prefixed_lb = normalized_quantities[0]["prefixed_unit"]
                unit_suffixed_lb = normalized_quantities[0]["suffixed_unit"]
                unit_prefixed_ub = normalized_quantities[1]["prefixed_unit"]
                unit_suffixed_ub = normalized_quantities[1]["suffixed_unit"]
                suffixed_units_match = units_match(unit_suffixed_lb, unit_suffixed_ub)
                prefixed_units_match = units_match(unit_prefixed_lb, unit_prefixed_ub)
                
                surface_unit_prefixed_lb = unit_prefixed_lb["text"] if unit_prefixed_lb != None else None
                surface_unit_prefixed_ub = unit_prefixed_ub["text"] if unit_prefixed_ub != None else None
                surface_unit_suffixed_lb = unit_suffixed_lb["text"] if unit_suffixed_lb != None else None
                surface_unit_suffixed_ub = unit_suffixed_ub["text"] if unit_suffixed_ub != None else None

                if any(s != None for s in [surface_unit_prefixed_lb, surface_unit_prefixed_ub, surface_unit_suffixed_lb, surface_unit_suffixed_ub]) \
                    and surface_unit_prefixed_lb == surface_unit_prefixed_ub and surface_unit_suffixed_lb == surface_unit_suffixed_ub:
                    # If lower and upper bound share the same explicitly expressed unit, they are likely to be correct.
                    unlikely_score -= 1
             
                # Heuristic: Intervals typically go from a smaller to a larger value. However, sometimes
                # an interval is expressed in reverse order (e.g., in 'USD 470/MWh to a minimum of USD 120/MWh').
                # Therefore, this is not checked in the formal validation, but only here
                # to check how likely the quantity superstructure is correct.
                lower_bound = normalized_quantities[0]["value"]["normalized"]["numeric_value"]
                upper_bound = normalized_quantities[1]["value"]["normalized"]["numeric_value"]
                if lower_bound is not None and upper_bound is not None and lower_bound > 0 and lower_bound >= upper_bound \
                    and suffixed_units_match and prefixed_units_match:
                        unlikely_score += 1
                
                # Heuristic: ranges typically 
                if not suffixed_units_match and prefixed_units_match \
                    and unit_suffixed_lb != None and unit_suffixed_ub != None \
                        and (unit_suffixed_lb["text"] != None and unit_suffixed_ub["text"] != None) \
                            and (unit_suffixed_lb["text"] in unit_suffixed_ub["text"] \
                                or unit_suffixed_ub["text"] in unit_suffixed_lb["text"]):
                    # If the suffixed units are not the same, but one is a substring of the other, 
                    # the additional characters are likely not part of the unit or if they are, 
                    # missing in the other unit (e.g., '/kWh in Jos' and '/kWh' in '$0.2/kWh in Jos to $0.3/kWh')
                    unlikely_score += 1
            
            return unlikely_score
        
        formally_valid = check_if_superstructure_is_formally_valid(normalized_quantities, superstructure_type, skip_individual_validation)
        if not formally_valid:
            # If the superstructure is not formally valid, it is unlikely to be correct.
            unlikely_score = 10
        else:
            # The superstructure is formally valid, but may still be incorrect.
            unlikely_score = check_if_superstructure_is_likely_correct(normalized_quantities, superstructure_type)

        return formally_valid, unlikely_score



    def validate_normalized_quantity(self, normalized_quantity):                    
        """
        Validate a normalized quantity.
        
        Returns:
            - formally_valid (bool): Whether the normalized quantity is valid or not.            
        """

        def uncertainty_expression_is_valid(normalized_uncertainty_expression):

            if normalized_uncertainty_expression["normalized"] == None:
                # If the uncertainty expression is not normalized, it is not valid.
                return False
                        
            normalized_units = normalized_uncertainty_expression["normalized"]["unit"]["normalized"]
            uncertainty_range = normalized_uncertainty_expression["normalized"]["value"]

            # Check if the uncertainty range is valid.
            if None in uncertainty_range:
                # If one of the bounds of the uncertainty range is not normalized, the uncertainty expression is not valid.
                return False

            if normalized_units != None and len(normalized_units) == 2:
                # Check if surface of successully normalized unit is in the not normalized unit.
                succefully_normalized_units = [v["normalized"] is not None for v in normalized_units.values()]
                if sum(succefully_normalized_units) == 1:
                    # Only one unit was successfully normalized, the other one is not a valid unit.
                    surface_of_successfully_normalized_unit = list(normalized_units.values())[succefully_normalized_units.index(True)]["text"]
                    surface_of_unsuccessfully_normalized_unit = list(normalized_units.values())[succefully_normalized_units.index(False)]["text"]
                    if surface_of_successfully_normalized_unit not in surface_of_unsuccessfully_normalized_unit:
                        # Two very different units indicate that the uncertainty range is not valid.
                        # (e.g., 'th percentile' and 'SEK/kWh' in '25th percentile to 1.15 SEK/kWh')
                        return False
            
            if len(uncertainty_range) == 2 and uncertainty_range[0] >= uncertainty_range[1]:                
                units_match = normalized_units == None or len(normalized_units) == 1 or len({v["text"] for v in normalized_units.values()}) == 1
                if units_match:
                    # Uncertainty range is not valid, lower bound must be less than or equal to upper bound.
                    return False

            return True    
    
        try:
            # A normalized quantity must have a numeric value.
            assert normalized_quantity["value"] != None

            # and the value must be normalized.
            assert normalized_quantity["value"]["normalized"] != None

            # Uncertainty ranges go from a smaller to a larger value.
            uncertainty_expressions = [normalized_quantity["uncertainty_expression_pre_unit"], normalized_quantity["uncertainty_expression_post_unit"]]
            for unc_expr in uncertainty_expressions:
                if unc_expr != None:
                    assert uncertainty_expression_is_valid(unc_expr)

            # All good.
            formally_valid = True 
        except AssertionError:
            # If any assertion fails, the normalized quantity is not formally valid.
            formally_valid = False

        return formally_valid


    def normalize_uncertainty_expression(self, uncertainty_expression, center_prefixed_unit, center_suffixed_unit):
        """Normalize uncertainty expressions, e.g., 
            '7.04 (SD 4.27) days',
            '2.25 (95% CI 1.92-2.65)',        
            (95% confidence interval 0.55%, 0.71%)'
            '3.1 (95% UI = 1.5-4.5)'
        """

        def normalize_uncertainty_expression(unc_expr: str) -> str:            
            unc_expr = unc_expr.removeprefix(r", ")
            return unc_expr.rstrip()

        
        def clean_suffixed_unit(suffixed_unit):
            """Account for the regex being a bit too greedy."""     
            if suffixed_unit:
                suffixed_unit_clean = suffixed_unit.removesuffix(")").removesuffix("]").removeprefix(")").strip()
                if suffixed_unit_clean == "":
                    return None
                else:
                    return suffixed_unit_clean
            else: 
                return None
            
        if uncertainty_expression is None or uncertainty_expression == "": 
            return None
             
        uncertainty_type = "unknown"
        uncertainty_range = None
        unit_same_as_mean = None
        uncertainty_prefixed_unit = None
        uncertainty_suffixed_unit = None
        uncertainty_prefixed_unit_lb = None
        uncertainty_suffixed_unit_lb = None
        uncertainty_prefixed_unit_ub = None
        uncertainty_suffixed_unit_ub = None

        # TODO: Write REGEX without numeric value.
        
        # Check for uncertainty intervals, standard deviations, and tolerances.                
        uncertainty_expression = normalize_uncertainty_expression(uncertainty_expression)
        unc_match = TOLERANCE_W_UNITS_PATTERN.fullmatch(uncertainty_expression)
        if unc_match is not None:
            # Value is given with a tolerance.
            unc_match = unc_match.groupdict()           
            uncertainty_type = "tolerance"

            # Get uncertainty range.
            uncertainty_value = str2num(unc_match["numeric_value"], normalize_chars=False, allow_evaluating_str_as_python_expr=self.allow_evaluating_str_as_python_expr)
            uncertainty_range = (-uncertainty_value, uncertainty_value)
            
            # Get units.
            uncertainty_prefixed_unit = unc_match["prefixed_unit"]
            uncertainty_suffixed_unit = clean_suffixed_unit(unc_match["suffixed_unit"])      
        else:
            # Check for uncertainty intervals.
            unc_match = UNCERTAINTY_INTERVAL_W_UNITS_PATTERN.fullmatch(uncertainty_expression)
        
            if unc_match is not None:
                # Value is given with an uncertainty interval.
                unc_match = unc_match.groupdict()
                uncertainty_type = unc_match["uncertainty_type"]
                
                # Get uncertainty range.
                unvertainty_lb = str2num(unc_match["numeric_value_000"], normalize_chars=False, allow_evaluating_str_as_python_expr=self.allow_evaluating_str_as_python_expr)
                uncertainty_ub = str2num(unc_match["numeric_value_001"], normalize_chars=False, allow_evaluating_str_as_python_expr=self.allow_evaluating_str_as_python_expr)
                uncertainty_range = (unvertainty_lb, uncertainty_ub)
                
                # Get units.
                uncertainty_prefixed_unit_lb = unc_match["prefixed_unit_000"]
                uncertainty_suffixed_unit_lb = unc_match["suffixed_unit_000"]
                uncertainty_prefixed_unit_ub = unc_match["prefixed_unit_001"]
                uncertainty_suffixed_unit_ub = clean_suffixed_unit(unc_match["suffixed_unit_001"])
            else:
                # Check for uncertainty intervals without type.
                unc_match = UNCERTAINTY_INTERVAL_WO_TYPE_W_UNITS_PATTERN.fullmatch(uncertainty_expression)
                if unc_match is not None:  
                    # Value is given with an uncertainty interval without type.
                    unc_match = unc_match.groupdict()
                    uncertainty_type = "unknown"      
                    
                    # Get uncertainty range.
                    unvertainty_lb = str2num(unc_match["numeric_value_000"], normalize_chars=False, allow_evaluating_str_as_python_expr=self.allow_evaluating_str_as_python_expr)
                    uncertainty_ub = str2num(unc_match["numeric_value_001"], normalize_chars=False, allow_evaluating_str_as_python_expr=self.allow_evaluating_str_as_python_expr)
                    uncertainty_range = (unvertainty_lb, uncertainty_ub)
                                      
                    # Get units.
                    uncertainty_prefixed_unit_lb = unc_match["prefixed_unit_000"]
                    uncertainty_suffixed_unit_lb = unc_match["suffixed_unit_000"]
                    uncertainty_prefixed_unit_ub = unc_match["prefixed_unit_001"]
                    uncertainty_suffixed_unit_ub = clean_suffixed_unit(unc_match["suffixed_unit_001"])
                else:
                    # Check for standard deviations.
                    unc_match = STD_DEV_W_UNITS_PATTERN.fullmatch(uncertainty_expression)
                    if unc_match is not None:
                        # Value is given with a standard deviation.
                        unc_match = unc_match.groupdict()
                        if unc_match["uncertainty_a"] != None:
                            uncertainty_value_match = unc_match["numeric_value_000"]
                            uncertainty_prefixed_unit = unc_match["prefixed_unit_000"]
                            uncertainty_suffixed_unit = clean_suffixed_unit(unc_match["suffixed_unit_000"])     
                        else:
                            uncertainty_value_match = unc_match["numeric_value_001"]
                            uncertainty_prefixed_unit = unc_match["prefixed_unit_001"]
                            uncertainty_suffixed_unit = clean_suffixed_unit(unc_match["suffixed_unit_001"])

                        uncertainty_type = "standard_deviation"
                        uncertainty_value = str2num(uncertainty_value_match, normalize_chars=False, allow_evaluating_str_as_python_expr=self.allow_evaluating_str_as_python_expr)
                        uncertainty_range = (-uncertainty_value, uncertainty_value)

        
        if not any([uncertainty_prefixed_unit, uncertainty_suffixed_unit, uncertainty_prefixed_unit_lb, uncertainty_suffixed_unit_lb, uncertainty_prefixed_unit_ub, uncertainty_suffixed_unit_ub]):
            # No units were found.
            unit_same_as_mean = True
            normalized_units = None
        else:            
            # Normalize the units.
            normalized_units = {}
            
            if uncertainty_prefixed_unit:
                # Check if surface form is the same as the center prefixed unit.
                if center_prefixed_unit != None and center_prefixed_unit["text"] == uncertainty_prefixed_unit:
                    unit_same_as_mean = True
                else:
                    unit_same_as_mean = False              
                    normalized_units["prefixed"] = self.normalize_units(uncertainty_prefixed_unit, check_for_forgetting_magnitude=False)
            
            if uncertainty_suffixed_unit:
                # Check if surface form is the same as the center suffixed unit.             
                if center_suffixed_unit != None and center_suffixed_unit["text"] == uncertainty_suffixed_unit:
                    unit_same_as_mean = True
                else:
                    unit_same_as_mean = False
                    normalized_units["suffixed"] = self.normalize_units(uncertainty_suffixed_unit, check_for_forgetting_magnitude=False, is_suffixed_unit=True)

            if uncertainty_prefixed_unit_lb:
                # Check if surface form is the same as the center suffixed unit.
                if center_prefixed_unit != None and center_prefixed_unit["text"] == uncertainty_prefixed_unit_lb:
                    unit_same_as_mean = True
                else:
                    unit_same_as_mean = False    
                    normalized_units["prefixed_lb"] = self.normalize_units(uncertainty_prefixed_unit_lb, check_for_forgetting_magnitude=False)
            
            if uncertainty_suffixed_unit_lb:
                # Check if surface form is the same as the center suffixed unit.             
                if center_suffixed_unit != None and center_suffixed_unit["text"] == uncertainty_suffixed_unit_lb:
                    unit_same_as_mean = True
                else:
                    unit_same_as_mean = False
                    normalized_units["suffixed_lb"] = self.normalize_units(uncertainty_suffixed_unit_lb, check_for_forgetting_magnitude=False, is_suffixed_unit=True)
            
            if uncertainty_prefixed_unit_ub:
                # Check if surface form is the same as the center suffixed unit.
                if center_prefixed_unit != None and center_prefixed_unit["text"] == uncertainty_prefixed_unit_ub:
                    unit_same_as_mean = True
                else:
                    unit_same_as_mean = False   
                    normalized_units["prefixed_ub"] = self.normalize_units(uncertainty_prefixed_unit_ub, check_for_forgetting_magnitude=False)
            
            if uncertainty_suffixed_unit_ub:
                # Check if surface form is the same as the center suffixed unit.             
                if center_suffixed_unit != None and center_suffixed_unit["text"] == uncertainty_suffixed_unit_ub:
                    unit_same_as_mean = True
                else:
                    unit_same_as_mean = False
                    normalized_units["suffixed_ub"] = self.normalize_units(uncertainty_suffixed_unit_ub, check_for_forgetting_magnitude=False, is_suffixed_unit=True)
        
        if uncertainty_range != None:
            normalized_uncertainty = {"type": uncertainty_type, "value": uncertainty_range, "unit": {"is_same_as_mean": unit_same_as_mean, "normalized": normalized_units}}                     
        else:            
            normalized_uncertainty = None
            
        uncertainty = {
            "text": uncertainty_expression,
            "normalized": normalized_uncertainty,            
        }

        return uncertainty


    def normalize_segmented_quantity(self, segmented_quantity):
        """Normalize already segmented quantity spans.
        
        Args:
            segmented_quantity (dict): Segmented quantity span, for example,             
                segmented_quantity = {
                    'prefixed_quantity_modifier': 'about', 
                    'prefixed_unit': None, 
                    'numeric_value': '1.24 million', 
                    'uncertainty_expression_pre_unit' = '(SD 0.53 million)',
                    'suffixed_unit': 'euros', 
                    'uncertainty_expression_post_unit' = None,
                    'suffixed_quantity_modifier': None
                    }

        Returns:
            results (dict): Normalized quantity span parts.
        """
                            
        # Normalize units, that is, parse the units and link them to a unit ontology.
        # Note: Due to imperfect regexes sometimes magnitude words like "million" are matched as part 
        # of the suffixed unit, hence, we detect it and add it back to the numeric value.        
        normalized_prefixed_unit = self.normalize_units(segmented_quantity["prefixed_unit"], check_for_forgetting_magnitude=False)        
        normalized_suffixed_unit = self.normalize_units(segmented_quantity["suffixed_unit"], check_for_forgetting_magnitude=True, is_suffixed_unit=True)

        # Add magnitude back to numeric value that has been wrongly matched as unit.
        if normalized_suffixed_unit != None:
            if normalized_suffixed_unit["forgotten_magnitude"] != "":
                segmented_quantity["numeric_value"] +=  " " + normalized_suffixed_unit.pop("forgotten_magnitude")            
            else:
                del normalized_suffixed_unit["forgotten_magnitude"]
            
        # Normalize the numeric value.        
        normalized_value = self.normalize_value(segmented_quantity["numeric_value"])

        # Normalize the uncertainty expressions.
        uncertainty_expression_pre_unit = self.normalize_uncertainty_expression(segmented_quantity["uncertainty_expression_pre_unit"], normalized_prefixed_unit, normalized_suffixed_unit)
        uncertainty_expression_post_unit = self.normalize_uncertainty_expression(segmented_quantity["uncertainty_expression_post_unit"], normalized_prefixed_unit, normalized_suffixed_unit)    
        
        # Normalize the quantity modifiers.
        normalized_prefixed_modifier = self.normalize_modifier(segmented_quantity["prefixed_quantity_modifier"], is_prefixed=True)
        normalized_suffixed_modifier = self.normalize_modifier(segmented_quantity["suffixed_quantity_modifier"], is_prefixed=False)
        
        results = {
            "prefixed_modifier": normalized_prefixed_modifier,
            "prefixed_unit": normalized_prefixed_unit,
            "value": normalized_value,
            "uncertainty_expression_pre_unit": uncertainty_expression_pre_unit,
            "suffixed_unit": normalized_suffixed_unit,
            "uncertainty_expression_post_unit": uncertainty_expression_post_unit,
            "suffixed_modifier": normalized_suffixed_modifier            
        }

        return results


    def sliding_window_parser(self, quantity_span_parts):
        """Parse and normalize quantity span parts using a sliding window approach, assuming that
        a quantity span consists of a prefixed modifier, prefixed unit, value, 
        suffixed unit, suffixed modifier in this order, where only the value is mandatory.
        
        Args:
            quantity_span_parts (list): List of quantity span parts, for example,
                quantity_span_parts = ['about', ' ', '1.23', ' ', 'to', ' ', 'about', ' ', '1.24', ' ', 'million', ' ', 'euros']

        Returns:
            results (dict): Normalized quantity span parts.
        """

        prefixed_modifier_normalizer = lambda x: self.normalize_modifier(x, is_prefixed=True)
        suffixed_modifier_normalizer = lambda x: self.normalize_modifier(x, is_prefixed=False)        
        # Note: Due to the sequential approach a magnitude word cannot be identified as part 
        # of the suffixed unit by mistake, since the largest value span is identified before.        
        # However, a number word plus unit can be detected as prefixed unit instead of a value
        # plus suffixed unit. For example, "million US dollars per year" or "million years" 
        # can be mapped to a single unit in the QUDT. Therefore, in contrast to the one-shot 
        # parser, we check the prefixed unit for forgotten magnitudes.
        prefixed_unit_normalizer = lambda x: self.normalize_units(x, check_for_forgetting_magnitude=True)
        suffixed_unit_normalizer = lambda x: self.normalize_units(x, check_for_forgetting_magnitude=False, is_suffixed_unit=True)
        uncertainty_normalizer = lambda x: self.normalize_uncertainty_expression(x, prefixed_unit_normalizer(None), suffixed_unit_normalizer(None))
        value_normalizer = lambda x: self.normalize_value(x)

        normalizers = [prefixed_modifier_normalizer, prefixed_unit_normalizer, value_normalizer, uncertainty_normalizer, suffixed_unit_normalizer, uncertainty_normalizer, suffixed_modifier_normalizer]
        keys = ["prefixed_modifier", "prefixed_unit", "value", "uncertainty_expression_pre_unit", "suffixed_unit", "uncertainty_expression_post_unit", "suffixed_modifier"]

        max_valid_i = 0
        results = {}
        for key, normalizer in zip(keys, normalizers):
            max_valid_normalization = None
            offset = max_valid_i
            
            if offset < len(quantity_span_parts) and quantity_span_parts[offset] == " ":
                # If the window starts with whitespace, we can skip it.
                offset += 1

            for i in range(offset + 1, len(quantity_span_parts) + 1):
                window = quantity_span_parts[offset:i]
                if window[-1] == " ":
                    # If the window ends with whitespace, we can skip it.
                    continue
                else:
                    result = normalizer("".join(window).strip())
                    if result["normalized"] != None:
                        
                        if key == "prefixed_unit" and result["forgotten_magnitude"] != "":
                            # If a prefixed unit starts with a magnitude word 
                            # it is not a prefixed unit.
                            continue
                        else:
                            # Normalization was successful.
                            max_valid_normalization = result
                            max_valid_i = i
                
            results[key] = max_valid_normalization
        
                         
        if results["prefixed_unit"] is not None:
            del results["prefixed_unit"]["forgotten_magnitude"]
        
        if max_valid_i != len(quantity_span_parts):
            # Did not manage to parse the whole quantity span.              
            if results["value"] != None:
                if results["suffixed_modifier"] == None:
                    # Assume that the last part is a suffixed unit.
                    suffixed_unit_span = results["suffixed_unit"]["text"] if results["suffixed_unit"] != None else ""
                    suffixed_unit_span += "".join(quantity_span_parts[max_valid_i:])
                    results["suffixed_unit"] = suffixed_unit_normalizer(suffixed_unit_span.strip())            
                elif results["suffixed_unit"] == None:
                    # Assume that the last part is a suffixed unit preceding a suffixed modifier.
                    # Without this special rule, quantities like 'two or more atoms' are not parsed correctly, 
                    # as the parser assumes the suffixed modifiers after the suffixed unit.
                    suffixed_unit_span = "".join(quantity_span_parts[max_valid_i:])
                    results["suffixed_unit"] = suffixed_unit_normalizer(suffixed_unit_span.strip())      
                else:
                    # Assume that the last part is a suffixed modifier.
                    suffixed_modifier_span = results["suffixed_modifier"]["text"] 
                    suffixed_modifier_span += "".join(quantity_span_parts[max_valid_i:])
                    results["suffixed_modifier"] = suffixed_modifier_normalizer(suffixed_modifier_span.strip())

        return results
    

    def resolve_ellipses(self, i, normalized_quantity, ellipsed, order_of_magnitude):
        """Deal with ellipses, e.g., in "1, 2, 3, and 4 million km" the units
        and orders of magnitude for the first three quantities are ellipsed.
        """

        if i == 0:
            # Get ellipsed units and orders of magnitude from last quantity, 
            # which is the first one in the list.
            ellipsed = {
                "prefixed_unit": normalized_quantity["prefixed_unit"].copy() if normalized_quantity["prefixed_unit"] != None else None, 
                "suffixed_unit": normalized_quantity["suffixed_unit"].copy() if normalized_quantity["suffixed_unit"] != None else None,
                "magnitude": 1 if order_of_magnitude == None else order_of_magnitude
                }

        else:
            # Resolve ellipses for a previous quantities.

            # Only resolve unit ellipses if both prefixed and suffixed units are missing.
            if normalized_quantity["prefixed_unit"] == None and normalized_quantity["suffixed_unit"] == None:
                
                if ellipsed["prefixed_unit"] != None:
                    # Add ellipsed units.    
                    normalized_quantity["prefixed_unit"] = deepcopy(ellipsed["prefixed_unit"])
                    # Add ellipsed surface.
                    normalized_quantity["prefixed_unit"]["ellipsed_text"] = normalized_quantity["prefixed_unit"]["text"]
                    # No surface form.
                    normalized_quantity["prefixed_unit"]["text"] = None 

                if ellipsed["suffixed_unit"] != None:
                    # Add ellipsed units.    
                    normalized_quantity["suffixed_unit"] = deepcopy(ellipsed["suffixed_unit"])              
                    # Add ellipsed surface.
                    normalized_quantity["suffixed_unit"]["ellipsed_text"] = normalized_quantity["suffixed_unit"]["text"]
                    # No surface form.
                    normalized_quantity["suffixed_unit"]["text"] = None

            # Deal with order of magnitude ellipses.
            if order_of_magnitude == None and normalized_quantity["value"]["normalized"] != None and normalized_quantity["value"]["normalized"]["numeric_value"] != None and ellipsed["magnitude"] != 1:
                # Multiply value with ellipsed order of magnitude.
                normalized_quantity["value"]["normalized"]["numeric_value"] *= ellipsed["magnitude"]
                # normalized_quantity["value"]["ellipsed_text"] =                 
            
        return normalized_quantity, ellipsed
    

    def tokenize_quantity_str(self, quantity_span_agglomerate: str) -> list[str]:
        """Split quantity string into tokens as large as possible but as small as necessary.
        
        Args:
            quantity_span_agglomerate (str): Quantity string to be tokenized.

        Returns:   
            quantity_span_parts (list): List of tokens.

        """

        # Protect quantity modifier phrases, imprecise quantities, number words and uncertainty expressions
        initial_quantity_span_parts, is_protected = protect_quantity_parts_from_being_split(quantity_span_agglomerate)

        # Keep modifier phrases and imprecise quantity phrases intact and split the rest further.        
        quantity_span_parts = []        
        for i, part in enumerate(initial_quantity_span_parts):             
            if part in ["", None]:
                continue
            elif is_protected[i]:                
                quantity_span_parts.append(part)
            else:            
                # Part is not protected, so we can split it further. Split at whitespace,
                # comma or semicolon with whitespace, boundaries between digits and letters,
                # and digits sperated by hyphen that denote ranges.
                quantity_span_parts += QUANTITY_TOKENIZATION_PATTERN_2.split(part)
            
        # Remove potential zero-width matches.
        quantity_span_parts = [part for part in quantity_span_parts if part != '']

        # Merge adjecent ", " and "and" or "or" tokens.
        for separator in ["and", "or"]:
            if separator in quantity_span_parts and ", " in quantity_span_parts:
                for i, part in enumerate(quantity_span_parts.copy()[:-1]):
                    if part == ", " and quantity_span_parts[i + 1] == separator:
                        quantity_span_parts[i] += quantity_span_parts.pop(i+1)
                        if not separator in quantity_span_parts:
                            break

        return quantity_span_parts
    
    
    def get_token_roles(self, quantity_span_parts: list[str]) -> list[tuple[str]]:
        """Get role candidates for each token of the quantity span.

        Args:
            quantity_span_parts (list): List of tokens.

        Returns:
            role_set_permutation (list): List of role candidates for each token of the quantity span.
        
        """

        # Helper function
        is_preceded_by_list_separator = lambda r: (len(r) > 0 and "list_separator" in r[-1]) or (len(r) > 1 and "list_separator" in r[-2] and "whitespace" in r[-1])
        is_preceded_by_number = lambda r: len(r) > 0 and 'number' in r[-1]
        is_preceded_by_whitespace_and_number = lambda r: len(r) > 1 and 'whitespace' in r[-1] and 'number' in r[-2]        
        is_followed_by_number = lambda i, qsp: len(qsp) > i and NUMERIC_VALUE_PATTERN.fullmatch(qsp[i + 1]) is not None
        is_followed_by_whitespace_and_number = lambda i, qsp: len(qsp) > i + 1 and qsp[i + 1] == " " and NUMERIC_VALUE_PATTERN.fullmatch(qsp[i + 2]) is not None

        # Loop through the individual parts of the quantity span.
        roles = []                      
        for i, quantity_span_part in enumerate(quantity_span_parts):
                    
            # Cannot start or end with seperator
            sep_allowed = 0 < i < len(quantity_span_parts) - 1
            
            part_roles = []
            if quantity_span_part == " ":
                part_roles.append("whitespace")
            elif quantity_span_part in ["a", "an"] and len(quantity_span_parts) > 1:
                if is_followed_by_whitespace_and_number(i, quantity_span_parts):
                    part_roles.append("prefixed_quantity_modifier")
                    if len(roles) > 0 and "number" in roles:
                        # If the 'a' is preceded by a number, it may refer to the unit year.
                        part_roles.append("unit")
                else:
                    # 'a' can be a number word (e.g., in 'up to a kilometer')
                    part_roles.append("number")
                    if quantity_span_part == "a":
                        # 'a' can refer to the unit year
                        part_roles.append("unit")         
            elif CURRENCY_YEAR_PATTERN.fullmatch(quantity_span_part) is not None:
                part_roles += ["year", "number"]
            elif NUMERIC_VALUE_PATTERN.fullmatch(quantity_span_part) is not None:                
                if STANDALONE_NUMBER_WORD_PATTERN.fullmatch(quantity_span_part) != None and is_preceded_by_whitespace_and_number(roles):
                    # If the number word is a standalone number word that is preceded by a number and whitespace, it is likely a unit.
                    part_roles.append("unit")
                elif IMPRECISE_VALUE_PATTERN.fullmatch(quantity_span_part) and is_preceded_by_whitespace_and_number(roles):
                    # If the number word is an imprecise value that is preceded by a number and whitespace, it is likely part of the unit.
                    # (e.g., 'tons of' is not an imprecise quantity in '100 tons of products per day' but part of the unit)
                    part_roles.append("unit")
                else:
                    part_roles.append("number")
            elif ORDER_OF_MAGNITUDE_WORD_PATTERN.fullmatch(quantity_span_part) is not None:
                part_roles.append("number")
            elif quantity_span_part in ["e", "E"]:
                # Probably part of a number in scientific notation, e.g., '1.23e-4'
                part_roles.append("number")            
            elif sep_allowed and quantity_span_part in self.RANGE_SEPARATORS:
                
                part_roles.append("range_separator")
                if quantity_span_part in self.MATH_OPERATORS:
                    # The "-" sign can be a range seperator (e.g., in 472 − 473 cm) 
                    # or a math operator (e.g., in '472 cm − 1').
                    if is_preceded_by_list_separator(roles) and quantity_span_part in ["-", "+"]:
                        # If '-' is preceded by a list separator, it is more likely a minus sign
                        # (e.g., in '50 and − 50%').
                        part_roles.append("number")
                    elif quantity_span_part == "-" and (is_preceded_by_number(roles) or is_preceded_by_whitespace_and_number(roles)):
                        # Can also be unit ellipses as in '3-to 5-years'
                        part_roles.append("math_operator")
                        part_roles.append("unit")
                    else:
                        part_roles.append("math_operator")
                elif quantity_span_part == "to" and is_preceded_by_list_separator(roles):
                    # In this case, it is more likely a prefixed_quantity_modifier 
                    # (e.g., in '0%, 10%, to 20%').
                    part_roles.append("prefixed_quantity_modifier")
            elif sep_allowed and quantity_span_part.strip() in self.LIST_SEPARATORS:
                part_roles.append("list_separator")
            elif sep_allowed and quantity_span_part in self.MULTIDIM_SEPARATORS:
                part_roles.append("multidim_separator")
                if quantity_span_part in ["times", "by"]:
                    # Could also be a unit such as in '2-3 times' or '5% by weight'.
                    part_roles.append("unit")
                elif quantity_span_part == "*":
                    # Could also be a math operator such as in '2 * 3'.
                    part_roles.append("math_operator")
            elif quantity_span_part in self.MATH_OPERATORS:
                if len(roles) == 0 and quantity_span_part in PREFIXED_QMOD_MATH_SYMBOLS:
                    # If it is the first part of the quantity span, it is more likely a prefixed quantity modifier
                    # (e.g., '−' in '−$97M' or '− 10%').
                    if quantity_span_part in MATH_SYMBOLS_CONSIDERED_AS_PART_OF_QUANTITY_SPAN and is_followed_by_whitespace_and_number(i, quantity_span_parts):
                        # e.g., '− 1' should be parsed to -1
                        part_roles.append("number")
                    else:                        
                        part_roles.append("prefixed_quantity_modifier")
                else:
                    part_roles.append("math_operator")
                    part_roles.append("prefixed_quantity_modifier")
            elif quantity_span_part.lower() in PREFIXED_QUANTITY_MODIFIERS:
                # If it is suffixed, it will be caught in split_superstructure_into_individual_quantities()
                part_roles.append("prefixed_quantity_modifier")
                if quantity_span_part.lower() in SUFFIXED_QUANTITY_MODIFIERS and len(roles) > 0:
                    part_roles.append("suffixed_quantity_modifier")
                if quantity_span_part in self.QMODS_IN_UNITS and len(roles) > 0:
                    # Could also be a unit (e.g., 'min' in '2 min 45 s').
                    part_roles.append("unit")
            elif quantity_span_part.lower() in SUFFIXED_QUANTITY_MODIFIERS and len(roles) > 0:
                part_roles.append("suffixed_quantity_modifier")
            elif UNCERTAINTY_EXPRESSION_W_UNITS_PATTERN.fullmatch(quantity_span_part):
                part_roles.append("uncertainty_expression")
            elif sep_allowed and quantity_span_part in self.RATIO_SEPARTORS:
                part_roles.append("ratio_separator")
                if (is_preceded_by_number(roles) or is_preceded_by_whitespace_and_number(roles)) \
                    and (is_followed_by_number(i, quantity_span_parts) or is_followed_by_whitespace_and_number(i, quantity_span_parts)):
                    # If ":" etc. is preceded by a number and followed by a number, it is unlikely part of a unit.
                    pass
                else:                    
                    part_roles.append("unit")
            else:
                part_roles.append("unit")
        
            roles.append(part_roles)

        # Create permutations of all role options.    
        role_set_permutation = list(itertools.product(*roles))

        # Filter known invalid role combinations if more than one role set.
        for role_set in role_set_permutation.copy():
            if len(role_set_permutation) > 1:
                # Check if any invalid subpattern is present in the role set.
                invalid_subpatterns = [('range_separator', 'whitespace', 'range_separator')]               
                for invalid_subpattern in invalid_subpatterns:
                    if str(invalid_subpattern)[1:-1] in str(role_set):
                        role_set_permutation.remove(role_set)
                        break
        
        # Filter known according to known dominant role sets.
        if any('ratio_separator' in r for r in role_set_permutation):
            # Do not confuse ratios with units.
            if role_set_permutation == [('number', 'ratio_separator', 'number'), ('number', 'unit', 'number')]:
                role_set_permutation = [('number', 'ratio_separator', 'number')]
            elif role_set_permutation == [('number', 'whitespace', 'ratio_separator', 'whitespace', 'number'), ('number', 'whitespace', 'unit', 'whitespace', 'number')]:
                role_set_permutation = [('number', 'whitespace', 'ratio_separator', 'whitespace', 'number')]

        return role_set_permutation


    def split_superstructure_into_individual_quantities(self, role_set: tuple[str], quantity_span_parts: list[str]) -> tuple[list[list[str]], list[tuple[str]], list[tuple[str]]]:
        """Split a superstructure into individual quantities based on the role set
        and determine the superstructure type.

        Args:
            role_set (tuple): Tuple of roles of each part of the quantity superstructure span.
            quantity_span_parts (list): List of parts of the quantity superstructure span.
        
        Returns:
            quantities (list): List of parts per individual quantity.
            quantities_roles (list): List of roles per individual quantity.
            separators (list): List of separators and their kind.
        
        """
          
        # Split superstructure at separators into individual quantities.        
        quantities = []
        quantities_roles = []
        separators = []
        last_separator_index = 0        
        for i, role in enumerate(role_set):
            if role in ["range_separator", "list_separator", "multidim_separator", "ratio_separator"]:
                if len(role_set) > i - 1 and role_set[i + 1] == "uncertainty_expression":
                    # If the next role is an uncertainty expression, we skip the separator
                    # (e.g., '2.30, 95% CI 1.03-5.13' should not be split into two quantities at the comma).
                    continue
                else:
                    pass
            elif role == "prefixed_quantity_modifier" and any(r not in ["prefixed_quantity_modifier","whitespace"] for r in role_set[last_separator_index:i]):
                # Prefixed quantity modifiers are only allowed at the beginning of a quantity span. 
                # If there are any other roles before it, it triggers a new quantity span to start.
                if i == len(role_set) - 1:
                    # If at end of quantity span, it is a suffixed quantity modifier.
                    role = "suffixed_quantity_modifier"
                    continue
                elif quantity_span_parts[i] in ["between","up to"]:
                    # The quantity modifier is used as a range separator here.
                    role = "range_separator"
                    pass
            else:
                continue
            
            # Add new quantity.
            if quantity_span_parts[last_separator_index] == " ":
                last_separator_index += 1
            if quantity_span_parts[i] == " ":
                i -= 1
            
            quantities.append(quantity_span_parts[last_separator_index:i])
            quantities_roles.append(role_set[last_separator_index:i])
            separators.append((quantity_span_parts[i], role))
            last_separator_index = i + 1
                    
        # Add last items.
        if last_separator_index < len(role_set):
            if quantity_span_parts[last_separator_index] == " ":
                last_separator_index += 1
            if quantity_span_parts[i] == " ":
                i -= 1
            quantities.append(quantity_span_parts[last_separator_index:])
            quantities_roles.append(role_set[last_separator_index:])

        return quantities, quantities_roles, separators
    

    def get_superstructure_type(self, separators: list[tuple[str]]) -> str:
        """Determine the type of superstructure, that is, whether it is a 
        single quantity, a range, a list, or a multidimensional quantity.
        
        Args:
            separators (list): List of separators and their roles.

        Returns:
            superstructure_type (str): Type of superstructure.

        """

        if len(separators) == 0:
            superstructure_type = "single_quantity"
        else:
            superstructure_type = "unknown"
            for separator in ["range_separator", "list_separator", "multidim_separator", "ratio_separator"]:
                if all(sep == separator for _, sep in separators):
                    superstructure_type = separator.split("_")[0]
                    break

        return superstructure_type
    

    def split_quantities_into_parts(self, quantities: list[list[str]], quantities_roles: list[tuple[str]]):
        """Split the individual quantities into meaningful parts, that is, value, units, and modifiers.
        
        Args:
            quantities (list): List of parts per individual quantity.
            quantities_roles (list): List of roles per individual quantity.

        Returns:
            superstructure_quantity_parts (list): List of quantity part dictionary per individual quantity.

        """
        
        superstructure_quantity_parts = []
        for i, quantity_roles in enumerate(quantities_roles):

            # Create string from role set.
            role_set_str = "".join(["_" + role + "_" for role in quantity_roles if role != ""])
        
            # Check if the role set matches a known superstructure.
            match = ABSTRACT_QUANTITY_PATTERN.fullmatch(role_set_str) 

            if match is not None:
                parsed_quantity_parts = match.groupdict()
                last_key_index = 0
                for key in ["prefixed_quantity_modifier", "prefixed_unit", "numeric_value", "uncertainty_expression_pre_unit", "suffixed_unit", "uncertainty_expression_post_unit", "suffixed_quantity_modifier"]:
                    if parsed_quantity_parts[key] is not None:
                        j = len(parsed_quantity_parts[key].split("__"))
                        next_key_index = last_key_index + j
                        part_string = "".join(quantities[i][last_key_index:next_key_index]).strip()
                        parsed_quantity_parts[key] = None if part_string == "" else part_string
                        last_key_index = next_key_index 
            else:
                # Could not parse quantity span
                parsed_quantity_parts = None
            
            superstructure_quantity_parts.append(parsed_quantity_parts)

        return superstructure_quantity_parts 


    def normalize_value(self, value_span: str) -> tuple[dict, Union[float, None]]:
        """Normalize the given value span by interpreting it as a numeric data type. 
        Additionally, the order of magnitude and whether the value is imprecise is determined.
        
        Args:
            value_span (str): Surface form of a value.
        
        Returns:    
            result (dict): Dictionary of normalized value.

        """
        
        if value_span is None:
            value = None
            is_imprecise = None
            order_of_magnitude = None         
        else:                                    
            try:
                # Try to consider the numeric value separately from its potential order of magnitude expression.                
                value, order_of_magnitude = parse_value_and_order_of_magnitude_separately(value_span)
            except ValueError:
                # Parse numeric value without separately considering order of magnitudes.
                value = str2num(value_span, normalize_chars=False, skip_cast_as_num_and_order_of_magnitude=True, allow_evaluating_str_as_python_expr=self.allow_evaluating_str_as_python_expr)
                order_of_magnitude = None

            if value is None:
                # Check if value is in list of imprecise number words.
                match = IMPRECISE_VALUE_PATTERN.fullmatch(value_span)
                if match is None:
                    is_imprecise = False
                else:
                    value_span = value_span.removesuffix(" of")                       
                    is_imprecise = True
            else:
                is_imprecise = False
                if order_of_magnitude is not None:
                    # Get value with suffixed order of magnitude. Because simply 
                    # calculating the value as `value = value * order_of_magnitude` 
                    # can result in numerical errors, we use the following approach.
                    value = float(Decimal(str(value)) * Decimal(str(order_of_magnitude)))

        if value is None and is_imprecise is False:
            # Could not parse value span.
            numeric_value = None
        else:
            numeric_value = {"numeric_value": value, "is_imprecise": is_imprecise, "order_of_magnitude": order_of_magnitude}#, "uncertainty": uncertainty}

        result = {
            "text": value_span,
            "normalized": numeric_value,
        }

        return result


    def normalize_units(self, unit_span: str, check_for_forgetting_magnitude: bool=True, is_suffixed_unit=None) -> tuple[dict, dict, str]:
        """Normalize the given unit spans by parsing them and linking them to a unit ontology.
        
        Args:
            unit_span (str): Surface form of a unit.            

        Returns:
            unit (dict): Dictionary of normalized units.

        """

        # Normalize unit, that is, parse the unit and link it to a unit ontology.
        forgotten_magnitude = ""
        normalized_unit = None        
        if unit_span is None or unit_span == "": 
            return None
        else:            
            if check_for_forgetting_magnitude:
                # If by mistake a number word like million is matched as unit candidate and not as
                # part of the number, remove it from the units span and add it to the number span.
                num_word_match = ORDER_OF_MAGNITUDE_WORD_PATTERN.match(unit_span)
                if num_word_match is not None:
                    forgotten_magnitude = num_word_match.group()
                    unit_span = unit_span[num_word_match.span()[1] :].strip()  

            # Find know units using QUDT unit parser.
            if unit_span != "" and not CONTAINS_DECIMAL_NUMBER_PATTERN.match(unit_span):
                try:            
                    normalized_unit = self.unit_parser.parse(unit_span, quantity_normalization_already_done=True)
                except Exception as e: 
                    print(e)
                    if str(e).startswith("No priority found for unit"):
                        pass
                    else:
                        # Debug.                        
                        raise e
                                
            # Post-process non-physical units for suffixed units
            # (e.g., the unit in 'three-compartment' is 'compartment' and not '-compartment').
            if is_suffixed_unit and unit_span.startswith("-") and IS_NON_PHYSICAL_UNIT_PATTERN.match(unit_span):                
                unit_span = unit_span[1:].strip()
            
            if normalized_unit and unit_span.endswith(" in") and len(normalized_unit) > 1:
                # It is more likely that 'in' belongs to 'in 2015' or 'in Paris' 
                # than it reffering to inch as part of the unit.
                normalized_unit = None

            result = {
                "text": unit_span,
                "ellipsed_text": None, # placeholder
                "normalized": normalized_unit,
            }
            if check_for_forgetting_magnitude:
                result["forgotten_magnitude"] = forgotten_magnitude
    
            return result


    def normalize_modifier(self, quantity_modifier_span: str, is_prefixed: bool=True) -> dict:
        """Normalize quantity modifiers using a dictionary of known modifier phrases and their normalized form.
        For example, "at least" is normalized to "≥", "at most" to "≤", "above" to ">", and "around" to "~", etc.
        
        Args:
            prefixed_quantity_modifier_span (str): Surface form of a prefixed quantity modifier phrase.
            suffixed_quantity_modifier_span (str): Surface form of a suffixed quantity modifier phrase.

        Returns:
            normalized_modifiers (dict): Dictionary of normalized quantity modifiers.

        """

        # Select the normalization mapping.
        mapping = self.PREFIXED_QUANTITY_MODIFIER_MAPPING if is_prefixed else self.SUFFIXED_QUANTITY_MODIFIER_MAPPING

        # Normalize quantity modifiers.
        if quantity_modifier_span is None or quantity_modifier_span == "": 
            return None
        else:            
            normalized_quantity_modifier = mapping.get(quantity_modifier_span.lower())

            if normalized_quantity_modifier is None:
                if quantity_modifier_span == "a":
                    # 'a' is kept separate from the mapping, to not identify years as modifiers.
                    normalized_quantity_modifier = "="
                elif quantity_modifier_span in ["-", "+"] and is_prefixed:
                    normalized_quantity_modifier = quantity_modifier_span
                else:
                    normalized_quantity_modifier = mapping.get(quantity_modifier_span.lower().replace(" ", ""))

            result = {"text": quantity_modifier_span, "normalized": normalized_quantity_modifier}

            return result


def protect_quantity_parts_from_being_split(quantity_span_agglomerate: str) -> tuple[list[str], list[bool]]:
    """
    Pre-tokenize string at boundaries of quantity modifier phrases, imprecise quantities, number words 
    and uncertainty expressions to prevent them from being split during further tokenization.
    """    

    # Protect quantity modifier phrases, imprecise quantities, and number words from being split.
    matches_a_ = list(QUANTITY_TOKENIZATION_PATTERN_1.finditer(quantity_span_agglomerate))
    
    # Special tokenization rule for ambiguous fraction words.
    # If a fraction word is preceded by 'a', it is more likely to be a fraction and we adapt tokenization accordingly.
    # (e.g., 'about a third' is tokenized to ['about', 'a third'] instead of ['about a', 'third']).
    matches_a_.reverse()        
    matches_a = []
    adapt_char_offset = 0        
    for match in matches_a_:
                    
        start_char = match.start("protected_expression")
        end_char = match.end("protected_expression")
        surface = match.groupdict()["protected_expression"]
        
        # Adapt end character offset due to change of previous match.
        if adapt_char_offset > 0:
            end_char -= adapt_char_offset
            surface = surface[:-2]
            adapt_char_offset = 0

        if surface in AMBIGOUS_FRACTION_WORDS:
            # Check if preceded by 'a' which makes it more likely to be a fraction.                
            if start_char > 1 and quantity_span_agglomerate[start_char - 2:start_char] == "a " \
                and (start_char - 2 == 0 or quantity_span_agglomerate[start_char - 3] == " "):
                # Move "a " into fraction span for it to be considered by str2num.
                adapt_char_offset = 2
                start_char -= adapt_char_offset
                surface = "a " + surface

        matches_a.append({"start": start_char, "end": end_char, "text": surface})
    
    matches_a.reverse()
        
    # Protect uncertainty expressions from being split.
    matches_b_ = list(NUMERIC_VALUE_WITH_UNCERTAINTY_EXPRESSION_W_UNITS_PATTERN.finditer(quantity_span_agglomerate))    
    matches_b = []
    for match in matches_b_:
        unc_expr = match.groupdict()["protected_expression"]            
        if quantity_span_agglomerate.split(unc_expr)[0].endswith(", ") and UNCERTAINTY_INTERVAL_WO_TYPE_W_UNITS_PATTERN.match(unc_expr):
            # ", " is only allowed as separator between quantity and uncertainty expression if the latter is not a simple range
            continue
        else:
            matches_b.append({"start": match.start("protected_expression"), "end": match.end("protected_expression"), "text": unc_expr})

    # Drop matches from matches_a that are inside matches_b.
    matches = []
    for match_a in matches_a:
        if not any(is_inside((match_a["start"], match_a["end"]), (match_b["start"], match_b["end"])) for match_b in matches_b):
            matches.append(match_a)        
    
    matches += matches_b

    # Sort matches by lowest start character.
    # Overlap should not be possible, hence we do not sort by end character.
    matches.sort(key=lambda x: x["start"])

    # Split at protected parts and note to keep them intact in further tokenization in "is_protected".
    max_char_seen = 0
    is_protected = []
    initial_quantity_span_parts = []            
    for match in matches:
        if match["start"] > max_char_seen:
            part_before = quantity_span_agglomerate[max_char_seen:match["start"]]
            initial_quantity_span_parts.append(part_before)
            is_protected.append(False)
        
        part = match["text"]
        initial_quantity_span_parts.append(part)
        is_protected.append(True)
        max_char_seen = match["end"]

    # Remove None values.
    initial_quantity_span_parts = [part for part in initial_quantity_span_parts if part != None]

    # Add the rest of the quantity span if it was not covered by a match.
    if max_char_seen < len(quantity_span_agglomerate):
        initial_quantity_span_parts.append(quantity_span_agglomerate[max_char_seen:])
        is_protected.append(False)

    return initial_quantity_span_parts, is_protected