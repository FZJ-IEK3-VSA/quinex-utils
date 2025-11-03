import os
import json
import argparse 
from datetime import datetime
from collections import defaultdict
import pandas as pd

# Set arguments.
parser = argparse.ArgumentParser(description="Analyze eval result files")
parser.add_argument('--results_dir', type=str, 
                    default="benchmark/quantity_parser/result_files",
                    help="Directory to save validation results")
args = parser.parse_args()
result_dir = args.results_dir

# Get all results files in dir.
results_files = []
for file in os.listdir(result_dir):
    if file.startswith("eval_results_") and file.endswith(".json"):
        results_files.append(os.path.join(result_dir, file))

analysis_results = []
analysis_results_err = []
for results_file in results_files:
    print("############################################")
    print(f"        Results for {results_file}:        ")
    print("############################################")

    with open(results_file, "r") as f:
        data = json.load(f)

    # Print the number of examples in each category
    print("\nNumber of examples in each category:")
    for key, examples in data.items():
        if key == "initial_stats":
            continue
        print(f"- {key}: {len(examples)} examples")

    # Make sure all examples are organized correctly.
    assert all(e["quinex_success_manual_decision"] in ["🟢", "🟡"] for e in data["correct"])
    assert all(e["quinex_success_manual_decision"] in ["🔴", "🟠"] for e in data["false"])
    assert list(data.keys()) == ["correct", "false", "initial_stats"]

    # Analyze failure modes in the false examples.
    error_categories = defaultdict(int)
    for example in data["false"]:
        assert example["error_category"] != ""
        error_categories[example["error_category"]] += 1

    print("\nError categories:")
    # Sort
    error_categories = dict(sorted(error_categories.items(), key=lambda item: item[1], reverse=True))
    for category, count in error_categories.items():
        print(f"- {category}: {count} examples")

    # Calculate accuracy.
    accuracy = len(data["correct"]) / (len(data["correct"]) + len(data["false"]))
    print(f"\nAccuracy: {accuracy:.2%}")

    # Calculate accuracy ignoring examples of certain error categories.
    ignore_examples_of_error_category = ["unexpected quantity expression (not considered quantity in quinex)", "non-english language"]
    count_ignored_examples = sum(count for category, count in error_categories.items() if category in ignore_examples_of_error_category)
    accuracy_without_ignored = len(data["correct"]) / (len(data["correct"]) + len(data["false"]) - count_ignored_examples)
    print(f"Accuracy without ignored examples: {accuracy_without_ignored:.2%}")

    # Check performance of self-assessment
    # We only count success=True as success. Both success=False and success=None (that is, basically asking for human feedback) are counted as failure.
    self_assessment_true_negative = sum(1 for example in data["false"] if example["quinex_success_self_assessment"] in [False, None])
    self_assessment_true_positive = sum(1 for example in data["correct"] if example["quinex_success_self_assessment"] is True)
    self_assessment_false_positive = sum(1 for example in data["false"] if example["quinex_success_self_assessment"] is True)
    self_assessment_false_negative = sum(1 for example in data["correct"] if example["quinex_success_self_assessment"] in [False, None])
    assert len(data["false"]) == self_assessment_true_negative + self_assessment_false_positive 
    assert len(data["correct"]) == self_assessment_true_positive + self_assessment_false_negative
    
    self_assessment_calling_for_human_feedback_in_negatives = sum(1 for example in data["false"] if example["quinex_success_self_assessment"] is None)
    self_assessment_calling_for_human_feedback_in_positives = sum(1 for example in data["correct"] if example["quinex_success_self_assessment"] is None)    

    # Calculate precision and recall.
    self_assessment_precision = self_assessment_true_positive / (self_assessment_true_positive + self_assessment_false_positive)
    self_assessment_recall = self_assessment_true_positive / (self_assessment_true_positive + self_assessment_false_negative)
    self_assessment_f1 = 2 * (self_assessment_precision * self_assessment_recall) / (self_assessment_precision + self_assessment_recall)
    
    print(f"\nSelf-assessment results (assumption: Count asking for human feedback as false):")
    print(f"- True negatives: {self_assessment_true_negative}")
    print(f"- False negatives: {self_assessment_false_negative}")
    print(f"- True positives: {self_assessment_true_positive}")     
    print(f"- False positives: {self_assessment_false_positive}")
    print(f"- Calling for human feedback in negatives: {self_assessment_calling_for_human_feedback_in_negatives}")
    print(f"- Calling for human feedback in positives: {self_assessment_calling_for_human_feedback_in_positives}")
    print(f"- Precision: {self_assessment_precision:.2%}")
    print(f"- Recall: {self_assessment_recall:.2%}")
    print(f"- F1 score: {self_assessment_f1:.2%}")

    # Prepare results for DataFrame.
    row = {
            "file": results_file,        
            "accuracy": f"{accuracy_without_ignored:.2%}",
            "num_examples": len(data["correct"]) + len(data["false"]),
            "num_correct": len(data["correct"]),
            "num_false": len(data["false"]),
            "self_assessment_precision": f"{self_assessment_precision:.2%}",
            "self_assessment_recall": f"{self_assessment_recall:.2%}",
            "self_assessment_f1": f"{self_assessment_f1:.2%}",         
        }    
    analysis_results.append(row)
    analysis_results_err.append(error_categories)

all_unique_error_categories = set()
for error_categories in analysis_results_err:
    all_unique_error_categories.update(error_categories.keys())

# Add missing error categories.
for error_categories in analysis_results_err:
    for category in all_unique_error_categories:
        if category not in error_categories:
            error_categories[category] = 0

# Sort by sum of error counts across all results.
error_categories_sums = {category: sum(error_categories[category] for error_categories in analysis_results_err) for category in all_unique_error_categories}
analysis_results_err_ = []
for error_categories in analysis_results_err:
    error_categories = sorted(error_categories.items(), key=lambda key_and_count: error_categories_sums[key_and_count[0]], reverse=True)
    analysis_results_err_.append(dict(error_categories))    

# Add percentage to error counts.
add_percentages = True
if add_percentages:
    for error_categories in analysis_results_err_:
        total = sum(error_categories.values())
        for category in error_categories:
            error_categories[category] = f"{error_categories[category]} ({error_categories[category] / total:.2%})"        

# Add error counts to results.
for analysis_result, err_counts in zip(analysis_results, analysis_results_err_):
    analysis_result.update(err_counts)

# Make a DataFrame for the results.
df = pd.DataFrame(analysis_results)

if not add_percentages:
    # Make all columns that are in error categories of int type.
    for column in df.columns:
        if column not in ["file", "accuracy"]:
            df[column] = df[column].astype(int)

# Make LaTeX table.
df = df.T
latex_table = df.to_latex(index=True, float_format="%.2f", escape=True)
print(latex_table)

today = datetime.now().strftime("%Y-%m-%d")
result_path = os.path.join(result_dir, f"analysis_results_{today}.md")
df.to_markdown(result_path, index=True)

print("Done.")