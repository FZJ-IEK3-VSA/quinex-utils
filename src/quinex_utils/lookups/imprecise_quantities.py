from text_processing_utils.boolean_checks import an_vs_a
from quinex_utils.lookups.number_words import ORDER_OF_MAGNITUDE_WORDS_MAPPING


# The following list of imprecise quantities is partly based on
# Hanauer et al. „Complexities, Variations, and Errors of Numbering within Clinical Notes: The Potential Impact on Information Extraction and Cohort-Identification“, 2019. (https://doi.org/10.1186/s12911-019-0784-1)"
IMPRECISE_QUANTITIES = [
    # We do not include "hundreds of", "thousands of", etc.
    "multi",
    "multiple",
    "quadrillions of",
    "tens of thousands",
    "tens of millions",
    "tens of billions",
    "hundreds of thousands",
    "hundreds of millions",
    "hundreds of billions",
    "various",
    "several",    
    "handful",
    "handful of",
    "many",
    "few",  
    "few of",    
    "couple",
    "couple of",
    "some",
    "lots of",
    "lot of",    
    "not much",
    "not many",
    "ton of",
    "tons of",
    "bunch of",            
    "bunchs of",
    "gobs of",
    "oodles and oodles of",
    "lots and lots of",
    "plenty",
    "plenty of",
    "multitude of",
    "cornucopia of",
    "great deal of",
    "all kinds of",        
    "too many to count",
    "way too many",
    "uncountable",
    "hell of a lot",
    "lions share of",    
    "waist deep in",
    "infinitesimally small",    
    "infinitely more",
    "up the wazoo",
    "infinitely small",
    "infinitely",
    "less",
    "infinitely large",
]

quantifying_amounts = [
    ("dozen", "dozens"), 
    ("hundred", "hundreds"),
    ("thousand", "thousands"),
    ("million", "millions"),
    ("billion", "billions"),
    ("trillion", "trillions"),
    ("oodle", "oodles"),
    ("plethora", "plethoras"),
    ("myriad", "myriads"),    
    ("butt load", "butt loads"),
    ("crap load", "crap loads"),
    ("shit load", "shit loads"),        
    ("truck load", "truck loads"),
    ("gazillion", "gazillions"),
    ("bazillion", "bazillions"),
]

# Add version of "truck load" etc. without whitespace (e.g., "truckload").
quantifying_amounts += [(a[0].replace(" ",""), a[1].replace(" ","")) for a in quantifying_amounts if a[0].endswith(" load")]

for amount_s, amount_pl in quantifying_amounts:
    IMPRECISE_QUANTITIES += [amount_s, amount_pl, f"{amount_s} of", f"{amount_pl} of"]
    for adj in ["few", "several", "some", "couple", "couple of", "handful", "handful of", "many", "multiple"]:
        templ_a = f"{adj} {amount_s}"
        templ_b = f"{adj} {amount_pl}"
        assert templ_a not in IMPRECISE_QUANTITIES
        assert templ_b not in IMPRECISE_QUANTITIES
        IMPRECISE_QUANTITIES += [templ_a, templ_b]


neutral_amounts = [("number", "numbers"), ("amount", "amounts"), ("quantity", "quantities")]
for amount_s, amount_pl in neutral_amounts:
    for adj in ["tiny", "very tiny", "small", "very small", "vanishingly small", "large", "very large", "great", "miniscule", "minuscule", "significant", "considerable", "vast", "huge", "massive"]:
        templ_a = f"{adj} {amount_s} of"        
        if an_vs_a(adj):
            templ_b = f"an {adj} {amount_s} of"
        else:
            templ_b = f"a {adj} {amount_s} of"
        
        templ_c = f"the {adj} {amount_s} of"
        templ_d = f"{adj} {amount_pl} of"

        assert templ_a not in IMPRECISE_QUANTITIES
        assert templ_b not in IMPRECISE_QUANTITIES
        assert templ_c not in IMPRECISE_QUANTITIES

        IMPRECISE_QUANTITIES += [templ_a, templ_b, templ_c, templ_d]  


for t in ["a small number of",
    "vast quantities of",
    "miniscule amounts of",
    "small numbers of",
    "a small amount of",
    "small amounts of",
    "a large number of",
    "large numbers of",
    "a large amount of",
    "large amounts of",
    "a great number of",
    "great numbers of",
    "a great amount of",
    "great amounts of",
    "a significant number of",
    "significant numbers of",
    "a significant amount of",
    "significant amounts of",
    "a considerable number of",
    "considerable numbers of",
    "a considerable amount of",
    "considerable amounts of",
    "a vast number of",
    "vast numbers of",
    "a vast amount of",
    "vast amounts of",
    "a huge number of",
    "huge numbers of",
    "a huge amount of",
    "huge amounts of",
    "a massive number of",
    "massive numbers of",
    "a massive amount of",        
    "massive amounts of",
    "a vanishingly small number of",
    "a very small number of",
    "a very large number of",
]:
    assert t in IMPRECISE_QUANTITIES, f"Expected {t} to be in IMPRECISE_QUANTITIES, but it is not."


assert len(IMPRECISE_QUANTITIES) > 0, "IMPRECISE_QUANTITIES should not be empty."
assert len(set(IMPRECISE_QUANTITIES)) == len(IMPRECISE_QUANTITIES), "IMPRECISE_QUANTITIES should not contain duplicates."
# Debug-tip: duplicates = set([t for t in IMPRECISE_QUANTITIES if IMPRECISE_QUANTITIES.count(t) > 1])

# Some imprecise quantities can be precise if not followed by "of" or refer to a unit, 
# so we ensure they are not in the list.
for amount_s, amount_pl in [
    ("hundred", "hundreds"),
    ("thousand", "thousands"),
    ("million", "millions"),
    ("billion", "billions"),
    ("trillion", "trillions"),
    ("dozen", "dozens"),
    ("ton", "tons"),
    ]:
    if amount_s in IMPRECISE_QUANTITIES:        
        IMPRECISE_QUANTITIES.remove(amount_s)
    if amount_pl in IMPRECISE_QUANTITIES:
        IMPRECISE_QUANTITIES.remove(amount_pl)

IMPRECISE_QUANTITIES_W_OPT_ARTICLE = IMPRECISE_QUANTITIES.copy()
for q in IMPRECISE_QUANTITIES:
    IMPRECISE_QUANTITIES_W_OPT_ARTICLE += [f"a {q}", f"an {q}", f"the {q}"]

# Add order of magnitudes.
order_of_magnitude_words = ["tens"] + [o + "s" for o in ORDER_OF_MAGNITUDE_WORDS_MAPPING.keys()]
IMPRECISE_QUANTITIES += order_of_magnitude_words
IMPRECISE_QUANTITIES_W_OPT_ARTICLE += order_of_magnitude_words

# Sort from longest to shortest to ensure that longer phrases are matched first in regex patterns.
IMPRECISE_QUANTITIES = sorted(IMPRECISE_QUANTITIES, key=lambda x: len(x), reverse=True)
IMPRECISE_QUANTITIES_W_OPT_ARTICLE = sorted(IMPRECISE_QUANTITIES_W_OPT_ARTICLE, key=lambda x: len(x), reverse=True)





