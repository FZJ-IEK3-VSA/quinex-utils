import pytest
import time
import pprint
from quinex_utils.parsers.unit_parser import FastSymbolicUnitParser


pp = pprint.PrettyPrinter(indent=1)

def test_unit_parser():
    unit_parser = FastSymbolicUnitParser()
    for unit_string in [
        "€ ton −1",
        "km / s", 
        "g /cm3",
        "$2021/kWh", 
        "$_{2021}/kWh", 
        "$_2021/kWh", 
        "$ 2021/kWh", 
        "$ 2021 /kWh", 
        "pint (uk) per minute", 
        "TWh/a", 
        "TWh kg*s^2/(m^2 per year)^3", 
        "km", 
        "%", 
        "$/kWh"
    ]:
        print(unit_string)
        pp.pprint(unit_parser.parse(unit_string))
        print("")


def test_unit_aggregation():
    """
    Test aggregation of compund unit back to a single class.
    """
    unit_parser = FastSymbolicUnitParser()
    units = [('μg', 1, 'http://qudt.org/vocab/unit/MicroGM', None), ('mL', -1, 'http://qudt.org/vocab/unit/MilliL', None)]
    normalized_unit_string = 'μg/ mL'
    unit = unit_parser.get_single_class_for_compound_unit(units, normalized_unit_string)
    assert unit == 'http://qudt.org/vocab/unit/MicroGM-PER-MilliL'    


def test_ucum_code_generation():
    unit_parser = FastSymbolicUnitParser(load_ucum_codes=True)
    units_and_results = [    
        ([(1, 'http://qudt.org/vocab/unit/KiloM'), (-1, 'http://qudt.org/vocab/unit/SEC')], {'/': 'km/s', '-1': 'km.s-1'}),
        ([(1, 'http://qudt.org/vocab/unit/ERG'), (-1, 'http://qudt.org/vocab/unit/CentiM2'), (-1, 'http://qudt.org/vocab/unit/SEC')], {'/': 'erg/(cm2.s)', '-1': 'erg.cm-2.s-1'}),
        ([(1, 'http://qudt.org/vocab/unit/ERG'), (-2, 'http://qudt.org/vocab/unit/CentiM'), (-1, 'http://qudt.org/vocab/unit/SEC')], {'/': 'erg/(cm2.s)', '-1': 'erg.cm-2.s-1'}),        
    ]

    for units, true_result in units_and_results:
        result = unit_parser.get_compound_ucum_codes(units)
        if result != true_result:
            raise ValueError(f"Expected {true_result} but got {result}")
        

if __name__ == "__main__":
    
    start = time.perf_counter()
    
    test_unit_aggregation()
    test_ucum_code_generation()
    
    end = time.perf_counter()

    print("All tests passed.")
    print("Elapsed time = {}s".format((end - start)))

