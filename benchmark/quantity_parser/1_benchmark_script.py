
import os
import json
import argparse
from tqdm import tqdm
from datetime import date
from bs4 import BeautifulSoup, NavigableString, Tag, Comment
from quinex_utils.functions.str2num import str2num
from quinex_utils.functions import normalize_quantity_span
from quinex_utils.functions.extract_quantity_modifiers import GazetteerBasedQuantityModifierExtractor
from quinex_utils.parsers.quantity_parser import FastSymbolicQuantityParser



parser = argparse.ArgumentParser(description="Benchmark script for quinex quantity parser")
parser.add_argument('--split', type=str, choices=['train', 'dev', 'test'], default='train',
                    help="Data split to use ('dev' or 'test')")
parser.add_argument('--results_dir', type=str, 
                    default="benchmark/result_files",
                    help="Directory to save validation results")
parser.add_argument('--save_parser_output', action='store_true',
                    help="Set to just save parser outputs without validation")

args = parser.parse_args()
split = args.split
results_dir = args.results_dir
save_parser_output = args.save_parser_output

if not os.path.exists(results_dir):
    os.makedirs(results_dir)

today = date.today().strftime("%Y-%m-%d")
results_path = os.path.join(results_dir, f"eval_results_grobid_quantities_corpus_{split}_{today}.json")
parser_outputs_path = os.path.join(results_dir, f"parser_outputs_grobid_quantities_corpus_{split}_{today}.json")

QUINEX_TO_GROBID_QUANTITY_TYPES = {
    "single_quantity": "value",
    "range": "interval",
    "list": "list",
    "ratio": "value",
    "unknown": None,
}
GROBID_TO_QUDT_QUANTITY_KINDS = {
    'Fraction': ['DimensionlessRatio'],
    'Concentration': ['MassRatio', 'AmountOfSubstanceConcentration', 'AmountOfSubstancePerUnitVolume'],
    'Frequency': ['Frequency', 'AngularVelocity', 'HeartRate'],
    'Pressure': ['Pressure', 'ForcePerArea', 'MassPerArea'],
    'MagneticInduction': ['MagneticFluxDensity'],
    'WeightRatio': ['DimensionlessRatio'],
    "Power": ['Power', 'ApparentPower', 'SpecificPower', 'ComplexPower'],
    "ElectricConductance": ["Conductance"],
}

def pp_results(g_quantity, result, correct=None):
    """
    Transform the resutls in an output format that allows easy human validation.
    """
    pp_result = {}
    pp_result['source'] = "doc: " + g_quantity['source'] + " | par_idx: " + str(g_quantity['par_idx']) + " | char_offsets: " + str(g_quantity['start_char']) + "-" + str(g_quantity['end_char'])
    pp_result['raw_quantity_surface_wo_qmods'] = g_quantity['quantity_surface']
    pp_result['quantity_surface_w_qmods_extr'] = result["text"]
    pp_result['quantity_type_grobid_vs_quinex'] = str(g_quantity['type']) + " vs. " + result['type']    
    pp_result['nbr_quantities_grobid_vs_quinex'] = str(len(g_quantity["normalized_quantities"]["numeric_values"])) + " vs. " + str(result["nbr_quantities"])
    pp_result['normalized_quantity_grobid_values'] = json.dumps(g_quantity["normalized_quantities"]['numeric_values'])
    pp_result['normalized_quantity_grobid_units'] = json.dumps(g_quantity["normalized_quantities"]['units'])
    pp_result['normalized_quantity_grobid_dates'] = json.dumps(g_quantity["normalized_quantities"]['dates'])
    pp_result['normalized_quantity_quinex_values'] = json.dumps([v["value"] for v in result["normalized_quantities"]])
    pp_result['normalized_quantity_quinex_units'] = json.dumps([(v["prefixed_unit"], v["suffixed_unit"]) for v in result["normalized_quantities"]])
    pp_result['normalized_quantity_quinex_modifiers'] = json.dumps([(v["prefixed_modifier"], v["suffixed_modifier"]) for v in result["normalized_quantities"]])
    pp_result['normalized_quantity_quinex_uncertainty'] = json.dumps([(v["uncertainty_expression_pre_unit"], v["uncertainty_expression_post_unit"]) for v in result["normalized_quantities"]])
    pp_result['normalized_quantity_quinex_separators'] = json.dumps(result["separators"])    
    pp_result['quinex_success_self_assessment'] = result['success']
    pp_result['quinex_success_auto_validated_based_on_grobid'] = correct
    pp_result['quinex_success_manual_decision'] = None
    pp_result['error_category'] = ""
    
    return pp_result


def read_normalized_quantities_from_grobid_quantities_data(tei_dir_path):
    """
    Parses annotated tei xml data from grobid-quantities project to dict
    """
    tei_files = os.listdir(tei_dir_path) 
    grobid_quantities_normalized_quantities = []
    par_idx = -1
    paragraph_texts = []
    for tei in tqdm(tei_files):

        with open(os.path.join(tei_dir_path, tei), "r", encoding="utf8") as f:
            soup = BeautifulSoup(f, "lxml")

        paragraphs = soup.find("text").find_all("p")
        
        for paragraph in paragraphs:            
            par_idx += 1
            cummalative_text = ""
            skip_next = False
            for i, span in enumerate(paragraph.contents):

                if skip_next:
                    skip_next = False
                    continue
                else:
                    skip_next = False

                if type(span) == NavigableString:
                    # Span is a string without annotations
                    cummalative_text += span.text
                elif (type(span) is Comment) or (type(span) is Tag and span.name in ["list", "figure"]):
                    # Ignore lists and figure tags
                    pass
                elif type(span) is Tag and span.name == "measure":
                    # Span is a quanitity annotation, thus parse it.                    
                    num = None
                    unit = None
                    date = None                    
                    nums = []
                    units = []
                    dates = []
                    measure_type = span.attrs.get("type")                    
                    for child in span.children:
                        if type(child) is Tag:
                            if child.name == "num":                                                             
                                num = dict(child.attrs)
                                num["text"] = child.text
                                nums.append(num)
                            elif child.name == "date":                            
                                date = dict(child.attrs)
                                date["text"] = child.text                            
                                dates.append(date)
                            elif child.name == "measure" and child.attrs.get("unit", False):                                
                                unit = dict(child.attrs)
                                unit["text"] = child.text
                                units.append(unit)
                            elif child.name == "measure" and child.attrs['type'] != "value":
                                # Probably unit without a unit.
                                unit = dict(child.attrs)
                                unit["text"] = child.text
                                unit["unit"] = None
                                units.append(unit)

                        elif type(child) in [NavigableString, Comment]:
                            # Ignore whitespace.
                            continue
                        else:
                            print("Investigate!")

                    if (len(dates) > 0 and len(units) == 0 and len(nums) == 0) or (len(units) > 0 and len(nums) == 0):
                        # Ignore dates and standalone units
                        cummalative_text += span.text
                        continue
                    else:
                        # Get char offsets
                        quantity_surface = span.text
                        start_char = len(cummalative_text)
                        cummalative_text += quantity_surface
                        end_char = len(cummalative_text)                    

                        grobid_quantities_normalized_quantities.append(
                            {   
                                "par_idx": par_idx,
                                "source": tei,
                                "quantity_surface": quantity_surface,
                                "start_char": start_char,
                                "end_char": end_char,
                                "type": measure_type,
                                "normalized_quantities": {                                    
                                    "numeric_values": nums,
                                    "units": units,
                                    "dates": dates,
                                }
                            }
                        )
                else:
                    raise Exception("Unknown tag: Adapt code to handle this tag.")
                    
            
            paragraph_texts.append(cummalative_text)

    return paragraph_texts, grobid_quantities_normalized_quantities


def compare_units(quinex_normalized_quantity, grobid_quantity_unit):    
    # Check if the unit surface is correct.
    if grobid_quantity_unit == None: #grobid_quantity["unit"] == None:
        # No unit in grobid-quantities.
        assert quinex_normalized_quantity["suffixed_unit"] is None, "Expected unit to be None"
        assert quinex_normalized_quantity["prefixed_unit"] is None, "Expected unit to be None"
        quinex_parser_correct = True
    else:
        # Got units to compare.
        if quinex_normalized_quantity["suffixed_unit"] != None and quinex_normalized_quantity["prefixed_unit"] == None:
            quinex_unit = quinex_normalized_quantity["suffixed_unit"]
        elif quinex_normalized_quantity["prefixed_unit"] != None and quinex_normalized_quantity["suffixed_unit"] == None:
            quinex_unit = quinex_normalized_quantity["prefixed_unit"]
        elif quinex_normalized_quantity["suffixed_unit"] != None and quinex_normalized_quantity["prefixed_unit"] != None:
            print("Investigate! Both prefixed and suffixed unit found.")
        else:
            # Expected either prefixed or suffixed unit, but got both or none.
            quinex_unit = None

        if quinex_unit == None:
            # Expected unit to be not None
            quinex_parser_correct = False
        else: 
            quinex_unit_surface = quinex_unit["text"] if quinex_unit["text"] != None else quinex_unit["ellipsed_text"]                
            if quinex_unit_surface.removeprefix("-") != normalize_quantity_span(grobid_quantity_unit["text"]):
                # Expected unit surface to match
                quinex_parser_correct = False            
            elif grobid_quantity_unit["unit"] == None:
                if quinex_unit_surface == normalize_quantity_span(grobid_quantity_unit["text"]):
                    if quinex_unit["normalized"] == None:
                        quinex_parser_correct = True
                    elif (grobid_quantity_unit["type"], grobid_quantity_unit["text"], quinex_unit["normalized"]) in [
                        ('VOLUME', 'ml', [('ml', 1, 'http://qudt.org/vocab/unit/MilliL', None)]),
                        ('VOLUME', 'µl', [('μl', 1, 'http://qudt.org/vocab/unit/MicroL', None)]),
                        ('MASS', 'g', [('g', 1, 'http://qudt.org/vocab/unit/GM', None)]),
                        ('ACIDITY', 'pH', [('pH', 1, 'http://qudt.org/vocab/unit/PH', None)]),
                        ('TEMPERATURE', 'K', [('μl', 1, 'http://qudt.org/vocab/unit/MicroL', None)]),
                        ('FREQUENCY', 'MHz', [('MHz', 1, 'http://qudt.org/vocab/unit/MegaHZ', None)])
                    ]:
                        quinex_parser_correct = True
                    else:
                        quinex_parser_correct = None
                else:
                    # Expected normalized unit to be None
                    quinex_parser_correct = False
            elif quinex_unit["normalized"] == None:
                # Expected normalized unit to be not None
                quinex_parser_correct = False
            elif len(quinex_unit["normalized"]) == 1:
                # Check if quantity kind of unit is correct.
                qudt_uri = quinex_unit["normalized"][0][2]                    
                grobid_quantity_kind = "".join([p.capitalize() for p in grobid_quantity_unit["type"].split("_")])
                if quinex_unit["normalized"][0][1] == 1:
                    if any(qk in qudt_quantity_kinds[qudt_uri]["qudt"] for qk in GROBID_TO_QUDT_QUANTITY_KINDS.get(grobid_quantity_kind, [grobid_quantity_kind])):
                        quinex_parser_correct = True
                    else:
                        # Expected quantity kinds to match
                        print("\n\nWarning: Quantity kinds do not match: ", grobid_quantity_kind, " vs. ", qudt_quantity_kinds[qudt_uri]["qudt"])
                        user_feedback = input("Are they equivalent? (y/n): ").strip().lower()
                        if user_feedback == 'y':
                            quinex_parser_correct = True
                        else:
                            # Manual check required.
                            quinex_parser_correct = None                                                
                elif (quinex_unit["normalized"][0][1] == -1 and "Time" in qudt_quantity_kinds[qudt_uri]["qudt"] and grobid_quantity_kind == 'Frequency') \
                    or (grobid_quantity_unit["type"] == 'DENSITY' and grobid_quantity_unit["unit"] == 'm^-2' and quinex_unit["normalized"] ==  [('m -2', -2, 'http://qudt.org/vocab/unit/M', None)]) \
                    or (grobid_quantity_unit["type"] == 'DENSITY' and grobid_quantity_unit["unit"] == 'cm^-3' and quinex_unit["normalized"] ==  [('cm -3', -3, 'http://qudt.org/vocab/unit/CentiM', None)]):
                    # Special case for frequency, which is a time unit with negative exponent.
                    quinex_parser_correct = True
                else:
                    # Manual check required.
                    print("\n\nQuinex unit with negative exponent: ", quinex_unit["normalized"])
                    print("Grobid quantity unit: ", grobid_quantity_unit)
                    user_feedback = input("Are they equivalent? (y/n): ").strip().lower()
                    if user_feedback == 'y':
                        quinex_parser_correct = True
                    else:                        
                        quinex_parser_correct = False
                    
            elif (grobid_quantity_unit["unit"] == 'µg/ml' and quinex_unit["normalized"] == [('μg', 1, 'http://qudt.org/vocab/unit/MicroGM', None), ('ml', -1, 'http://qudt.org/vocab/unit/MilliL', None)]) \
                or (grobid_quantity_unit["unit"] == 'mg/ml' and quinex_unit["normalized"] == [('mg', 1, 'http://qudt.org/vocab/unit/MilliGM', None), ('ml', -1, 'http://qudt.org/vocab/unit/MilliL', None)]) \
                or (grobid_quantity_unit["unit"] == 'kJ/mol' and quinex_unit["normalized"] == [('kJ', 1, 'http://qudt.org/vocab/unit/KiloJ', None), ('mol', -1, 'http://qudt.org/vocab/unit/MOL', None)]) \
                or (grobid_quantity_unit["unit"] == 'm.s^-1' and quinex_unit["normalized"] == [('m', 1, 'http://qudt.org/vocab/unit/M', None), ('s', -1, 'http://qudt.org/vocab/unit/SEC', None)]) \
                or (grobid_quantity_unit["unit"] == 'cm.s^-1' and quinex_unit["normalized"] == [('cm', 1, 'http://qudt.org/vocab/unit/CentiM', None), ('s', -1, 'http://qudt.org/vocab/unit/SEC', None)]) \
                or (grobid_quantity_unit["unit"] == 'km.s^-1' and quinex_unit["normalized"] == [('km', 1, 'http://qudt.org/vocab/unit/KiloM', None), ('s', -1, 'http://qudt.org/vocab/unit/SEC', None)]) \
                or (grobid_quantity_unit["unit"] == 'week' and quinex_unit["normalized"] == [('weeks', 1, 'http://qudt.org/vocab/unit/WK', None)]) \
                or (grobid_quantity_unit["unit"] == 'knot' and quinex_unit["normalized"] == [('knots', 1, 'http://qudt.org/vocab/unit/KN', None)]) \
                or (grobid_quantity_unit["unit"] == 'au.d^-2' and quinex_unit["normalized"] == [("au", 1, "http://qudt.org/vocab/unit/AU", None), ("d", -2, "http://qudt.org/vocab/unit/DAY", None)]) \
                or (grobid_quantity_unit["unit"] == 'mg.m^2' and quinex_unit["normalized"] == [("mg", 1, "http://qudt.org/vocab/unit/MilliGM", None), ("m", -2, "http://qudt.org/vocab/unit/M", None)]) \
                or (grobid_quantity_unit["unit"] == 'g.cm^-3' and quinex_unit["normalized"] == [("g", 1, "http://qudt.org/vocab/unit/GM", None), ("cm", -3, "http://qudt.org/vocab/unit/CentiM", None)]) \
                or (grobid_quantity_unit["type"] == "CONCENTRATION" and grobid_quantity_unit["unit"] == 'M' and quinex_unit["normalized"] == [('M', 1, 'http://qudt.org/vocab/unit/MOL-PER-L', None)]) \
                or (grobid_quantity_unit["type"] == 'DENSITY' and grobid_quantity_unit["unit"] == 'µg.ml⁻¹' and quinex_unit["normalized"] ==  [('μg', 1, 'http://qudt.org/vocab/unit/MicroGM', None), ('ml', -1, 'http://qudt.org/vocab/unit/MilliL', None)]) \
                or (grobid_quantity_unit["type"] == 'DENSITY' and grobid_quantity_unit["unit"] == 'IU.ml⁻¹' and quinex_unit["normalized"] ==  [('IU', 1, 'http://qudt.org/vocab/unit/IU', None), ('ml', -1, 'http://qudt.org/vocab/unit/MilliL', None)]) \
                or (grobid_quantity_unit["type"] == 'DENSITY' and grobid_quantity_unit["unit"] == 'kg/m^3' and quinex_unit["normalized"] ==  [('kg', 1, 'http://qudt.org/vocab/unit/KiloGM', None), ('m', -3, 'http://qudt.org/vocab/unit/M', None)]) \
                or (grobid_quantity_unit["type"] == 'DENSITY' and grobid_quantity_unit["unit"] == 'g.cc^-1' and quinex_unit["normalized"] ==  [('g', 1, 'http://qudt.org/vocab/unit/GM', None), ('cc', -1, 'http://qudt.org/vocab/unit/CentiM3', None)]) \
                or (grobid_quantity_unit["type"] == 'PRESSURE' and grobid_quantity_unit["unit"] == 'kg/mm^2' and quinex_unit["normalized"] ==  [('kg', 1, 'http://qudt.org/vocab/unit/KiloGM', None), ('mm', -2, 'http://qudt.org/vocab/unit/MilliM', None)]) \
                or (grobid_quantity_unit["type"] == 'MAGNETIC_FIELD_STRENGTH' and grobid_quantity_unit["unit"] == 'AT/cm' and quinex_unit["normalized"] ==  [('AT', 1, 'http://qudt.org/vocab/unit/AT', None), ('cm', -1, 'http://qudt.org/vocab/unit/CentiM', None)]) \
                or (grobid_quantity_unit["type"] == 'DENSITY' and grobid_quantity_unit["unit"] == 'grain.m^-2' and quinex_unit["normalized"] ==  [('grains', 1, 'http://qudt.org/vocab/unit/GRAIN', None), ('m', -2, 'http://qudt.org/vocab/unit/M', None)]) \
                or (grobid_quantity_unit["type"] == 'IRRADIANCE' and grobid_quantity_unit["unit"] == 'W.m^-2' and quinex_unit["normalized"] ==  [('W', 1, 'http://qudt.org/vocab/unit/W', None), ('m', -2, 'http://qudt.org/vocab/unit/M', None)]):
                # Correct 
                quinex_parser_correct = True
            else:                                
                print("\n\nQuinex compound unit: ", quinex_unit["normalized"])
                print("Grobid quantity unit: ", grobid_quantity_unit)
                user_feedback = input("Are they equivalent? (y/n): ").strip().lower()
                if user_feedback == 'y':
                    quinex_parser_correct = True
                else:                        
                    quinex_parser_correct = False
        
    return quinex_parser_correct


if split == "dev":
    # Dev set
    tei_dir_path = "benchmark/data/grobid-quantities/quantities/corpus"
    start_idx = 0
    end_idx = 919 # First quarter reserved for training
if split == "dev":
    # Dev set
    tei_dir_path = "benchmark/data/grobid-quantities/quantities/corpus"
    start_idx = 919
    end_idx = None
elif split == "test":
    # Test set
    tei_dir_path = "benchmark/data/grobid-quantities/quantities/evaluation"
    start_idx = 0
    end_idx = None
else:
    raise ValueError("Invalid split. Use 'dev' or 'test'.")

paragraph_texts, grobid_quantities_normalized_quantities = read_normalized_quantities_from_grobid_quantities_data(tei_dir_path)

with open("src/quinex_quantity_parser/static_resources/unit_quantity_kinds.json", "r", encoding="utf8") as f:
    qudt_quantity_kinds = json.load(f)

parser_outputs = []
eval_results = {"correct": [], "false": [], "manual_check_required": []}
quantity_parser = FastSymbolicQuantityParser()
qmod_extractor = GazetteerBasedQuantityModifierExtractor()
for j, g_quantity in tqdm(enumerate(grobid_quantities_normalized_quantities[start_idx:end_idx])):
    
    # =====================================================
    # =            Identify quantity modifiers            =
    # =====================================================
    g_quantity_span = {"start": g_quantity["start_char"], "end": g_quantity["end_char"], "text": g_quantity["quantity_surface"]}
    g_quantity_modifier_spans, g_quantity_spans = qmod_extractor(paragraph_texts[g_quantity["par_idx"]], [g_quantity_span])    
    
    # =====================================================
    # =                  Parse quantity                   =
    # =====================================================
    result = quantity_parser.parse(g_quantity_spans[0]["quantity_with_modifiers"]["text"])        
    
    if save_parser_output:
        parser_outputs.append(result)
        continue

    # =====================================================
    # =              Validate parser output               =
    # =====================================================
    # Check if parsing result matches the grobid-quantities annotations.
    g_quantity["quinex_parser_correct"] = False    
    try:        
        
        # Require at least one normalized quantity.
        assert len(result["normalized_quantities"]) > 0, "Expected at least one normalized quantity."

        # Check if quantity type is correct.
        quantity_type_correct = QUINEX_TO_GROBID_QUANTITY_TYPES.get(result["type"]) == g_quantity["type"]
        if result["type"] not in QUINEX_TO_GROBID_QUANTITY_TYPES:
            g_quantity["quinex_parser_correct"] = None
            print(f"Unknown quantity type: {result['type']}. Manual check required.")
            assert False, "Unknown quantity type. Manual check required."
        
        if len(result["normalized_quantities"]) == 1 and len(g_quantity["normalized_quantities"]["numeric_values"]) == 1:
            # =====================================================
            # =                  Single quantity                  =
            # =====================================================
            grobid_quantity = {
                "numeric_value": g_quantity["normalized_quantities"]["numeric_values"][0],
                "unit": g_quantity["normalized_quantities"]["units"][0] if len(g_quantity["normalized_quantities"]["units"]) > 0 else None,
                "date": g_quantity["normalized_quantities"]["dates"][0] if len(g_quantity["normalized_quantities"]["dates"]) > 0 else None,
            }
            normalized_quantity = result["normalized_quantities"][0]

            # Check if the value surface is correct.            
            assert normalized_quantity["value"]["text"] == grobid_quantity["numeric_value"]["text"]
            
            g_quantity["quinex_parser_correct"] = compare_units(normalized_quantity, grobid_quantity["unit"])     
            assert g_quantity["quinex_parser_correct"], "Expected unit to match"        

        elif len(result["normalized_quantities"]) == 2 and len(g_quantity["normalized_quantities"]["numeric_values"]) == 2:
            # =====================================================
            # =      Two quantities (e.g., interval or list)      =
            # =====================================================
            assert quantity_type_correct, "Expected quantity type to match"

            # Treat quantity is a range.
            lb = result["normalized_quantities"][0]
            ub = result["normalized_quantities"][1]
            g_quantity_lb_unit = g_quantity["normalized_quantities"]["units"][0] if len(g_quantity["normalized_quantities"]["units"]) > 0 else None            
            if len(g_quantity["normalized_quantities"]["units"]) == 0:
                g_quantity_ub_unit = None
            elif len(g_quantity["normalized_quantities"]["units"]) == 1:
                # Only one unit given that applies to both bounds.
                g_quantity_ub_unit = g_quantity_lb_unit
            else:
                # Upper bound has its own unit.
                g_quantity_ub_unit = g_quantity["normalized_quantities"]["units"][1]

            # Check lower bound.
            assert lb["value"]["text"] == normalize_quantity_span(g_quantity["normalized_quantities"]["numeric_values"][0]["text"]), "Expected lower bound surface to match"
            if "atleast" in g_quantity["normalized_quantities"]["numeric_values"][0]:
                assert lb["value"]["normalized"]["numeric_value"] == str2num(g_quantity["normalized_quantities"]["numeric_values"][0]["atleast"]), "Expected lower bound normalized numeric value to match"

            # Check upper bound.
            assert ub["value"]["text"] == normalize_quantity_span(g_quantity["normalized_quantities"]["numeric_values"][1]["text"]), "Expected upper bound surface to match"
            if "atmost" in g_quantity["normalized_quantities"]["numeric_values"][1]:            
                assert ub["value"]["normalized"]["numeric_value"] == str2num(g_quantity["normalized_quantities"]["numeric_values"][1]["atmost"]), "Expected upper bound normalized numeric value to match"

            # Check units of lower bound.
            g_quantity["quinex_parser_correct"] = compare_units(lb, g_quantity_lb_unit)
            assert g_quantity["quinex_parser_correct"], "Expected lower bound unit to match"

            # Check units of upper bound.
            g_quantity["quinex_parser_correct"] = compare_units(ub, g_quantity_ub_unit)
            assert g_quantity["quinex_parser_correct"], "Expected upper bound unit to match"

            g_quantity["quinex_parser_correct"] = True

        else:
            if result["type"] == 'ratio':
                # =====================================================
                # =                       Ratio                       =
                # =====================================================
                print("Manual check required")
                g_quantity["quinex_parser_correct"] = None
                assert False, "Not implemented yet."
            elif g_quantity["type"] == 'interval':
                if len(g_quantity["normalized_quantities"]["numeric_values"]) == 2:
                    if g_quantity["normalized_quantities"]["numeric_values"][0].get("type") == 'base' and g_quantity["normalized_quantities"]["numeric_values"][1].get("type") == "range":
                        # =====================================================
                        # =          Single quantity with tolerance           =
                        # =====================================================
                        # Grobid considers this an interval, but quinex considers it a single quantity with a tolerance.                        
                        if len(result["normalized_quantities"]) == 1:
                            if result["normalized_quantities"][0]['uncertainty_expression_post_unit'] != None:
                                unce_expr = result["normalized_quantities"][0]['uncertainty_expression_post_unit']
                            elif result["normalized_quantities"][0]['uncertainty_expression_pre_unit'] != None:
                                unce_expr = result["normalized_quantities"][0]['uncertainty_expression_pre_unit']
                            else:
                                print("Investigate!")
                                        
                            # Check if the value surface is correct.
                            if unce_expr["normalized"]["type"] == "tolerance":
                                assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == str2num(g_quantity["normalized_quantities"]["numeric_values"][0]["text"])
                                assert unce_expr["normalized"]["value"][1] == str2num(g_quantity["normalized_quantities"]["numeric_values"][1]["text"])
                            else:
                                print("Investigate!")

                            g_quantity["quinex_parser_correct"] = True
                    else:
                        print("Manual check required")
                        g_quantity["quinex_parser_correct"] = None
                        assert False, "Not implemented yet."
                else:
                    print("Manual check required")
                    g_quantity["quinex_parser_correct"] = None
                    assert False, "Not implemented yet."

            elif g_quantity["type"] == 'list':
                # =====================================================
                # =                       List                        =
                # =====================================================
                assert quantity_type_correct, "Expected quantity type to match"
                
                # Check if the list is correctly parsed.
                assert len(result["normalized_quantities"]) == len(g_quantity["normalized_quantities"]["numeric_values"]), "Expected number of normalized quantities to match"
                for i, normalized_quantity in enumerate(result["normalized_quantities"]):
                    assert normalized_quantity["value"]["text"] == normalize_quantity_span(g_quantity["normalized_quantities"]["numeric_values"][i]["text"]), "Expected normalized quantity surface to match"

                if len(g_quantity["normalized_quantities"]["units"]) > 0:
                    print("Manual check required")
                    g_quantity["quinex_parser_correct"] = None
                    assert False, "Not implemented yet."

                g_quantity["quinex_parser_correct"] = True

            else:
                print("Manual check required")
                g_quantity["quinex_parser_correct"] = None
                assert False, "Not implemented yet."

    except AssertionError as e:
        
        if str(e) == "Expected quantity kinds to match":
            print("Investigate!")

        # =================================================================
        # =           Sort result and groundtruth into category           =
        # =           (false, manual check required, or correct)          =
        # =================================================================        
        if g_quantity["quinex_parser_correct"] == None or result["text"].endswith("fold"):
            eval_results["manual_check_required"].append(pp_results(g_quantity, result, correct=None))
        else:
            eval_results["false"].append(pp_results(g_quantity, result, correct=False))
            
        continue  

    if g_quantity["quinex_parser_correct"]:
        eval_results["correct"].append(pp_results(g_quantity, result, correct=True))
    else:
        # This should not happen. Check it.
        raise ValueError("Expected quinex parser to be correct, but it was not.")


if save_parser_output:
    # Save parser outputs to file.
    with open(parser_outputs_path, "w", encoding="utf8") as f:
        json.dump(parser_outputs, f, indent=4, ensure_ascii=False)
    print(f"Parser outputs saved to {parser_outputs_path}.")


# Add stats.
eval_results["initial_stats"] = {
    "nbr_correct": len(eval_results["correct"]),
    "nbr_false": len(eval_results["false"]),
    "nbr_manual_check_required": len(eval_results["manual_check_required"]),    
}

# Save results to file.
result_str = json.dumps(eval_results, indent=4, ensure_ascii=False)
result_str = result_str.replace('\\"', "").replace("[null, null]", "[]").replace("[[], []]", "").replace("[]", "").replace("[]", "")    
with open(results_path, "w", encoding="utf8") as f:
    f.write(result_str)

print("Done.")
