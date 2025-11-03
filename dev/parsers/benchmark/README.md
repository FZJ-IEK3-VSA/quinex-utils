# Benchmark on grobid-quantities corpus

Run benchmark script on train, dev, or test set
```bash
python 1_benchmark_script.py --split dev
```
This will compare the results of the quantity parser to the annotations in the grobid-quantities corpus and mark them as either correct, false, or requiring manual check.

However, the automatic classification is not perfect and requires manual curation, in particular where the automatic classification marked the result as requiring manual check.

Curate the pre-categorized results by opening the result file `result_files/eval_results_grobid_quantities_corpus_<split>_<date>.json` and for each example set `quinex_success_manual_decision` to either "🟢" (correct), "🔴" (false), "🟡" (leaning towards correct), and "🟠" (leaning towards false). For examples, that are false or rather false, also set the `error_category` field to one or more of the following categories or add a new category:
- pdf_parsing_error
- non-english language
- unexpected quantity expression (not considered quantity in quinex)
- value rules not elaborate enough (str2num wrong)
- value rules not elaborate enough (unexpected value surface form)
- cannot distinguish between units and garbage
- qudt unit linking not elaborate enough (rules not elaborate enough)
- qudt unit linking not elaborate enough (unit not known due to prefix)
- qudt unit linking not elaborate enough (unit only apparent from context)
- qudt unit linking not elaborate enough (e.g., molecules as unit in 'molecules/s')
- qudt unit linking not elaborate enough (hard-coded disambiguation)
- qudt unit linking not elaborate enough (unit not known)
- qudt unit linking not elaborate enough (surface form not in gazetteer)
- qudt unit linking not elaborate enough (scoping)
- quantity rules not elaborate enough (rules not elaborate enough)
- quantity rules not elaborate enough (quantity modifier not in gazetteer)
- quantity rules not elaborate enough (unknown imprecise quantity)
- quantity rules not elaborate enough (no reverse unit ellipsis resolution)
- quantity rules not elaborate enough (unexpected quantity surface form)
- quantity rules not elaborate enough (wrong segmentation)
- quantity rules not elaborate enough (unexpected quantity surface form, complex list)
- quantity rules not elaborate enough (range and not list from context)
- quantity rules not elaborate enough (constants not considered)

Re-order examples based on manual curation
```bash
python 2_reorder.py 
```

Optionally, transfer manual curation to another results file (e.g., if you re-ran the benchmark script after making changes to the parser)
```bash
python 3_transfer_manual_curation.py --source <path_to_source_file> --target <path_to_target_file>
```
This will create a copy of the target file with suffix `_transferred_curation`.

Analyze results files and print summary statistics.
```bash
python 4_analyze_results_files.py
```
The results summary is saved to `result_files/analysis_results_<date>.md`