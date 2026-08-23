"""Official AlabamaVotes election-night transport boundary."""
from __future__ import annotations
from typing import Callable
from urllib.parse import urlparse

TextGetter=Callable[[str],str]
ALLOWED_HOSTS={"www2.alabamavotes.gov","alabamavotes.gov","www.alabamavotes.gov"}

class AlabamaVotesTransport:
    def __init__(self,url:str,get_text:TextGetter):
        parsed=urlparse(url)
        if parsed.scheme!="https" or parsed.hostname not in ALLOWED_HOSTS:
            raise ValueError("Alabama results URL must use an official AlabamaVotes HTTPS host")
        self.url=url; self.get_text=get_text; self._text=None
    def fetch_text(self)->str:
        if self._text is None:
            text=self.get_text(self.url)
            if not isinstance(text,str) or not text.strip(): raise RuntimeError("AlabamaVotes returned empty results")
            self._text=text
        return self._text
