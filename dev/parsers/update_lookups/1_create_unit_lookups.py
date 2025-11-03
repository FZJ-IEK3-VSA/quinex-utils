# Create unit lookups by combining data from QUDT, Wikidata, CQE and OM-2

import re
import sys
import json
import decimal
from pathlib import Path
from copy import deepcopy
from collections import defaultdict
from tqdm import tqdm
from rdflib import Graph
from thefuzz import fuzz
from SPARQLWrapper import SPARQLWrapper, JSON


# =============================================================
# =                       Configuration                       =
# =============================================================
output_dir = Path("src/quinex_utils/parsers/static_resources/")
raw_data_dir = Path("dev/parsers/update_lookups/raw_data/")

# QUDT
qudt_units_path = raw_data_dir / "unit_ontologies/qudt-public-repo/src/main/rdf/vocab/unit/VOCAB_QUDT-UNITS-ALL.ttl"
qudt_currencies_path = raw_data_dir / "unit_ontologies/qudt-public-repo/src/main/rdf/vocab/currency/VOCAB_QUDT-UNITS-CURRENCY.ttl"
save_qudt_iso4217_codes = False

# Wikidata
wikidata_sparql_endpoint = "https://query.wikidata.org/sparql"
debug_mode = False  # If True, only the first 100 units are augmented with Wikidata data as this steps takes the longest.

# OM-2
om_units_path = raw_data_dir / "unit_ontologies/OM/om-2.0.rdf"

# CQE
add_units_from_quantulum_or_cqe = True
use_cqe_instead_of_quantulum = False # If True, use CQE data. If False, use quantulum3 data. Note that CQE is GPL-3.0 licensed while quantulum3 is MIT licensed. 
add_qunantitiy_kinds_from_quantulum_or_cqe = False
quantulum_or_cqe_units_path = raw_data_dir / "units.json"


# =============================================================
# =                    Get QUDT unit data                     =
# =============================================================

# Load unit graph from QUDT.
g = Graph()
g.parse(qudt_units_path, format="turtle")

# Add currency units which are stored in a separate graph since QUDT Release 2.1.26.
g.parse(qudt_currencies_path, format="turtle")

# Query unit information from QUDT.
query = """
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX qudt: <http://qudt.org/schema/qudt/>

SELECT DISTINCT *
WHERE {
  { ?unit a qudt:Unit } UNION { ?unit a qudt:CurrencyUnit }  
  OPTIONAL {?unit qudt:expression ?expression }
  OPTIONAL {?unit qudt:symbol ?symbol }
  OPTIONAL {?unit qudt:ucumCode ?ucumCode }
  OPTIONAL {
    ?unit rdfs:label ?label .
    # langMatches(lang(?label), "en") finds "en" and regional variants such as "en-GB" or "en-US".
    FILTER langMatches(lang(?label), "en")
  }
  OPTIONAL {?unit qudt:iec61360Code ?iec61360Code }
  OPTIONAL {?unit qudt:currencyCode ?iso4217Code }
  OPTIONAL {?unit qudt:omUnit ?om2_id }  
  OPTIONAL {?unit qudt:hasDimensionVector ?dimension_vector }
  OPTIONAL {?unit qudt:hasQuantityKind ?quantity_kind }
  OPTIONAL {?unit qudt:applicableSystem ?applicable_system }  
  OPTIONAL {?unit qudt:conversionOffset ?conversion_offset }  
  OPTIONAL {?unit qudt:conversionMultiplier ?conversion_multiplier }    
  OPTIONAL {?unit qudt:exactMatch ?exactMatch }
  OPTIONAL {?unit qudt:deprecated ?is_deprecated }
}
"""

qres = g.query(query)

unit_dict = {}

for row in tqdm(qres):
    
    qudt_unit_uri = str(row.unit) # URI of current unit

    # Do not add NUM unit, beacuse its ucumCode is "1" which makes problems
    # when parsing quantity in a numeric value and unit.
    if qudt_unit_uri.split("/")[-1] in ["NUM", "COUNT", "UNITLESS"]:
        continue
    
    # Ignore deprecated units.
    if row["is_deprecated"] != None:
        if bool(row["is_deprecated"]) == True:
            continue
        
    if use_https := False:
        qudt_unit_uri.replace("http://", "https://")

    # Check if unit already in dict. If not, add it.
    if unit_dict.get(qudt_unit_uri) == None:
        new_unit = {
            qudt_unit_uri: {
                "expression": [],
                "symbol": [],
                "ucumCode": [],
                "label": [],
                "iso4217Code": [],
                "om2_id": [],
                "dimension_vector": [],
                "quantity_kind": [],
                "applicable_system": [],
                "conversion_offset": [],
                "conversion_multiplier": [],
                "description": [],
                "exactMatch": [],
                "wikidata_preferred_label": [],
                "wikidata_altLabel": [],
                "wikidata_short_name": [],
                "wikidata_symbol": [],
                "wikidata_unicode_character": [],
                "wikidata_tex_command": [],
                "wikidata_om2_id": [],
                "wikidata_description": [],
                "wikidata_ucumCode": [],
                "wikidata_en_wikipedia_article": [],
                "quantulum_or_cqe_surfaces": [],
                "quantulum_or_cqe_symbols": [],
                "quantulum_or_cqe_currency_code": [],
                "quantulum_or_cqe_URI": [],   
                "quantulum_or_cqe_entity": [],
                "om2_label": [],
                "om2_alternative_label": [],
                "om2_symbol": [],
                "om2_alternative_symbol": [],            
                "om2_description": [],                
            }
        }
        unit_dict.update(new_unit)

    # Add unit information to dict.
    for key in [
        "expression",
        "symbol",
        "ucumCode",
        "label",
        "iso4217Code",
        "om2_id",
        "dimension_vector",
        "quantity_kind",
        "applicable_system",
        "conversion_offset",
        "conversion_multiplier",
        "exactMatch",
    ]:
        if row[key] is not None:
            value = str(row[key])
            if key == "om2_id":
                value = value.removeprefix(
                    "http://www.ontology-of-units-of-measure.org/resource/om-2/"
                )            
            if value == "":
                continue                    
            elif value not in unit_dict[qudt_unit_uri][key]:
                unit_dict[qudt_unit_uri][key].append(value)

# =============================================================

if save_qudt_iso4217_codes:
    iso_currency_codes = {}
    for uri, info in unit_dict.items():
        if len(info["iso4217Code"]) == 0:
            continue
        elif len(info["iso4217Code"]) > 1:
            print(f"Warning: More than one ISO 4217 code for {uri}: {info['iso4217Code']}")
        else:
            iso_currency_codes[uri] = info["iso4217Code"][0]

    # Save currency codes lookup.
    path = output_dir / "currency_codes.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(iso_currency_codes, f, indent=4, ensure_ascii=False)


# =============================================================
# =           Enrich with information from Wikidata           =
# =============================================================

def get_results(endpoint_url, query):
    user_agent = "WDQS-example Python/%s.%s" % (
        sys.version_info[0],
        sys.version_info[1],
    )
    # TODO adjust user agent; see https://w.wiki/CX6
    sparql = SPARQLWrapper(endpoint_url, agent=user_agent)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    return sparql.query().convert()

print("Augment with Wikidata data.")

i = 0
for uri, info in tqdm(unit_dict.items()):
    
    if debug_mode:
        i += 1
        if i > 100:
            break
    
    # Filter out some unit surface forms.
    if uri == "http://qudt.org/vocab/unit/Gs":
        continue

    # Create query to get unit via external identifiers.
    identification_satements = []
    qudt_id = uri.removeprefix("http://qudt.org/vocab/unit/")
    identification_satements.append(f'{{ ?unit wdt:P2968 "{qudt_id}" }}')
    for ucum_code in info["ucumCode"]:
        identification_satements.append(f'{{ ?unit wdt:P7825 "{ucum_code}" }}')

    for iso4217_code in info["iso4217Code"]:
        identification_satements.append(f'{{ ?unit wdt:P498 "{iso4217_code}" }}')

    for om2_id in info["om2_id"]:        
        identification_satements.append(f'{{ ?unit wdt:P8769 "{om2_id}" }}')

    unit_identification_query = " UNION ".join(identification_satements)

    query = f"""    
SELECT DISTINCT *
WHERE 
{{
  # Get unit via one of the following external identifiers.
  {unit_identification_query}

  # Get the different denotations of the unit.
  ?unit rdfs:label ?preferred_label .  
  FILTER (lang(?preferred_label) = 'en')
  
  OPTIONAL {{
    ?unit skos:altLabel ?altLabel .
    FILTER (lang(?altLabel) = 'en')
  }}
  
  OPTIONAL {{
    ?unit  wdt:P1813 ?short_name .
    FILTER (lang(?short_name) = 'en')
  }}
  
  OPTIONAL {{
    ?unit wdt:P5061 ?symbol .
    FILTER (lang(?symbol) = 'en')
  }}
  
  OPTIONAL {{
    ?unit wdt:P487 ?unicode_character .    
  }}
  
  OPTIONAL {{
    ?unit wdt:P1993 ?tex_command .    
  }}

  OPTIONAL {{
    ?unit wdt:P8769 ?om2_id .
  }}  

  OPTIONAL {{
    ?unit schema:description ?description .
  }}  

  OPTIONAL {{
    ?unit wdt:P7825 ?ucumCode .
  }}  
  
  OPTIONAL {{
    ?unit ^schema:about ?en_wikipedia_article .
    ?en_wikipedia_article schema:isPartOf <https://en.wikipedia.org/>;
  }}
}}
    """

    results = get_results(wikidata_sparql_endpoint, query)

    # Concatenate results into lists.
    preferred_label = []
    altLabel = []
    short_name = []
    symbol = []
    unicode_character = []
    tex_command = []
    for result in results["results"]["bindings"]:
        # Get URI of unit.
        Q = result["unit"]["value"].removeprefix("https://www.wikidata.org/entity/")                

        # Add labels.
        for key in [
            "preferred_label",
            "altLabel",
            "short_name",
            "symbol",
            "unicode_character",
            "tex_command",
            "om2_id",
            "en_wikipedia_article",
        ]:
            if key in result:
                value = result[key]["value"]            
                if value == "":
                    continue
                if value not in unit_dict[uri]["wikidata_" + key]:
                    # Value is not already in list.
                    if key == 'altLabel':
                        # Correct some mistakes in Wikidata.
                        if uri == "http://qudt.org/vocab/unit/KiloJ" and value == 'J':
                            continue                            
                        elif uri == 'http://qudt.org/vocab/unit/NUM-PER-MicroL' and value == '/mm3':
                            continue
                        elif uri == "http://qudt.org/vocab/unit/HR" and value in ["60 minutes", "sixty minutes"]:
                            continue
                        elif uri.removeprefix("http://qudt.org/vocab/unit/").startswith("Kibi") and value.lower().startswith("kilo"):
                            continue
                        elif uri.removeprefix("http://qudt.org/vocab/unit/").startswith("Tebi") and value.lower().startswith("tera"):
                            continue
                        elif uri.removeprefix("http://qudt.org/vocab/unit/").startswith("Pebi") and value.lower().startswith("peta"):
                            continue                        
                        elif (uri == "http://qudt.org/vocab/unit/KiloCAL" or uri == "http://qudt.org/vocab/unit/KiloCAL_TH") and value == 'kilogram calorie':
                            continue
                    elif key == "symbol" and uri == 'http://qudt.org/vocab/unit/DeciM3-PER-MOL' and value in ['l/mol', 'L/mol']:
                        continue

                    unit_dict[uri]["wikidata_" + key].append(value)


# =============================================================
# =      Enrich with information from quantulum3 or CQE       =
# =============================================================
if add_units_from_quantulum_or_cqe:
    print("Augment with quantulum3 or CQE data.")

    # Load unit dict from CQE.
    with open(quantulum_or_cqe_units_path, "r", encoding="utf-8") as f:
        quantulum_or_cqe_unit_dict = json.load(f)

    # Count the frequency of URIs in the unit dict.
    uri_count = defaultdict(int)
    for unit_key, info in quantulum_or_cqe_unit_dict.items():
        uri_count[info.get("URI", [])] += 1

    # Remove all entries that have a URI that is not unique to prevent wrong matches
    # (e.g., 'Base_pair' is used for both 'base pair' and 'kilo base pair').
    quantulum_or_cqe_unit_dict_unique = deepcopy(quantulum_or_cqe_unit_dict)
    for unit_key, info in quantulum_or_cqe_unit_dict.items():
        if uri_count.get(info.get("URI"), 0) > 1:
            print(f"Remove {unit_key} from quantulum_or_cqe_unit_dict_unique because its URI {info.get('URI')} is not unique.")
            del quantulum_or_cqe_unit_dict_unique[unit_key]

    # Create mappings.
    quantulum_or_cqe_article_unit_map = {}
    quantulum_or_cqe_currency_code_unit_map = {}
    quantulum_or_cqe_label_unit_map = {}
    for unit_key, info in quantulum_or_cqe_unit_dict.items():
        
        # Create a map from CQE URI (which is the end of the URL of the associated article in the English Wikipedia) to unit key.
        wikipedia_article_full_url = "https://en.wikipedia.org/wiki/" + info["URI"]
        if wikipedia_article_full_url not in quantulum_or_cqe_article_unit_map:
            quantulum_or_cqe_article_unit_map.update({wikipedia_article_full_url: [unit_key]})
        else:
            quantulum_or_cqe_article_unit_map[wikipedia_article_full_url].append(unit_key)   

        # Create a map from currency code to unit key.
        if info.get("currency_code") != None:
            if info["currency_code"] not in quantulum_or_cqe_currency_code_unit_map:
                quantulum_or_cqe_currency_code_unit_map.update({info["currency_code"]: [unit_key]})
            else:
                quantulum_or_cqe_currency_code_unit_map[info["currency_code"]].append(unit_key)

        # Create a map from label to unit key.
        for label in info.get("surfaces", []):
            label_ = label.lower()
            if label_ not in quantulum_or_cqe_label_unit_map:
                quantulum_or_cqe_label_unit_map.update({label_: [unit_key]})
            else:
                quantulum_or_cqe_label_unit_map[label_].append(unit_key)

    # First, match on associated Wikipedia article.
    for uri, info in tqdm(unit_dict.items()):
        quantulum_or_cqe_match = None

        # Try to match on Wikipedia article.    
        for wikipedia_article in info["wikidata_en_wikipedia_article"]:
            wiki_article_match = quantulum_or_cqe_article_unit_map.get(wikipedia_article, [])
            if len(wiki_article_match) == 1:
                # Got a match.
                quantulum_or_cqe_match = wiki_article_match[0]        
                break    
        
        # Try to match on currency code.
        if quantulum_or_cqe_match == None:
            for currency_code in info["iso4217Code"]:
                currency_code_match = quantulum_or_cqe_currency_code_unit_map.get(currency_code, [])
                if len(currency_code_match) == 1:
                    # Got a match.
                    quantulum_or_cqe_match = currency_code_match[0]
                    break

            if quantulum_or_cqe_match == None:
                # No match found.
                continue

        # Add CQE information to unit dict.
        quantulum_or_cqe_unit = quantulum_or_cqe_unit_dict[quantulum_or_cqe_match]

        # Assert that British and US units are not mixed.
        if ('uk' in info["label"][0].lower().split(" ") or '(uk)' in info["label"][0].lower() or 'british' in info["label"][0].lower()) \
            and (any('us' in _.lower().split(" ") for _ in  quantulum_or_cqe_unit['surfaces']) \
                or any('(us)' in _.lower().split(" ") for _ in  quantulum_or_cqe_unit['surfaces'])):        
            continue
        elif ('us' in info["label"][0].lower().split(" ") or '(us)' in info["label"][0].lower()) \
            and (any('uk' in _.lower().split(" ") for _ in  quantulum_or_cqe_unit['surfaces'])
            or any('br' in _.lower().split(" ") for _ in  quantulum_or_cqe_unit['surfaces'])
            or any('british' in _.lower().split(" ") for _ in  quantulum_or_cqe_unit['surfaces'])
            or any('(uk)' in _.lower().split(" ") for _ in  quantulum_or_cqe_unit['surfaces'])
            ):        
            continue

        # Filter out some unit surface forms.
        if uri in ["http://qudt.org/vocab/unit/Gs", 'http://qudt.org/vocab/unit/KAT', 'http://qudt.org/vocab/unit/DAY'] \
            or (any('litre' in _.lower() for _ in  quantulum_or_cqe_unit['surfaces']) \
            and any('metre' in _.lower() for _ in  quantulum_or_cqe_unit['surfaces'])):
            # Ask user whether to skip these units.
            answer = None
            while answer not in ["y", "n"]:
                answer = input(f'Do you want to add {quantulum_or_cqe_unit["surfaces"][0]} ({quantulum_or_cqe_unit.get("URI")}) to {uri} ({info["label"][0]})? (y/n): ')
            if answer.lower() == "n":
                continue    
        
        for key in [
            "surfaces",
            "symbols",
            "currency_code",
            "URI",
            "entity",
        ]:        
            if quantulum_or_cqe_unit.get(key) is not None:
                value = quantulum_or_cqe_unit[key]
                if type(value) == str and value != "" and value not in unit_dict[uri]["quantulum_or_cqe_" + key]:
                    unit_dict[uri]["quantulum_or_cqe_" + key].append(value)
                elif type(value) == list:                    
                    for v in value:
                        if v != "" and v not in unit_dict[uri]["quantulum_or_cqe_" + key]:
                            unit_dict[uri]["quantulum_or_cqe_" + key].append(v)          

# =============================================================
# =             Enrich with information from OM-2             =
# =============================================================
om = Graph()
om.parse(om_units_path, format="xml")

print("Augment with OM-2 data.")
for uri, info in tqdm(unit_dict.items()):
    om2_id = info["om2_id"] + info["wikidata_om2_id"]
    om2_id = list(set(om2_id))
    if len(om2_id) == 0:
        continue
    elif len(om2_id) > 1:
        print(f"Warning: More than one OM-2 ID for {uri}: {om2_id}. Skipping unit.")
        continue
        
    query = f"""
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX om: <http://www.ontology-of-units-of-measure.org/resource/om-2/>

    SELECT DISTINCT *
    WHERE {{
        VALUES ?unit {{om:{om2_id[0]}}} 
        OPTIONAL {{
            ?unit rdfs:label ?label
            FILTER (lang(?label) = 'en')
        }}
        OPTIONAL {{
            ?unit om:alternativeLabel ?alternative_label
            FILTER (lang(?alternative_label) = 'en')
        }}
        OPTIONAL {{
            ?unit rdfs:comment ?description 
            FILTER (lang(?comment) = 'en')
        }}
        OPTIONAL {{
            ?unit om:symbol ?symbol             
        }}    
        OPTIONAL {{
            ?unit om:alternativeSymbol ?alternative_symbol
        }}    

        
    }}
    """
    # TODO: Maybe also add om:longcomment

    qres = om.query(query)
    for row in qres:
        # Add unit information to dict.
        for key in [
            "label",
            "alternative_label",
            "description",
            "symbol",
            "alternative_symbol",
        ]:
            if row[key] is not None:
                value = str(row[key])
                if value == "":
                    continue
                elif value not in unit_dict[uri]["om2_" + key]:
                    unit_dict[uri]["om2_" + key].append(value)


# ====================================================================
# =  Combine information from QUDT, Wikidata, quantulum3/CQE and OM  =
# ====================================================================
print("Merge exact matches into a single record.")
unit_dict_copy =  deepcopy(unit_dict)
for uri, info in tqdm(unit_dict_copy.items()):

    # Filter out exact matches that are not in the unit dict because they were deprecated.
    valid_exact_matches = [em for em in info["exactMatch"] if em in unit_dict] 
    if len(valid_exact_matches) > 0:
        # Take the shortest URI as the main URI.
        # If there are multiple URIs with the same length, sort alphabetically.
        exact_match_set = [uri] + valid_exact_matches
        main_uri = sorted(exact_match_set, key=lambda x: (len(x), x))[0]      
        
        # Merge information from exact matches into main URI.
        for exact_match_uri in exact_match_set:
            if exact_match_uri != main_uri:
                # Get unit info if not already moved.
                if unit_dict.get(exact_match_uri) != None:                    
                    # Assure that the conversion multiplier, offset and the dimension vector are equal.
                    if unit_dict[main_uri]["dimension_vector"] == None or unit_dict[exact_match_uri]["dimension_vector"] == None:                        
                        continue
                    if unit_dict[main_uri]["dimension_vector"] != unit_dict[exact_match_uri]["dimension_vector"]:
                        print(f"Warning: The dimension vectors of {main_uri} and {exact_match_uri} do not match.")
                        dimension_vectors = unit_dict[main_uri]["dimension_vector"] + unit_dict[exact_match_uri]["dimension_vector"]
                        if len(dimension_vectors) == 1:
                            print("One unit has no dimension vector. Take the dimension vector of the unit that has one.")
                            dimension_vector = [dimension_vectors[0]]
                        else:
                            continue
                    else:
                        # Dimension vectors are equal.
                        dimension_vector = unit_dict[main_uri]["dimension_vector"]

                    if unit_dict[main_uri]["conversion_offset"] != unit_dict[exact_match_uri]["conversion_offset"]:
                        print(f"Warning: The conversion offsets of {main_uri} and {exact_match_uri} do not match.")
                        conversion_offsets = unit_dict[main_uri]["conversion_offset"] + unit_dict[exact_match_uri]["conversion_offset"]
                        if len(conversion_offsets) == 1:
                            print("One unit has no conversion offset. Take the conversion offset of the unit that has one.")
                            conversion_offset = [conversion_offsets[0]]
                        else:
                            continue     
                    else:
                        # Conversion offsets are equal.
                        conversion_offset = unit_dict[main_uri]["conversion_offset"]
                                         
                    if unit_dict[main_uri]["conversion_multiplier"] != unit_dict[exact_match_uri]["conversion_multiplier"]:                                                
                        print(f"Warning: The conversion multipliers of {main_uri} and {exact_match_uri} do not match.") 
                        # Make sure that rounding the more precise conversion multiplier to the number of decimal places of the less precise conversion multiplier does not change the value.
                        conversion_multipliers = unit_dict[main_uri]["conversion_multiplier"] + unit_dict[exact_match_uri]["conversion_multiplier"]
                        if len(conversion_multipliers) == 1:
                            print("One unit has no conversion multiplier. Take the conversion multiplier of the unit that has one.")
                            conversion_multiplier = [conversion_multipliers[0]]
                        else:
                            conversion_multipliers_ = [float(c) for c in conversion_multipliers]
                            # Get number of decimal places of the less precise conversion multiplier. 
                            # Note that len(conversion_multiplier[1].split(".")[1]) is not used because it does not work for numbers like '3.335641e-10'.
                            nbr_decimal_places = min([abs(decimal.Decimal(c).as_tuple().exponent) for c in conversion_multipliers])
                            if round(conversion_multipliers_[0], nbr_decimal_places) == round(conversion_multipliers_[1], nbr_decimal_places):
                                print("The conversion multiplier with more decimal places is kept.")
                                # Sort conversion multipliers by number of decimal places.
                                conversion_multiplier = sorted(conversion_multipliers, key=lambda x: abs(decimal.Decimal(x).as_tuple().exponent))
                                conversion_multiplier = [conversion_multipliers[-1]]
                            else:
                                continue
                    else:
                        # Conversion multipliers are equal.
                        conversion_multiplier = unit_dict[main_uri]["conversion_multiplier"]


                    exact_match_info = unit_dict.pop(exact_match_uri)

                    # Merge information.                
                    for key in unit_dict[main_uri].keys():
                        if key == "conversion_multiplier":
                            unit_dict[main_uri][key] = conversion_multiplier
                        elif key == "conversion_offset":
                            unit_dict[main_uri][key] = conversion_offset
                        elif key == "dimension_vector":
                            unit_dict[main_uri][key] = dimension_vector
                        else:
                            for el in exact_match_info[key]:
                                if el not in unit_dict[main_uri][key]:
                                    unit_dict[main_uri][key].append(el)

# Reduce to label, description, symbol, ucumCode, and expression.
key_map = {'expression': "symbol",
            'symbol': "symbol",
            'ucumCode': "symbol",
            'label': "label",
            'iso4217Code': "symbol",
            'om2_id': None,
            'dimension_vector': None,
            'quantity_kind': None,
            'applicable_system': None,
            'conversion_offset': None,
            'conversion_multiplier': None,
            'description': None,
            'exactMatch': None,
            'wikidata_preferred_label': "label",
            'wikidata_altLabel': "label",
            'wikidata_short_name': "label",
            'wikidata_symbol': "symbol",
            'wikidata_ucumCode': "symbol",            
            'wikidata_unicode_character': "symbol",
            'wikidata_tex_command': "label",
            'wikidata_om2_id': None,
            'wikidata_description': None,
            'wikidata_en_wikipedia_article': None,
            'quantulum_or_cqe_surfaces': "label",
            'quantulum_or_cqe_symbols': "symbol",
            'quantulum_or_cqe_currency_code': None,
            'quantulum_or_cqe_URI': None,  
            'quantulum_or_cqe_entity': None,
            'om2_label': "label",
            'om2_alternative_label': "label",
            'om2_symbol': "symbol",
            'om2_alternative_symbol': "symbol",
            'om2_description': None,            
  }
print("Remove duplicates and assign to 'label' or 'symbol'.")
reduced_unit_dict = {}
for uri, info in tqdm(unit_dict.items()):
    reduced_unit_dict[uri] = {"label": set(), "symbol": set()}
    for key, values in info.items():
        if key_map[key] is not None:
            for value in values:
                if value == "":
                    continue
                elif key_map[key] == "label" and len(re.sub('[^a-zA-Z]+', '', value)) < 3:
                    # Assume is symbol instead (e.g., in Wikidata the altLabel for ampere is A)
                    reduced_unit_dict[uri]["symbol"].add(value)
                elif key.split("_")[-1] == "ucomCode":
                    # kW.h, kW.h --> kWh, kW.h --> kW h
                    alternatives = {value, value.replace(".", ""), value.replace(".", " ")}
                    reduced_unit_dict[uri][key_map[key]].update(alternatives)            
                else:                    
                    if key == "expression":
                        value = value.removeprefix("\\(").removesuffix("\\)")
                    if key_map[key] == "label":
                        value = value.lower()
                    if "{" in value:
                        # Remove substring in curly brackets.   
                        # TODO: Do not remove exponents like ['\\(C m^{2}\\)']                     
                        # reduced_unit_dict[uri][key_map[key]].add(re.sub(r"\{.*\}", "", value))
                        pass

                    reduced_unit_dict[uri][key_map[key]].add(value)


# =============================================================
# =             Transform into output structures              =
# =============================================================
symbol_lookup = defaultdict(list)
label_lookup = defaultdict(list)
ambiguous_unit_lookup = defaultdict(list)
for uri, surface_forms in reduced_unit_dict.items():

    for symbol in surface_forms["symbol"]:
        if uri not in symbol_lookup[symbol]:
            symbol_lookup[symbol].append(uri)
        if uri not in ambiguous_unit_lookup[symbol]:
            ambiguous_unit_lookup[symbol].append(uri)
            
    for label in surface_forms["label"]:
        if uri not in label_lookup[label.lower()]:
            label_lookup[label.lower()].append(uri)
        if uri not in ambiguous_unit_lookup[label.lower()]:
            ambiguous_unit_lookup[label.lower()].append(uri)
            

# Find ambiguous units.
ambiguous_units = {}
for surface_form, uris in ambiguous_unit_lookup.items():

    # Delete labels with UK for US specific units etc.
    if "us" in re.split('[^a-z]', surface_form.lower()) or "u.s. " in surface_form.lower():
        for uri in uris:
            if "UK" in uri.split("_"):
                uris.remove(uri)

        # Remove units without 'US' if there is a unit with 'US'.
        if any("US" in u.split("_") for u in uris):
            for uri in uris:
                if not "US" in uri.split("_"):
                    uris.remove(uri)
    else:
        for uk in ["uk", "br", "british"]:
            if uk in re.split('[^a-z]', surface_form.lower()):               
                for uri in uris:
                    if "US" in uri.split("_"):
                        uris.remove(uri)

                # Remove units without 'UK' if there is a unit with 'UK'.
                if any("UK" in u.split("_") for u in uris):
                    for uri in uris:
                        if not "UK" in uri.split("_"):
                            uris.remove(uri)

    if "dry" in re.split('[^a-z]', surface_form.lower()):
        for uri in uris:
            # Remove units without 'DRY' if there is a unit with 'DRY'.
            if not "DRY" in uri.split("_") and any("DRY" in u.split("_") for u in uris):
                uris.remove(uri)

    if "nautical" in re.split('[^a-z]', surface_form.lower()):
        for uri in uris:
            # Remove units without 'N' if there is a unit with 'N'.
            if not "N" in uri.split("_") and any("N" in u.split("_") for u in uris):
                uris.remove(uri)
    
    if "nmi" == surface_form.lower() and "http://qudt.org/vocab/unit/MI" in uris:        
        uris.remove("http://qudt.org/vocab/unit/MI")    
    elif "a_t" == surface_form.lower() and "http://qudt.org/vocab/unit/YR" in uris:
        uris.remove("http://qudt.org/vocab/unit/YR") 
    elif "thermochemical kilocalorie" == surface_form.lower() and "http://qudt.org/vocab/unit/KiloCAL" in uris:
        uris.remove("http://qudt.org/vocab/unit/KiloCAL")
    elif "n/mm²" == surface_form.lower() and "http://qudt.org/vocab/unit/MegaPA" in uris:
        uris.remove("http://qudt.org/vocab/unit/MegaPA")
    
    if "it" in re.split('[^a-z]', surface_form.lower()):
        for uri in uris:
            # Remove units with 'TH' instead of 'IT' if there is a unit with 'IT'.
            if "_TH-" in uri and not "_IT-" in uri and any("_IT-" in u for u in uris):
                uris.remove(uri)

    if "th" in re.split('[^a-z]', surface_form.lower()):
        for uri in uris:
            # Remove units with 'IT' instead of 'TH' if there is a unit with 'TH'.
            if "_IT-" in uri and not "_TH-" in uri and any("_TH-" in u for u in uris):
                uris.remove(uri)              

    if len(uris) > 1:
        # Sort uris by lowest Levenshtein distance with surface form. If there is a tie, take the one with the shortest URI.
        uris = sorted(uris, reverse=True, key=lambda x: (fuzz.ratio(x.removeprefix('http://qudt.org/vocab/unit/').lower(), surface_form), -len(x)))

        # Add to ambiguous units.
        ambiguous_units.update({surface_form: {uri: i + 1 for i, uri in enumerate(uris)}})

# Get dimension vector and quantity kind information in isolation.
unit_dimensions_and_kinds = {}
for uri, info in unit_dict.items():
    unit_dimensions_and_kinds[uri] = {"dimension_vector": [], "applicable_system": [], "conversion_multiplier": None, "conversion_offset": None, "is_currency": False}

    # Get dimension vector from QUDT.
    dimension_vectors = info.get("dimension_vector", [])
    if len(dimension_vectors) == 1:
        unit_dimensions_and_kinds[uri]["dimension_vector"] = dimension_vectors[0].removeprefix("http://qudt.org/vocab/dimensionvector/")
    elif len(dimension_vectors) > 1:
        raise ValueError("Assumed a single dimension vector per unit, but got multiple for {}.".format(uri))
    
    # Get conversion multiplier from QUDT.
    conversion_multiplier = info.get("conversion_multiplier", [])
    if len(conversion_multiplier) == 1:
        unit_dimensions_and_kinds[uri]["conversion_multiplier"] = float(conversion_multiplier[0])
    elif len(conversion_multiplier) > 1:
        raise ValueError("Assumed a single conversion multiplier per unit, but got multiple for {}.".format(uri))

    # Get dimension vector from QUDT.
    conversion_offset = info.get("conversion_offset", [])
    if len(conversion_offset) == 1:
        unit_dimensions_and_kinds[uri]["conversion_offset"] = float(conversion_offset[0])
    elif len(conversion_offset) > 1:
        raise ValueError("Assumed a single conversion offset per unit, but got multiple for {}.".format(uri))

    # Get applicable system from QUDT.
    applicable_systems = info.get("applicable_system", [])
    applicable_systems = [s.removeprefix("http://qudt.org/vocab/sou/") for s in applicable_systems] 
    unit_dimensions_and_kinds[uri]["applicable_system"] = applicable_systems

    # Get quantity kind from QUDT.
    quantity_kinds = info.get("quantity_kind", [])
    if "http://qudt.org/vocab/quantitykind/Currency" in quantity_kinds:
        unit_dimensions_and_kinds[uri]["is_currency"] = True

# Get ucum codes lookup.
ucum_codes_lookup = {}
for uri, info in unit_dict.items():
    ucum_codes_lookup[uri] = info.get("ucumCode", [])

# Get quantity kind lookup.
unit_quantity_kinds = {}
for uri, info in unit_dict.items():
    # Get quantity kind from QUDT.
    qudt_quantity_kinds = [qk.removeprefix("http://qudt.org/vocab/quantitykind/") for qk in info.get("quantity_kind", [])]    

    if add_units_from_quantulum_or_cqe and add_qunantitiy_kinds_from_quantulum_or_cqe:
        # Get quantity kind from CQE.
        quantulum_or_cqe_entity = info.get("quantulum_or_quantulum_or_cqe_entity", [])    
        quantulum_or_cqe_entity = quantulum_or_cqe_entity[0] if len(quantulum_or_cqe_entity) == 1 else None
        # Add to lookup.
        unit_quantity_kinds[uri] = {"qudt": qudt_quantity_kinds, "quantulum_or_cqe": quantulum_or_cqe_entity}
    else:
        unit_quantity_kinds[uri] = {"qudt": qudt_quantity_kinds}

# =============================================================
# =                    Save as JSON files                     =
# =============================================================

# Save ucum codes lookup.
path = output_dir / "ucum_codes.json"
with open(path, "w", encoding="utf-8") as f:
    json.dump(ucum_codes_lookup, f, indent=4, ensure_ascii=False)

# Save dimension vector and quantity kind information dictionary.
path = output_dir / "unit_dimensions_and_kinds.json"
with open(path, "w", encoding="utf-8") as f:
    json.dump(unit_dimensions_and_kinds, f, indent=4, ensure_ascii=False)

# Save quantity kind lookup.
path = output_dir / "unit_quantity_kinds.json"
with open(path, "w", encoding="utf-8") as f:
    json.dump(unit_quantity_kinds, f, indent=4, ensure_ascii=False)

# Save ambiguous units dictionary.
path = output_dir / "ambiguous_unit_priorities_raw.json"
with open(path, "w", encoding="utf-8") as f:
    json.dump(ambiguous_units, f, indent=4, ensure_ascii=False)

# Save symbol lookup dictionary.
path = output_dir / "unit_symbol_lookup.json"
with open(path, "w", encoding="utf-8") as f:
    json.dump(symbol_lookup, f, indent=4, ensure_ascii=False)

# Save label lookup dictionary.
path = output_dir / "unit_label_lookup.json"
with open(path, "w", encoding="utf-8") as f:
    json.dump(label_lookup, f, indent=4, ensure_ascii=False)

print("Finished")
