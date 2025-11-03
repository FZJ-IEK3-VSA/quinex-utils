# Get information about ambiguous units
import json


with open('src/quinex_utils/parsers/static_resources/ambiguous_unit_priorities_curated.json', 'r') as f:
    ambiguous_unit_priorities = json.load(f)

with open('src/quinex_utils/parsers/static_resources/unit_quantity_kinds.json', 'r') as f:
    unit_quantity_kinds = json.load(f)

# Get all units for which potentially a disambiguation is needed.
all_ambigous_units = set()
distinguishable_based_on_quantity_kind_count = 0
not_distinguishable_based_on_quantity_kind_count = 0
nbr_of_ambiguous_unit_sets = len(ambiguous_unit_priorities.keys())
average_nbr_of_units_per_ambiguous_set = sum([len(v) for v in ambiguous_unit_priorities.values()])/nbr_of_ambiguous_unit_sets
for key, value in ambiguous_unit_priorities.items():

    distinguishable_based_on_quantity_kind = True

    all_ambigous_units.update(value.keys())

    # Check if all units have a quantity kind associated with them
    # and that there is no overlap in quantity kinds.
    quantity_kinds_in_ambiguous_set = set()
    for unit in value.keys():
        
        if not distinguishable_based_on_quantity_kind:
            break

        quantity_kinds = unit_quantity_kinds.get(unit)
        if quantity_kinds is None:
            print(f"Unit {unit} does not have a quantity kind associated with it.")
            distinguishable_based_on_quantity_kind = False
            break

        quantity_kinds_ = quantity_kinds.get("qudt", []) 
        if quantity_kinds.get("cqe") is not None:
            quantity_kinds_.append(quantity_kinds.get("cqe"))

        for quantity_kind in quantity_kinds_:
            if quantity_kind in quantity_kinds_in_ambiguous_set:
                print(f"Quantity kind {quantity_kind} is already in the set of quantity kinds for unit {unit}.")
                distinguishable_based_on_quantity_kind = False
                break         
            else:
                quantity_kinds_in_ambiguous_set.add(quantity_kind)

    if distinguishable_based_on_quantity_kind:
        distinguishable_based_on_quantity_kind_count += 1
    else: 
        not_distinguishable_based_on_quantity_kind_count += 1            

print(f"Number of ambiguous unit sets: {nbr_of_ambiguous_unit_sets}")
print(f"Average number of units per ambiguous set: {average_nbr_of_units_per_ambiguous_set}")
print(f"Number of units that are distinguishable based on quantity kind: {distinguishable_based_on_quantity_kind_count}")
print(f"Number of units that are not distinguishable based on quantity kind: {not_distinguishable_based_on_quantity_kind_count}")

print("Finished")