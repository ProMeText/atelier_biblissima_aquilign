import copy
import os
import random
import re
import json
import sys
import langid 
import aquilign.align.utils as utils

def syntactic_tokenization(path, corpus_limit=None, use_punctuation=False, standalone=True, text=None):
    if standalone:
        with open(path, "r") as input_text:
            text = input_text.read().replace("\n", " ")
    else:
        pass
    # text = utils.normalize_text(text)
    codelang, _ = langid.classify(text[:300])
    with open("aquilign/tokenize/delimiters.json", "r") as input_json:
        dictionary = json.load(input_json)
    # Il ne reconnaît pas toujours le castillan
    if codelang == "an" or codelang == "oc":
        codelang = "es"
    if codelang == "eo" or codelang == "ht":
        codelang = "fr"
    
    single_tokens_punctuation = [punct for punct in dictionary[codelang]['punctuation'] if len(punct) == 1]
    multiple_tokens_punctuation = [punct for punct in dictionary[codelang]['punctuation'] if len(punct) != 1]
    single_token_punct = "".join(single_tokens_punctuation)
    multiple_tokens_punct = "|".join(multiple_tokens_punctuation)
    punctuation_subregex = f"{multiple_tokens_punct}|[{single_token_punct}]"
    if use_punctuation:
        tokens_subregex = "(" + " | ".join(dictionary[codelang]['word_delimiters']) + " |" + punctuation_subregex + ")"
    else:
        tokens_subregex = "(" + " | ".join(dictionary[codelang]['word_delimiters']) + ")"
    delimiter = re.compile(tokens_subregex)
    search = re.search(delimiter, text)
    tokenized_text = []
    if search:
        matches = re.split(delimiter, text)
        tokenized_text.append(matches[0])
        tokenized_text.extend([matches[index] + matches[index+1] for index in range(1, len(matches[:-1]), 2)])
        tokenized_text = [token.strip() for token in tokenized_text]
    else:
        tokenized_text = [text]
    # Let's limit the length for test purposes
    if corpus_limit:
        tokenized_text = tokenized_text[:corpus_limit]
    return tokenized_text

if __name__ == '__main__':
    input_file = sys.argv[1]
    tokens = syntactic_tokenization(sys.argv[1])
    with open(input_file.replace(".txt", ".tokenized.txt"), "w") as output_file:
        output_file.write("\n".join(tokens))