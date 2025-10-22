celsius_to_kelvin = lambda t: t + 273.15
kelvin_to_celsius = lambda t: t - 273.15
celsius_to_fahrenheit = lambda t: (t * (9 / 5)) + 32
fahrenheit_to_celsius = lambda t: (t - 32) * 5 / 9


def remove_exponent_from_ucum_code_of_single_unit(ucum_code: str) -> tuple[str, int]:
    """Remove exponent from UCUM code of a single unit, e.g., "m2" -> ("m", 2).
    
    Note:
        It is assumed that the exponent is an integer in the range [-9, 9].

    Args:   
        ucum_code: UCUM code of a single unit, e.g., "m2" or "m-2".
    
    Returns:
        ucum_code: UCUM code of a single unit without exponent, e.g., "m".
        exponent: Exponent of the unit, e.g., 2 or -2 for "m2" or "m-2", respectively.        
    """
    
    if len(ucum_code) <= 1:
        exponent = 1
    else:   
        start_index = -2 if len(ucum_code) > 2 and ucum_code[-2] == "-" else -1                             
        try:                        
            exponent = int(ucum_code[start_index:])
            ucum_code = ucum_code[:start_index]
        except ValueError:
            exponent = 1

    return ucum_code, exponent