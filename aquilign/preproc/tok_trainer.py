# -*- coding: utf-8 -*-
import sys
from transformers import BertTokenizer, Trainer, TrainingArguments, AutoModelForTokenClassification
from tok_trainer_functions import *

## script for the training of the text tokenizer : identification of tokens (label 1) which will be used to split the text
## produces folder with models (best for each epoch) and logs


## usage : python tok_trainer.py model_name train_file.txt eval_file.txt num_train_epochs batch_size logging_steps
## where :
# model_name is the full name of the model (same name for model and tokenizer)
# train_file.txt is the file with the sentences and words of interest are identified  (words are identified with $ after the line)
# which will be used for training
## ex. : uoulentiers mais il nen est pas encor temps. Certes fait elle si$mais£Certes
# eval_file.txt is the file with the sentences and words of interest which will be used for eval
# num_train_epochs : the number of epochs we want to train (ex : 10)
# batch_size : the batch size (ex : 8)
# logging_steps : the number of logging steps (ex : 50)

# function which produces the train, which first gets texts, transforms them into tokens and labels, then trains model with the specific given arguments
def training_trainer(modelName, train_dataset, eval_dataset, num_train_epochs, batch_size, logging_steps):
    model = AutoModelForTokenClassification.from_pretrained(modelName, num_labels=3)
    tokenizer = BertTokenizer.from_pretrained(modelName, max_length=10)
    train_file = open(train_dataset, "r")
    train_lines = train_file.readlines()
    eval_file = open(eval_dataset, "r")
    eval_lines = eval_file.readlines()
    train_texts = convertToSentencesAndLabels(train_lines)[0]
    train_labels = convertToSentencesAndLabels(train_lines)[1]
    eval_texts = convertToSentencesAndLabels(eval_lines)[0]
    eval_labels = convertToSentencesAndLabels(eval_lines)[1]
    train_dataset = SentenceBoundaryDataset(train_texts, train_labels, tokenizer)
    eval_dataset = SentenceBoundaryDataset(eval_texts, eval_labels, tokenizer)

    if '/' in modelName:
        name_of_model = re.split('/', modelName)[1]
    else:
        name_of_model = modelName

    # training arguments
    # num train epochs, logging_steps and batch_size should be provided
    # evaluation is done by epoch and the best model of each one is stored in a folder "results_+name"
    training_args = TrainingArguments(
        output_dir=f"results_{name_of_model}/epoch{num_train_epochs}_bs{batch_size}",
        num_train_epochs=num_train_epochs,
        logging_steps=logging_steps,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        evaluation_strategy="epoch",
        logging_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True
        # best model is evaluated on loss
    )

    # define the trainer : model, training args, datasets and the specific compute_metrics defined in functions file
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        compute_metrics=compute_metrics
    )

    # fine-tune the model
    trainer.train()

    # get the best model path
    best_model_path = trainer.state.best_model_checkpoint
    print(f"Best model can be found at : {best_model_path} ")

    # print the whole log_history with the compute metrics
    print("Best model is evaluated on the loss results. Here is the log history with the performances of the models :")
    print(trainer.state.log_history)

    # functions returns best model_path
    return best_model_path


# list of arguments to provide and application of the main function
if __name__ == '__main__':
    model = sys.argv[1]
    train_text = sys.argv[2]
    eval_text = sys.argv[3]
    num_train_epochs = int(sys.argv[4])
    batch_size = int(sys.argv[5])
    logging_steps = int(sys.argv[6])

    training_trainer(model, train_text, eval_text, num_train_epochs, batch_size, logging_steps)
