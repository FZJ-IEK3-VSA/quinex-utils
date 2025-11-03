# Update unit resources

First, download the required source data:
```bash
cd dev/parsers/update_lookups/raw_data/unit_ontologies
git clone https://github.com/qudt/qudt-public-repo.git
git clone https://github.com/HajoRijgersberg/OM.git
cd ..
wget https://raw.githubusercontent.com/nielstron/quantulum3/refs/heads/dev/quantulum3/units.json
```

Then run the scripts in the following order (you can configure the scripts in their headers):
```bash
python 1_create_unit_lookups.py
python 2_transfer_ambiguous_unit_priorities.py
python 3_optionally_show_unit_disambiguation_stats.py
python 4_add_and_remove_units.py
python 5_show_diff_to_old.py
```

You can manually edit which units to prioritize in case of ambiguities by editing `src/quinex_utils/parsers/static_resources/ambiguous_unit_priorities_curated.json`. The lower the number, the higher the priority (e.g., a unit with priority 1 will be chosen over a unit with priority 2). To not consider a unit, set the priority to None.

If you make changes to the other resources, you can document them in `src/quinex_utils/parsers/scripts/patches`. This lets you automatically re-apply them when you update the resources (e.g., to a new version of QUDT).

TODO: Automatically add ambigous manually added units to the ambigouous units priorities file. For example, having added "c" for "cent", it is now ambigous with "c" for "calorie" and should be added to `ambiguous_unit_priorities_curated.json`.