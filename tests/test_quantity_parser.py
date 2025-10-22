
import pytest
import time
import pprint
from quinex_utils.lookups.quantity_modifiers import PREFIXED_QUANTITY_MODIFIERS, SUFFIXED_QUANTITY_MODIFIERS
from quinex_utils.functions.normalize import normalize_quantity_span
from quinex_utils.functions.str2num import parse_value_and_order_of_magnitude_separately
from quinex_utils.parsers.quantity_parser import FastSymbolicQuantityParser


pp = pprint.PrettyPrinter(indent=1)

def test_parse_value_and_order_of_magnitude_separately():
    for value_span, result in [
        ("1.23×10^6", (1.23, 1e6)),
        ("1.23*10^6", (1.23, 1e6)),
        ("1.23 10**6", (1.23, 1e6)),
        ("1.23e-5", (1.23, 1e-5)),
        ("123e6", (123, 1e6)),
        ("10e6", (10, 1e6)),
        ('12.3 million', (12.3, 1e6)),        
        ("fifty seven billion", (57, 1e9)),      
    ]:
        clean_value_span = normalize_quantity_span(value_span) 
        value, order_of_magnitude = parse_value_and_order_of_magnitude_separately(clean_value_span)
        assert value == result[0]
        assert order_of_magnitude == result[1]


def test_no_unit_qmod_confusion():
    quantity_parser = FastSymbolicQuantityParser()
    unit_symbols = list(quantity_parser.unit_parser.unit_symbol_lookup.keys())
    unit_labels = list(quantity_parser.unit_parser.unit_label_lookup.keys())

    
    ambiguity_implemented = quantity_parser.QMODS_IN_UNITS

    prefixed_qmod_in_unit_symbols = [qmod for qmod in PREFIXED_QUANTITY_MODIFIERS if qmod in unit_symbols and qmod not in ambiguity_implemented]
    prefixed_qmod_in_unit_labels = [qmod for qmod in PREFIXED_QUANTITY_MODIFIERS if qmod in unit_labels and qmod not in ambiguity_implemented]
    suffixed_qmod_in_unit_symbols = [qmod for qmod in SUFFIXED_QUANTITY_MODIFIERS if qmod in unit_symbols and qmod not in ambiguity_implemented]
    suffixed_qmod_in_unit_labels = [qmod for qmod in SUFFIXED_QUANTITY_MODIFIERS if qmod in unit_labels and qmod not in ambiguity_implemented]

    assert len(prefixed_qmod_in_unit_symbols) == 0, f"Found prefixed quantity modifiers in unit symbols: {prefixed_qmod_in_unit_symbols}"
    assert len(prefixed_qmod_in_unit_labels) == 0, f"Found prefixed quantity modifiers in unit labels: {prefixed_qmod_in_unit_labels}"
    assert len(suffixed_qmod_in_unit_symbols) == 0, f"Found suffixed quantity modifiers in unit symbols: {suffixed_qmod_in_unit_symbols}"
    assert len(suffixed_qmod_in_unit_labels) == 0, f"Found suffixed quantity modifiers in unit labels: {suffixed_qmod_in_unit_labels}"


def test_quantity_parser_on_single_quantities():

    quantity_parser = FastSymbolicQuantityParser(error_if_no_success=True)
    quantity_parser_silent_fail = FastSymbolicQuantityParser(error_if_no_success=False)

    # TODO: Deal with alternative notations in parentheses.
    # '60% (163/270)'
    # '43% (89/208)'
    
    # TODO: Deal with subunit ellipses
    # result = quantity_parser.parse("30 • to 800 • C")

    # TODO: Deal with M for million etc.
    # result = quantity_parser_silent_fail.parse("−$97M")

    # TODO: Deal with the following cases:        
    # 'Rs. 5.81/kWh- Rs. 6.95/kWh'
    # '($/1kWh)'    
    # '$0.04/kWh to a maximum of $0.15/kWh'    
    # 'Rp 6,100.kWh-1'
    # "6 −10%"
    # "single-carbon"

    result = quantity_parser.parse('5 bpm')
    assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"] == [('bpm', 1, 'http://qudt.org/vocab/unit/BEAT-PER-MIN', None)]

    result = quantity_parser_silent_fail.parse('3 per mL')
    assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"] == [('per mL', -1, 'http://qudt.org/vocab/unit/MilliL', None)]

    result = quantity_parser_silent_fail.parse('4.6µm')
    assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"] == [('μm', 1, 'http://qudt.org/vocab/unit/MicroM', None)]
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 4.6

    result = quantity_parser.parse("0.5′′")
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 0.5
    assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"] == [('′′', 1, 'http://qudt.org/vocab/unit/ARCSEC', None)]

    result = quantity_parser.parse('1.5-m')
    assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"] == [('m', 1, 'http://qudt.org/vocab/unit/M', None)]

    result = quantity_parser.parse("-1")
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == -1
    
    result = quantity_parser.parse("− 1")
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == -1

    result = quantity_parser.parse("1%.")
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 1

    result = quantity_parser.parse('85[%]')
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 85

    result = quantity_parser.parse("0.98")
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 0.98     

    result = quantity_parser.parse("472 cm−1")
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 472 

    result = quantity_parser.parse("472 cm − 1")
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 472 

    result = quantity_parser_silent_fail.parse('− 10%')
    assert len(result["normalized_quantities"]) == 1
    assert result["success"]

    result = quantity_parser.parse("90.1°")
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 90.1
    assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"] == [('°', 1, 'http://qudt.org/vocab/unit/DEG', None)]

    result = quantity_parser.parse("1 µm")
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 1
    assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"] == [('μm', 1, 'http://qudt.org/vocab/unit/MicroM', None)]

    result = quantity_parser.parse("5% by weight")
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 5
    result["normalized_quantities"][0]["suffixed_unit"]["text"] == '% by weight'

    result = quantity_parser.parse("220 max H meV")
    assert result["normalized_quantities"][0]["suffixed_unit"]["text"] == 'max H meV'

    result = quantity_parser.parse("215 C a K")
    assert result["normalized_quantities"][0]["suffixed_unit"]["text"] == 'C a K'
    # TODO: Do not assign unlikely combination of units
    # result["normalized_quantities"][1]["suffixed_unit"]["normalized"] == None    
    
    result = quantity_parser_silent_fail.parse("1,331.4 kJ/mol")
    assert len(result["normalized_quantities"]) == 1
    assert result["success"]

    result = quantity_parser_silent_fail.parse("96 485 C mol −1")
    assert len(result["normalized_quantities"]) == 1
    assert result["success"]
  
    for quantity_string in [
        "($20/ MWh",    
        "40%)", 
        "66%).",    
        "$50%)",    
        "5 wt%",            
    ]:
        result = quantity_parser.parse(quantity_string)
        assert len(result["normalized_quantities"]) == 1    

    # Test degree celsius.        
    for temperature_string in ["60 °C", "60 ∘ C", "60 • C", "60 °C.", "60 ∘ C.", "60 • C."]:
        result = quantity_parser.parse(temperature_string)
        assert len(result["normalized_quantities"]) == 1
        assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 60
        assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"][0][1:4] == (1, 'http://qudt.org/vocab/unit/DEG_C', None)
    
    result = quantity_parser.parse("+20%.")
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 20   
    assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"] == [('%', 1, 'http://qudt.org/vocab/unit/PERCENT', None)]

    result = quantity_parser.parse("96.3‰")
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 96.3
    assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"] == [('‰', 1, 'http://qudt.org/vocab/unit/PPTH', None)]

    result = quantity_parser.parse("1 h")
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 1

    result = quantity_parser.parse("−$.240/kWh")
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["prefixed_modifier"]["normalized"] == "-"
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 0.240
    assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"] == [('/kWh', -1, 'http://qudt.org/vocab/unit/KiloW-HR', None)]
    assert result["normalized_quantities"][0]["prefixed_unit"]["normalized"] in [[('$', 1, 'http://qudt.org/vocab/currency/USD', None)], [('$', 1, 'http://qudt.org/vocab/unit/CCY_USD', None)]]
    
    # Do not link '¢' to 'http://qudt.org/vocab/currency/CAD'. 
    # TODO: Improve handling of cents
    result = quantity_parser.parse('1 ¢')
    assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"] == None \
        or result["normalized_quantities"][0]["suffixed_unit"]["normalized"][0][2] not in ['http://qudt.org/vocab/currency/CAD', 'http://qudt.org/vocab/unit/CCY_CAD']

    result = quantity_parser.parse('USD $0.30/ kWh')
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 0.30

    # Compound units
    result = quantity_parser.parse('4.1 m s −1')
    assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"] == [('m s -1', 1, 'http://qudt.org/vocab/unit/M-PER-SEC', None)]

    result = quantity_parser.parse("0.7 beat.min −1 .year −1")
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"] == [('beat', 1, 'http://qudt.org/vocab/unit/HeartBeat', None), ('min', -1, 'http://qudt.org/vocab/unit/MIN', None), ('year', -1, 'http://qudt.org/vocab/unit/YR', None)]

    result = quantity_parser_silent_fail.parse('2.4 l · day −1 ')
    assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"] in [
        [('l · day -1', 1, 'http://qudt.org/vocab/unit/L-PER-DAY', None)],
        [('l', 1, 'http://qudt.org/vocab/unit/L', None), ('day', -1, 'http://qudt.org/vocab/unit/DAY', None)]
    ]

    result = quantity_parser.parse('0.72 TWh kg*s^2/(m^2 per year)^3')
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 0.72
    assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"] == [
        ('TWh', 1, 'http://qudt.org/vocab/unit/TeraW-HR', None),
        ('kg', 1, 'http://qudt.org/vocab/unit/KiloGM', None),
        ('s', 2, 'http://qudt.org/vocab/unit/SEC', None),
        ('m', -6, 'http://qudt.org/vocab/unit/M', None),
        ('year', 3, 'http://qudt.org/vocab/unit/YR', None)
    ]

    # Abstract from two units (μg, mL-1) to a single unit.
    result = quantity_parser_silent_fail.parse('1.10 μg/ mL')
    assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"] == [('μg/ mL', 1, 'http://qudt.org/vocab/unit/MicroGM-PER-MilliL', None)]

    result = quantity_parser_silent_fail.parse('50 ml.kg −1 .min −1')


def test_quantity_parser_on_unit_modifiers():
    quantity_parser = FastSymbolicQuantityParser(error_if_no_success=True)
    quantity_parser_silent_fail = FastSymbolicQuantityParser(error_if_no_success=False)

    result = quantity_parser_silent_fail.parse("9419.6 million tons of CO 2")
    assert result["success"] in [True, None]

    result = quantity_parser.parse("0.23-0.44 t ethylene per t")
    assert len(result["normalized_quantities"]) == 2
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 0.23
    assert result["normalized_quantities"][1]["value"]["normalized"]["numeric_value"] == 0.44    


def test_quantity_parser_on_intervals():
    
    # TODO: Deal with false postive ranges 
    # result = quantity_parser_silent_fail.parse("0.40 mmol h − 1 cm − 2")
    # assert len(result["normalized_quantities"]) == 1
    
    # TODO: Support intervals in brackets
    # result = quantity_parser_silent_fail.parse('[0, 100]')
    # assert len(result["normalized_quantities"]) == 2   

    quantity_parser = FastSymbolicQuantityParser(error_if_no_success=True)
    quantity_parser_silent_fail = FastSymbolicQuantityParser(error_if_no_success=False)
    
    result = quantity_parser_silent_fail.parse("213 to well above 300 g/kWh")
    assert len(result["normalized_quantities"]) == 2
    assert result["success"]

    result = quantity_parser.parse('0.28–0.34 $/kWh')
    assert len(result["normalized_quantities"]) == 2
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 0.28
    assert result["normalized_quantities"][1]["value"]["normalized"]["numeric_value"] == 0.34

    result = quantity_parser.parse('0.0462–1.0864 $/kWh')
    assert len(result["normalized_quantities"]) == 2
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 0.0462
    assert result["normalized_quantities"][1]["value"]["normalized"]["numeric_value"] == 1.0864

    result = quantity_parser.parse('0.02–0.054 $/kWh')
    assert len(result["normalized_quantities"]) == 2
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 0.02
    assert result["normalized_quantities"][1]["value"]["normalized"]["numeric_value"] == 0.054

    result = quantity_parser.parse('$0.07/kWh to $0.16/kWh')
    assert len(result["normalized_quantities"]) == 2
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 0.07
    assert result["normalized_quantities"][1]["value"]["normalized"]["numeric_value"] == 0.16

    # TODO: Split into two quantities
    result = quantity_parser.parse('50-44 year')

    result = quantity_parser.parse("PH: 6.5-8.5")
    assert len(result["normalized_quantities"]) == 2
    assert result["normalized_quantities"][0]["prefixed_unit"]["normalized"] == [('PH:', 1, 'http://qudt.org/vocab/unit/PH', None)]

    result = quantity_parser.parse("5-to 10-year")
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 5
    assert result["normalized_quantities"][1]["value"]["normalized"]["numeric_value"] == 10
    assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"] == [('year', 1, 'http://qudt.org/vocab/unit/YR', None)]
    assert result["normalized_quantities"][1]["suffixed_unit"]["normalized"] == [('year', 1, 'http://qudt.org/vocab/unit/YR', None)]

    result = quantity_parser.parse("range from 0 meV")

    result = quantity_parser.parse("US$0.031–US$0.039/kWh")
    assert result["normalized_quantities"][0]["prefixed_unit"]["normalized"] in [ 
            [('US$', 1, 'http://qudt.org/vocab/currency/USD', None)],
            [('US$', 1, 'http://qudt.org/vocab/unit/CCY_USD', None)]
        ]
    # TODO: Deal with unit ellipses even if prefixed unit is present.
    # assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"] == [('kWh', -1, 'http://qudt.org/vocab/unit/KiloW-HR', None)]
    assert result["normalized_quantities"][1]["prefixed_unit"]["normalized"] in [ 
            [('US$', 1, 'http://qudt.org/vocab/currency/USD', None)],
            [('US$', 1, 'http://qudt.org/vocab/unit/CCY_USD', None)]
        ]
    assert result["normalized_quantities"][1]["suffixed_unit"]["normalized"] == [('/kWh', -1, 'http://qudt.org/vocab/unit/KiloW-HR', None)]
    
    result = quantity_parser_silent_fail.parse("0.022 mF/cm 2 to 0.13 mF/cm 2")
    
    result = quantity_parser.parse('0.62 $(kWh)−1 to 0.69 $(kWh)−1')
    assert len(result["normalized_quantities"]) == 2
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 0.62
    assert result["normalized_quantities"][1]["value"]["normalized"]["numeric_value"] == 0.69
    expected_units = [
        [('$', 1, 'http://qudt.org/vocab/currency/USD', None), ('kWh', -1, 'http://qudt.org/vocab/unit/KiloW-HR', None)], 
        [('$', 1, 'http://qudt.org/vocab/unit/CCY_USD', None), ('kWh', -1, 'http://qudt.org/vocab/unit/KiloW-HR', None)]
    ]
    assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"] in expected_units
    assert result["normalized_quantities"][1]["suffixed_unit"]["normalized"] in expected_units

    result = quantity_parser.parse('25.5 $/MWh-t to 46.9 $/MWh-t')    
    assert len(result["normalized_quantities"]) == 2    

    result = quantity_parser.parse("55%-60%)")    
    assert len(result["normalized_quantities"]) == 2

    result = quantity_parser.parse("6− 10%")
    assert len(result["normalized_quantities"]) == 2
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 6
    assert result["normalized_quantities"][1]["value"]["normalized"]["numeric_value"] == 10

    result = quantity_parser.parse("−0.6 to −1.2 V")
    assert len(result["normalized_quantities"]) == 2
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == -0.6
    assert result["normalized_quantities"][1]["value"]["normalized"]["numeric_value"] == -1.2


def test_quantity_parser_on_lists():
    quantity_parser = FastSymbolicQuantityParser(error_if_no_success=True)
    quantity_parser_silent_fail = FastSymbolicQuantityParser(error_if_no_success=False)

    # TODO: Debug '3% on average and 46%'

    result = quantity_parser.parse('1.5 vs. 1 Hz')
    assert len(result["normalized_quantities"]) == 2
    assert result["type"] == 'list'

    result = quantity_parser_silent_fail.parse("$1.2, $1.2, $0.51, $0.21,$ 1.2, and $0.8 kg À1")
    assert len(result["normalized_quantities"]) == 6
    assert result["success"] in [True, None]

    result = quantity_parser_silent_fail.parse("0.39, 0.13, 0.31, 0.13, and 0.18, respectively")
    assert len(result["normalized_quantities"]) == 5
    assert result["success"]

    result = quantity_parser.parse("50 and − 50%")
    assert len(result["normalized_quantities"]) == 2
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 50
    assert result["normalized_quantities"][1]["value"]["normalized"]["numeric_value"] == -50 
    assert result["type"] == 'list'

    result = quantity_parser_silent_fail.parse("0.8Mt and 1.05Mt")
    assert len(result["normalized_quantities"]) == 2
    assert result["success"] in [True, None]

    result = quantity_parser_silent_fail.parse("4 GtC yr −1 or 14.7 GtCO 2 yr −1")
    assert len(result["normalized_quantities"]) == 2
    assert result["success"] in [True, None]

    result = quantity_parser.parse('7.970, 8.138, 7.864, and 6.351$/kWh')
    assert len(result["normalized_quantities"]) == 4
    
    result = quantity_parser.parse('0.053, 0.057, and 0.063 $/KWh')
    assert len(result["normalized_quantities"]) == 3
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 0.053
    assert result["normalized_quantities"][1]["value"]["normalized"]["numeric_value"] == 0.057
    assert result["normalized_quantities"][2]["value"]["normalized"]["numeric_value"] == 0.063

    result = quantity_parser.parse('0.09138 $/kWh, 0.16588 $/kWh, and 0.24862 $/kWh')
    assert len(result["normalized_quantities"]) == 3
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 0.09138
    assert result["normalized_quantities"][1]["value"]["normalized"]["numeric_value"] == 0.16588
    assert result["normalized_quantities"][2]["value"]["normalized"]["numeric_value"] == 0.24862

    result = quantity_parser.parse("240, 333, 383, and 552 USD per tonne")
    assert len(result["normalized_quantities"]) == 4
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 240
    assert result["normalized_quantities"][1]["value"]["normalized"]["numeric_value"] == 333        
    assert result["normalized_quantities"][2]["value"]["normalized"]["numeric_value"] == 383
    assert result["normalized_quantities"][3]["value"]["normalized"]["numeric_value"] == 552

    # Test lists and ranges depending on quantity modifiers.
    result_a = quantity_parser.parse('25 and 30 kilometers per hour (km/h)')    
    result_b = quantity_parser.parse('between 25 and 30 kilometers per hour (km/h)')
    assert result_a["type"] == "list"
    assert result_b["type"] == "range"

    # Test lists with different units.
    result = quantity_parser.parse('8.40 %, 1.87, and 0.198 $/kWh')
    assert len(result["normalized_quantities"]) == 3
    assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"] == [('%', 1, 'http://qudt.org/vocab/unit/PERCENT', None)]
    assert result["normalized_quantities"][1]["suffixed_unit"]["normalized"] in [
        [('$', 1, 'http://qudt.org/vocab/currency/USD', None), ('kWh', -1, 'http://qudt.org/vocab/unit/KiloW-HR', None)],
        [('$', 1, 'http://qudt.org/vocab/unit/CCY_USD', None), ('kWh', -1, 'http://qudt.org/vocab/unit/KiloW-HR', None)]
    ]


def test_quantity_parser_localisation():
    quantity_parser = FastSymbolicQuantityParser(error_if_no_success=True)

    # Test localisation.
    result = quantity_parser.parse('0,378$/kWh')
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 0.378

    result = quantity_parser.parse('0,17 USD/kWh')
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 0.17


def test_quantity_parser_self_assessment():
    quantity_parser = FastSymbolicQuantityParser(error_if_no_success=True)
    quantity_parser_silent_fail = FastSymbolicQuantityParser(error_if_no_success=False)
    
    # Test correct despite unknown unit if rest can be normalized.
    result = quantity_parser.parse('2-3 times')
    assert len(result["normalized_quantities"]) == 2
    assert result["success"] in [True, None]

    # Fail when it should.    
    for should_fail in [
        "this is not a quantity",
        "J mol −1",
        "a", 
        "severalt housand hours",
        '($/1kWh)',
        '$0.24/kWh and a maximum',
        'Tk.2.52/kWh',
        '0.85 SEK/kWh (25th percentile) to 1.15 SEK/kWh (75th percentile)',        
    ]:
        result = quantity_parser_silent_fail.parse(should_fail)
        assert result["success"] == False, f"Expected to fail but got {result}"

    # Do not succeed when it should not.
    for should_not_fail_but_no_certain_success in [
        '$0.16/kWh in Yola to $0.169/kWh',
        '$0.261/kWh in Jos to $0.319/kWh',
        '$0.404/kWh in scenario-3 to $0.887/kWh',       
    ]:
        result = quantity_parser_silent_fail.parse(should_not_fail_but_no_certain_success)
        assert result["success"] == None


def test_quantity_parser_on_modifiers():
    """Test quantity parser on quantity modifiers."""    
    quantity_parser = FastSymbolicQuantityParser(error_if_no_success=True)

    result = quantity_parser.parse('max ±5 bpm')
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["prefixed_modifier"]["text"] == 'max ±'

    result = quantity_parser.parse('every 10 min')
    assert result["normalized_quantities"][0]["prefixed_modifier"]["text"] == 'every'
    assert len(result["normalized_quantities"]) == 1        

    result = quantity_parser.parse('About 30 mg')
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["prefixed_modifier"]["normalized"] == '~'

    result = quantity_parser.parse('After 80 %')
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["prefixed_modifier"]["text"] == 'After'

    result = quantity_parser.parse("$0.04/kWh to a maximum of $0.15/kWh")
    assert result["normalized_quantities"][1]["prefixed_modifier"]["text"] == "a maximum of"

    result = quantity_parser.parse('0.1% to well over 1.3%')
    assert len(result["normalized_quantities"]) == 2
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 0.1
    assert result["normalized_quantities"][1]["value"]["normalized"]["numeric_value"] == 1.3

    result = quantity_parser.parse('USD 470/MWh to a minimum of USD 120/MWh')
    assert len(result["normalized_quantities"]) == 2
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 470    
    assert result["normalized_quantities"][1]["value"]["normalized"]["numeric_value"] == 120

    result = quantity_parser.parse("‡20")
    assert result["normalized_quantities"][0]["prefixed_modifier"]["text"] == '‡'

    result = quantity_parser.parse("minus 5%")
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 5
    assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"] == [('%', 1, 'http://qudt.org/vocab/unit/PERCENT', None)]
    assert result["normalized_quantities"][0]["prefixed_modifier"]["normalized"] == "-"

    result = quantity_parser.parse('< ~40 meV 100 meV') 
    assert result["normalized_quantities"][0]["prefixed_modifier"]["text"] == '< ~'
    assert result["normalized_quantities"][0]["prefixed_modifier"]["normalized"] == '<~'

    result = quantity_parser.parse("< 0. 0 5")
    assert result["normalized_quantities"][0]["prefixed_modifier"]["normalized"] == '<'
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 0.05


def test_quantity_parser_on_scientific_notation():
    """Test quantity parser on scientific notation."""    
    
    quantity_parser = FastSymbolicQuantityParser(error_if_no_success=True)

    result = quantity_parser.parse('1.23e-5 USD/kWh')
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 1.23e-5

    result = quantity_parser.parse('8.75 × 10−2 $/kW-h')
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 8.75e-2

    result = quantity_parser.parse("1.0 x 107")    
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 1e7
    
    result = quantity_parser.parse("10²³ m")
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 10**23

    result = quantity_parser.parse("5.2*10⁻³ m")
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 5.2e-3

    # Do not confuse ranges with powers of ten.
    result = quantity_parser.parse('10-15 min')
    assert len(result["normalized_quantities"]) == 2

    result = quantity_parser.parse('10-16 knots')   
    assert len(result["normalized_quantities"]) == 2


def test_quantity_parser_on_ratios():
    """Test quantity parser on ratios."""
    quantity_parser = FastSymbolicQuantityParser(error_if_no_success=True)

    for ratio in ['1 of 2', '1:7.5', '78 of the 250', '156 out of 180', 'Twenty-eight of 50', 'from a 1:1']:        
        result = quantity_parser.parse(ratio)    
        assert result["type"] == 'ratio'
        assert len(result["normalized_quantities"]) == 2
        assert result["success"]

def test_quantity_parser_on_multidim():
    """Test quantity parser on multidimensional quantities."""

    # TODO: do not trigger multidim with 'by' here
    # result = quantity_parser.parse('not more than 0.025% by weight')   

    quantity_parser = FastSymbolicQuantityParser(error_if_no_success=True)
    
    result = quantity_parser.parse("100 mm x 100 mm x 400 mm")
    assert result["type"] == "multidim"
    assert len(result["normalized_quantities"]) == 3    
            
    # TODO: Ambiguity in whether to also multiply unit or not.
    result = quantity_parser.parse('2 x 2 min')
    assert len(result["normalized_quantities"]) == 1
    # result = quantity_parser.parse('2 x 2 m')
    # assert len(result["normalized_quantities"]) == 1


def test_quantity_parser_on_negation():
    """Test quantity parser on negation expressions."""
    quantity_parser = FastSymbolicQuantityParser(error_if_no_success=True)
            
    result = quantity_parser.parse("non-zero")
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["prefixed_modifier"]["normalized"] == '!=' 

    result = quantity_parser.parse("not 5%")
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 5
    assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"] == [('%', 1, 'http://qudt.org/vocab/unit/PERCENT', None)]
    assert result["normalized_quantities"][0]["prefixed_modifier"]["normalized"] == "!="

    result = quantity_parser.parse("not equals 6%")
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 6
    assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"] == [('%', 1, 'http://qudt.org/vocab/unit/PERCENT', None)]
    assert result["normalized_quantities"][0]["prefixed_modifier"]["normalized"] == "!="


def test_quantity_parser_on_number_words():
    quantity_parser = FastSymbolicQuantityParser(error_if_no_success=True)
    quantity_parser_silent_fail = FastSymbolicQuantityParser(error_if_no_success=False)

    result = quantity_parser.parse("few hundred rad m −2")
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"] == [('rad', 1, 'http://qudt.org/vocab/unit/RAD', None), ('m', -2, 'http://qudt.org/vocab/unit/M', None)]

    result = quantity_parser_silent_fail.parse("an hour")

    result = quantity_parser.parse('several hundred-fold')
    assert len(result["normalized_quantities"]) == 1

    result = quantity_parser.parse('twofold')
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 2

    result = quantity_parser.parse('at least two-thirds')
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 2/3
    assert result["normalized_quantities"][0]["suffixed_unit"] == None, "Do not confuse 'thirds' with year."

    result = quantity_parser.parse('third')
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 3

    result = quantity_parser_silent_fail.parse('€ 123 million')
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 123_000_000
    assert result["normalized_quantities"][0]["prefixed_unit"]["normalized"] in [
        [('€', 1, 'http://qudt.org/vocab/currency/EUR', None)],
        [('€', 1, 'http://qudt.org/vocab/unit/CCY_EUR', None)]
    ]

    result = quantity_parser.parse("zero")
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 0
    assert result["normalized_quantities"][0]["prefixed_unit"] == None
    assert result["normalized_quantities"][0]["suffixed_unit"] == None     

    result = quantity_parser.parse('10 to 15 million')
    assert len(result["normalized_quantities"]) == 2
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 10e6
    assert result["normalized_quantities"][1]["value"]["normalized"]["numeric_value"] == 15e6
        
    result = quantity_parser.parse('12.3 million Single-Family Houses (SFH)')
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 12.3e6

    result = quantity_parser.parse('one hundred and twenty three')
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 123

    result = quantity_parser.parse('one hundred and twenty three and four')
    assert (len(result["normalized_quantities"]) == 2 and result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 123) \
        or (len(result["normalized_quantities"]) == 1 and result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 127)


def test_quantity_parser_on_placeholder_units():
    """Test quantity parser on quantities with added placeholder units."""

    # TODO: Consider multiple tokens for QUDT linking in unit parser (e.g., "US" and "cents" to class with label "US cents").
    # result = quantity_parser.parse('6.94 to 13.30 US cents/kWh')
    # assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"] == [('US cents', 1, 'http://qudt.org/PLACEHOLDER_CENT', None), ('kWh', -1, 'http://qudt.org/vocab/unit/KiloW-HR', None)]  

    # TODO: Do not confuse "cents/kW h" with [('cents', 1, 'http://qudt.org/PLACEHOLDER_CENT', None), ('kW', -1, 'http://qudt.org/vocab/unit/KiloW', None), ('h', 1, 'http://qudt.org/vocab/unit/HR', None)]
    # result = quantity_parser.parse('7.4 to 6.7 cents/kW h')
    # assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"] == [('cents', 1, 'http://qudt.org/PLACEHOLDER_CENT', None), ('kW h', -1, 'http://qudt.org/vocab/unit/KiloW-HR', None)]  

    quantity_parser = FastSymbolicQuantityParser(error_if_no_success=True, allow_evaluating_str_as_python_expr=False)
        
    result = quantity_parser.parse("0.70⊄/(kW·h)")
    assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"] == [('⊄', 1, 'http://qudt.org/PLACEHOLDER_CENT', None), ('kW h', -1, 'http://qudt.org/vocab/unit/KiloW-HR', None)]

    result = quantity_parser.parse("12.7 to 5.1 GW el")
    assert len(result["normalized_quantities"][1]["suffixed_unit"]["normalized"]) == 1
    assert result["normalized_quantities"][1]["suffixed_unit"]["normalized"][0][0] == 'GW el'

    result = quantity_parser.parse("9.23 wt.%")
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 9.23   
    assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"] == [('wt.%', 1, 'http://qudt.org/PLACEHOLDER_PERCENT_BY_MASS', None)]
    
    result = quantity_parser.parse('3.25 ¢/kWh to 4.25 ¢/kWh')
    assert result["normalized_quantities"][1]["suffixed_unit"]["normalized"] == [('¢', 1, 'http://qudt.org/PLACEHOLDER_CENT', None), ('kWh', -1, 'http://qudt.org/vocab/unit/KiloW-HR', None)]

    result = quantity_parser.parse('$6/MMBtu')
    usd_alternatives = [
        [('$', 1, 'http://qudt.org/vocab/currency/USD', None)],
        [('$', 1, 'http://qudt.org/vocab/unit/CCY_USD', None)]
    ]
    assert result["normalized_quantities"][0]["prefixed_unit"]["normalized"] in usd_alternatives
    assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"] == [('/MMBtu', -1, 'http://qudt.org/vocab/unit/MegaBTU_IT', None)]
    
    result = quantity_parser.parse('∼$3 – $20/MMBtu')
    assert result["normalized_quantities"][0]["prefixed_unit"]["normalized"] in usd_alternatives
    # TODO: Deal with unit ellipses even if prefixed unit is present.
    # assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"] == [('MMBtu', -1, 'http://qudt.org/vocab/unit/MegaBTU_IT', None)]
    assert result["normalized_quantities"][1]["prefixed_unit"]["normalized"] in usd_alternatives
    assert result["normalized_quantities"][1]["suffixed_unit"]["normalized"] == [('/MMBtu', -1, 'http://qudt.org/vocab/unit/MegaBTU_IT', None)]
    
    # TODO: Do not devide the individual values
    # result = quantity_parser.parse("49.5/36.5/14 (vol%)")
    result = quantity_parser.parse("36.5 (vol%)")
    assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"] == [('(vol%)', 1, 'http://qudt.org/PLACEHOLDER_PERCENT_BY_VOL', None)]

    result = quantity_parser.parse('6.02 cents/kWh, and 5.95 cents/kWh')
    assert result["normalized_quantities"][1]["suffixed_unit"]["normalized"] == [('cents', 1, 'http://qudt.org/PLACEHOLDER_CENT', None), ('kWh', -1, 'http://qudt.org/vocab/unit/KiloW-HR', None)]
    
    result = quantity_parser.parse('4.52, 4.47, and 4.63 (Cents/kWh)') 
    assert result["normalized_quantities"][2]["suffixed_unit"]["normalized"] == [('Cents', 1, 'http://qudt.org/PLACEHOLDER_CENT', None), ('kWh', -1, 'http://qudt.org/vocab/unit/KiloW-HR', None)]
        
    result = quantity_parser.parse('8.72 to 10.01 cents/kWh')
    assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"] == [('cents', 1, 'http://qudt.org/PLACEHOLDER_CENT', None), ('kWh', -1, 'http://qudt.org/vocab/unit/KiloW-HR', None)]  
    
    result = quantity_parser.parse('7 to 17 cents per kWh')
    assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"] == [('cents', 1, 'http://qudt.org/PLACEHOLDER_CENT', None), ('kWh', -1, 'http://qudt.org/vocab/unit/KiloW-HR', None)]  
    
    result = quantity_parser.parse('5.03 cents kWh−1')
    assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"] == [('cents', 1, 'http://qudt.org/PLACEHOLDER_CENT', None), ('kWh', -1, 'http://qudt.org/vocab/unit/KiloW-HR', None)]  

    result = quantity_parser.parse('35–52 cents/kWh')
    assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"] == [('cents', 1, 'http://qudt.org/PLACEHOLDER_CENT', None), ('kWh', -1, 'http://qudt.org/vocab/unit/KiloW-HR', None)]  
    
    result = quantity_parser.parse("4 cents per kilowatt-hour")
    assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"] == [('cents', 1, 'http://qudt.org/PLACEHOLDER_CENT', None), ('kilowatt-hour', -1, 'http://qudt.org/vocab/unit/KiloW-HR', None)]  

    result = quantity_parser.parse("6 mol%")
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 6  
    assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"] != [('mol', 1, 'http://qudt.org/vocab/unit/MOL', None), ('%', 1, 'http://qudt.org/vocab/unit/PERCENT', None)]
    assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"] == [('mol%', 1, 'http://qudt.org/PLACEHOLDER_PERCENT_BY_MOL', None)]

    result = quantity_parser.parse("less than 0.2% by weight")
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"] == [('% by weight', 1, 'http://qudt.org/PLACEHOLDER_PERCENT_BY_MASS', None)]


def test_quantity_parser_with_spelling_and_decoding_errors():
    quantity_parser = FastSymbolicQuantityParser(error_if_no_success=True)
    quantity_parser_silent_fail = FastSymbolicQuantityParser(error_if_no_success=False)

    # Test extra whitespace.
    result = quantity_parser.parse('$0.2109 kWh -1')
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 0.2109

    result = quantity_parser.parse('$0.2109 kWh -1')
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 0.2109

    result = quantity_parser.parse('USD 0.61 / kWh')
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 0.61

    # Test spelling mistakes.
    result = quantity_parser.parse('0. 0273 US$/kWh')
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 0.0273

    # Test quantities in parentheses.
    result = quantity_parser.parse('(<1%)')
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 1
    assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"] == [('%', 1, 'http://qudt.org/vocab/unit/PERCENT', None)]

    result = quantity_parser.parse('(>99.5%)')
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 99.5
   
    result = quantity_parser.parse('(0.0737 USD/kWh)')
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 0.0737

    # Test decoding errors.
    result = quantity_parser.parse('354 to 505\xa0€/MWh')
    assert len(result["normalized_quantities"]) == 2
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 354
    assert result["normalized_quantities"][1]["value"]["normalized"]["numeric_value"] == 505
    assert result["normalized_quantities"][0]["suffixed_unit"]["ellipsed_text"] == "€/MWh"
    assert result["normalized_quantities"][1]["suffixed_unit"]["text"] == "€/MWh"

    result = quantity_parser.parse('1\xa0MW')
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 1
    assert result["normalized_quantities"][0]["suffixed_unit"]["text"] == "MW"
                
    for decoding_error_quantity in [        
        # '70\xa0€/MWh in 2015 to 52\xa0€/MWh',
        '45.3 to 40.3\xa0€/MWh',
        '25 to 200\xa0€/MWh',
        '$77.72 to 87.66\xa0MWh−1',
    ]:
        result = quantity_parser.parse(decoding_error_quantity)
        assert len(result["normalized_quantities"]) == 2

    # Test ignore known garbage suffixes.
    for quantity_string in [
        '$37.35/MWh, and',
        '0.576 $/kW·h, and',
        ]:
        result = quantity_parser.parse(quantity_string)
        assert result["success"] == True, f"Expected to parse but got {result}"
    
    # Test ellipsed zero before decimal point.
    result = quantity_parser.parse('US$.20/kWh')
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 0.20

    result = quantity_parser_silent_fail.parse(".19.23/kWh")
    assert not result["success"]      


def test_quantity_parser_on_non_physical_units():
    quantity_parser = FastSymbolicQuantityParser(error_if_no_success=True)
    
    # Test non-physical units.    
    result = quantity_parser.parse("three cases")
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 3
    assert result["normalized_quantities"][0]["suffixed_unit"]["text"] == "cases"
    assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"] == None

    result = quantity_parser.parse("three-compartment")
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 3
    assert result["normalized_quantities"][0]["suffixed_unit"]["text"] == "compartment"
    assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"] == None

    result = quantity_parser.parse("Two-dimensional")
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 2
    assert result["normalized_quantities"][0]["suffixed_unit"]["text"] == "dimensional"
    assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"] == None

    result = quantity_parser.parse("single carbon")
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 1
    assert result["normalized_quantities"][0]["suffixed_unit"]["text"] == "carbon"
    assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"] == None

    result = quantity_parser.parse("single-carbon")
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 1
    assert result["normalized_quantities"][0]["suffixed_unit"]["text"] == "carbon"
    assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"] == None

    result = quantity_parser.parse("5-fold")
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 5
    assert result["normalized_quantities"][0]["suffixed_unit"]["text"] == "fold"
    assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"] == None

    result = quantity_parser.parse("two strong equivalent C--O linear bonds")
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 2
    assert result["normalized_quantities"][0]["suffixed_unit"]["text"] == "strong equivalent C--O linear bonds"
    assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"] == None

    for non_physical_quantity in [
        "four rectification column",
        "four critical steps",
        "four adiabatic reactors",
        "four additional P-E T",
    ]:
        result = quantity_parser.parse(non_physical_quantity)
        assert len(result["normalized_quantities"]) == 1
        assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 4
        assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"] == None

def test_quantity_parser_on_cardinals_and_fractions():
    quantity_parser = FastSymbolicQuantityParser(error_if_no_success=True)
    quantity_parser_silent_fail = FastSymbolicQuantityParser(error_if_no_success=False)

    # Fractions.
    result = quantity_parser_silent_fail.parse('up to a quarter')
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["prefixed_unit"] == None, "Do not confuse 'a' with year."
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 0.25

    result = quantity_parser.parse('about a third')
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 1/3

    result = quantity_parser.parse('a quarter')
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["prefixed_unit"] == None, "Do not confuse 'a' with year."
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 0.25

    result = quantity_parser.parse('a third')
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 1/3

    result = quantity_parser.parse("one-quarter of a century")
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 0.25

    # Here, 'second' is not a cardinal number.
    result = quantity_parser.parse("after about 1 second")
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 1
    assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"] == [('second', 1, 'http://qudt.org/vocab/unit/SEC', None)]

def test_quantity_parser_on_imprecise_quantities():
    quantity_parser = FastSymbolicQuantityParser(error_if_no_success=True)
    quantity_parser_silent_fail = FastSymbolicQuantityParser(error_if_no_success=False)

    # Test imprecise quantities.
    for quantity_string in [
        "a few hundred hours",
        "a few km",
        "truckloads of kg",
        "a truckload of hours",
        "gazillion hours",      
        "crap load of hours",  
    ]:
        result = quantity_parser.parse(quantity_string)
        assert result["success"] == True
        assert len(result["normalized_quantities"]) == 1
        assert result["normalized_quantities"][0]["value"]["normalized"]["is_imprecise"]
        assert result["normalized_quantities"][0]["prefixed_unit"] == None, "Do not confuse 'a' with year."
        
    result = quantity_parser.parse("several research projects")
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["text"] == "several"
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == None
    assert result["normalized_quantities"][0]["value"]["normalized"]["is_imprecise"] == True
    assert result["normalized_quantities"][0]["suffixed_unit"]["text"] == "research projects"
    assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"] == None

    result = quantity_parser.parse("several tuned copper-based catalysts")
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["text"] == "several"
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == None
    assert result["normalized_quantities"][0]["value"]["normalized"]["is_imprecise"] == True
    assert result["normalized_quantities"][0]["suffixed_unit"]["text"] == "tuned copper-based catalysts"
    assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"] == None

    result = quantity_parser.parse("a few Mo-based materials")
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["text"] == "a few"
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == None
    assert result["normalized_quantities"][0]["value"]["normalized"]["is_imprecise"] == True
    assert result["normalized_quantities"][0]["suffixed_unit"]["text"] == "Mo-based materials"
    assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"] == None

    result = quantity_parser_silent_fail.parse("several hundred-hours")
    assert result["normalized_quantities"][0]["value"]["normalized"]["is_imprecise"]
    assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"] == [('hours', 1, 'http://qudt.org/vocab/unit/HR', None)]        

    result = quantity_parser.parse("hundreds")
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["normalized"]["is_imprecise"]

    result = quantity_parser.parse('tens of millions')
    assert len(result["normalized_quantities"]) == 1    
    assert result["normalized_quantities"][0]["value"]["text"] == 'tens of millions'
    assert result["normalized_quantities"][0]["value"]["normalized"]["is_imprecise"]

    result = quantity_parser.parse("hundreds of millions")
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["normalized"]["is_imprecise"]

    result = quantity_parser.parse("thousands or millions")
    assert len(result["normalized_quantities"]) == 2
    assert result["normalized_quantities"][0]["value"]["normalized"]["is_imprecise"]
    assert result["normalized_quantities"][1]["value"]["normalized"]["is_imprecise"]

    result = quantity_parser_silent_fail.parse('few-percent')
    assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"] == [('percent', 1, 'http://qudt.org/vocab/unit/PERCENT', None)]

    result = quantity_parser_silent_fail.parse('multi-hour')
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["normalized"]["is_imprecise"]

    result = quantity_parser.parse('multiple years')
    assert len(result["normalized_quantities"]) == 1    
        
    result = quantity_parser.parse("few-earth-mass")
    assert result["normalized_quantities"][0]["suffixed_unit"]["normalized"] == [('earth-mass', 1, 'http://qudt.org/vocab/unit/EarthMass', None)]


def test_quantity_parser_on_stats_expr():
    """Test quantities with statistical expressions, such as with tolerances and uncertainties."""

    quantity_parser = FastSymbolicQuantityParser(error_if_no_success=True)    
    quantity_parser_silent_fail = FastSymbolicQuantityParser(error_if_no_success=False)

    result = quantity_parser.parse('2.98 (2.62-3.38)', simplify_results=True)
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 2.98
    assert result["normalized_quantities"][0]["uncertainty"]["normalized"]["value"][0] == 2.62
    assert result["normalized_quantities"][0]["uncertainty"]["normalized"]["value"][1] == 3.38
    assert result["normalized_quantities"][0]["uncertainty"]["normalized"]["type"] == "unknown" 
    
    result = quantity_parser.parse('12.5 ± 3.7%', simplify_results=True)
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 12.5
    assert result["normalized_quantities"][0]["uncertainty"]["normalized"]["value"][0] == -3.7
    assert result["normalized_quantities"][0]["uncertainty"]["normalized"]["value"][1] == 3.7
    assert result["normalized_quantities"][0]["uncertainty"]["normalized"]["type"] == "tolerance"

    result = quantity_parser.parse('12.5% ± 3.7%', simplify_results=True)
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 12.5
    assert result["normalized_quantities"][0]["uncertainty"]["normalized"]["value"][0] == -3.7
    assert result["normalized_quantities"][0]["uncertainty"]["normalized"]["value"][1] == 3.7
    assert result["normalized_quantities"][0]["uncertainty"]["normalized"]["type"] == "tolerance"

    result = quantity_parser.parse('0.67 ± 0.18', simplify_results=True)
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 0.67
    assert result["normalized_quantities"][0]["uncertainty"]["normalized"]["value"][0] == -0.18
    assert result["normalized_quantities"][0]["uncertainty"]["normalized"]["value"][1] == 0.18
    assert result["normalized_quantities"][0]["uncertainty"]["normalized"]["type"] == "tolerance" 

    result = quantity_parser.parse('$0.2109 ± 0.0321 kWh -1', simplify_results=True)
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["value"]["normalized"]["numeric_value"] == 0.2109
    assert result["normalized_quantities"][0]["uncertainty"]["normalized"]["value"][0] == -0.0321
    assert result["normalized_quantities"][0]["uncertainty"]["normalized"]["value"][1] == 0.0321
    assert result["normalized_quantities"][0]["uncertainty"]["normalized"]["type"] == "tolerance"

    result = quantity_parser.parse('113 (± 1) nM')
    assert len(result["normalized_quantities"]) == 1
    assert result["normalized_quantities"][0]["uncertainty_expression_pre_unit"]["normalized"]["value"] == (-1, 1) 

    result = quantity_parser_silent_fail.parse('5.32, 95% CI: 3.13-9.04')

    # TODO: Handle the following cases.
    # '2.22 (+/- 1.21 SD)',
    # '8.50 days (95% confidence interval [CI] [7.22; 9.15])',
    # '27.5% (95% confidence interval, 15.7%-40.0%)',
    # '5.08 days (95% confidence interval (CI) 4.17-6.21)',
    # '0.60% (95% confidence interval: 0.43%-0.84%)',
    # '3.18 [3.09, 3.24] (95% confidence interval)',
    # '2.6928E7 (95% CI [2.6921E7,2.6935E7])',
    # '0.59 contacts per day (95% uncertainty interval (UI)=0.48-0.71)',
    # '0.59 contacts/day (95% uncertainty interval-UI = 0.48-0.71)',
    # '5.1% (95% UI=4.8-5.4%)',
    # '1,906,634 (95% CrI 1,373,500-2,651,124)',
    # '19.1% (95% CrI 13.5-26.6%)', 
    # '5.4 days (SD = 4.5; 95% CI: 4.3, 6.5)',
    # 'median: 16.0, range: 1.9 to 550.9',
    # 'mean: 96.3%, SD: 0.04%',
    # 'mean 2.5 ± SD 1.45 days',
    # '0.093 (+/- 0.037, p=0.025)',
    # '5.81 days (standard deviation: 3.24)',
    # '4.8 days (standard deviation 3.9)',
    # '2 secondary infected cases (mean 3.3, standard deviation 3.2)',
    # '6.93 (standard deviation = ±5.87, 95% confidence interval [CI] = 6.11-7.75)',
    # '1.07 (95% confidence interval: 0.58, 1.57; P<0.0001)',
    for stats_expr in [        
        '2.30, 95% CI 1.03-5.13',
        '5.71(95% credible interval: 4.08-7.55)',
        '0.60% (95% confidence interval 0.55%, 0.71%)',
        '7.04 (SD 4.27) days',
        '7.04 days (SD 4.27)',        
        '2.25 (95% CI 1.92-2.65)',                                
        '2.84 (95% confidence interval [CI] 1.66-4.88)',
        '0.62 (95% confidence interval [CI] 0.37-0.89)',
        '2.38 (95% confidence interval [CI] =1.79-3.07)',
        '3.59 (95% confidence interval [CI]: 3.48 - 3.72)',        
        '1.471 (95% confidence interval [CI], 1.351 to 1.592)',        
        '2.6 (95% confidence intervals 1.9-3.4)',
        '5.8 (confidence interval: 4.7-7.3)',
        '0.50 (95% confidence interval (CI): 0.30-0.77)',
        '1.02 [confidence interval (CI) of 0.75-1.29]',
        '0.72 (95% confidence interval (CI): 0.68, 0.76)',
        '0.63 (95% CI: 0.57, 0.69)',
        '0.7, 95% CI 0.6, 0.8',
        '2.15 [95% CI: 2.09-2.20]'    ,
        '0.76 (95% CI, 0.66 to 0.86)',
        '2.29 (95% CI: 1.84-2.78)',        
        '0.0415 (95% CI, 0.0138- 0.0691)',
        '0.37 (95% CI = 0.22-0.53)',
        '3.06 (95%CI: 2.64 - 3.51)',
        '1.23 (CI of 0.94-1.57)',
        '0.004 (95% UI=0.002-0.008)',
        '2.1 (95% UI = 1.8-2.4)'    ,
        '0.84 (95% CrI 0.81-0.88)',
        '3.58 (95% CrI: 2.46-5.08)',
        '2.51 (90% credible interval 0.47-9.0)',
        '5.71(95% credible interval: 4.08-7.55)',
        '2.95 (95% credible interval [CrI] 2.83-3.33)',
        '3.54 (95% credible interval [CrI]: 3.40-3.67)',
        '1.125 [0.933, 1.345]',   
    ]:
        result = quantity_parser.parse(stats_expr, simplify_results=True)
        assert len(result["normalized_quantities"]) == 1
        assert result["normalized_quantities"][0]["uncertainty"] != None


def test_quantity_parser_additional():
    # Test if no error is raised and collect expressions that fail or are doubtful.

    quantity_parser_silent_fail = FastSymbolicQuantityParser(error_if_no_success=False)

    quantity_strings_failed = []
    quantity_strings_success = []
    quantity_strings_doubt = []
    
    for quantity_string in [
        '0.89\xa0₨/kWh',
        '$0.07/kWh to $0.16/kWh',
        '0.32 to 0.41 CNY/kWh',
        '50.67 to 66.73 £/MWh',
        '0.5407 to 0.5439 CNY/kWh',
        '0.0001 $/kWh, 0.0031 $/kWh, and 0.0417 $/kWh',
        '0.03653 $/kWh, 0.003743 $/kWh, and 0.03328 $/kWh',
        '0.03736 $/kWh, 0.004726 $/kWh, and 0.03335 $/kWh',
        '8.98 to 9.90 ¢/kWh',
        '$0.174/kWh, and',
        '0.01$/kWh, and 0.0281$/kWh',
        '55 $/MWh to 78 $/MWh',
        '6.7 $/kg to 16.3 $/kg',
        '0.13 to 0.16 $/kWh',
        '0.0519, 0.04122, and 0.05383 $/kWh',
        '0.041 to 0.035 $/kWh',
        '139.07~141.19 KRW/kWh',
        '145.43~146.18 KRW/kWh',
        '139.07~145.43 KRW/kWh',
        '141.19~146.18 KRW/kWh',
        '32.3% to 0.365 kWh',
        '4% to 0.517 kWh',
        '4.6 to 7.31 $/kg',
        '0.025 to 0.051 USD/kWh',
        '$85/MWh to $91/MWh',
        '0.24 USD/kWh to 0.12 USD/kWh',
        '99.2 €/MWh to 68.2 €/MWh',
        '1.5 to 5.9 ¢/kWh',
        '0.118 $/kWh, 0.077 $/kWh, and 0.062 $/kWh',
        '10.97 %, 27.49 %, and 3.40 %',
        '0.0323 $/kWh, 0.0032 $/kWh, and 11.9$/kg',
        '$ 0.274 / kWh',
        '$ 0.300 / kWh',
        '0.0702 $/kWh to 0.0786 $/kWh',
        '0.07188 $/kWh to 0.1125 $/kWh',
        '0.21 to 0.63 €/kWh',
        '$0.084/kWh to $0.27/kWh',
        '102,124 NGN/kWh to 419 NGN/kWh',
        '123.2 /MWh to 164.4 /MWh',
        '1.29 % to 0.1687 USD/kWh',
        '0.17/kWh, and 0.09/kWh',
        '0.308 $/kWh to 0.353 $/kWh',
        '€0.043/kWh to €0.049/kWh',
        '79 to 53 €/MWh',
        '100 to 31.9 €/MWh',
        '40 to 70%',
        '67 to 115 €/MWh',
        '0.728 $/kWh, and',
        '0.1267 $/kWh to 0.1815 $/kWh',
        '0.1096 $/kWh to 0.1294 $/kWh',
        '0.042, 0.074, and 0.110 USD/kWh',
        '0.086, 0.122, and 0.142 USD/kWh',
        '0.07 to 0.09 €/kWh',
        '0.4362 €/kWh to 0.1533 €/kWh',
        '0.54 $2021/kWh to 0.29 $2021/kWh',
        '$0.1289/kWh to $0.1262/kWh',
        '0.55 $/kWh, and 5.06 $/kWh',
        '0.488 CNY/kWh to 0.445 CNY/kWh',
        '172 £/MWh to 514 £/MWh',
        '0.06741 to 0.10251 US$/kWh',
        '0.06681 to 0.10160 US$/kWh',
        '56.45 to 32.52 $/(MWh)',
        '$68 to $102/MWh',
        '100 to 270$/MWh',
        '86.5 to 243.4 USD/MWh',
        '0.198 to 0.207 $/kWh',
        '0.02 to 0.58 CNY/kWh',
        '0.151 $/kWh to 0.195 $/kWh',
        '0.06 USD to 0.12 USD per kWh',        
        'USD 160/MWh to USD 102/MWh',
        '103.18 $/MWh, 108.45 $/MWh, and 110.07 $/MWh',
        '0.42£/kWh, and 0.45£/kWh',        
        '9.77 c/kWh to up to 8 c/kWh',
        '0.5385 USD/kWh, and',
        '30.77 $/MWh, 32.06 $/MWh, and 33.6 $/MWh',
        '0.110 USD/kWh to 0.125 USD/kWh',
        '0.031 to 0.043 (USD/kWh).', 
        '0.03 USD/kWh to 0.07 USD/kWh',
        '0.0696, 0.0698, and 0.0696 USD/kWh',
        '0.1318, 0.1332, and 0.1182 USD/kWh',
        '13.11 to 12.35 c/kWh',
        '0.18 to 0.157 ($/kW h)',
        '13.01 c/kWh to 16.27 c/kWh',
        '$100 / MWh',
        '0, 0.04, and 0.06',
        '0.138 $/kWh to 0.251 $/kWh',
        '8.409 $/kg to 14.070 $/kg',
        '97 to 141 EUR/MWh',        
        '0.5059 $/kWh, and 0.42114 $/kWh',
        '0.0359 $/kWh to 0.1185 $/kWh',
        '0.10 US$/kWh-e to 0.243 US$/kWh-e',
        '60 to 30 €/MWh',
        '0.099 USD/kWh, 0.108 USD/kWh, and 0.138 USD/KWh',
        '75.6 to 170 €/kWh',
        '0.075 to 0.067 ($/kWh)',
        '$382.64 / MWh',
        '$274.63 / MWh',
        '0.047 to 0.099U$/kWh',
        '0.1034 USD/kWh to 0.0866 USD/kWh',
        '0.063 to 0.059 ($/kWh)',
        '8.46 to 9.11 ¢/kWh',
        '103.0 to 105.0 ¢/m3',
        '0.17 to 0.36 BBD/kWh',
        '−15 to 134 USD/MWh',
        '$0.04/kWh to a maximum of $0.15/kWh',
        '0.065 $/kWh, and',
        '0.054 $/kWhH2 (1.78 $/kgH2) to 0.103 $/kWhH2 (3.4 $/kgH2).',
        '0.12 to 0.16 $/kWh',
        '$83 to $2,200 per MWh',        
        '17.5 to 15.2 c€/kWh',
        '18.5 to 17.3 c€/kWh',
        '27.37 to 49.39 €/MWh',
        '0.103 to 0.120 USD/kWh',
        '₨. 4.76 crore',
        '0.6 to 0.4 $/kWh',
        '0.17 to 0.50 $/kWh',
        '2.2 to 3.2 times',
        '$0.119/kWh to $0.129/kWh',
        '0.351 to 0.769 RMB/kWh',
        'INR 2.71/kWh to INR 3.41/kWh',
        '$0.25/kWh to $0.36/kWh',
        '$0.25/kWh to $0.3/kWh',
        '0.131 to 0.409 $/kW h',
        '0.12 to 0.357 $/kW h',
        '10.532 to 15.507 US$/MWh',
        '7.320 to 13.002 US$/MWh',

        '68 to 150 EUR/MWh',
        '106 to 241 EUR/MWh',
        'Indian rupees (INR) 6.76–INR 26.32 (US $0.095–US $0.371) per kWh',
        '$2.37/ kWh',
        '85.4%, 14.85%, 9.15%, and 0.396 MYR/kWh',
        '0.0208 to 0.053 US$/kWh',
        '7.0074 to 10.5667 US$/kg',
        '145.6 USD/MWh to 186.8 USD/MWh',
        '112.2 USD/MWh to 154.2 USD/MWh',
        '179.2 USD/MWh to 220.4 USD/MWh',
        '150 to 250/MWh',
        '12.55 to 15.93 €/MWh',
        '45 to 51 €/MWh',
        '80 US$ to 90 US$ MWh-1',
        '0.07 to 0.15 USD/kWh',
        'USD 0.54/kWh to USD 0.77/kWh',
        '174.0, 283.1, and 327.3 $ ton−1',
        '9.89, 10.63, and 10.99 ₹/kWh',
        '$ 0.11 / kWh',
        '68 to 86 £/MWh',
        '0.447 €/kWh to 0.242 €/kWh',
        '0.387 €/kWh to 0.115 €/kWh',
        '8 to 10 ¢/kWh',
        '0.0452 to 0.1108 $/kWh',
        'US0.185 to US0.158',
        '57.40$/MWh to 55.87$/MWh',
        '53.71 to 164.94 USD/MWh',
        '0.0665 €/kWh to 0.0771 €/kWh',
        'USD 0.92 / kWh',
        'USD 1.30 / kWh',
        'USD 0.40 / kWh and',
        'USD 0.61 / kWh',
        '0.54 USD / kWh to 0.77 USD / kWh',
        '0.04 to 0.07 CAD/kWh',
        '0.34 EUR/kWh to 0.46 EUR/kWh',
        '51.6 $/MWh to 89 $/MWh',
        '54.42 to 57.04 $/MWh',
        '$91/ MWh',
        '65 to 85 USD/MWh',
        '61 €/MWh in 2015 to 53 €/MWh',
        '29 €/MWh to 20 €/MWh',
        '0.09 to 0.14 $-kWh-1',
        '0.7911 to 1.6778 $/kg',
        '(-300 USD / MWh)',
        '0.0491 USD/kWh to 0.0605 USD/kWh',
        '9 to 15 €/MWh',
        '0.373 to 0.628 CNY/kWh',
        '239.0 to 127.5 EUR/MWh',
        '9.4 to 5.0 EUR/GJ',
        '0.062$/kWh to 0.041$/kWh',
        '314 to 455 $/MWh',
        'two to three times',
        '6.99¢ to 8.32¢ per kWh',
        '$ 41.1 to 46.2 per MWh',
        '32.06 to 18.95 USc/kWh',
        '0.04 to 0.20 €/kWh',
        'Rs. 9.56/kWh to Rs. 12.55/kWh',
        '$142/MWh to $781/MWh',
        'US$0.056 to 0.147/kWh',
        '65 to 85 Euro/MWh',
        '0.15 to 0.073 Euro/Nm3',
        '11.6 to 12.5 ¢/kWh',
        '13.0 to 14.4 ¢/kWh',
        '5.2 ¢/kWh, 5.5 ¢/kWh, 6.2 ¢/kWh, and 7.5 ¢/kWh',
        '0.10 USD/kWh to 0.20 USD/kWh',
        '6.37, 6.40, and 6.41 ¢/kWh',
        '0.185 to 0.486 ¥ kWh−1',
        '88.34 $/MWh to 113.76 $/MWh',
        '97.61 $/MWh to 126.60 $/MWh',
        '19.9 US$/MWh to 18.6 US$/MWh',
        '0.398 USD/kWh to 0.743 USD/kWh',
        '0.19 € kW h−1, and',

        'INR 8.0/kWh to INR 19.04/kWh',
        'INR 8.0/kWh to INR 16.38/kWh',
        
        '13.1 ¢/kWh to 25.9¢/kWh',
        '0.12 to 10.6 €/kWh',
        '54.8 to 51.4 €/MWh',
        '$0.445 / kWh',
        'USD 0.156/kWh to 0.172/kWh',
        '142.5 to 190.0 $/MWh',        
        '160 to 215 US$/MWh',
        '11.96 INR/kWh to 18.47 INR/kWh',
        'Rp.7668',
        'Rp.7970',
        'US $0.0695 and US $0.1132/kWh',
        '0.096 €/kW h to 0.159 €/kW h',
        '0.036 €/kWh up to 0.159 €/kWh',
        'Rs.1.767/- per kWh',
        'Rs.1.734 /- per kWh',
        '0.1831 /kWh to 0.1870 /kWh',
        '0.1781 /kWh to 0.1832 /kWh',
        '49.1 to 53.6 $/MWh',

        'US$0.031–US$0.039/kWh',
        '100 to 125 USD/MWh',
        '0.70⊄/(kW·h)',
        '0.60⊄/(kW·h)',
        'RM0.2400 to RM0.3186 per kWh',
        '60 €/MWhe to 45 €/MWhe',
        '6.7 to 9.0 ctEUR/kWh',
        '106 to 96 €/Mwh',
        '0.35, 0.28, and 0.25 USD/kWh',
        '115.31 US$/MW h to 150.67 US$/MW h',
        '183 to 368 $/MWh',
        'US$0.866 to US$2.846/m3',
        'US$0.077 to US$0.155/kWh',
        '0.219 €/kWh to 0.485 €/kWh',
        '5.5 c€/kWh to 22.2 c€/kWh',
        '0.216 to 0.254 μ/kWh',
        '$54.68 to $56.41/MW h',
        '$54.62 to $57.35/MW h',
        '$75/MWh to $133/MWh',
        '$0.20 to $20/MWh',
        '66 to 170 $/MWh',
        '6.5. c€/kWh',
        '$69 to $91/MWh',
        '0.30. £/kW. h',
        '0.11. £/kW. h',
        '$0.15/(kW$h)',
        '$0.09/(kW$h)',
        '$0.2109 kWh -1',
        '5.08 ZAR/kWh (∼0.63 US$/kWh)',
        '2.78 ZAR (∼0.34 $/kWh)',
        '68, 82, and 104 €2012/MWh',
        '0.035 to 0.080. €/kW. h',
        '15 to 27 cts/kWh',
        '(3 to 5) USc·(kW·h)-1',
        '41 mills/kWh to 83 mills/kWh',
        'two to nine times',
        '$65 to $130 per net MWh',
        '$ 32 to $46 per MWh',
        '15-year',
        '45.8 to 67.2 dollars per MW h',
        '$108/MW. h to $129/MW. h',

        '$ 0.524/kWh', # should be success = False if value not normalized        
        '$0.2109 kWh -1',
        "$0.287/kWh",
        "$38.69/MWh",
        "20 %",
        "20%",
        "20 %",    
        "5.94-17.82 Mt",
        "0 USD/MWh",
        "about 5% and 8%",     
        "ton 800 per year",
        "800 € ton −1", # TODO: Don't split ton        
        "in the range of 200-250 € ton −1",
        "1,700-2,100 € ton −1",
        "700-900 °C",
        "about 1.23 to about 1.24 million euros",
        "between 1.23 and 1.24 million euros",
        "1.23 g /cm3", 
        "million years",
        "million US dollars per year",
        "1.23 g /cm^3",        
        "1.23 million g /cm3",
        "lots of miles",
        "Various sizes",                         
        "3 $ 2021/kWh", 
        "3.0 $2021/kWh", 
        "3.0 $2021/kWh",  
        "1 km / s", 
        "3.0 $2021/kWh", 
        "3 $_2021/kWh", 
        "3 $ 2021/kWh", 
        "3 $ 2021 /kWh", 
        "1 pint (uk) per minute", 
        "1TWh/a", 
        "120 TWh kg*s^2/(m^2 per year)^3" ,
        "5.3 km", 
        "9 %", 
        "ten $/kWh",
        "1e5 km",
        "1.5 miles per hour",
        "1.23 million EUR",
        "1.23 million €", 
        "1 or 2",
        "1.23 million years",
        "9 3/4 m",
        "9 + 3/4 g",
        "two pathways",
        "$75 billion",
        "2191 MM $",
        "Two years",
        "0.53",
        "12.2 mA cm −2",
        "0.0 V",
        "765 USD per tonne",
        "40 mol %",
        "800 C",
        "610",
        "18 mol%.",
        "790,000 m 2",
        "10 6 €",
        "49.5/36.5/14 (vol %",
        "99.5 mol%",
        "12,000 km",
        "a few rooms",
        "100%",
        "$1,200/ ton, $800/ton, $800/ton, and $1,000/ton",
        "150 pages",
        "70 bar",
        "120 nm",
        "$4.2 mF",
        "3 m",
        "600 MHz",
        "655, 1023, and 1636 electrolyzers",
        "2 2 4 kJ",
        "$8.5 billion",
        "four PCET steps",
        "$0.75-0.8 V",
        "2.44",        
        "one-pass",
        "four types of processes",
        "0.022 mF/cm 2 to 0.13 mF/cm 2",
        "5%-10%",
        "30 wt",
        "three-phase",
        "250-2,000 eV",
        "$24.6/MWh",
        "double",
        "2200 stacks",       
        "3 × 3",
        "$46M",
        "one calc",
        "450 °C",
        "400 mA cm À2",
        "three-stage",
        "-100 mA cm-2 to -500 mA cm-2",
        "19 to 55 mol %",
        "119 USD/t",
        "20 MPa",
        "12%",
        "68, 90, and 101 USD per tonne",
        "6%",
        "1,130 to 1,552 €/t",
        "200 mA cm −2",
        "1 mole",
        "$1,200/ton, $800/ton, $800/ton, and $1,000/ton",
        "43.99 $ millions",
        "95.8%",
        "$0 to $6/kg",
        "1936 €/t",
        "0.31-0.50 t/t",
        "two or more atoms",
        "1, 1, 3, and 2 years",

        "zero-waste",
        "10 GW",
        "77%-87%",
        "100,000 simulations",
        "65%",
        "11%",
        "480 cm − 1",
        "− 75 mA cm −2",
        "36.4 GW",
        "several studies",
        "6 to 150 MW",    
        "86%)",
        "6%).",
        "$1080/m 2 ($300/kW)",
        "50 mL",
        "20 hours",
        "three categories",
        "couple of CO 2 and CO electrolyzers",        
        "92.4%",
        "11.7 wt",
        "25 ℃",
        "4 mm",
        "single-electron",
        "$11 billion",
        "30-85%",
        "$$980/t",
        "1.7%",
        "1095 MM$.",
        "216 times",
        "1803 €/t",
        "1000 Euro",
        "60%.",
        "2.3%",
        "141 billion",
        "two main competitive pathways",
        "$3¢/kWh",
        "5-10%",
        "5 mV s −1",
        "0.4 −0.23",
        "102%",
        "36.4 to 68.4 kt",
        "four selected potentials",
        "1 year",
        "53.6%",
        "− 0.5 V",
        "−2.4 V",
        "60% and 90%.",
        "420 mV",
        "15.6",
        "one variable",
        "2.29 $ millions",
        "3,920 and 7,163 €/t",
        "$0.06 kWh À1",
        "140 min",
        "175-225 mA/cm 2",
        "two metals",
        "20-45%",
        "four types",
        "99.5 mol",
        "12.5%.",
        "$0.8 V",
        "1.2 tons",
        "3.3 ct/kWh",
        "several challenges",
        "0.22",
        "411 kJ mol − 1",
        "Two pathways",
        "two heterogeneous metal layers",
        "91%",
        "3-6%.",
        "$0.3−$3.3/kg",
        "3-M",
        "4.1 −1.1",
        "300 mA cm − 2",
        "few years",
        "one",
        "5-20%",
        "13.91, 27.27, 15.21, 24.65, and 44.66 GJ",
        "990 cm − 1 , 821 cm − 1",
        "0.030 metric ton",
        "0.98 g",
        "80-200 TWh of excess power per year",
        "0.08 bar",

        "2.5-5 V",
        "10%)",
        "0.94%",
        "10 and 20%",
        "109% of CO 2 reduction per ton",
        "4 t of hydrocarbons per hour",
        "200/ton",
       
        "0 to 50 USD per ton",
        "10 ton/h",
        "55 wt%",
        "three cell designs",
        "25% to 75%",

        "40.5 million apartments",
        "several products",
        "$0.7 V",
        "89.3%",
        "one-or two-sided",
        "270 ppm",
        "−1.6 V",
        "$5%-10%",
        "$0.03 kWh -1",
        "$2-20 h",
        "0.3 and ∼0.5 Gt",
        "0.651 t CO 2",
        "11.5",
        "15 N",
        "eight chemical products",
        "2,5 V",
        "$0.9/kg",
        "US$0.44 and 0.59 kg −1",
        "ten times",
        "5%, 10%, 15%, and 20%",
        "0.8Mt and 1.05Mt",
        "0.21 million",
        "72%",
        "64.8 TWh/a",
        "$135 cm 2",
        "5.6 kWh/kg",
        "$1500/t",
        "−0.9 V",
        "several common C 2+ chemicals",
        "73 g of CO 2 equivalent per kWh",
        "one specific high-value",
        "100 days",
        "1.5 Å",
        "two types of components",
        "3 mol kg −1",
        "50 MW",
        "US$0.44 and 0.59 kg -1",
        "twostep",
        "27.5 μmol m −2",
        "15%",
        "three types",
        "1000 $/tonne",
        "two main reasons",
        "1,000s of hours",
        "$1250/kW",
        "USD 159 billion",
        "68%",
        "34.8%",
        "two design specifications",
        "0.1-eV",
        "68 and 4 MMT",
        "361-1696 USD per tonne",
        "$2/t",
        "49.7 mA cm −2",
        "0.40 mmol h − 1 cm − 2",
        "56.16 USD/MWh",
        "2-14 nm",
        "0.00",
        "296.8 m 2",
        "4-membered",
        "single",
        "100 MW th",
        "37.6 mA cm − 2",
        "18 environmental indicators",
        "10%.",
        "0.2 A cm −2",
        "32%-60%",
        "0.01%).",
        "2 °C",
        "20 $/MWh",
        "13%",
        "97.2 billion Euro",
        "14%",
        "7.5 m 2 g −1",
        "85%-95%",
        "0.32",
        "$1.2, $1.2, $0.51, $0.21,$ 1.2, and $0.8 kg À1",
        "2200 GW",
        "37-53%",
        "34%",
        "zero single-pass",
        "one final preferred process alternative",
        "5 min",
        "20% wt",
        "0<<0.2 V",
        "25 electroly",
        "8%).",
        "336 kJ mol − 1",
        "0%, 10%, to 20%",
        "86.79, −80. 85, 132.77, 116.25, and 194.38 $ millions",
        "1.05",
        "$0.8−$1.5/kg",
        "$39%",
        "312 mA cm −2",
        "920 $ per m 2",
        "2c/kWh-8c/kWh",
        "0.1%",
        "six times",
        "single-pass",
        "3.65 Å",
        "1340 MM$",
        "three sample injections",
        "2% to 5%",
        "2 mol",
        "1450 cm − 1 (Lewis) and 1545 cm − 1",
        "several issues",
        "0.18 V",
        "500, 200, 1,000 and 500 mA cm −2",
        "two new intense bands",
        "90%.",
        "0.0625",
        "93.8%",
        "98.75 mol",
        "2200 h",
        "4.3 mA cm −2",
        "1.7 V",
        "75 mol%",
        "2,160-2,910 €/t",
        "three times",
        "10 wt.%.",
        "250-500 USD/kW",
        "0.230 Mton/a",
        "several C 2+ products",
        "−0.4 V",
        "77.6%",
        "920 €/t",
        "4% and 9%",
        "98 mol%",
        "− 1.9 V",
        "$7.2/kg",
        "five years",
        "50 and 10%",
        "140 • C",
        "two possible reaction pathways",
        "10 M",
        "80-90%",
        "$94 to $232 per tonne",
        "two electroreduction systems",
        "8,440 h per year",
        "20 Å × 20 Å × 25 Å",
        "650 • C",
        "$0.11 mg Au /cm 2",
        "1000 $ per d",
        "two ventures",
        "0.58 $/kg",
        "751 MW",
        "USD 878.7 million",
        "172.5 TWh/a to 285.7 TWh/a",
        "51.2 tCO 2 kg metal −1",
        "1 −0.37",
        "one specific target product",
        "9 GJ/metric ton",
        "25 110 mA/cm 2",
        "120 mA/ cm 2",
        "25 years",
        "$$10.8/kg",
        "286 and 165 TWh/a",
        "Several reviews",
        "$44 mA/cm",
        "10% and 50%.",
        "$36M",
        "250 households",
        "0.1-10%",
        "85% wt",
        "3.8% and 7.2%",
        "12-electron",
        "25/ton",
        "several modification strategies",
        "30 and 85%",
        "20 °C",
        "99%)",
        "3.65%",
        "4 bar",
        "$0 to $6/kg. There are multiple inexpensive renewable H",
        "290 MMT",
        "12, 12, and 8",
        "two groups",
        "3.174 and 0.0456",
        "8%",
        "0.7 ton CO 2 -eq per ton",
        "700-800 • C",
        "$1.97 kg À1",
        "100 C",
        "180 • C",
        "few studies",
        "1.3 kg CO 2 /kg",
        "Several economies",
        "0.295 kg CO 2 e/kWh",
        "six",
        "6 kWh/Nm 3",
        "1245 GW",
        "12 apartments",
        "2 V",
        "$250/t",
        "500 °C",
        "Three conversion levels",
        "146.3 billion dollars",
        "70, 4, and 9%",
        "22-country",
        "0.76 $ per kg",
        "852.6 and 870 eV",
        "268, 162 and 136 TWh/a per year",
        "1 cent per kW h",
        "two-way",
        "2D-3D",
        "two different CO 2",
        "150%",
        "66 ha",
        "230 MW",
        "3.77",
        "seven side reactions",
        "two bands",
        "15,000 €/m 2",
        "100 mA cm −2",
        "115 USD tonne −1",
        "two methods",
        "$0.01 kWh -1",
        "25% to 50%",
        "2.5",
        "53",
        "2 h",
        "1 H",
        "30 °C",
        "five-bed",
        "two CO 2 electroreduction systems",
        "several assumptions",
        "three groups",
        "1.465 10 À4 mL À1",
        "150 million tonnes (Mt",
        "one distillation unit",
        "67% and 66%",
        "170 ha",
        "2:1",
        "7058",
        "400 USD per kW",
        "two GDEs",
        "0.297 kWh",
        "0.1 M",
        "One year",
        "1-4 h",
        "11.5 tonnes/day",
        "64",
        "one or two methods",
        "400 s",
        "45.4%",
        "20 years",
        "80 $/t",
        "2",
        "0.32, 0.09, 0.12, 0.07, and 0.10",
        "0.5 $/kg",
        "13",
        "−0.99 to −0.42 kg CO 2 equivalent per kg",
        "230 cm − 1",
        "5.94-17.82 Mt",
        "19.9 Mt/a",
        "51%",
        "one typical product",
        "15.4 n-",
        "12.8 billion Euro",
        "40-200 m",
        "400 µl",
        "1, 2 or 3",
        "13.5%",
        "31.4 MMT",
        "five electrocatalysts",
        "three samples",
        "100 µl",
        "10.8%",
        "zero carbonate",
        "750 kJ mol − 1",
        "0.1 to 1.0 A cm −2",
        "200-500 mA cm −2",
        "25 000 kg/h",
        "several mechanisms",
        "two other important parameters",
        "2 mg ml −1",
        "88.44 mA cm −2",
        "$0.01 to 0.05 kWh −1",
        "0.5 M-4",
        "50%",
        "20 mL/min 85%",
        "100 metric tons per day",
        "200-mm",
        "70%)",
        "∼22 mol%",
        "0.01-0.45 USD/kWh",
        "97 ppm",
        "20 stages",
        "1-20 h",
        "30 wt %",
        "1 bar",
        "half-cell",
        "2000 €/t",
        "1.68 V",
        "$1.4-1.45 V",
        "408 trillion RMB",
        "63.8 wt.%",

        "− 1.37 V",
        "1000 kt/year",
        "5%)",
        "855 eV",
        "55.9 GW",
        "263 million tons",
        "$90%",
        "12.37 mmol mg −1 h −1",
        "210 kPa",
        "150 Mt/ year",
        "40.8%",
        "100m",
        "49-65%.",
        "55%",
        "8.314 J (mol K) −1",
        "4.3 Mtons/year",
        "40% (200 mA/ cm 2",
        "107.6 C",
        "Several reports",
        "0.3%",
        "340 ppm",
        "four groups",
        "3.0 V",
        "300 million people",
        "21.9%",
        "7 mol%",
        "14.7 wt %",
        "4 M",
        "48%",
        "3000 and 4000 full load hours",
        "0.35 $2021/kWh",
        "two product streams",
        "70 °C",
        "0.29 $2021",
        "350 ppm",
        "30.94 kJ g −1",
        "85-90%",
        "three different energy scenarios",
        "$1/kg",
        "81%",
        "0.22 V",
        "17 to 16 t CO 2eq /t",
        "33 mM",
        "3-5 nm",
        "45 $ per MWh",
        "500 mA/cm 2",
        "10 tons/h",
        "28 €/metric ton",
        "26 eV",
        "1 metric ton CO 2 per metric ton",
        "1−10%",
        "29%.",
        "0.01 mmol d − 1 mL − 1",
        "10 ppm",
        "Three remaining process alternatives",
        "293 K",
        "0.46 mol L − 1",
        "various",
        "4 products",
        "6.5 bar",
        "four critical parameters",
        "0.2 and 4 A/mg",
        "25 • C",
        "several years",
        "1 to 0.22",
        "180 °C",
        "$275 mA/cm 2",
        "−1.5 V",
        "99.5",
        "94.6 wt.% (96.5 vol%)",
        "91.6%",
        "$41M",
        "$1.73 h À1",
        "1,200/ton",
        "two different cell configurations",
        "5 mA cm −2",
        "Several reactor designs",
        "800 archetype buildings",
        "24 h",
        "2.5 V",
        "100 archetype buildings",
        "0.02$-0.03$/kWh",
        "800 buildings",
        "1 metric ton",
        "15 Å",
        "several electrolytes",
        "20-year",
        "2.8 V",
        "275 USD per tonne",
        "84.1 and 87.7 eV",
        "US$0.25-1.00 kg −1",
        "$13 to 14",
        "0.9 V",
        "0.51 kgCO 2 kWh −1",
        "1200 A/m 2",
        "84 and 51 TWh/a per year",
        "9.5 mA cm −2",
        "17 and 25 GT/ton",
        "110 ppm",
        "40-60 s",
        "91.2%",
        "83%",
        "three sections",
        "100-400 µm",
        "80 to 100%",
        "213 to well above 300 g/kWh",
        "16 to 45 mol %",
        "3.95 and 4.70 V",
        "95.6%",
        "0.01 $/kWh",
        "5000",
        "two or more electrocatalytic materials",
        "0.33",
        "2 • C⋅min − 1",
        "several publications",
        "96,485 C mol −1",        
        "5%Þ and high ð$ 25%Þ",        
        "100, 150, 200, 250, 300, and 350 • C",
        "several orders of magnitude",
        "2 bar",
        "single catalytic material",
        "5 nm",
        "twodimensional",
        "6 to 7 mA cm −2",
        "50, 20, 20, and 10%",
        "0.08 $2021/kWh",        
        "1 kW per m 2",
        "75-80%",
        "3.5 V",
        "several overwhelming advantages",
        "0.02-0.03 $ per kW per h",
        "1350 and (band G) 1600 cm − 1",
        "0 USD/MWh",
        "60−80%",
        "50 mM",
        "30−100 ppm",
        "9.3 mA cm −2",
        "1.5418 Å",
        "0.2 A/cm 2",
        "three different processes",
        "single electrolyzer",
        "90.8%",
        "23.2% and 27.6%",
        "0.03 $2021/kWh to over 1.00 $2021/kWh",
        "300 mA cm −2",
        "5%-13%)",
        "$$1,900/t",
        "28%).",
        "19.56 GJ",
        "two electro-reduction pathways",
        "38 Mt/year",                
        "$3.33 A/mg",
        "1.8 m",
        "three liquid products",
        "single-atomic",
        "5.0 ¢/kWh",
        "2.5 Gt",        
        "$ 70 per (t",
        "$2.48 and 2.06 kg −1",
        "260 million tons",
        "45, 59, 66, and 101 USD per tonne",
        "Two valuable chemicals",
        "20 to 100%",
        "10 years",
        "240-mV",
        "361 and 1696 USD per tonne",
        "60",
        "6 nm",
        "87%",
        "1500 Mt of CO 2 per year",
        "5%",
        "two analyses",
        "1/2",
        "2p 3/2 / 3d; $853 eV",
        ">50%",
        "30000 USD/p",
        "several parameter",
        "27 investigated metals",
        "three conversion processes",
        "0 to 50 USD per MWh",
        "<1000 $/tonne",
        "10-60 bar",
        "0.5 wt %",
        "1 cm 2",
        "95.57 wt.% (97.3 vol%)",
        "2000 ho rl ess",
        "20 C-50 C",
        "several figures of merit",
        "32 319 kW",
        "22 mol",
        "two better-resolved bands",
        "99.9%",
        "367 MW",
        "half of",
        "$50/tonne CO 2",
        "one hundred times",
        "two PSA units",
        "two types",
        "three halogen-modified Cu",
        "2 ppm per year",
        "$1.16/kg",
        "six to threefold",
        "two syngas utilization routes",
        "1Acm À2",
        "$0.02/kW h",
        "85% or 60%",
        "21.2 TWh/a to 51.44 TWh/a",
        "14.9 t/h",
        "250-nm",
        "three main steps",
        "133.4 GW",
        "four clean energy sources",
        "0.2 V and 0 V",
        "0",
        "744-1696 USD per tonne",
        "350 • C",
        "−0.35 V",
        "99.999",
        "7.5 ct/kWh",
        "17.1%",
        "one-and two-person",
        "single building",
        "7 kWh/m",
        "few full load hours",
        "99.7 mol%",
        "1000 µm",
        "$125 billion",
        "1.04 mW cm −2",
        "several magnitudes",
        "700 o C",
        "one flame ionization detector",
        "1580 cm − 1",
        "second",
        "0.031 mF/cm 2",
        "23.26%",
        "30 ml min −1",
        "0.50 V",
        "10 −5 eV per atom",
        "US$2 kg −1",
        "− 1.09 V",
        "39 Mton",
        "millions of individual buildings",
        "five process alternatives",
        "1 wt%",
        "6",
        "6.6 mF",
        "4%",
        "two per CO 2",
        "$60M",
        "5.8%.",
        "341",
        "51%.",
        "Several SACs",
        "Several reactions",
        "two separation steps",
        "4 cm − 1",
        "100 metric ton CO 2 per day",
        "55.4 GW",
        "40 mM",
        "Two other factors",
        "330 t",
        "pH 7 and pH 10",
        "several kinds of promising and",
        "10 wt %",
        "US$105.2 billion",
        "7% to 16",
        "two temporally opposing effects",
        "53 carbon pricing initiatives",
        "$450/kW",
        "33%",
        "24 CO 2 molecules",
        "1.33 hPa",
        "250 °C",
        "several electrolyzer suppliers",
        "0.67 −0.54",
        "$115 billion",
        "two aspects",
        "1 ppmv",
        "0.5 m 2",
        "65%-92%",
        "98% and 80%",
        "half-or full-cell",
        "4.7-5.25 V",
        "single device",
        "$1 trillion",
        "$0.753/kg",
        "one level",
        "2D-2D, hybrid 1D-2D",
        "13 years",
        "83.2%",
        "21.8 billion Euro",
        "12.1 wt.%",
        "$0.031 mF/cm 2",
        "few research",
        "several different products",
        "several concrete systems",
        "4 times",
        "29",
        "2-fold",
        "−1.75, −1.8 and −2.1 V",
        "1.3 PW h",
        "85%-86%).",
        "1.5 and 1.2 V",
        "small number of archetype buildings",
        "91.86 (CO) and 137.84 (HCOOH) $ millions",
        "6.9 mA cm − 2",
        "pH 0",
        "45.55 times",
        "8 −1.8",
        "two years",
        "few recent studies",
        "99.99%",
        "13%)",
        "pH 3.1-4.4",
        "1.32 $ per kg",
        "76 Euro/ton",
        "20,000 tonnes",
        "3 ⋅g − 1",
        "10 €/t",
        "50-200 bar",
        "Six major CO 2 electroreduction products (that is, HCOOH",

        "425 ∘ C",
        "500 €/metric ton",
        "97%.",
        "173 °C",
        "two-fold",
        "66%",
        "+-20%.",
        "240 mM",
        "2 moles",
        "four exceptions",
        "0.1 t CO 2 /MWh",
        "4500 kWh/year",
        "0.0391 kg CO2 per scm",
        "25 bar",
        "22%",
        "39 m 2",
        "90%",
        "two step",
        "$84/ t",
        "59 to 79 m 2 per household",
        "20.6 m 2 g −1",
        "113.2 TWh/a",       
        "$40/MWh",
        "44 TWh/a",
        "1.2 eV",
        "1,700 cm −1 and 1,560 cm −1",
        "7.0",
        "18.0 MΩ cm",
        "1700 $/ton",
        "two factors",
        "200 mA cm À 2 Þ",
        "137 EJ",
        "32 kWh/t",
        "2.5 billion kW",
        "Several studies",
        "0.84 cm 2",
        "32-bit",
        "1 GW",
        "0.35 kgCO 2 kWh −1",
        "0.003 V",
        "24%",
        "37% and 30%",
        "53%",
        "1.3 A cm −2",
        "0.17 A/cm 2",
        "382.3 billion Euro",
        "300 mA/cm 2",
        "2.3 Å",
        "970 cm − 1",
        "0.1 to 0.5 A cm −2",
        "21%",
        "10 MW h per metric ton",
        "3 h",
        "5 mol",
        "16.1%.",
        "3000 h",
        "1 kg",
        "100 to 500 mA cm −2",
        "0.3-1.8 t/h",
        "100",
        "three main clusters",
        "92.0%",
        "0.45 V",
        "96.8%",
        "1.3%",       
        "0.5 M",
        "229 USD per tonne",
        "zero CO 2",
    
        "0.03 $ 2021 /kWh",
        "0.210 + 0.058 × pH",
        "several other large-scale processes",
        "zero-carbonate",
        "400 • C",
        "3.38",
        "76% and 89%",
        "1 to 9 years",
        "5500 total turnover number",
        "0.035 $ per kW per h",
        "43%.",
        "201 million tons",
        "$4.5 kg À1",
        "64%",
        "95.4%",
        "single-atom",
        "40 mL/min",
        "three steps",
        "57%",
        "$377 mA/cm 2",
        "0.76 GJ tCO 2",
        "0.0211 t CO 2",
        "2p 1/2 / 3d; $870 eV",
        "550, 765, and 1271 USD per tonne",
        "18%",
        "− 0.84 V",
        "two hundred individual cells",
        "3 mol%",
        "80 mA cm −2",
        "30.2 mA cm −2",
        "$ 10%",
        "100 cells",
        "6 Mt yr −1",
        "0.96 ± 0.78 $/kg",
        "single-crystal",
        "$0 to $6 per kg",
        "170 Mt",
        "600 mA/cm 2",
        "single report",
        "92",
        "1/0.74",
        "several forms",
        "30 wt.%",
        "161 of",
        "three-dimensional",
        "160 °C",
        "100 studies",
        "2.0 m",
        "45",
        "10-15 nm",
        "51.9 Mt/a",
        "5 wt",
        "1,000/ton",
        "92%",
        "one molecule",
        "36.95º",
        "1.0 V",
        "two stage",
        "532 nm",
        "100-year",
        "40 €/MWh",
        "99.2 vol%",
        "− 1.18 V",
        "$2.9/kg",
        "2.4 Mt",
        "4.5 −0.46 V",
        "five process routes",
        "six different gas separation processes",
        "15",
        "$23%.",
        "99.5 mol%.",
        "two oxides",
        "49.9 GW",
        "80%",
        "20 €/MWh",
        "97",
        "4",
        "3,920 to 7,163 €/t",
        "417.11 ppm",
        "39.2%",
        "560 million dollars",
        "22.9%",
        "70 individual stacks",
        "1",
        "550 and 700 • C",
        "10 mA cm −2",
        "0.7",
        "20.7 wt.%",
        "20 wt%",
        "3.1 ton CO 2 -eq per ton",
        "37 gigaton CO 2 per year",
        "0.42 GJ",
        "80 at",
        "1.01 V",
        "60 to 100%",
        "four more process alternatives",
        "2.0-2.2 V",
        "1.1 M",       
        "80.3%",
        "7 and 9%",
        "− 0.87 V",
        "517.1 µmol cm −2 h −1",
        "$15/MWh",
        "10 MW",
        "two gas compartments",
        "ten-fold",
        "$0.4 V",
        "−0.6078",
        "52%.",
        "$0.04 kWh À",
        "400 ppm",
        "45%",
        "110 × 10 6 tons/year",
        "77%",
        "100 kta",
        "one volt, the NER values of CO, CH 4 , HCOOH",
        "21C",
        "96 485 Cmol À1",
        "−0.6130 t",
        "two-stage",
        "10,000/m 2",
        "few advantages",
        "$0.02 kWh -1",
        "2.0 M",
        "750 mA/cm 2",
        "$2.50 and 2.06 kg -1",
        "two tools",
        "86%",
        "0.30 eV",
        "$30/tonne",
        "two- electricity",
        "100 bar",
        "63%",
        "billion-dollar",
        "0.2, 0.99 and 0.9",
        "1.56",
        "several hypotheses",
        "five metals",
        "100 h",
        "840 €/metric ton",
        "one year",
        "40 to 50%",
        "9.03 mA cm − 2",
        "seven key reasons",
        "20%",
        "800 mA/cm 2",
        "30%.",
        "$0.02/kWh",
        "200 km",
        "40 years",
        "45 mA cm −2",
        "2%",
        "13.8 ct/kWh",
        "two non-renewable energy sources",
        "one paper",
        "zero GHG",
        "two N atoms",
        "two pressure swing adsorption (PSA) units",
        "76.0 Mt/a",
        "200 Mt",
        "5730 USD per tonne",
        "1.2 × 3.3 cm 2",
        "eight-electron",
        "50 mm",        
        "several possible routes",
        "0.30 t/t",
        "2.4 V",
        "five fold",
        "850 • C",
        "36 kt",
        "0.58 eV",
        "0.26 V",
        "Nine methods",
        "three-membered",
        "20",
        "1000 $/ton",
        "0.0293 t CO 2",
        "0.24",
        "862 Mt CO 2 e per year",
        "0.05 eV Å −1",
        "five to ten archetype buildings",
        "half maximum",
        "four-person",
        "38%",
        "1.19",
        "four major products",
        "25 C",
        "50 mA/cm 2",
        "96%.",
        "+0.0 V",
        "$47,000",
        "40.8 mA cm − 2",
        "1.5 cm⋅μmol − 1",
        "0.2 to − 0.6 V",
        "three-electrode",
        "− 0.82 V",
        "three to four times",
        "178.7%",
        "5.5%",
        "15-25 s",
        "5.9 h − 1",
        "3 mm",
        "90.456 $ millions",
        "1,050 €/metric ton",
        "3.2 kg CO 2 per kg",
        "1.75 kg CO 2e /kg",
        "350 °C",
        "0.5 V",
        "12.4%",
        "0.56",
        "0.5 mg cm −2",
        "12.64, 35.88, 19.67, 63.4, 26.77 MJ cm −3",
        "$2.3/kg",
        "1M",
        "$213 cm 2",
        "16.5 CH",
        "65 to 70 inches",
        "5-10 Euro/t",
        "0.058 metric ton",
        "30 %",
        "ten kinds of metal",
        "60 €/MWh",
        "1.2 V",
        "80.0%",
        "281.5 GW",
        "7.4%.",
        "1.229 V",
        "1-2%",
        "52 µl",
        "10%",
        "1-2 μm",
        "20 and 80 wt %",
        "13 mol%",
        "20 million",        
        "80%.",
        "35/45 mesh",
        "5 • C/min",
        "232/t",
        "41 %o ft",
        "22%.",
        "3.621 Å",
        "36 and 68 kt",
        "19.7%",
        "1.4 V",
        "990 cm − 1",
        "$0.001 kg",
        "2 M",
        "220-350 o C",
        "100 mA/cm 2",
        "1,000 kg",
        "81.9%",
        "25 2.40 V",
        "five times",
        "92%.",
        "$0.12 kWh",
        "300 • C",
        "two additional (worst and best case) scenarios",
        "200-270 USD/kW",
        "56%.",
        "$$8.5/kg",
        "35 mol/m 3",
        "several gases, liquids",
        "−1.08 and −2.20 metric ton CO 2 per metric ton",
        "$70/ton",
        "750 C",
        "99.99 mol%",
        "99%.",
        "300°C",
        "− 0.85 to − 0.5 V",
        "several recent lab-scale studies",
        "two important parameters",
        "1003 more electrical",
        "4.8 ton CO 2 per ton",
        "$6.2−$9.2/kg and $3.9−$6.9/kg",
        "150 mA cm −2",
        "several engineering approximations",
        "several limitations of metals",
        "0.5 MJ/kg",
        "1.39 versus 1.67 eV",
        "several pathways",
        "20 USD per ton",
        "100%.",
        "À6",
        "0.60 $ per kg",
        "few buildings",
        "15 min",
        "one metric ton",
        "45 cm 3 /g",

        "$150 Mtons/year",
        "70",
        "1.6 V",
        "$6/kg",
        "18 million tons",
        "5.45 mmol/m 2sec",
        "10% or 15%",
        "7%.",
        "1.9%",
        "150 h",
        "1.36 electrons",
        "34 t/ h",
        "77.11 ppm",
        "$0.03 per kWh",
        "200 archetype buildings",
        "9.37 km 3",
        "0.6",
        "30 and 15 wt%",
        "1%",
        "−20 kg CO 2e /kg",
        "4,241 publications",
        "5 h",
        "1:1",
        "100 ppm",
        "1.82",
        "$360 billion",
        "0.8 t CO 2 /t",
        "2 mg cm -2",
        "0.6%",
        "3D",
        "5 sccm",
        "2.5%",
        "298 K",
        "100%",
        "1 t/h",
        "26,771 h −1",
        "228 articles",
        "0.12 V",
        "0.38",
        "2.25 V",
        "39.4 million",
        "several electrocatalytic NO 2 − RR studies",
        "$0.8/kg",
        "30-40%.",
        "1200 Mt",
        "three distinct scenarios",
        "few countries",
        "two hundred million metric tonnes per year",
        "60 mol% and 46 mol%",
        "3.70 g",
        "0.85 V",       
        "single-variable",
        "10 to 200%",
        "6000 h",
        "−1.23 V",
        "one factor",
        "10×10 cm 2",
        "253.4 GW",
        "∼10%",
        "− 1.2 V",
        "100%-",
        "46.9",
        "three scenarios",
        "two possible pathways",
        "two facets",
        "$20,000/m 2",
        "one product",
        "51.5%",
        "$0.06 kWh À",
        "0.59 ton CO 2 per ton",
        "single compression step",
        "0.54 $2021/kWh to 0.29 $2021/kWh",
        "10.3%",
        "2.6 V",
        "2 kJ",
        "5%-10%.",
        "50% and 34%",
        "~70%",
        "368 Mt",
        "2 of 9",
        "65 Euro/m 2 per living area",
        "0.8 V",
        "42% and 31%",
        "9.9 mA cm −2",
        "150 mA/cm 2",
        "0.4",
        "0.5 A cm −2",
        "0.541 V",
        "2 mm",
        "1400 $/ton",
        "1 to 10 bar",
        "0.15 M",
        "0.86 eV",
        "$4.5M",
        "2.58 ppm per year",
        "95%-99%",
        "two or more catalytic materials",
        "$20/MWh",
        "16 GJ/metric ton",
        "5 and 12 bar",
        "−0.75 V",
        "730 studies",
        "35 to 15 wt.%.",
        "1.94 mM",
        "16.9 GWh to 12.8 GWh",
        "3.3%",
        "0.05 M",
        "two or more carbon atoms",
        "10−30%",
        "2.5 ton CO 2 per ton",
        "−2.31 to −1.26 V",
        "0.6130 t",
        "8000 h/year",
        "27.1 million households",
        "45 to 79 g/kWh",
        "85%, ~80%, and ~50%",
        "90 s",
        "660 MW",
        "CO 2",
        "814 MMT per year",
        "56 mA cm À2",
        "95 wt.%.",
        "1.00 $ per kg",
        "8760 hours",
        "49%",
        "90.5%",
        "singleatom",
        "1350 and at 1600 cm − 1",
        "6-12 GW",
        "several advantages",
        "0.25 kWh/m 3",
        "1.3 MWh",
        "$10,000/m 2",
        "350 o C",
        "2 cm",
        "mol/cm 2 s",
        "1.98%, 1.32%, and 0.87%",
        "99 wt %",
        "2.6 mol/L",
        "200 mA cm − 2",
        "0.0169 and 0.0055 t CO 2",       
        "hundreds of possibilities",
        "$0 to $150/t CO 2",
        "1.1 V",
        "5 min-2 h",
        "16 kg CO 2e / kg",
        "10.000 h",
        "10 A",
        "1 tonne/ year",
        "4-6 USD/t",
        "30%).",
        "50°C",
        "127.5 μg h − 1 mg − 1 cat",
        "53%.",
        "26 mA cm −2",
        "threecompartment",
        "two percentages",
        "0.34",
        "9419.6 million tons of CO 2",
        "$1.5-1.55 V",
        "73.0",
        "2.9/kg",
        "2,900 kJ",
        "one electron",
        "1.23 V",
        "25.7 GW",
        "250 mA/cm 2",
        "−5 kg CO 2e /kg",
        "2000 € per metric ton",
        "3 CO 2 molecules",
        "7",
        "23 n",
        "3.9-4.4 V",
        "1.17 V",
        "20 MW h per metric ton",
        "16%-36%",
        "2.8%",
        "30 mL/ min",
        "single residential",
        "Various nation-specific works",
        "700 USD/kW",
        "six-electron",
        "120−180 °C",
        "5",
        "$0.44 and 0.59 kg -1",
        "6.9 billion Euro",
        "$1.77−$2.05/kg",
        "two peaks",
        "22",
        "0.3",
        "81.2%",
        "370 and 403 cm − 1",
        "1350 cm − 1",
        "370 GW",
        "99.7",
        "99.9 wt.%",
        "$50/metric ton",
        "0.10 metric ton",
        "800 €/t",
        "21.8",
        "1000 mA cm −2",
        "139 standard cubic centimeters per minute (sccm",
        "several (by)products",
        "10 vol%H 2",
        "− 0.78 to − 1.18 V",
        "98-100%",
        "0.9",
        "3 atm",
        "0.45",
        "two aforementioned strategies",
        "0.23 to 0.44 t ethylene/t",
        "$175 mA/cm 2",
        "0.006 cm À2",
        "single atoms",
        "$1080/m 2 ($300/kW",
        "120 °C",
        "22 mol%",
        "70%",
        "475 mA/cm 2",
        "two different types of catalyst",
        "5-6 kWh/m 3",
        "3.14 metric ton",
        "one CO 2 molecule",
        "cm 2 s",
        "50,000 kg d −1",
        "200 mA/cm 2",
        "0.17 V",
        "$70%",
        "10 to 50000 units per annum",
        "several process optimizations",
        "500 and 225 €/metric ton",
        "25 archetype buildings",
        "23.2 million of",
        "0.7 eV to 0.59 eV",
        "60 atm",
        "300/metric ton",
        "0.065 kgCO m −2 h −1",
        "$0.2-0.3 kg −1",
        "12.5% and 90%",
        "two of the five process alternatives",
        "1-6 h",
        "five un-electrified villages",
        "8 mol",
        "105 new studies",
        "$50%.",
        "27 73",
        "124 years",
        "700 € per metric ton",
        "two CAPEX graph lines",
        "100 mA/ cm 2",
        "48 hours",
        "100.6 MHz",
        "5.38 GW",
        "four products",
        "4900 Mt",
        "0.13 metric ton per MW h",
        "one ton",
        "two electrolytic components",
        "5% and 8%",
        "25%).",
        "$4.6 3 10 5 kJ steam / kg",
        "25 Mt/year",
        "4 moles",
        "750-950 o C",
        "8.314 J mol −1 K −1",
        "156 mA cm −2",
        "250 kW −1",
        "744 and 1696 USD per tonne",
        "99.0 wt %",
        "5 mol%",
        "− 0.6 V",
        "1-3%",
        "23%",
        "80 $/ton or 0 $/ton",
        "13.8 GJ/ton",
        "350 days per year",
        "17 and 18 years",
        "100 kt",
        "thousands of tons of CO 2 per day",
        "2.1%",
        "0.15406 nm",
        "905-1912 USD per tonne",
        "three main determinants",
        "29 Si NMR (1p",
        "0.2196 GJ per t",
        "800,000 years",
        "0 V",
        "852.71 eV",
        "109%",
        "0.25-0.55 µm",
        "two CO 2 recycle streams",
        "2.0 V",
        "0.045 USD/kWh",
        "13.5 TWh/a",
        "$0.2 V",
        "0.10 to 0.17 t/t",
        "several research studies",
        "five electrochemical technologies",
        "0.022 mF/cm 2 to 0.04 mF/cm 2",
        "3 V",
        "three different scenarios",
        "$ 7",
        "500 rpm",
        "21 to 93%",
        "several months",
        "66%.",
        "7 kWh/Nm",
        "two maxima",
        "30 MW",
        "1.3 V",
        "$230 billion",
        "one SFH",
        "two main goals",
        "0.88 V",
        "10 mol%",
        "69.42%",
        "two transition metals",
        "1,000 hours",
        "66 million €",
        "$2.4-3.5 V",
        "two chambers",
        "10,000/ m 2",
        "1 mol",
        "six protons-electrons",
        "1.04 eV and − 1.12 eV",
        "0.01 eV Å −1",
        "854 cm − 1",
        "a few hours per year",
        "4 wt.%",
        "5−12 bar",
        "1D",
        "2200 windmills",
        "144 mA/cm 2",
        "4000 h",
        "1000 full load hours",
        "93.5%",
        "3-5%",
        "-4% to + 2%",
        "1.6 mm",
        "0.1 A cm −2",
        "100 • C",
        "6.2 × 10 −3 wt%",
        "a few studies",
        "85%.",
        "12.5 times",
        "0.154178 nm",
        "3 ¢/kWh",
        "7 m",
        "97%",
        "106 cells",
        "+-10%",
        "0.357 times",
        "20 wt %",
        "5−10",
        "0.74 V",
        "120°C",
        "two vital parameters",
        "600-650 • C",
        "$0−$6/ kg",
        "81.3 Mt/a",
        "85%",
        "74, 97, and 109 USD per tonne",
        "1-2 V",
        "($13.5 million",
        "0.01 and 10 m",
        "5.9 years",
        "658 MW",
        "3 years",
        "100 t C 2 H 4 /day",
        "4 t CO 2 /h",
        "three reaction pathways",
        "0%).",
        "single carbon",
        "2°C",
        "− 0.99 V",
        "62%-65%",
        "three years",
        "20 mg",
        "90",
        "50 archetype buildings",
        "three-step",
        "1.90",
        "six electrons",
        "66 to 74%",
        "10 5 metric ton",
        "38 Cu atoms",
        "Several recent techno-economic studies",
        "0.54 $ 2021 /kWh",
        "1.23",
        "54.5°",
        "95.6 wt %",
        "89.7 TWh/a",
        "100 °C",
        "100 years",
        "1.05 kgCO m −2 h −1",
        "10 emerging technologies",
        "16 MMT per year",
        "3.2 GJ/ metric ton",
        "few decades",
        "95%.",
        "0.23 $ 2021 /kWh and 0.29 $ 2021 /kWh",
        "0.41",
        "2−3:1 mole",
        "13.44 mmol mg −1 h −1",
        "single-step",
        "91 C",
        "two orders of magnitude",
        "four layers",
        "1.48 V",
        "−1.3 V",
        "90 TWh/a",
        "88 billion Euro",
        "− 30 CO 2",
        "CO 2 per ton",
        "0.2 bar",
        "1.36 times",
        "several TEA",
        "3,437-3,644 €/t",
        "450 ppm",
        "2 22 76",
        "0.8",
        "4.45 years",
        "40-60 nm",
        "thousands of hours",
        "two drops",
        "2mmt",
        "8.5 −0.45 V",
        "78 ton",
        "$25−50/ton",
        "50 USD/t",
        "920 $/m 2",
        "two pressure equalization steps",        
        "465 mA cm À2",
        "3.14 × 10 5 metric ton CO 2 per year",
        "323.15 K",
        "50MW",
        "2V",
        "two CO molecules",
        "50",
        "2,8 • C⋅min − 1",
        "two industries",
        "30 and 15%",
        "0.24 $2021",
        "3%",
        "zero loss of CO 2",
        "750 °C-875 °C",
        "540 MM$",
        "225 and 300 ∘ C",
        "30.94 kJ/g",
        "one more electron",
        "six studied electrochemical CO 2",
        "40%-50%",
        "Two main routes",
        "two) steps",
        "$0.4 and $0.8 V",
        "$10/ tonne",
        "1 M",
        "2040",
        "$10 m",
        "4.6 €/metric ton",
        "$60 tonne À1",
        "2D",
        "$2/kg",
        "35%",
        "0.5-eV",
        "− 1.6 V",
        "300 W",
        "$300/kW",
        "Five hypothetical cases",
        "two active sites",
        "101.3 kPa",
        "94.2 t of high-pressure steam per hour",
        "30 times",
        "$155 billion",
        "2 %",
        "45.1 Mt/a",
        "3 M",
        "90.7%",
        "$3.1 × 10 −3 /mol",
        "0.2",
        "300−1000 mA/cm 2",
        "$250/tonne",
        "2.2 PW h",
        "−0.9, −0.95 and −1.3 V",
        "76%",
        "40%.",
        "6.9 ¢/kWh",
        "12 mol",
        "two or more mechanistically distinct reaction steps",
        "two-dimensional (2D",
        "120 eV",
        "30 s",
        "161 case studies",
        "two consecutive industrial processes",
        "81.7%",
        "60% to 90",
        "326.4 mA cm − 2",
        "150 nm",
        "1.74 −0.95",
        "0.39, 0.13, 0.31, 0.13, and 0.18, respectively",
        "8.3 €/GJ",
        "1 ct/kWh",
        "300 −0.68",
        "12 times",
        "970 and 1035 cm − 1",
        "50%-90%",
        "− 0.5 and − 0.8 kg CO 2 -e per kg",
        "30 mins",
        "0%",
        "50%.",
        "600 • C",
        "950 °C",
        "0.7 eV",
        "several technical and economic challenges",
        "77",
        "3.0 Å",
        "900 °C",
        "660 ha",
        "98 wt",
        "10 5 metric ton per year",
        "40 h",
        "20%-30%",
        "1 MW",
        "several different anodic reactions",
        "5.5 −1.7",
        "five drops",
        "Several parameters",
        "1% to 25%",
        "250 mA cm −2",
        "160.3 GW",
        "3.5 GJ/t",
        "$1.0 × 10 −3 /",
        "11 −0.47",
        "10-20 mV",
        "two optimization problems",
        "one-step",
        "50-60 μm",
        "600 to 1200 $/tonne",
        "209.1 TWh/a",
        "133.4 GW to 142.3 GW",
        "<$3,000/m 2",
        "18 times",
        "7.5 mA cm −2",
        "46%",
        "three compressors, coolers and phase separators",
        "5.38%",
        "14",
        "$$1.1/kg",
        "3.01",
        "38.1%",
        "−10 °C",
        "6.27 $ millions",
        "few minutes",
        "2.48 ± 1.83 $/kg",
        "half price",
        "6.3 multi-family houses",
        "32 22%",
        "15 years",
        "17.8%",
        "−1.01 V",
        "2 ⋅g − 1",
        "3 times",
        "75%",
        "1.3 billion tons",
        "0.99 $2021/kWh",
        "10 times",
        "100 nm",
        "10 • C/min",
        "three birds",
        "10-20 nm",
        "1.04 eV",
        "52",
        "19.8%",
        "single family",
        "$50%",
        "35 €/MW h",
        "$500/m",
        "12 h",
        "one-dimensional",
        "1 MW h",
        "0.06/ kW h",
        "zero-",
        "4.6 ¢/kWh",
        "1.9 V",
        "3 MW per turbine",
        "two main aspects",
        "84%",
        "14.6 GW",
        "$24.6 per MWh",
        "two calculator blocks",
        "100 ton/day",
        "$50",
        "800 µl",
        "25%",
        "70 stages",
        "4% per year",
        "30 years",
        "one step",
        "800 mV",
        "$0",
        "9%",
        "0.28 to 0.06 $ per kW per h",
        "1.45 billion",
        "$0−$6/kg",
        "Several cutoff criteria",
        "1,100-0 eV",
        "1.4 billion €",
        "− 0.89 V",
        "− 1.1 V",
        "$1 per gasoline gallon",
        "one cost curve",
        "15 °C",
        "70.15 mmol mg −1 h −1",
        "31%",
        "70 €/metric ton CO 2 /year",
        "− 125",
        "300 $/t",
        "0.032 metric ton",
        "few efforts",
        "1.8 cm⋅μmol − 1",
        "0.59 $/kg",
        "half",
        "120 $/t",
        "3 Mt",
        "four different parameters",
        "two distillation columns",
        "17.4 GJ",
        "four times",
        "10 h",
        "0.462 kgCO m −2 h −1",
        "90.9%",
        "single apartment",
        "7%",
        "3.0 t",
        "5 bar",
        "two main components",
        "0.31, 0.14, 0.06, 0.14 and 0.22",
        "70 electrochemical flow reactors",
        "8,400 h",
        "11.9 kg CO 2 /t",
        "1.0",
        "1,486.6 and 26 eV",
        "7 48 45",
        "$9%.",
        "$1650/tonne",
        "3.6 eV",
        "2.4% mol",
        "Several attempts",
        "65.2%",
        "13 C",
        "470 • C",
        "one arrow",
        "three additional P-E T",
        "1.12, 0.25, and 0.2 eV",
        "1 to 5%.",
        "20 sccm",
        "zero operational costs",
        "− 3.2 mA cm −2",
        "1.2",
        "1 to 5 cent per kW h",
        "920 and 1470 $/t",
        "96,485",
        "two overlapping peaks",
        "−2.32 V",
        "single pass",
        "2−3",
        "50 MJ kg − 1",
        "1300 $/ton",
        "100 t",
        "Zero Energy",
        "15 %",
        "8,440 h",
        "20−40%",
        "2 ¢/kWh",
        "$1200/tonne",
        "− 1.4 V",
        "1.8 ¢/kWh",
        "$130M and $24M/year",
        "500 mA cm −2 to 1 A cm −2",
        "940.95 kJ mol −1",
        "0.53%",
        "two variable input price parameters",
        "0.08 V",
        "1-3 Mt ethylene per year",
        "0.03 and 0.5 mg Au /cm 2",
        "3 mol/L",
        "93.2 CH",
        "5 • C",
        "8.2 × 10 −8 mol cm −2 s −1",
        "90-95 wt",
        "0.1%).",
        "−3.65 V",
        "1.5 and 2. For the design, the number of stages",
        "32.3 GW",
        "300 ∘ C",
        "4 carbon atoms",
        "2 Mt yr −1",
        "15 equivalent",
        "~80%",
        "200°C",
        "64 CH",
        "854 cm − 1 and 821 cm − 1",
        "1 min",
        "0.6078 t",
        "Fifty watts",
        "$0.03 kWh −1",
        "51 mol%",
        "0.01-0.045 USD/kWh",
        "88.5 Mt/y",
        "0.38 kg of CO 2 /kg",
        "19 ton CO 2",
        "10",
        "12.47 mA cm −2",
        "531.7 eV",
        "$44/tonne",
        "1.80",
        "5.8 kg/h",
        "2,829 €/t",
        "500 mA cm −2",
        "10 − 6 hPa",
        "few reports",
        "two radical ions",
        "0.4 V",
        "90 kJ/mol",
        "449 TWh/a",
        "1:2",
        "0.61",
        "$2.68/gge",
        "45 GW",
        "Two cases",
        "20 different production paths",
        "Two-step",
        "20 min",
        "116 Mt/year",
        "345 and 413 kJ/mol",
        "50.8 mA/cm 2",
        "6 mA cm −2",
        "40%",
        "7511 TWh",
        "0.7 V",
        "0.4 M",
        "10,000-20,000 A/m 2",
        "$0.7/kg",
        "30 • to 800 • C",
        "97.57 and 139.05 $ millions",
        "zero valence",
        "9.6 ct/kWh",
        "− 0.79 V",
        "43 €/metric ton",
        "0.18 $ per kg",
        "15 mA/cm 2",
        "4 GtC yr −1",

        "26 chemical compounds",
        "two birds",
        "95%",
        "75% and 91%",
        "40 nm per minute",
        "3-electro",
        "30 n",
        "$1.35 V",
        "$10/tonne CO 2",
        "10 wt.%",
        "factor of 10",
        "0.473 V",
        "1.0 M",
        "0.496 kgCO2eq/kg",
        "four categories of building attributes",

        "3.6-4.0 GJ/t",
        "one of the archetype buildings",
        "10 annually",
        "quarter hourly",
        "$8",
        "single atom",
        "62.7 mA cm −2",
        "157 kt",
        "30 mM",
        "3-5 mol",
        "one process alternative",
        "5 M",
        "0.04 $ per kW per h",
        "339, 468, 537, and 786 USD per tonne",
        "36%",
        "3 USD per tonne",
        "94 • C",
        "5 years",
        "one atom",
        "Half-cell",
        "four parameters",
        "15 and 45 %",
        "three most used reactor designs",
        "0.2 eV",
        "5500 to 12000 kWh/p",
        "single-",
        "− 271 to − 407 meV",
        "35%.",
        "500 eV",
        "zero-gap",
        "78%",
        "five studied cases",
        "24.5 mA cm −2",
        "3,174-3,485 €/t",
        "175 mA/cm 2",
        "185 million metric tons (MMT",
        "40 V",
        "$30/MWh",
        "1.9 ct/kWh",
        "100 MW",
        "96%",
        "6 mol",
        "11 Gt CO 2",
        "single-electrode",
        "83.2%",
        "single metal atoms",
        "0.87 V",
        "0.2 V",
        "two cell systems",
        "three different C E values",
        "− 1.8 V",
        "two products",
        "several aspects",
        "single (100) facets",
        "−0.72",
        "180 million tonnes",
        "400 A/m 2",
        "3.1 ton CO 2 per ton",
        "60 mA cm −2",
        "1.25 mM",
        "0.83 V",
        "40 °C",
        "one electrochemical cell",
        "Two-hundred-fifty-nanometer-th",
        "5mLmin À1",
        "161 studies",
        "1 g",
        "several hundred-hours",
        "391 mA cm −2",
        "602 and 391 € per metric ton",
        "two scenarios",
        "43.1 GW",
        "− 1.0 V",
        "130.3 MHz",
        "99.2%",
        "20 $ per t",
        "50 min",
        "three independent measurements",
        "23 %",
        "− 0.76 V",
        "12.7 years",
        "200 typical buildings",
        "80 + years",
        "3.14 × 10 5 metric ton of CO 2 per year",
        "78.4",
        "three separation parameters",
        "26%",
        "700−850 °C",
        "2 4 kJ",
        "5 mg⋅cm − 2",
        "0.02/kW h",
        "800 o C",
        "2000 full load hours",
        "73%",
        "862 Mtons of CO 2 /year",
        "three reference buildings",
        "$ 5% and $ 22%",
        "91.7%",
        "$1,990,000 per 1,000 m 3 /h",
        "120 USD/kW",
        "three different system boundaries",
        "0.10 t/t",
        "Three decades",
        "3.2 and 0.50 GJ/ metric ton",
        "$$1.0-$1.3/kg",
        "1,331.4 kJ/mol",
        "4:1",
        "0.211 kWh",
        "two decades",
        "366 USD per tonne per volt",
        "several factors",
        "2.7 ¢/kWh",
        "1000 assignments 100 assignments 10 assignments",
        "− 0.8 V",
        "8000 hp",
        "$0.006 kg",
        "250 USD per kW",
        "97.5%",
        "1 ml",
        "0.44 t/t",
        "35 mm",
        "$0.02 kWh À1",
        "509, 585, and 850 USD per volt",
        "6 MW",
        "two electrolysis devices",
        "2.25 Vw",
        "$50/ton",
        "0.5 mol",
        "6−8 kWh/Nm 3",
        "30%",
        "71.9 TWh/a to 80.9 TWh/a",
        "two major reasons",
        "96 485 C mol −1",
        "18 bar",
        "94.6 wt",
        "three potential 2060 energy mix scenarios",
        "4.1",
        "100,000 independent simulations",
        "1.25 v/v%",
        "− 0.97 V",
        "1500 kg per day",
        "−$97M",
        "1.65 m",
        "2.3 V",
        "2.75 times",
        "3 mol%.",
        "98 wt%",
        "− 1.7 V",
        "92.2%",
        "10.6 n-",
        "18C",
        "1050 $/t",
        "116 Mton/a",
        "twelve typical days",
        "743 TWh",
        "few economically dominant technologies",
        "99%",
        "5,000 €/t",
        "3.3",
        "0.48",
        "two",
        "2.5 mg⋅cm − 2",
        "32.4 mA cm −2",
        "21 mA cm −2",
        "3.8 tonnes CO 2 /tonne",
        "15-30 bar",
        "60 min",
        "43.8 mA cm −2",
        "990 cm − 1 and 950 cm − 1",
        "0.72 V",
        "three major drawbacks",
        "4.8 ton",
        "80%-55%",
        "29.7%.",
        "5 to 1 cent per kW h",
        "16 mA cm −2",
        "3.4 wt.%",
        "3-10 years",
        "1.0 atm",
        "830 mA/cm 2",
        "1 atm",
        "0:67 bar",
        "7 M",
        "2 × 10 6 tons",
        "single archetypes",
        "27 Al",
        "two main challenges",
        "0.71 eV",
        "two *CO",
        "25% singlepass",
        "800 ℃",
        "1 mM",
        "15 kV",
        "a few by-products",
        "407.4 ppm",
        "60%",
        "80-200 TWh",
        "$25/MWh",
        "two reactors",
        "104.6 billion Euro",
        "0.02-0.03 USD/kWh",
        "0.232 kgCO2eq/kg",
        "175 mA cm −2",
        "27.4%",
        "47.11%, 42.83%, and 39.26%",
        "6 h",
        "1 86",
        "90 cm 3 /g to 70 cm 3 /g",
        "98 ± 0.7%.",
        "0 to −1.5 V",
        "98%",
        "$0.006cm À2",
        "24.78 $ millions",
        "− 0.9 V",
        "28%",
        "$6.0 × 10 −3 /mol",
        "four carbon atoms",
        "118",
        "0.1 mm",
        "three studies",
        "six different gas separation",
        "$0.04 and US$0.06 kWh −1",
        "283 million metric tons",
        "500 USD/kW",
        "1 A/cm 2",
        "∼11",
        "16 scans",
        "950 cm − 1 , 854 cm − 1",
        "327 kJ mol − 1",
        "9-13",
        "0.32 $ 2021 /kWh",
        "$2.8 × 10 −3 /mol",
        "4 GtC yr −1 or 14.7 GtCO 2 yr −1",
        "three halogenmodified Cu electrodes",
        "1,09 tons",
        "265, 28, and 1",
        "10 t/ h",
        "309.8 TWh/a",
        "4.8:30.6:64.6",
        "5 × 2 cm 2",
        "− 1.3 V",
        "1.18 V",
        "83 studies",
        "400 mV",
        "14 kHz",
        "300 €/ kW",
        "100 mA cm -2",
        "Various works",
        "multiple H 2 sources",
        "three decades",
        "14 or 3 MW",
        "0.33 $ 2021 /kWh",
        "one million years",
        "31.8 mA cm − 2",
        "377 °C",
        "180 s",
        "22 −1.1",
        "3.95 V",
        "4.2 times",
        "$36M/ year",
        "single digits",
        "12 t CO 2 /h",
        "single metal",
        "30 mA cm −2",
        "1 tonne",
        "two neighboring *CO",
        "60-80%",
        "24.65 $ millions",
        "45%.",
        "two electrolyzers",
        "17%",
        "250, 100, 300 and 600 mA cm −2",
        "28,000 m 3",
        "two most important pathways",
        "0.26 to 0.45 tonnes CO 2 /tonne",
        "22 h",
        "17.6%",
        "58%",
        "550 • C",
        "one volt",
        "$3.4-3.8/kg",
        "$180M and $30M/year",
        "600 $/tonne",
        "100 metric ton/day",
        "1 $2021/kWh",
        "5.4%",
        "27",
        "240 °C",
        "300 mg",        
        "3.3 ¢/kWh",
        "$1.1 V",
        "28.3%.",
        "$40/MWh and $50/MWh",
        "1 3 1 cm",
        "25%.",
        "−433.84 $ millions",
        "15 to 45 %",
        "several pieces of",
        "0.5 mg cm À2",
        "1.5 V",
        "three potential power generation structure scenarios",
        "two-staged",
        "131 mA cm −2",
        "two radical anions",
        "$$230 billion",
        "$240 to $525/tonne",
        "7 wt.%",
        "single sites",
        "14 years",
        "800-900 • C",
        "750 °C",
        "100 tons of products per day",
        "$0.30 kg −1",
        "16, 65, and 19 mol %",
        "3 × 3 × 1",
        "20% and 44%",
        "double-layer",
        "14%.",
        "5%).",
        "Three theories",
        "24.5 A g − 1",
        "5 mA/cm 2",
        "several efforts",
        "7.2%",
        "20 MW",
        "4 electrodes",
        "1 V",
        "69 mA cm À2",
        "57.8%",
        "90-95%",
        "several strategies",
        "25.5%",
        "15 mA cm −2",
        "C 2+ product",
        "100 case studies",
        "$10,000",
        "1, 2, 4, 6, and 8-electron",
        "few exceptions",
        "91 mol%",
        "5-year",
        "5-70%",
        "0 V to −1.0 V",
        "3.52-2.22 GJ/t",
        "97.7%",
        "zero-point",
        "$150/t",
        "− 0.80 V",
        "5, 25 and 50 archetype buildings",
        "10 bar",
        "59",
        "77-K",
        "3 Euro/m 2 per living area",
        "20 bar",
        "two thermal conductivity detectors",
        "15 MMT per year",
        "one stone",
        "three major trends",

        "100 %",
        "80 °C",
        "two reasons",
        "600−1200 $/tonne",
        "220 wind turbines",
        "two short-term solutions",
        "three-dimensional (3D",
        "Three important assumptions",
        "one input parameter",

        "$82 billion",
        "500 MW",
        "0.9 mA/cm 2",

        "570 ppm",
        "9.8%",
        "700 • C",
        "50,000 kg H 2 /day",
        "10 nm",
        "$0.12 kWh À1",
        "4,200 €/t",
        "27%",
        "0.25 mm",
        "2.2 V",
        "416.47 ppm",
        "5 times",
        "13 wt.%",
        "11.5%",
        "0.1 V",
        "0.42 V",
        "100 to 800",
        "− 1 V",
        "$1000 per ton",
        "200 °C",
        "0:5 V",
        "82%",
        "52%",
        "170 mA cm −2",
        "23-32%",
        "70 ∘ C",
        "25 °C",
        "1 ton",
        "0.5−0.9 V",
        "7.52 kJ mol product −",
        "221 M€",
        "140 eV",
        "7 in",
        "4.48 × 10 5 metric ton CO 2 per year",
        "8 h",
        "0.4-0.5 V",
        "US$0.17−0.67 kg HCOOH -",
        "$1,512/m 2",
        "10-50 000 electrolyzers per year",
        "37.8 mA cm −2",
        "1 A cm −2",
        "0.8 −0.33",
        ]:
        result = quantity_parser_silent_fail.parse(quantity_string)
        if result["success"] == True:
            # print(f"\nFailed parsing: {quantity_string}")
            quantity_strings_success.append(quantity_string)
        elif result["success"] == None:
            quantity_strings_doubt.append(quantity_string)
        else:
            quantity_strings_failed.append(quantity_string)
            # pp.pprint(result)

    print("\nFailed parsing quantities:")
    for failed_string in quantity_strings_failed:
        print("- " + failed_string)


if __name__ == "__main__":
    start = time.perf_counter()
    test_parse_value_and_order_of_magnitude_separately()
    test_no_unit_qmod_confusion()
    test_quantity_parser_on_single_quantities()
    test_quantity_parser_on_unit_modifiers()
    test_quantity_parser_on_intervals()
    test_quantity_parser_on_lists()
    test_quantity_parser_localisation()
    test_quantity_parser_self_assessment()
    test_quantity_parser_on_modifiers()
    test_quantity_parser_on_scientific_notation()
    test_quantity_parser_on_ratios()
    test_quantity_parser_on_multidim()
    test_quantity_parser_on_negation()
    test_quantity_parser_on_number_words()
    test_quantity_parser_on_placeholder_units()
    test_quantity_parser_with_spelling_and_decoding_errors()
    test_quantity_parser_on_non_physical_units()
    test_quantity_parser_on_cardinals_and_fractions()
    test_quantity_parser_on_imprecise_quantities()
    test_quantity_parser_on_stats_expr()
    test_quantity_parser_additional()
    end = time.perf_counter()
    print("Elapsed time = {}s".format((end - start)))
