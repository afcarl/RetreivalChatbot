import numpy as np
from tensorflow.python.platform import gfile
from tensorflow.contrib.learn.python.learn.preprocessing.categorical_vocabulary import CategoricalVocabulary
import re

try:
    # pylint: disable=g-import-not-at-top
    import cPickle as pickle
except ImportError:
    # pylint: disable=g-import-not-at-top
    import pickle

TOKENIZER_RE = re.compile(r"[A-Z]{2,}(?![a-z])|[A-Z][a-z]+(?=[A-Z])|[\'\w\-]+",
                          re.UNICODE)


def tokenizer(iterator):
    """Tokenizer generator.
    Args:
      iterator: Input iterator with strings.
    Yields:
      array of tokens per each value in the input.
    """
    for value in iterator:
        yield TOKENIZER_RE.findall(value)


class VocabularyProcessor(object):
    """Maps documents to sequences of word ids."""

    def __init__(self,
                 max_document_length,
                 min_frequency=0,
                 vocabulary=None,
                 tokenizer_fn=None):
        """Initializes a VocabularyProcessor instance.
        Args:
          max_document_length: Maximum length of documents.
            if documents are longer, they will be trimmed, if shorter - padded.
          min_frequency: Minimum frequency of words in the vocabulary.
          vocabulary: CategoricalVocabulary object.
        Attributes:
          vocabulary_: CategoricalVocabulary object.
        """
        self.max_document_length = max_document_length
        self.min_frequency = min_frequency
        if vocabulary:
            self.vocabulary_ = vocabulary
        else:
            self.vocabulary_ = CategoricalVocabulary()
        if tokenizer_fn:
            self._tokenizer = tokenizer_fn
        else:
            self._tokenizer = tokenizer

    def fit(self, raw_documents, unused_y=None):
        """Learn a vocabulary dictionary of all tokens in the raw documents.
        Args:
          raw_documents: An iterable which yield either str or unicode.
          unused_y: to match fit format signature of estimators.
        Returns:
          self
        """
        for tokens in self._tokenizer(raw_documents):
            for token in tokens:
                self.vocabulary_.add(token)
        if self.min_frequency > 0:
            self.vocabulary_.trim(self.min_frequency)
        self.vocabulary_.freeze()
        return self

    def fit_transform(self, raw_documents, unused_y=None):
        """Learn the vocabulary dictionary and return indexies of words.
        Args:
          raw_documents: An iterable which yield either str or unicode.
          unused_y: to match fit_transform signature of estimators.
        Returns:
          x: iterable, [n_samples, max_document_length]. Word-id matrix.
        """
        self.fit(raw_documents)
        return self.transform(raw_documents)

    def transform(self, raw_documents, zero_padding=True):
        """Transform documents to word-id matrix.
        Convert words to ids with vocabulary fitted with fit or the one
        provided in the constructor.
        Args:
          raw_documents: An iterable which yield either str or unicode.
          zero_padding: Boolean activating zero_padding
        Yields:
          x: iterable, [n_samples, max_document_length]. Word-id matrix.
        """

        for tokens in self._tokenizer(raw_documents):
            if zero_padding:
                word_ids = np.zeros(self.max_document_length, np.int64)
            else:
                word_ids = np.zeros(min(len(tokens), self.max_document_length), np.int64)
            for idx, token in enumerate(tokens):
                if idx >= self.max_document_length:
                    break
                word_ids[idx] = self.vocabulary_.get(token)
            yield word_ids

    def reverse(self, documents):
        """Reverses output of vocabulary mapping to words.
        Args:
          documents: iterable, list of class ids.
        Yields:
          Iterator over mapped in words documents.
        """
        for item in documents:
            output = []
            for class_id in item:
                output.append(self.vocabulary_.reverse(class_id))
            yield ' '.join(output)

    def save(self, file_name, path='./data'):
        """Saves vocabulary processor into given file.
        Args:
          filename: Path to output file.
        """
        with gfile.Open(path + '/' + file_name, 'wb') as f:
            f.write(pickle.dumps(self))

    @classmethod
    def restore(cls, filename):
        """Restores vocabulary processor from given file.
        Args:
          filename: Path to file to load from.
        Returns:
          VocabularyProcessor object.
        """
        with gfile.Open(filename, 'rb') as f:
            return pickle.loads(f.read())