import pytest
from quinex_utils.functions.boolean_checks import contains_any_number


def test_contains_any_number():
    for option in [True, False]:
        assert contains_any_number("This text contains a number at some point 1.23.", consider_imprecise_quantites=option) == True
        assert contains_any_number("This text does not contain a number.", consider_imprecise_quantites=option) == False
        assert contains_any_number("This text contains a number at some point 1.23e-5.", consider_imprecise_quantites=option) == True
        assert contains_any_number("This text contains two or three numbers.", consider_imprecise_quantites=option) == True
        assert contains_any_number("This text does not contain a trillion numbers.", consider_imprecise_quantites=option) == True

    assert contains_any_number("This text does not contain a gazillion numbers.", consider_imprecise_quantites=False) == False
    assert contains_any_number("This text does not contain a gazillion numbers.", consider_imprecise_quantites=True) == True


if __name__ == "__main__":    
    test_contains_any_number()
    print("All tests passed.")