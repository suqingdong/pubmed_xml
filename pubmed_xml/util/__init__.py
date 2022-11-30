import re
import pathlib
import datetime

import requests
from dateutil.parser import parse as parse_date
from w3lib import html


def safe_open(filename: str, mode='r'):
    file = pathlib.Path(filename)

    if 'w' in mode and not file.parent.exists():
        file.parent.mkdir(parents=True)

    if filename.endswith('.gz'):
        import gzip
        return gzip.open(filename, mode=mode)

    return file.open(mode=mode)


def check_email(text: str):
    res = re.findall(r'([^\s]+?@.+)\.', text)
    return res[0] if res else None


def replace_entities(text: str):
    """
        multi level entites:
            - eg. PMID=33866717:  '&amp;lt;10' => '&lt;10' => '<10'
    """
    raw_text = text
    n = 5
    while n > 0:
        if re.search(r'&\w{2,7};', text):
            text = html.replace_entities(text)
        else:
            break
        n -= 1

    if n == 0:
        print(f'too many levels for: {repr(raw_text)}')
    return text


def get_pubmed_xml(pmid):
    """get pubmed xml with eutils
    """
    url = f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={pmid}&format=xml'
    return requests.get(url).text


def check_date(element):
    year = element.findtext('Year')
    month = element.findtext('Month')
    day = element.findtext('Day') or '1'

    return parse_date(f'{year}-{month}-{day}')
