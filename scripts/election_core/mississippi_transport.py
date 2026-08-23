"""Transport policy for Mississippi certified and provisional election data."""
from __future__ import annotations
from urllib.parse import urlparse
from typing import Callable

TextGetter=Callable[[str],str]
CERTIFIED_HOSTS={"www.sos.ms.gov","sos.ms.gov"}

def _validate_https(url:str)->str:
    p=urlparse(url)
    if p.scheme!="https" or not p.hostname: raise ValueError("Mississippi election source must use HTTPS")
    return p.hostname.lower()

class MississippiCertifiedTransport:
    def __init__(self,url:str,get_text:TextGetter):
        host=_validate_https(url)
        if host not in CERTIFIED_HOSTS: raise ValueError("certified Mississippi results must use the Secretary of State host")
        self.url=url; self.get_text=get_text; self._text=None
    def fetch_text(self)->str:
        if self._text is None:
            text=self.get_text(self.url)
            if not isinstance(text,str) or not text.strip(): raise RuntimeError("Mississippi certified source returned empty results")
            self._text=text
        return self._text

class MississippiProvisionalTransport:
    def __init__(self,url:str,get_text:TextGetter,*,county_fips:str,approved_hosts:set[str]):
        host=_validate_https(url)
        if len(county_fips)!=5 or not county_fips.startswith("28") or not county_fips.isdigit(): raise ValueError("valid Mississippi county FIPS required")
        normalized={h.lower() for h in approved_hosts}
        if host not in normalized: raise ValueError("county election-night host is not approved")
        if host in CERTIFIED_HOSTS: raise ValueError("SOS host cannot be labeled provisional county source")
        self.url=url; self.get_text=get_text; self.county_fips=county_fips; self.host=host; self._text=None
    def fetch_text(self)->str:
        if self._text is None:
            text=self.get_text(self.url)
            if not isinstance(text,str) or not text.strip(): raise RuntimeError("Mississippi provisional county source returned empty results")
            self._text=text
        return self._text
