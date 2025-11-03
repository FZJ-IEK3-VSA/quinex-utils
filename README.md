<a href="https://www.fz-juelich.de/en/ice/ice-2"><img src="https://github.com/FZJ-IEK3-VSA/README_assets/blob/main/JSA-Header.svg?raw=True" alt="Forschungszentrum Juelich Logo" width="175px"></a>

# NLP Utilities for Processing Quantities, Numbers, and Units
A collection of utilities for natural language processing (NLP) tasks that involve quantities, numbers, and units.


## Features

* **Rule-based quantity parser**
    * Various writing styles of quantities
    * Single quantities, lists, intervals, ratios, and multidimensional quantities
    * Imprecise quantities (e.g., 'a few km')
    * Parses simple uncertainty expressions (e.g., tolerances, standard deviations, and confidence intervals)
    * Resolves ellipses of units and order of magnitudes
    * Uses unit parser with features below
    * Lookups for imprecise quantities, number words, etc. can be customized
* **Rule-based unit parser**
    * Links units to the QUDT ontology
    * Attempts to find a single QUDT unit for compound units
    * Handles unknown compound units
    * Unit symbol and label lookups can be customized     
* **Quantity modifer extraction based on dictionary-matching**
    * Lists of considered quantity modifiers can be customized
* **str2num** converts number strings to a numeric datatype and accounts
for mamy different ways numbers can be expressed in:
    * cardinals (e.g., "27")
    * ordinals (e.g., "27." or "27th")
    * fractions (e.g., "1/27")
    * with suffixes (e.g., "27-year")
    * spelled out (e.g., "twenty-seven")
    * with different thousands separators (e.g., "1'234" vs. "1234")
    * powers of ten (e.g., "2.7×10^6" or "2.6M" or "2.6 million")
    * etc.
* **Lookup tables** for number words, imprecise quantities, quantity modifiers, physical constants, currencies
* **REGEX patterns** to identify numbers in text


## Installation

Create and activate a virtual environment.<br>
Then, install the package via pip and download the spaCy pipeline.
```bash
pip install quinex-utils
python3 -m spacy download en_core_web_md
```


## Usage

Convert numbers from strings to numeric data types
```python
>>> from quinex_utils.functions import str2num

>>> num = str2num("3.23 10^3")
3230

>>> num = str2num("one million")
1e6
```

Use REGEX patterns 
```python
>>> from quinex_utils.src.quinex_utils.patterns.imprecise_quantities import IMPRECISE_VALUE_PATTERN

>>> IMPRECISE_VALUE_PATTERN.findall("They harvested a few apples and oodles of blueberries.")
["a few", "oodles"]
```

Use boolean checks
```python
>>> from quinex_utils.functions.boolean_checks import contains_any_number

>>> if contains_any_number("..."):
>>>     ...
```

Use lookups 
```python
>>> from quinex_utils.lookups.physical_constants import PHYSICAL_CONSTANTS 

>>> string = "..."
>>> if any(c.lower() in string.lower() for c in PHYSICAL_CONSTANTS)
>>>     ...
```

Parse unit strings
```python
>>> from quinex_utils.parsers.unit_parser import FastSymbolicUnitParser
>>> unit_parser = FastSymbolicUnitParser()
>>> unit_parser.parse("$2021/kWh")
[
    ('$', 1, 'http://qudt.org/vocab/currency/USD', 2021),
    ('kWh', -1, 'http://qudt.org/vocab/unit/KiloW-HR', None)
]
```

Parse quantity strings
```python
>>> from quinex_utils.parsers.quantity_parser import FastSymbolicQuantityParser
>>> quantity_parser = FastSymbolicQuantityParser()
>>> quantity_parser.parse("above -120.123/-5 to 10.3 * 10^5 TWh kg*s^2/(m^2 per year)^3 at least")
{
    'nbr_quantities': 2,
    'normalized_quantities': [
        {
            'prefixed_modifier': {'normalized': '>', 'text': 'above'},
            'prefixed_unit': None,
            'value': {
                'normalized': {'is_imprecise': False, 'numeric_value': 2402460.0},
                'text': '-120.123/-5'
                }
            'suffixed_modifier': {'normalized': None, 'text': None},
            'suffixed_unit': {
                'ellipsed_text': 'TWh kg*s^2/(m^2 per year)^3',
                'normalized': [
                    ('TWh', 1, 'http://qudt.org/vocab/unit/TeraW-HR', None),
                    ('kg', 1, 'http://qudt.org/vocab/unit/KiloGM', None),
                    ('s', 2, 'http://qudt.org/vocab/unit/SEC', None),
                    ('m', -6, 'http://qudt.org/vocab/unit/M', None),
                    ('year', 3, 'http://qudt.org/vocab/unit/YR', None)],
                'text': None
                },
        },
        {
            'prefixed_modifier': {'normalized': None, 'text': None},
            'prefixed_unit': None,
            'value': {
                'normalized': {'is_imprecise': False, 'numeric_value': 1030000.0000000001},
                'text': '10.3 * 10^5'
                }
            'suffixed_modifier': {'normalized': '>=', 'text': 'at least'},
            'suffixed_unit': {
                'ellipsed_text': None,
                'normalized': [
                    ('TWh', 1, 'http://qudt.org/vocab/unit/TeraW-HR', None),
                    ('kg', 1, 'http://qudt.org/vocab/unit/KiloGM', None),
                    ('s', 2, 'http://qudt.org/vocab/unit/SEC', None),
                    ('m', -6, 'http://qudt.org/vocab/unit/M', None),
                    ('year', 3, 'http://qudt.org/vocab/unit/YR', None)],
                'text': 'TWh kg*s^2/(m^2 per year)^3'
                },
            }],
    'separators': [('to', 'range_separator')],
    'success': True,
    'text': 'above -120.123/-5 to 10.3 * 10^5 TWh kg*s^2/(m^2 per year)^3 at least',
    'type': 'range'
}
```

Convert quantities from one unit to another (this is an experimental feature)
```python
from quinex_utils.parsers.unit_parser import FastSymbolicUnitParser

unit_parser = FastSymbolicUnitParser()
value = 9.5
from_unit = unit_parser.parse("kWh/kg")
to_unit = unit_parser.parse("MJ/kg")
conv_value, conv_unit = unit_parser.unit_conversion(
                    value=from_value,
                    from_compound_unit=from_unit,
                    to_compound_unit=convert_to,
                )
```

You can adjust for inflation and exchange rates when converting currency.
```python
value = 56
from_unit = unit_parser.parse("€/kWh")
to_unit = unit_parser.parse("$_2025/kWh")
conv_value, conv_unit = unit_parser.unit_conversion(
                    value=from_value,
                    from_compound_unit=from_unit,
                    to_compound_unit=convert_to,
                    from_default_year=2020,
                    to_default_year=2025,
                )
```


## Rule-based quantity and unit parsers

Parses strings such as '3 m/s', '16-20.000 Hz', '4,186 kJ/(kg·K)', or 'five kilograms' to structured data.

The quantity parser dissects quantity strings into individual quantities and their components (i.e., numeric values, units, and modifiers). The type of the quantity expression is determined (i.e., single quantity, lists, intervals, ratios, and multidimensional quantities) and values, units
and modifiers are normalized. Values are normalized to numeric datatypes if applicable. Units are parsed and normalized using a rule-based unit parser that links units to their corresponding QUDT unit class. Rather than dividing compound units into their smallest parts, the aim is to return as few parts as possible, ideally a single QUDT class.


### Please note

> [!IMPORTANT]
> The functions are not fully tested and should not be used in high-stakes or safety-critical applications without careful validation and verification.

* Short scale is assumed (e.g., a billion is interpretated as 10⁹ and not 10¹²)
* '-' and '+' are not considered quantity modifiers but directly included in the quantity span. However, 'minus' and 'negative' are considered quantity modifiers. Hence, for '-5%' the numeric value would be -5 and the quantity modifier empty, but for 'minus 5%' the numeric value would be 5 and the normalized quantity modifier '-'.
* Third, fourth, fifth, etc. are interpreted as ordinals and not as fractions unless they are preceded by a number word smaller than twenty (e.g., "one third" is 1/3 and "twenty third" is 23th)
* No floating-point arithmetic error mitigation (e.g., '10.3 \* 10^5' is normalized to 1030000.0000000001).
* As the maximum integer value is unbounded in Python 3, the parser's result has no length limit, however, floats larger sys.float_info.max are normalized to inf.
* The result of quantity parser depends on quantity modifier detection. For example, '25 and 30 km/h' will be interpretated as a list of quantities, whereas 'between 25 and 30 km/h' will be interpretated as a quantity range.


### Limitations

* Only English-language support
* Unit disambiugations based on hard-coded priorities without considering context
* Only adjacent quantity modifiers considered
* Cannot deal well with OCR errors or spelling mistakes
* Cannot deal with unit modifiers (e.g., CO2 in "kgCO2") 
* Cannot deal with quantity expressions containing additional information (e.g., italy and spain in "2 million (italy) to 5 million (spain)")
* Repeating units will be detected twice (e.g., in 'kilometers per hour (km/h)')
* Constants like speed of light in vacuum not considered
* Cannot distinguish between ordinals and fractions based on context (e.g., fourth could be 1/4 or 4th)
* The unit lookups may contain errors, as they have been automatically compiled form different sources
* In particular, cents could be incorrectly mapped to a currency without considering its order of magnitude
* Unit converstion is an experimental feature and may return incorrect results in some cases
* Can only perform unit ellipses resolution for suffixed and not prefixed units (e.g., for "10, 20, and 30 km/h" but not for "EUR 10, 20, and 30")
* OCR and spelling errors matter (e.g., '6.5 EUR/kW h' will be parsed to EUR.kW-1.h not EUR.kW-1.h-1, and '0.8 −0.3' will be normalized to 0.5)


### Evaluation

We evaluated a previous version of the parser on the Grobid-quantities test set (see `quinex_utils/benchmark/quantity_parser`).
The results are summerized in the Appendix of our paper *Quinex: Quantitative Information Extraction from Text using Open and Lightweight LLMs* (search for "rule-based quantity parser"). Since then we updated the unit lookups and fixed some minor bugs, but we have not yet performed a new evaluation.


### Update unit lookups

You can update the unit lookups by following the instruction in [`src/quinex_utils/parsers/scripts/README.md`](src/quinex_utils/parsers/scripts/README.md).


## Contents

* **Lookups**
    * Number words
    * Imprecise quantities
    * Quantity modifiers
    * Physical constants
    * Character mapping
* **Patterns**
    * Contains
    * Imprecise quantities
    * Number words
    * Number
    * Numeric value
    * Order of magnitude
    * Split
* **Parsers**
    * Unit parser
    * Quantity parser
* **Functions**
    * boolean_checks
        * contains_any_number
        * is_imprecise_quantity
        * is_relative_quantity
        * is_small_int
    * normalize
        * normalize_unicode_string
        * normalize_unit_span
        * normalize_num_span
        * normalize_quantity_span
        * rectify_quantity_annotation
    * num2str
        * num2str
        * get_fraction_str
        * get_number_spellings
        * get_digit_notations
    * str2num
        * str2num
            * cast_str_as_int
            * cast_str_as_float
            * cast_str_as_fraction_sum
            * cast_str_as_number_words
            * cast_str_as_num_with_order_of_magnitude
            * cast_str_as_math_expr
            * cast_str_as_digits_and_number_words
            * cast_str_as_power
    * Units
        * remove_exponent_from_ucum_code_of_single_unit


## Contribute

We welcome contributions.

## License
This project is licensed under the MIT License -- see the [LICENSE](LICENSE) file for details.

The unit lookups in `src/quinex_utils/parsers/static_resources/` are compiled from the following sources:
* [QUDT](https://github.com/qudt/qudt-public-repo) (CC BY 4.0 license)
* [Wikidata](https://www.wikidata.org) (CC0 license)
* [OM](https://github.com/HajoRijgersberg/OM) (CC BY 4.0 license)
* [quantulum3](https://github.com/nielstron/quantulum3) (MIT licensed)


## Citation

If you use quinex in your research, please cite the following paper:

```bibtex
@article{quinex2025,
    title = {{Quinex: Quantitative Information Extraction from Text using Open and Lightweight LLMs}},	
    author = {Göpfert, Jan and Kuckertz, Patrick and Müller, Gian and Lütz, Luna and Körner, Celine and Khuat, Hang and Stolten, Detlef and Weinand, Jann M.},
    month = okt,
    year = {2025},
}
```


## About Us 

<a href="https://www.fz-juelich.de/en/ice/ice-2"><img src="https://github.com/FZJ-IEK3-VSA/README_assets/blob/main/iek3-square.png?raw=True" alt="Institute image ICE-2" width="280" align="right" style="margin:0px 10px"/></a>

We are the <a href="https://www.fz-juelich.de/en/ice/ice-2">Institute of Climate and Energy Systems (ICE) - Jülich Systems Analysis</a> belonging to the <a href="https://www.fz-juelich.de/en">Forschungszentrum Jülich</a>. Our interdisciplinary department's research is focusing on energy-related process and systems analyses. Data searches and system simulations are used to determine energy and mass balances, as well as to evaluate performance, emissions and costs of energy systems. The results are used for performing comparative assessment studies between the various systems. Our current priorities include the development of energy strategies, in accordance with the German Federal Government’s greenhouse gas reduction targets, by designing new infrastructures for sustainable and secure energy supply chains and by conducting cost analysis studies for integrating new technologies into future energy market frameworks.

## Acknowledgements

The authors would like to thank the German Federal Government, the German state governments, and the Joint Science Conference (GWK) for their funding and support as part of the NFDI4Ing consortium. Funded by the German Research Foundation (DFG) – project number: 442146713. Furthermore, this work was supported by the Helmholtz Association under the program "Energy System Design".

<p float="left">
    <a href="https://nfdi4ing.de/"><img src="https://nfdi4ing.de/wp-content/uploads/2018/09/logo.svg" alt="NFDI4Ing Logo" width="130px"></a>&emsp;<a href="https://www.helmholtz.de/en/"><img src="https://www.helmholtz.de/fileadmin/user_upload/05_aktuelles/Marke_Design/logos/HG_LOGO_S_ENG_RGB.jpg" alt="Helmholtz Logo" width="200px"></a>
</p>