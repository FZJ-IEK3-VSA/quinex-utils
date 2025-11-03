import re
import json
from tqdm import tqdm


manual_edits_paths = {
    "unit_label_lookup": "dev/parsers/update_lookups/patches/unit_label_lookup_manual_edits.json",                    
    "unit_symbol_lookup": "dev/parsers/update_lookups/patches/unit_symbol_lookup_manual_edits.json",
    "unit_dimensions_and_kinds": "dev/parsers/update_lookups/patches/unit_dimensions_and_kinds_manual_edits.json",
    "unit_quantity_kinds": "dev/parsers/update_lookups/patches/unit_quantity_kinds_manual_edits.json",
}
check_for_wrong_labels = True
check_for_wrong_cent_units = True

for resource, path in manual_edits_paths.items():
    
    print(f"\nProcessing {resource}...")    
    list_entries = resource in ["unit_label_lookup", "unit_symbol_lookup"]

    with open(path, 'r') as f:
        manual_edits = json.load(f)

    resource_path = f"src/quinex_utils/parsers/static_resources/{resource}.json"
    with open(resource_path, 'r') as f:
        resource_data = json.load(f)

    # Apply manual edits.
    for key, changes in manual_edits.items():
        if key == "added":
            for k, v in changes.items():
                if k in resource_data:
                    if list_entries:
                        new_entries = [el for el in v if el not in resource_data[k]]
                        if len(new_entries) == 0:
                            print(f"Skipping {k} as all entries already exist.")
                        else:
                            # Add diff.
                            print(f"Adding new entries to {k}: {new_entries}.")
                            resource_data[k] = resource_data[k] + new_entries
                    else:
                        print(f"Skipping {k} as it already exists.")
                else:
                    print(f"Adding {k}.")
                    resource_data[k] = v
        elif key == "removed":
             for k, v in changes.items():
                if k in resource_data:
                    print(f"Removing {k}.")
                    if list_entries:
                        # Remove all entries.
                        for entry in v:
                            if entry in resource_data[k]:
                                print(f"Removing entry {entry} from {k}.")
                                resource_data[k].remove(entry)
                        # Remove key if list is empty.
                        if len(resource_data[k]) == 0:
                            print(f"Removing {k} as it is now empty.")
                            del resource_data[k]
                    else:
                        print(f"Removing {k}.")
                        del resource_data[k]
                else:
                    print(f"Skipping {k} as it does not exist.")            
        else:
            raise ValueError(f"Unknown key {key} in manual edits file {path}.")
        
    if check_for_wrong_labels and resource == "unit_label_lookup":
        print("\nChecking for unit expressions that are likely symbols rather than labels...")

        def ask_user_if_label_should_be_removed(unit_expr, uri):
            print(f"\nUnit expression {unit_expr} was likely intended as symbol and not label for {uri}. Please check if this is correct.")
            answer = None
            remove_uri = False
            while answer not in ["y", "n"]:
                answer = input(f"Should {unit_expr} be removed from {uri}? (y/n): ")
                if answer.lower() == "y":
                    remove_uri = True
            
            return remove_uri
        
        made_canges = False
        prefixes = {
            "k": "Kilo",
            "M": "Mega",
            "G": "Giga",
            "T": "Tera",
            "m": "Milli",
            "u": "Micro",
            "n": "Nano",
            "p": "Pico",
            "d": "Deci",
            "c": "Centi"
        }
        for unit_expr, uris in tqdm(resource_data.items()):
            if " per " in unit_expr or "force" in unit_expr:
                continue
            for uri in uris:
                # Ask user for feedback on entries that are likely symbol not label for unit with prefix.
                remove_uri = False
                unit_id = uri.split("/")[-1]                
                for prefix, full in prefixes.items():
                    if unit_id.startswith(full):
                        if unit_expr.lower().startswith(prefix.lower()) and not unit_expr.lower().startswith(full.lower()) and not unit_expr.lower().split()[0] in ["cubic", "square", "conventional", "million"]:
                            remove_uri = ask_user_if_label_should_be_removed(unit_expr, uri)
                            break

                if not remove_uri:
                    # Ask user for feedback on very short entries.
                    unit_expr_alpha_only = re.sub(r'[^a-zA-Z]', '', unit_expr)
                    if len(unit_expr_alpha_only) <= 2 or (len(unit_expr_alpha_only) <= 10 and any(symbol in unit_expr for symbol in ["/","^","*"])):
                        remove_uri = ask_user_if_label_should_be_removed(unit_expr, uri)
                        
                if remove_uri:
                    # Update resource data.
                    resource_data[unit_expr].remove(uri)
                    print(f"Removed {uri} from {unit_expr}.")
                    made_canges = True
    
                    # Update manual edits file.
                    if "removed" not in manual_edits:
                        manual_edits["removed"] = {}
                    if unit_expr not in manual_edits["removed"]:
                        manual_edits["removed"][unit_expr] = []
                    manual_edits["removed"][unit_expr].append(uri)
        
        if made_canges:
            # Save updated manual edits file.
            with open(path, 'w') as f:
                json.dump(manual_edits, f, indent=4, ensure_ascii=False)

    if check_for_wrong_cent_units and resource in ["unit_symbol_lookup", "unit_label_lookup"]:
        for unit_expr, uris in resource_data.items():            
            if len(uris) > 1 and "http://qudt.org/PLACEHOLDER_CENT" in uris and any(uri.startswith("http://qudt.org/vocab/unit/CCY_") for uri in uris):
                # Surface form is associated with both cent and the standard currency unit.
                # Remove standard currency unit.
                print(f"Unit expression {unit_expr} is associated with both cent and the standard currency unit. Removing standard currency unit.")
                uris_to_remove = [uri for uri in uris if uri.startswith("http://qudt.org/vocab/unit/CCY_")]
                for uri in uris_to_remove:
                    uris.remove(uri)
                    print(f"Removed {uri} from {unit_expr}.")


    # Save updated resource.
    with open(resource_path, 'w') as f:
        json.dump(resource_data, f, indent=4, ensure_ascii=False)

print("Done.")