import tok_trainer_functions as functions
import aquilign.tokenize.syntactic_tokenization as SyntacticTok
import aquilign.preproc.create_train_data as FormatData
import sys
from transformers import BertTokenizer, AutoModelForTokenClassification, pipeline
import re
import torch
import numpy as np
import evaluate
from tabulate import tabulate


def unalign_labels(human_to_bert, predicted_labels, splitted_text):
    realigned_list = []
    # itering on original text
    final_prediction = []
    for idx, value in enumerate(splitted_text):
        index = idx + 1
        predicted = human_to_bert[index]
        # if no mismatch, copy the label
        if len(predicted) == 1:
            correct_label = predicted_labels[predicted[0]]
        # mismatch
        else:
            ###
            correct_label = [predicted_labels[predicted[n]] for n in range(len(predicted))]
            # Dans ce cas on regarde s'il y a 1 dans n'importe quelle position des rangs correspondants:
            # on considère que BERT ne propose qu'une tokénisation plus importante que nous
            if any([n == 1 for n in correct_label]):
                correct_label = 1
            elif any([n == 2 for n in correct_label]):
                correct_label = 0
            else:
                correct_label = 0

        final_prediction.append(correct_label)

    assert len(final_prediction) == len(splitted_text), "List mismatch"
    tokenized_sentence = " ".join(
        [element if final_prediction[index] != 1 else f"\n{element}" for index, element in enumerate(splitted_text)])
    return final_prediction

def simpleconversion(text:list):
    sentencesList = []
    splitList = []
    for l in text:
        l = l.replace(".", "")
        l = l.replace(".", "")
        l = l.replace("'", " ")
        i = re.split('\n', l)[0]
        j = re.split('\$', i)

        sentenceAsList = re.findall(r"[\.,;—:?!’'«»“/-]|\w+", j[0])
        split= j[1]
        if '£' in split:
            splitOk = re.split('£', split)
        else:
            splitOk = [split]

        # case where token has a position, when there are several identical tokens in the sentence (and for ex. we want to get the 2nd one)
        positionList = []
        tokenList = []
        for i in range(len(splitOk)):
            if re.search(r'-\d', splitOk[i]):
                position = re.split('-', splitOk[i])[1]
                positionList.append(int(position))
                splitOkk = re.split('-', splitOk[i])[0]
                tokenList.append(splitOkk)
            else:
                pass


        localList = []

        #set tokenList to get all the concerned values
        tL = list(set(tokenList))

        #prepare an emptyList with as empty sublists as concerned words
        emptyList = []
        for item in tL:
            localEmptyList = []
            emptyList.append(localEmptyList)

        for e in enumerate(sentenceAsList) :

            # get just the token
            token = e[1]

            # if it is a word that separate and that correspond to same other tokens in the sentence
            if '-' in split and token in tokenList:

                # we get the position of the token in the set list
                postL = tL.index(token)

                # if it is the correct token
                if token == tL[postL]:
                    # we fill the empty list with the current token (empty list with a position that correspond to the position in the tL list
                    emptyList[postL].append(token)
                else:
                    pass

                # we get correspondant idx for tokenList ans positionList
                goodidx = [i for i, e in enumerate(tokenList) if e == token]

                # empty list in which we'll put the position we want to get for the correct token
                goodpos = []

                # we activate the position to get the correct element in positionList, based on idx
                for i in goodidx:
                    goodelem = positionList[i]
                    goodpos.append(int(goodelem))

                # if the actual len of the emptyList is in the list of the positions that interest us: we add one to the list
                if len(emptyList[postL]) in goodpos:
                    localList.append(1)
                else:
                    localList.append(0)


            elif token in splitOk:
                localList.append(1)
            else:
                localList.append(0)

        sentence = j[0]
        sentencesList.append(sentence)
        splitList.append(localList)
    return sentencesList, splitList

def tokenize(text,num):
    words = text.split(" ")
    return [' '.join(words[i:i+num]) for i in range(0, len(words), num)]

def get_labels_from_preds(preds):
    bert_labels = []
    for pred in preds[-1]:
        label = [idx for idx, value in enumerate(pred) if value == max(pred)][0]
        bert_labels.append(label)
    return bert_labels


def get_metrics(preds, gt):
    """
    This function produces the metrics for evaluating the model at the end of training
    """
    metric1 = evaluate.load("accuracy")
    metric2 = evaluate.load("recall")
    metric3 = evaluate.load("precision")
    metric4 = evaluate.load("f1")
    all_accs, all_recall, all_precision, all_f1 = [], [], [], []
    for un_pred, un_gt in zip(preds, gt):
        assert len(un_gt) == len(un_pred), "Length mismatch"
        all_accs.append(metric1.compute(predictions=un_pred, references=un_gt)['accuracy'])
        all_recall.append(metric2.compute(predictions=un_pred, references=un_gt, average=None)['recall'])
        all_precision.append(metric3.compute(predictions=un_pred, references=un_gt, average=None)['precision'])
        all_f1.append(metric4.compute(predictions=un_pred, references=un_gt, average=None)['f1'])
    mean_acc = np.mean(all_accs, axis=0)
    mean_recall = list(np.mean(all_recall, axis=0))
    mean_precision = list(np.mean(all_precision, axis=0))
    mean_f1 = list(np.mean(all_f1, axis=0))
    return mean_acc, mean_precision, mean_recall ,mean_f1
    
    
# correspondences between our labels and labels from the BERT-tok
def get_correspondence(sent, tokenizer):
    out = {}
    # First token is CLS
    tokenized_index =  1
    out[0] = (0,)
    for index, word in enumerate(sent.replace("'", " ").split()):
        tokenized_word = tokenizer.tokenize(word)
        out[index + 1] = tuple(item for item in range(tokenized_index, tokenized_index + len(tokenized_word)))
        tokenized_index += len(tokenized_word)
    human_split_to_bert = out
    bert_split_to_human_split = {value: key for key, value in human_split_to_bert.items()}
    return human_split_to_bert, bert_split_to_human_split


def run_eval(file, model_path, tokenizer_name, num, verbose=False):
    with open(file, "r") as input_file:
        as_list = [item.replace("\n", "").replace(".", "") for item in input_file.readlines()]
    
    all_preds, all_gts = [], []
    tokenizer = BertTokenizer.from_pretrained(tokenizer_name, max_length=10)
    new_model = AutoModelForTokenClassification.from_pretrained(model_path, num_labels=3)
    # get the path of the default tokenizer
    result = simpleconversion(as_list)
    texts, labels = result
    assert len(texts) == len(labels),  "Lists mismatch"
    
    print("Performing syntactic tokenization evaluation")
    # First, regexp evaluation
    syntactic_preds, all_syntactic_gt = [], []
    for idx, (example, label) in enumerate(zip(texts, labels)):
        tokenized = SyntacticTok.syntactic_tokenization(path=None, standalone=False, text=example, use_punctuation=False)
        formatted = FormatData.format(file=None, keep_punct=False, save_file=False, standalone=False, tokenized_text=tokenized, examples_length=100)
        predicted = [labels[0] for labels in simpleconversion(formatted)][1]
        assert len(predicted) == len(label), "Length mismatch, please check the regular expressions don't split any word."
        syntactic_preds.append(predicted)
        all_syntactic_gt.append(label)
        if verbose:
            print("---\nNew example")
            print(f"Example:   {example}")
            print(f"Predicted:    {predicted}")
            print(f"Ground Truth: {label}")
            print(f"Example length: {len(example.split())}")
            print(f"Preds length: {len(predicted)}")
            print(f"GT length: {len(label)}")
            print(f"Orig GT: {as_list[idx]}")
    synt_results = get_metrics(syntactic_preds, all_syntactic_gt)
    
    
    # Second, model evaluation
    print("Performing bert-based tokenization evaluation")
    toks_and_labels = functions.convertToSentencesAndLabels(as_list, tokenizer)
    for txt_example, gt in zip(as_list, toks_and_labels):
        # We get only the text
        example, _ = txt_example.split("$")
        splitted_example = example.replace("'", " ").split()
        # BERT-tok
        enco_nt_tok = tokenizer.encode(example, truncation=True, padding=True, return_tensors="pt")
        # get the predictions from the model
        predictions = new_model(enco_nt_tok)
        
        preds = predictions[0]
        # apply the functions
        bert_labels = get_labels_from_preds(preds)
        
        # On crée la table de correspondance entre les words et les subwords
        human_to_bert, _ = get_correspondence(example, tokenizer)
        unaligned_preds = unalign_labels(human_to_bert, bert_labels, splitted_example)
        unaligned_tgts = unalign_labels(human_to_bert, gt['labels'].tolist(), splitted_example)
        
        # On remet la première et la dernière prédiction qui correspond au [CLS] et [SEP] et n'est pas prise en compte dans le réalignement
        unaligned_preds.insert(0, bert_labels[0])
        unaligned_tgts.insert(0, gt['labels'].tolist()[0])
        unaligned_preds.append(bert_labels[-1])
        unaligned_tgts.append(gt['labels'].tolist()[:len(bert_labels)][-1])
        
        assert len(unaligned_preds) == len(unaligned_tgts), f"Target and Preds mismatch, please check data: " \
                                                       f"\n{unaligned_preds}" \
                                                       f"\n{unaligned_tgts}"
        all_preds.append(unaligned_preds)
        all_gts.append(unaligned_tgts)
        if verbose:
            print(f"---\nNew example: {example}")
            print(f"Example lenght: {len(splitted_example)}")
            print(f"Bert Tokenized: {enco_nt_tok.tolist()}")
            print(f"Tokens: {tokenizer.convert_ids_to_tokens(ids=enco_nt_tok.tolist()[0])}")
            print(f"Preds Labels length:  {len(bert_labels)}")
            print(f"Tokens length: {len(enco_nt_tok.tolist()[0])}")
            print(f"Zip: {list(zip(tokenizer.convert_ids_to_tokens(ids=enco_nt_tok.tolist()[0]), bert_labels))}")
            print(f"Bert labels (subwords):            {bert_labels}")
            print(f"Truncated ground truth (subwords): {gt['labels'].tolist()[:len(bert_labels)]}")
            print("Unaligning labels")
            print(f"First bert label: {bert_labels[0]}")
            print(f"Last bert label: {bert_labels[-1]}")
            print(f"Predictions (words):               {unaligned_preds}")
            print(f"Targets (words):                   {unaligned_tgts}")
            print(f"Length: {len(unaligned_preds)}")
    bert_results = get_metrics(all_preds, all_gts)
    
    zipped_results = list(zip(['Accuracy', 'Precision', 'Recall', 'F1-score'], synt_results, bert_results))
    print(tabulate(zipped_results, headers=['', 'Synt (None, Delim.)', 'Bert (None, Delim., Pad.)'], tablefmt='orgtbl'))
        
        


if __name__ == '__main__':
    file_to_test = sys.argv[1]
    model_path = sys.argv[2]
    tokenizer_name = sys.argv[3]
    num = int(sys.argv[4])
    run_eval(file_to_test, model_path, tokenizer_name, num)