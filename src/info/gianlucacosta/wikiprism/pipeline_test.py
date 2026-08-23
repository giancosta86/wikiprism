from time import sleep

from info.gianlucacosta.eos.core.multiprocessing.pool import (
    AnyProcessPool,
    InThreadPool,
)

from .dictionary import Dictionary
from .dictionary.memory import InMemoryDictionary
from .global_test import MyTestTerm, create_wiki_stream
from .page import Page
from .pipeline import run_extraction_pipeline
from .pipeline.protocol import PipelineCanceledException, TermExtractor, WikiFile
from .pipeline.strategy import PipelineStrategy


class MyTestInMemoryDictionary(InMemoryDictionary[MyTestTerm]):
    pass


class MySlowTestInMemoryDictionary(InMemoryDictionary[MyTestTerm]):
    def add_term(self, term: MyTestTerm) -> None:
        sleep(0.2)
        return super().add_term(term)


class BasicTestPipelineStrategy(PipelineStrategy[MyTestTerm]):
    def __init__(
        self,
        dictionary: Dictionary[MyTestTerm],
        term_extractor: TermExtractor[MyTestTerm] | None = None,
        add_wiki_error: bool = False,
    ) -> None:
        super().__init__()
        self._dictionary = dictionary
        self._term_extractor = (
            term_extractor if term_extractor else lambda page: [MyTestTerm(page.text)]
        )
        self._add_wiki_error = add_wiki_error
        self.exception: Exception | None = None

    def create_pool(self) -> AnyProcessPool:
        return InThreadPool()

    def initialize_pipeline(self) -> None:
        pass

    def create_dictionary(self) -> Dictionary[MyTestTerm]:
        return self._dictionary

    def get_wiki_file(self) -> WikiFile:
        return create_wiki_stream(add_error=self._add_wiki_error)

    def get_term_extractor(self) -> TermExtractor[MyTestTerm]:
        return self._term_extractor

    def perform_last_successful_steps(self) -> None:
        pass

    def on_message(self, message: str) -> None:
        pass

    def on_ended(self, exception: Exception | None) -> None:
        self.exception = exception


class TestRunExtractionPipeline:
    def test_merry_path(self):
        test_dictionary = MyTestInMemoryDictionary()

        pipeline_strategy = BasicTestPipelineStrategy(test_dictionary)

        pipeline_handle = run_extraction_pipeline(pipeline_strategy)
        pipeline_handle.join()

        assert pipeline_strategy.exception is None
        assert test_dictionary.terms == {
            MyTestTerm(entry) for entry in ["A1", "B2", "C3", "D4", "E5", "Z6"]
        }

    def test_cancelation(self):
        test_dictionary = MySlowTestInMemoryDictionary()

        pipeline_strategy = BasicTestPipelineStrategy(test_dictionary)

        pipeline_handle = run_extraction_pipeline(pipeline_strategy)
        pipeline_handle.request_cancel()
        pipeline_handle.join()

        assert isinstance(pipeline_strategy.exception, PipelineCanceledException)

    def test_with_extraction_errors(self):
        test_dictionary = MyTestInMemoryDictionary()

        def sometimes_failing_extractor(page: Page) -> list[MyTestTerm]:
            if page.text in {"B2", "E5"}:
                raise Exception("Very expected failure!")

            return [MyTestTerm(entry=page.text)]

        pipeline_strategy = BasicTestPipelineStrategy(
            test_dictionary, term_extractor=sometimes_failing_extractor
        )

        pipeline_handle = run_extraction_pipeline(pipeline_strategy)
        pipeline_handle.join()

        assert pipeline_strategy.exception is None

        assert test_dictionary.terms == {
            MyTestTerm("A1"),
            MyTestTerm("C3"),
            MyTestTerm("D4"),
            MyTestTerm("Z6"),
        }

    def test_with_dictionary_errors(self):
        class DictionaryWithCustomErrors(MyTestInMemoryDictionary):
            def add_term(self, term: MyTestTerm) -> None:
                if term.entry in {"C3", "E5"}:
                    raise Exception("Custom dictionary exception!")

                return super().add_term(term)

        test_dictionary = DictionaryWithCustomErrors()

        pipeline_strategy = BasicTestPipelineStrategy(test_dictionary)

        pipeline_handle = run_extraction_pipeline(pipeline_strategy)
        pipeline_handle.join()

        assert pipeline_strategy.exception is None

        assert test_dictionary.terms == {
            MyTestTerm("A1"),
            MyTestTerm("B2"),
            MyTestTerm("D4"),
            MyTestTerm("Z6"),
        }

    def test_sax_error(self):
        test_dictionary = MyTestInMemoryDictionary()

        pipeline_strategy = BasicTestPipelineStrategy(
            test_dictionary, add_wiki_error=True
        )

        pipeline_handle = run_extraction_pipeline(pipeline_strategy)
        pipeline_handle.join()

        assert pipeline_strategy.exception is None
        assert test_dictionary.terms == {
            MyTestTerm(entry) for entry in ["A1", "B2", "C3", "D4", "E5", "Z6"]
        }
