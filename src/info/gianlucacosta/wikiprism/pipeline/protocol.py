from typing import TextIO

from info.gianlucacosta.eos.core.functional import Consumer, Mapper, Producer

from ..dictionary import Dictionary
from ..page import Page

type WikiFile = str | TextIO

type PipelineMessageListener = Consumer[str]
type PipelineEndedListener = Consumer[Exception | None]

type DictionaryFactory[TTerm] = Producer[Dictionary[TTerm]]

type TermExtractor[TTerm] = Mapper[Page, list[TTerm]]


class PipelineCanceledException(Exception):
    """
    Exception describing an extraction pipeline canceled because of a request issued
    by the client.

    It is actually never raised by the pipeline; however:

    * it must be raised by the methods of PipelineStrategy to notify that the pipeline
      must be canceled

    * it is passed to the on_ended() method of PipelineStrategy as soon as the extraction
      is actually canceled.
    """
