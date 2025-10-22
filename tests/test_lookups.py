from quinex_utils.lookups.quantity_modifiers import QMODS, ALL_NORMALIZED_QMOD_SYMBOLS, MATH_SYMBOLS_CONSIDERED_AS_PART_OF_QUANTITY_SPAN


def test_all_normalized_qmod_symbols():
    """
    Test that ALL_NORMALIZED_QMOD_SYMBOLS is a unique list of all symbols quantity modifiers are normalized to.
    """    
    assert isinstance(ALL_NORMALIZED_QMOD_SYMBOLS, list)
    assert len(ALL_NORMALIZED_QMOD_SYMBOLS) > 0
    unique_normalized_qmod_symbols = set()    
    for mapping in QMODS.values():
        unique_normalized_qmod_symbols.update(mapping.values())
    unique_normalized_qmod_symbols.remove(None) 
    for sym in MATH_SYMBOLS_CONSIDERED_AS_PART_OF_QUANTITY_SPAN:
        if sym in unique_normalized_qmod_symbols:
            unique_normalized_qmod_symbols.remove(sym)
    assert len(ALL_NORMALIZED_QMOD_SYMBOLS) == len(unique_normalized_qmod_symbols)
    assert set(ALL_NORMALIZED_QMOD_SYMBOLS) == unique_normalized_qmod_symbols


if __name__ == "__main__":
    test_all_normalized_qmod_symbols()
    print("All tests passed.")