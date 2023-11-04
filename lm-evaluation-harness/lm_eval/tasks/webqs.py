"""
Semantic Parsing on Freebase from Question-Answer Pairs
https://cs.stanford.edu/~pliang/papers/freebase-emnlp2013.pdf

WebQuestions is a benchmark for question answering. The dataset consists of 6,642
question/answer pairs. The questions are supposed to be answerable by Freebase, a
large knowledge graph. The questions are mostly centered around a single named entity.
The questions are popular ones asked on the web (at least in 2013).

Homepage: https://worksheets.codalab.org/worksheets/0xba659fe363cb46e7a505c5b6a774dc8a
"""
from lm_eval.base import rf, Task
from lm_eval.metrics import mean
import regex
import string

_CITATION = """
@inproceedings{berant-etal-2013-semantic,
    title = "Semantic Parsing on {F}reebase from Question-Answer Pairs",
    author = "Berant, Jonathan  and
      Chou, Andrew  and
      Frostig, Roy  and
      Liang, Percy",
    booktitle = "Proceedings of the 2013 Conference on Empirical Methods in Natural Language Processing",
    month = oct,
    year = "2013",
    address = "Seattle, Washington, USA",
    publisher = "Association for Computational Linguistics",
    url = "https://aclanthology.org/D13-1160",
    pages = "1533--1544",
}
"""


class WebQs(Task):
    VERSION = 0
    DATASET_PATH = "web_questions"
    DATASET_NAME = None

    def has_training_docs(self):
        return True

    def has_validation_docs(self):
        return False

    def has_test_docs(self):
        return True

    def training_docs(self):
        if self._training_docs is None:
            self._training_docs = list(self.dataset["train"])
        return self._training_docs

    def test_docs(self):
        return self.dataset["test"]

    def doc_to_text(self, doc):
        return "Q: " + doc["question"] + "\nA:"

    def should_decontaminate(self):
        return True

    def doc_to_decontamination_query(self, doc):
        return doc["question"]

    def doc_to_target(self, doc):
        # this picks one answer to be the "correct" one, despite sometimes
        # multiple correct answers being possible.
        # TODO: make sure we're actually handling multi-answer correctly
        return " " + doc["answers"][0]

    def _remove_prefixes(self, aliases):
        # Optimization: Remove any alias that has a strict prefix elsewhere in the list
        # we can do this because if the prefix is acceptable by isgreedy, we can stop looking
        aliases.sort()
        ret = [aliases[0]]
        for alias in aliases[1:]:
            if not alias.startswith(ret[-1]):
                ret.append(alias)

        return ret

    def construct_requests(self, doc, ctx):
        """Uses RequestFactory to construct Requests and returns an iterable of
        Requests which will be sent to the LM.
        :param doc:
                The document as returned from training_docs, validation_docs, or test_docs.
        :param ctx: str
                The context string, generated by fewshot_context. This includes the natural
                language description, as well as the few shot examples, and the question
                part of the document for `doc`.
        """
        continuation = rf.greedy_until(ctx, {"until": ["\n", ".", ","]})
        return continuation

    def _normalize_answer(self, text):
        # Lowercase and remove punctuation, strip whitespace
        text = text.strip().lower().translate(str.maketrans('', '', string.punctuation))

        # Remove articles, resulting in duplicate whitespace
        text = regex.sub(r'\b(a|an|the)\b', ' ', text)

        # Remove duplicate whitespace
        text = " ".join(text.split())

        return text

    def process_results(self, doc, results):
        """Take a single document and the LM results and evaluates, returning a
        dict where keys are the names of submetrics and values are the values of
        the metric for that one document
        :param doc:
            The document as returned from training_docs, validation_docs, or test_docs.
        :param results:
            The results of the requests created in construct_requests.
        """
        continuation = self._normalize_answer(results[0])
        answers = [self._normalize_answer(answer) for answer in doc["answers"]]

        return {
            "em": float(continuation in answers)
        }

    def aggregation(self):
        """
        :returns: {str: [float] -> float}
            A dictionary where keys are the names of submetrics and values are
            functions that aggregate a list of metrics
        """
        return {
            "em": mean,
        } 

    def higher_is_better(self):
        """
        :returns: {str: bool}
            A dictionary where keys are the names of submetrics and values are
            whether a higher value of the submetric is better
        """
        return {
            "em": True,
        } 

