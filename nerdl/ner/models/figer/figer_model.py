from nerdl.ner.models.figer.figer_client_socket import FigerSocket
from nerdl.ner.models.model import Model
from nerdl.ner.utils import tokenizer


class FigerNERModel(Model):
    def __init__(self):
        self.socket = FigerSocket()

    def __del__(self):
        self.socket.close()

    def predict_tokenized_sentence(self, tokenized_sentence):
        untokenized_sentence = tokenizer.untokenize_words(tokenized_sentence)

        prediction = self.socket.request_prediction(untokenized_sentence)

        prediction = align_sentences(tokenized_sentence, prediction)

        prediction = cutoff_top(prediction)

        return prediction

    def predict_sentence(self, sentence):
        tokenized_sentence = tokenizer.tokenize_in_words(sentence)

        return self.predict_tokenized_sentence(tokenized_sentence)


def align_sentences(tokenized_sentence, prediction):
    if len(tokenized_sentence) > len(prediction):
        # TODO: last '.' is not splitted in prediction
        raise (ValueError, 'Sentence length > Prediction length. Probably wrong tokenization of FIGER.')
    elif len(tokenized_sentence) < len(prediction):
        raise (ValueError, 'Sentence length < Prediction length.')  # rare
    else:
        correct = True
        for el in zip(tokenized_sentence, prediction):
            if el[0] != el[1][0]:
                correct = False

        if not correct:
            raise (ValueError, 'Sentence length == Prediction length, but different tokens.')  # rare
            print('Equal length but not the same')

    return prediction


def cutoff_top(prediction):
    prediction = normalize_scores(prediction)
    word_types = []

    # TODO: top x
    for word_typescore in prediction:
        types = []
        for type_score in word_typescore[1]:
            types.append(type_score[0])
        word_types.append((word_typescore[0], types))

    return word_types


def normalize_scores(prediction):
    normalized_prediction = []

    for pred_tuple in prediction:
        word, types_scores = pred_tuple
        sum_score = 0
        new_types_scores = []
        for type, score in types_scores:
            sum_score += float(score)
        for type, score in types_scores:
            new_type_score = (type, float(score) / sum_score)
            new_types_scores.append(new_type_score)
        normalized_prediction.append((word, new_types_scores))

    return normalized_prediction
