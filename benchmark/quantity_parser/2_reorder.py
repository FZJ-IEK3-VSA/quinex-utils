import json
import argparse


parser = argparse.ArgumentParser(description="Re-order examples based on human feedback")
parser.add_argument('--path', type=str, required=True,
                    default="benchmark/eval_results_grobid_quantities_corpus_<split>_<date>.json",
                    help="Path to the JSON file with examples and human feedback")
args = parser.parse_args()
path = args.path

with open(path, "r") as f:
    data = json.load(f)

correct = []
false = []
manual_check_required = []
for category, examples in data.items():
    if category == "initial_stats":
        continue
    for example in examples:
        if example["quinex_success_manual_decision"] == "🟢":
            correct.append(example)
        elif example["quinex_success_manual_decision"] == "🔴":
            false.append(example)
        else:
            manual_check_required.append(example)

new_data = {
    "correct": correct,
    "false": false,
    "manual_check_required": manual_check_required,
    "initial_stats": data["initial_stats"]
}

# Save the new data to a file
output_path = path.removesuffix(".json") + "_organized.json"
with open(output_path, "w", encoding="utf8") as f:
    json.dump(new_data, f, indent=4, ensure_ascii=False)
