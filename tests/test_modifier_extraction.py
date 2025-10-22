import pytest
from quinex_utils.functions.extract_quantity_modifiers import GazetteerBasedQuantityModifierExtractor


def test_gazetteer_based_quantity_modifier_extraction():
    examples = [
        ("...with the sail angle between ~45° and 90° or higher when the...", "45° and 90°", ['between ~', 'or higher']),
        ("...the temperature is approximately 25 °C, which is around 77 °F.", "25 °C", ['approximately']),
        ("...the temperature is approx. 25 °C, which is around 77 °F.", "25 °C", ['approx.']),
        ("...in general due to two key factors there is...", "two key factors", []),
        ]
    qmod_extractor = GazetteerBasedQuantityModifierExtractor()
    for par, q_surface, qmods_expected in examples:            
        start_char = par.find(q_surface)
        end_char = start_char + len(q_surface)
        quantity_span = {"start": start_char, "end": end_char, "text": q_surface}
        qmods_result, _ = qmod_extractor(par, [quantity_span])
        qmods_result_surfaces = [qmod["text"] for qmod in qmods_result[0]]
        assert qmods_result_surfaces == qmods_expected


if __name__ == "__main__":    
    test_gazetteer_based_quantity_modifier_extraction()
    print("All tests passed.")