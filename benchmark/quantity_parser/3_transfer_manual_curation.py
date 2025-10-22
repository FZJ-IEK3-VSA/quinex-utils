import json
import argparse
from copy import deepcopy


parser = argparse.ArgumentParser(description="Transfer manual curation from one results file to another")
parser.add_argument('--source', type=str, required=True,
                    default="benchmark/eval_results_grobid_quantities_corpus_<split>_<date>.json",
                    help="Path to the JSON file with examples and human feedback to transfer from")
parser.add_argument('--target', type=str, required=True,
                    default="benchmark/eval_results_grobid_quantities_corpus_<split>_<later_date>.json",
                    help="Path to the JSON file with examples and human feedback to transfer to")

args = parser.parse_args()
file_1 = args.source
file_2 = args.target

# If set to True, it is ensured that only the same example (same location in same document) is considered for transfer. 
# If set to False, equivalent examples in different locations are also considered for transfer.
only_consider_same_examples = False 

with open(file_1, "r") as f1, open(file_2, "r") as f2:
    data_1 = json.load(f1)
    data_2 = json.load(f2)

# Remove curation.
transfers_count = 0
data_2_wo_manual_curation = deepcopy(data_2)
for category_key_2, category_2_without_manual_curation in data_2_wo_manual_curation.items():
    if category_key_2 != "initial_stats":
        for example_2_wo_manual_curation in category_2_without_manual_curation:
            del example_2_wo_manual_curation["quinex_success_manual_decision"]
            del example_2_wo_manual_curation["error_category"]
            del example_2_wo_manual_curation["quinex_success_auto_validated_based_on_grobid"]
            if not only_consider_same_examples:
                del example_2_wo_manual_curation["source"]

# Now, transfer examples from file_1 to file_2.
for category_key_1, category_1 in data_1.items():
    if category_key_1 != "initial_stats":
        for example_1 in category_1:
            if example_1["quinex_success_manual_decision"] != None:
                example_1_wo_manual_curation = deepcopy(example_1)
                del example_1_wo_manual_curation["quinex_success_manual_decision"]
                del example_1_wo_manual_curation["error_category"]
                del example_1_wo_manual_curation["quinex_success_auto_validated_based_on_grobid"]
                if "comment" in example_1_wo_manual_curation:
                    del example_1_wo_manual_curation["comment"]
                if not only_consider_same_examples:
                    del example_1_wo_manual_curation["source"]

                for category_key_2, category_2_without_manual_curation in data_2_wo_manual_curation.items():                    
                    if category_key_2 != "initial_stats" and example_1_wo_manual_curation in category_2_without_manual_curation:
                        # Could locate example in file_2, transfer curation.
                        if only_consider_same_examples:    
                            overwrite_indices = [category_2_without_manual_curation.index(example_1_wo_manual_curation)]
                        else:
                            overwrite_indices = [i for i, ex_2 in enumerate(category_2_without_manual_curation) if ex_2 == example_1_wo_manual_curation]
                        
                        for overwrite_idx in overwrite_indices:
                            example_2 = data_2[category_key_2][overwrite_idx]
                            if example_2["quinex_success_manual_decision"] != None:
                                # Already curated, do not overwrite.
                                if example_2["quinex_success_manual_decision"] != example_1["quinex_success_manual_decision"]:
                                    if example_2["quinex_success_manual_decision"] == "🟢" and example_1["quinex_success_manual_decision"] == "🟢":
                                        pass
                                    else:
                                        print(f"Warning: Example in {file_2} already has manual curation, but different from {file_1}.")
                                elif example_2["error_category"] != example_1["error_category"]:
                                    print(f"Warning: Example in {file_2} already has error category, but different from {file_1}.")                                    
                                else:
                                    pass 
                            else:
                                example_2["quinex_success_manual_decision"] = example_1["quinex_success_manual_decision"]
                                example_2["error_category"] = example_1["error_category"]
                                if "comment" in example_1:
                                    example_2["comment"] = example_1["comment"]                       
                                transfers_count += 1
                        
                        if only_consider_same_examples:
                            break

# Save the modified examples back to the second file
with open(file_2.removesuffix(".json") + "_transferred_curation.json", "w") as f2:
    json.dump(data_2, f2, ensure_ascii=False, indent=4)

print("Done.")