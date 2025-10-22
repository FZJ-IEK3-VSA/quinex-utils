import json


label_or_sysbol = "label"  # "symbol" or "label"
with open(f'src/quinex_utils/parsers/static_resources_used_for_paper/unit_{label_or_sysbol}_lookup.json', 'r') as f:
    surfaces_old = json.load(f)

with open(f'src/quinex_utils/parsers/static_resources/unit_{label_or_sysbol}_lookup.json', 'r') as f:
    surfaces_new = json.load(f)


new_count = sum(1 for v in surfaces_new.keys() if v not in surfaces_old)
removed_count = sum(1 for v in surfaces_old.keys() if v not in surfaces_new)
unchanged_count = sum(1 for v in surfaces_new.keys() if v in surfaces_old and surfaces_new[v] == surfaces_old[v])
changed_count = sum(1 for v in surfaces_new.keys() if v in surfaces_old and surfaces_new[v] != surfaces_old[v])

print(f"New units: {new_count}")
print(f"Removed units: {removed_count}")
print(f"Unchanged units: {unchanged_count}")
print(f"Changed units: {changed_count}")

for key in surfaces_old.keys():
    if key in surfaces_new:
        if surfaces_new[key] != surfaces_old[key]:
            print(f"Changed unit: {key}")
            print(f"  Old: {surfaces_old[key]}")
            print(f"  New: {surfaces_new[key]}")
    else:
        print(f"Removed unit: {key}")


