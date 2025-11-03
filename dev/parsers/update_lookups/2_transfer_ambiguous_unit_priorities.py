# Transfer manually adapted unit priorities to newly generated list of ambiguous units.
import json


old_prios_path = "src/quinex_utils/parsers/static_resources_used_for_paper/ambiguous_unit_priorities_curated.json"
new_prios_path = "src/quinex_utils/parsers/static_resources/ambiguous_unit_priorities_raw.json"
new_prios_path_after_update = "src/quinex_utils/parsers/static_resources/ambiguous_unit_priorities_curated.json"

with open(old_prios_path, 'r') as f:  
    old_prios = json.load(f)

with open(new_prios_path, "r") as f:
    new_prios = json.load(f)

# In the past, currencies had a different URI pattern.
for unit_expr, prios_old in old_prios.items():
    old_prios[unit_expr] = {unit.replace("http://qudt.org/vocab/currency/", "http://qudt.org/vocab/unit/CCY_"): prio for unit, prio in prios_old.items()}
        
for unit_expr, prios_new in new_prios.items():
    if unit_expr in old_prios:
        prios_old = old_prios[unit_expr]
        if prios_new == prios_old:
            # Perfect, nothing to do.
            continue
        elif any(prio in prios_old for prio in prios_new):
            # Sort by old priorities. If not in old priorities, put to the end.
            prios_new_list_sorted = sorted(prios_new, key=lambda x: prios_old.get(x) if prios_old.get(x) != None else len(prios_old))
            prios_new_adapted = {prio: idx + 1 for idx, prio in enumerate(prios_new_list_sorted)}  # Transform into dict with index as value

            # Set prio to None if None in old prios.
            for k, v in prios_old.items():
                if v == None and k in prios_new_adapted:
                    prios_new_adapted[k] = None

            # Update if something changed.
            if prios_new_adapted != prios_new:
                print(f"Updating priorities based on old prios for {unit_expr}: {prios_new} -> {prios_new_adapted}")
                new_prios[unit_expr] = prios_new_adapted
        else:
            # Sort by URI length.
            prios_new_list_sorted = sorted(prios_new, key=lambda x: (len(x.replace("/CCY_","")), x)) # We replace /CCY_ to boost currency codes rather than penalize them.
            prios_new_adapted = {prio: idx + 1 for idx, prio in enumerate(prios_new_list_sorted)}  # Transform into dict with index as value
            if prios_new_adapted != prios_new:
                print(f"Updating priorities based on URI length for {unit_expr}: {prios_new} -> {prios_new_adapted}")
                new_prios[unit_expr] = prios_new_adapted            
    else:
        # New ambiguous unit, no old priorities available.
        continue

# Save updated priorities.
with open(new_prios_path_after_update, "w") as f:
    json.dump(new_prios, f, indent=4, ensure_ascii=False)

print("Done.")