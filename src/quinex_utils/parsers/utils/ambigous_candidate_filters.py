from decimal import *
from pprint import pp
from quinex_utils.functions.boolean_checks import is_small_int


def ignore_duplicates_and_prioritize_successful_matches(all_quantities, superstructure_types, superstructure_quantity_parts_):
    """
    Ignore duplicates and prioritize candidates that could already be
    successfully parsed and have a known superstructure type.
    """
    unique_matches = []
    unique_successful_matches = []
    unique_successful_and_known_matches = []
    unique_known_matches = []
    for q, s, p in zip(all_quantities, superstructure_types, superstructure_quantity_parts_):
        # Only keep unique matches.
        if (q, s, p) not in unique_matches:            
            unique_matches.append((q, s, p))
            if None not in p:
                # Until now quantity was successfully parsed.
                unique_successful_matches.append((q, s, p))
                if s != "unknown":
                    # Until now quantity was successfully parsed and its type is known.
                    unique_successful_and_known_matches.append((q, s, p))
            elif s != "unknown":
                # Quantity could not yet be successfully parsed, but its type is known.
                unique_known_matches.append((q, s, p))

    if len(unique_successful_and_known_matches) > 0:
        # Prio 1: prioritize successfully parsed matches with known superstructure.
        filtered_matches = unique_successful_and_known_matches
    elif len(unique_successful_matches) > 0:
        # Prio 2: prioritize successfully parsed matches.
        filtered_matches = unique_successful_matches
    elif len(unique_known_matches) > 0:
        # Prio 3: prioritize matches with known superstructure.
        filtered_matches = unique_known_matches
    else:        
        filtered_matches = unique_matches

    all_quantities, superstructure_types, superstructure_quantity_parts_ = [list(t) for t in zip(*filtered_matches)]

    return all_quantities, superstructure_types, superstructure_quantity_parts_


def filter_false_positve_ranges(all_quantities, superstructure_types, superstructure_quantity_parts_):
    """
    Filter out false positive ranges. The quantity is unlikely to be a range if the first 
    one has a suffixed unit but the second one not (e.g., '472 cm − 1' is not a range).
    """

    if "range" in superstructure_types:
        false_candidate_idx = superstructure_types.index("range")
        if all(p is not None for p in superstructure_quantity_parts_[false_candidate_idx]) \
        and superstructure_quantity_parts_[false_candidate_idx][0]["suffixed_unit"] != None \
        and superstructure_quantity_parts_[false_candidate_idx][-1]["suffixed_unit"] == None:
            try:
                if is_small_int(Decimal(superstructure_quantity_parts_[false_candidate_idx][-1]["numeric_value"]), threshold=10):
                    # If the quantity was successfully segmented and the first quantity has a suffixed unit, 
                    # but the last quantity has no suffixed unit and is a small integer, 
                    # it is probably a false positive. Remove it.
                    del all_quantities[false_candidate_idx]
                    del superstructure_quantity_parts_[false_candidate_idx]
                    del superstructure_types[false_candidate_idx]
            except:
                pass

    return all_quantities, superstructure_types, superstructure_quantity_parts_


def filter_false_positive_single_quantities(all_quantities, superstructure_types, superstructure_quantity_parts_, role_set_permutation, quantity_span_parts):
    """
    Filter out false positive single quantities (e.g., '10,000 - 240,000 s-1' is a range and not a subtraction).        
    """

    if "single_quantity" in superstructure_types and "range" in superstructure_types:
        range_idx = superstructure_types.index("range")
        false_candidate_idx = superstructure_types.index("single_quantity")                    
        # If the range separator is a hyphen, it is likely a range.                    
        if "range_separator" in role_set_permutation[range_idx] and quantity_span_parts[role_set_permutation[range_idx].index("range_separator")].strip() in ["-", "--", "---"]:
            del all_quantities[false_candidate_idx]
            del superstructure_quantity_parts_[false_candidate_idx]
            del superstructure_types[false_candidate_idx]

    return all_quantities, superstructure_types, superstructure_quantity_parts_


def filter_multidim(all_quantities, superstructure_types, superstructure_quantity_parts_):

    if "multidim" in superstructure_types:
        spatial_multidim_indices = [i for i, t in enumerate(superstructure_types) if t == "multidim" and len(all_quantities[i]) == 3] # 2 is not enough as it leads to confusion with 3.14x10−2
        if len(spatial_multidim_indices) > 0:
            # Only keep the spatial multidimensional quantities.
            all_quantities = [all_quantities[i] for i in spatial_multidim_indices]
            superstructure_types = [superstructure_types[i] for i in spatial_multidim_indices]
            superstructure_quantity_parts_ = [superstructure_quantity_parts_[i] for i in spatial_multidim_indices]

    return all_quantities, superstructure_types, superstructure_quantity_parts_


def filter_reverse_ranges(all_quantities, superstructure_types, superstructure_quantity_parts_):
    """Filter out reverse ranges. Ranges tend to go from small to large values 
    (e.g., '1-2' is a range but '2-1' and '1-1/3' are not).
    """

    if "range" in superstructure_types:
        range_idx = superstructure_types.index("range")
        try:
            # Assumes that numeric values can be interpreted as floats.
            if float(superstructure_quantity_parts_[range_idx][0]["numeric_value"]) > float(superstructure_quantity_parts_[range_idx][-1]["numeric_value"]):
                # Remove the range candidate.
                del all_quantities[range_idx]
                del superstructure_quantity_parts_[range_idx]
                del superstructure_types[range_idx]
            else:
                # Remove the subtraction candidate.
                single_quantity_idx = superstructure_types.index("single_quantity")
                del all_quantities[single_quantity_idx]
                del superstructure_quantity_parts_[single_quantity_idx]
                del superstructure_types[single_quantity_idx]
        except:
            pass

    return all_quantities, superstructure_types, superstructure_quantity_parts_


def take_simplest_option(all_quantities, superstructure_types, superstructure_quantity_parts_, quantity_span_agglomerate, verbose=True):
    """
    Take the simplest option, i.e., the one with the least quantities.
    """
    if verbose:
        print(f"WARNING: Ambiguous quantity span. Multiple possible interpretations for {quantity_span_agglomerate}:")
        for i, interpetation in enumerate(superstructure_quantity_parts_):
            print(f"\n{'vs. ' if i > 0 else ''}Interpretation {i+1}:")
            for quantity in interpetation:
                pp(quantity)

    # Get index of the most simple one.
    idx = all_quantities.index(min(all_quantities, key=len))
    all_quantities = [all_quantities[idx]]
    superstructure_types = [superstructure_types[idx]]
    superstructure_quantity_parts_ = [superstructure_quantity_parts_[idx]]

    return all_quantities, superstructure_types, superstructure_quantity_parts_


def filter_none_in_quanity_parts(all_quantities, superstructure_types, superstructure_quantity_parts_):
    """
    Filter out superstructures with None in quantity parts if at least one superstructure will remain.
    """
    if any(not None in q for q in superstructure_quantity_parts_):
        # There is at least one superstructure with no None in quantity parts.
        # Remove superstructures with None in quantity parts.
        idx_to_remove = []
        for i, q in enumerate(superstructure_quantity_parts_):
            if None in q:
                idx_to_remove.append(i)

        for i in sorted(idx_to_remove, reverse=True):
            del all_quantities[i]
            del superstructure_quantity_parts_[i]
            del superstructure_types[i]

    return all_quantities, superstructure_types, superstructure_quantity_parts_