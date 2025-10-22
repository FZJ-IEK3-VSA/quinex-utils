import pytest
from quinex_utils.parsers.unit_parser import FastSymbolicUnitParser


def test_unit_conversion():
    unit_parser = FastSymbolicUnitParser()

    # Test without conversion offset.
    compound_unit = [(None, 1, 'http://qudt.org/vocab/unit/M', None), (None, -1, 'http://qudt.org/vocab/unit/KiloW-HR', None)]
    conv_info = unit_parser.get_compound_unit_conversion_info(compound_unit)
    assert conv_info != None

    # Test with coversion offset.
    compound_unit = [(None, 1, 'http://qudt.org/vocab/unit/DEG_C', None), (None, -1, 'http://qudt.org/vocab/unit/YR', None)]
    sodv, sodv_str, conv_multi, unit_sys, allow_conversion = unit_parser.get_compound_unit_conversion_info(compound_unit)    
    assert sodv_str == "A0E0L0I0M0H1T-1D0"
    assert round(conv_multi, 22) == round(3.16880878140289e-08, 22)    
    assert unit_sys == {'CGS', 'SI'}
    assert allow_conversion == True

    # Test with currency.
    compound_unit = [(None, 1, 'http://qudt.org/vocab/unit/CCY_EUR', None), (None, -1, 'http://qudt.org/vocab/unit/KiloW', None)]
    sodv, sodv_str, conv_multi, unit_sys, allow_conversion = unit_parser.get_compound_unit_conversion_info(compound_unit)
    assert sodv_str == "A0E0L-2I0M-1H0T3D0"
    assert conv_multi == 0.001
    assert 'SI' in unit_sys
    assert allow_conversion == False


if __name__ == "__main__":
    test_unit_conversion()
    print("All tests passed.")