import re
import warnings   
try:
    import spacy
    from spacy.tokens import Doc
    from spacy.language import Language
    from spacy.matcher import PhraseMatcher    
except ImportError:    
    warnings.warn("Spacy is not installed. Please install it to use the quantity modifier extraction.")
from text_processing_utils.char_offsets import is_inside, get_span_distance_sorted, merge_annotation_offsets
from text_processing_utils.bio_tags import transform_into_char_offsets_and_readable_tag
from text_processing_utils.locate import get_sent_idx
from quinex_utils.lookups.quantity_modifiers import PREFIXED_QUANTITY_MODIFIERS, SUFFIXED_QUANTITY_MODIFIERS, PREFIXED_QMOD_MATH_SYMBOLS


class GazetteerBasedQuantityModifierExtractor():
    """
    Class for extracting quantity modifiers for given quantity spans
    from their surrounding context using gazetteers.    
    """

    def __init__(self, verbose=False):
        
        self.verbose = verbose

        # Init Spacy pipeline.
        spacy_exclude_comps = ["entity_linker", "entity_ruler", "textcat", "textcat_multilabel", "lemmatizer", 
        "trainable_lemmatizer", "morphologizer", "attribute_ruler", "senter", "sentencizer", "ner", 
        "transformers", "tagger"]        
        self.nlp = spacy.load("en_core_web_md", exclude=spacy_exclude_comps)

        # Force spacy to tokenize qmods like '±' or '~' as a single token 
        # (e.g., '~45°' will be tokenized to  ['~', '45', '°']). 
        # Otherwise, the PhraseMatcher will not match them correctly.
        special_chars = [re.escape(c) for c in PREFIXED_QMOD_MATH_SYMBOLS] + [r"\/"]        
        prefixes = self.nlp.Defaults.prefixes + special_chars
        infixes = self.nlp.Defaults.infixes + special_chars
        prefix_regex = spacy.util.compile_prefix_regex(prefixes)        
        infix_regex = spacy.util.compile_infix_regex(infixes)
        self.nlp.tokenizer.prefix_search = prefix_regex.search                        
        self.nlp.tokenizer.infix_finditer = infix_regex.finditer

        # Make sure that sentence ends are separated from units
        # (e.g., 'is 273.15 K.' should be tokenized to ['is', '273.15', 'K', '.']).
        suffixes = self.nlp.Defaults.suffixes + [r"\."]
        suffix_regex = spacy.util.compile_suffix_regex(suffixes)
        self.nlp.tokenizer.suffix_search = suffix_regex.search
                
        # Init PhraseMatcher.
        self.prefixed_qmods_matcher = PhraseMatcher(self.nlp.vocab, attr="LOWER", validate=True)
        self.suffixed_qmods_matcher = PhraseMatcher(self.nlp.vocab, attr="LOWER", validate=True)
        with self.nlp.select_pipes(disable=["tok2vec","parser"]):
            self.prefixed_qmods_matcher.add("PREFIXED_QUANTITY_MODIFIER", list(self.nlp.pipe(PREFIXED_QUANTITY_MODIFIERS)))
            self.suffixed_qmods_matcher.add("SUFFIXED_QUANTITY_MODIFIER", list(self.nlp.pipe(SUFFIXED_QUANTITY_MODIFIERS)))


    def __call__(self, text: str, quantity_spans: list[dict]):
        """
        Baseline for extracting quantity modifiers (such as approx., above, at least, etc.) for each quantity span.
        Only quantity modifiers surrounding the quantity span are extracted not within the quantity span or distant ones.
        """
        doc = self.nlp(text)
        sents = list(doc.sents)
        quantity_modifier_spans = []
        for quantity_span in quantity_spans:

            # Locate quantity in sentence.
            sent_idx = get_sent_idx(quantity_span, sents)

            if sent_idx != None:
                # Start one idx earlier, in case sentence was wrongly split (e.g., due to dot in '...approx. 25 °C...').
                window_start_tok = sents[max(0, sent_idx - 1)].start
                window_end_tok = sents[sent_idx].end
                window = doc[window_start_tok:window_end_tok]
            else:
                # Quantity probably spans multiple sentences or sentence boundary detection failed.
                # Fall back to using the whole document as context window.
                # TODO: Instead use the specific sentences the quantity spans.
                window = doc
            
            # Convert char offsets to token offsets.            
            quantity = doc.char_span(quantity_span["start"], quantity_span["end"], alignment_mode="expand")
            if quantity == None or quantity.text != quantity_span["text"]:
                if self.verbose:
                    warnings.warn(f"Quantity span '{quantity_span['text']}' does not align with token boundaries in modifier extraction.")
                exact_alignment = False
            else:
                exact_alignment = True
            
            if not exact_alignment and quantity[0].idx < quantity_span["start"] and text[quantity[0].idx] in [")", "]", "(", "["]:
                # Closing parenthesis or bracket at the beginning of the quantity span indicates that 
                # whatever precedes it is not part of the quantity span.
                # Unbalanced opening parenthesis can hinder quantity parsing in later stages.
                quantity_modifier_spans.append([])
            else:            
                # Find prefixed and suffixed quantity modifiers in the sentence.
                # Note that we effectively ignore the quantity span in the sentence.
                prefixed_qmod_matches = self.prefixed_qmods_matcher(window[:quantity.start])
                suffixed_qmod_matches = self.suffixed_qmods_matcher(window[quantity.end:])
                modifier_matches = prefixed_qmod_matches + suffixed_qmod_matches
                
                # Transform the matches into a dictionary of lists of tuples of char offsets.
                # As PhraseMatcher returns token offsets relative to doc not window anyway,
                # we can set sent_offset to 0.
                modifier_annotations = transform_into_char_offsets_and_readable_tag(
                    modifier_matches, self.nlp, doc, sent_offset=0
                )

                # Merge adjecent or overlapping prefixed quantity modifier matches.
                merged_modifier_annotations = merge_annotation_offsets(modifier_annotations)

                # Filter the merged quantity modifier annotations.
                quantity_char_offsets = (
                    quantity_span["start"],
                    quantity_span["end"],
                )

                kept = []
                for modifier_candidate in merged_modifier_annotations[
                    "PREFIXED_QUANTITY_MODIFIER"
                ]:
                    # Accept quantity modifiers within the quantity span.
                    if is_inside(modifier_candidate, quantity_char_offsets):
                        kept.append(modifier_candidate)
                    elif 0 <= get_span_distance_sorted(modifier_candidate, quantity_char_offsets) < 2:
                        kept.append(modifier_candidate)

                for modifier_candidate in merged_modifier_annotations[
                    "SUFFIXED_QUANTITY_MODIFIER"
                ]:
                    # Accept quantity modifiers within the quantity span.
                    if is_inside(modifier_candidate, quantity_char_offsets):
                        kept.append(modifier_candidate)
                    elif 0 <= get_span_distance_sorted(quantity_char_offsets, modifier_candidate) < 2:
                        kept.append(modifier_candidate)

                quantity_modifier_spans.append(
                    [
                        {
                            "start": qmod[0], 
                            "end": qmod[1],
                            "text": doc.text[qmod[0] : qmod[1]]
                        }
                        for qmod in kept
                    ]
                )

        # Add quantity modifiers to quantity spans.
        for qmod, quantity_span in zip(quantity_modifier_spans, quantity_spans):
            quantity_span["modifiers"] = qmod

            if len(qmod) == 0:
                quantity_span["quantity_with_modifiers"] = quantity_span
            else:
                # Add quantitiy modifiers to the quantity surface.
                start_chars = [qmod["start"] for qmod in quantity_span["modifiers"]]
                start_chars.append(quantity_span["start"])
                min_start_char = min(start_chars)

                end_chars = [qmod["end"] for qmod in quantity_span["modifiers"]]                
                end_chars.append(quantity_span["end"])                
                max_end_char = max(end_chars)

                quantity_span["quantity_with_modifiers"] = {
                    "start": min_start_char, 
                    "end": max_end_char,
                    "text": doc.text[min_start_char:max_end_char]
                }

        return quantity_modifier_spans, quantity_spans
