import numpy as np

from settings import path_settings
from settings import settings


class Tag2VecReader:
    def __init__(self):
        self.tag2vec_map = {}  # contains both 'tag-vec' and 'vec-tag'
        self.nb_classes = 0

        self.class_list = settings.TAG2VEC_CLASS_LIST

        if len(self.class_list) == 0 or not self.class_list:
            print('Calculating output labels...')
            training_filepath = path_settings.TRAINING_FILE
            self.training_filepath = training_filepath

            self.calculate_output_labels()
        else:
            self.populate_tag_vector_map(self.class_list)

    def calculate_output_labels(self):
        with open(self.training_filepath, 'rt') as f:
            sentence_num = 0
            tag_class_id = 0
            tags = []

            for line in f:
                line = line.strip()

                if line == '\n':  # blank line
                    sentence_num += 1

                    if sentence_num % 100000 == 0:
                        print('Loaded {} training sentences'.format(sentence_num))

                    continue

                try:
                    word, tag = line.split('\t')
                except ValueError as e:
                    print(e.message)
                    print('Error at sentence #{}.\n Line: {}'.format(sentence_num, line))

                if tag not in tags:
                    tags.append(tag)

            # tags.append('NIL')

            for tag in tags:
                one_hot_vec = np.zeros(len(tags), dtype=np.int32)
                one_hot_vec[tag_class_id] = 1
                self.tag2vec_map[tag] = tuple(one_hot_vec)
                self.tag2vec_map[tuple(one_hot_vec)] = tag
                tag_class_id += 1

            self.nb_classes = tag_class_id + 1

    def populate_tag_vector_map(self, class_list):
        tag_class_id = 0

        for tag in class_list:
            one_hot_vec = np.zeros(len(class_list), dtype=np.int32)
            one_hot_vec[tag_class_id] = 1
            self.tag2vec_map[tag] = tuple(one_hot_vec)
            self.tag2vec_map[tuple(one_hot_vec)] = tag
            tag_class_id += 1

        self.nb_classes = tag_class_id

    # ENCODE
    def encode_tag(self, tag):
        return self.tag2vec_map[tag]

    def encode_tags_list(self, tags):
        if len(tags) <= 1:
            tags_vector = self.tag2vec_map[tags[0]]  # avoid useless calculations, not strictly needed
        else:
            tags_vector = self.encode_multiple_tags(tags)

        return tags_vector

    def encode_multiple_tags(self, tags):
        vector = [0] * self.nb_classes

        for tag in tags.split(','):
            current_vector = list(self.tag2vec_map[tag])
            vector = map(sum, zip(vector, current_vector))

        return vector

    # DECODE
    def decode_prediction(self, pred_seq):
        decoder = settings.KERAS_DECODER

        if decoder == 'max':
            return self.decode_prediction_max(pred_seq, settings.KERAS_MAX_DECODER_NB)
        elif decoder == 'top':
            return self.decode_prediction_top(pred_seq, settings.KERAS_TOP_DECODER_NB)
        else:
            raise (NameError, 'Decoder not found!')

    def decode_prediction_max(self, pred_seq, top_nb=1):
        sentence_pred_tags = []

        for pred_word in pred_seq:
            word_pred_tags = []

            class_vec = np.zeros(self.nb_classes, dtype=np.int32)
            class_vec[np.argmax(pred_word)] = 1

            if tuple(class_vec.tolist()) in self.tag2vec_map:
                word_pred_tags.append(self.tag2vec_map[tuple(class_vec.tolist())])

            # can be cleaner but more expensive # indexes = np.argsort(class_vec)[::-1]
            # NIL and O should be single labels
            if top_nb > 1 and 'NIL' not in word_pred_tags and 'O' not in word_pred_tags:
                while top_nb != 1:
                    class_vec[np.argmax(pred_word)] = 0
                    pred_word[np.argmax(pred_word)] = 0
                    class_vec[np.argmax(pred_word)] = 1

                    if tuple(class_vec.tolist()) in self.tag2vec_map:
                        tag = self.tag2vec_map[tuple(class_vec.tolist())]
                        if tag != 'NIL' and tag != 'O':
                            word_pred_tags.append(tag)

                    top_nb -= 1

            sentence_pred_tags.append(word_pred_tags)

        return sentence_pred_tags

    def decode_prediction_top(self, pred_seq, cutoff_perc=0.95):
        sentence_pred_tags = []

        for pred_word in pred_seq:
            word_pred_tags = []
            pred_cum_perc = 0

            for ix in np.argsort(pred_word)[::-1]:
                class_vec = np.zeros(self.nb_classes, dtype=np.int32)
                class_vec[ix] = 1

                if tuple(class_vec.tolist()) in self.tag2vec_map:
                    predicted_tag = self.tag2vec_map[tuple(class_vec.tolist())]
                    word_pred_tags.append(predicted_tag)

                pred_cum_perc += pred_word[ix]

                if pred_cum_perc > cutoff_perc:
                    break

            if len(word_pred_tags) > 1:
                word_pred_tags = clean_tags(word_pred_tags)

            sentence_pred_tags.append(word_pred_tags)

        return sentence_pred_tags


def clean_tags(predicted_tags):
    """
    Manage O and NIL tags. Removes other tags if first. Removes O/NIL tag if not first.
    :param predicted_tags:
    :return:
    """

    if 'O' in predicted_tags:
        if predicted_tags[0] == 'O':
            predicted_tags = ['O']  # can remove all other elements so we don't need to return a new list
        else:
            predicted_tags.remove('O')

    if 'NIL' in predicted_tags:
        if predicted_tags[0] == 'NIL':
            predicted_tags = ['NIL']  # can remove all other elements so we don't need to return a new list
        else:
            predicted_tags.remove('NIL')

    return predicted_tags