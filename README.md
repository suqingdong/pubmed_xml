# PubMed XML Parser

## Installation
```bash
python3 -m pip install pubmed_xml
```

## Usage
### CommandLine
```bash
pubmed_xml --help

# parse single
pubmed_xml 30003000

# parse batch
pubmed_xml 30003000,30003001,30003002

# parse multiple
pubmed_xml 30003000 30003001 30003002

# parse from xml file
pubmed_xml tests/pubmed22n1543.xml.gz -o out.jl

# save file
pubmed_xml 30003000,30003001,30003002 -o out.jl
```

### Python
```python
from pubmed_xml import Pubmed_XML_Parser

pubmed = Pubmed_XML_Parser()

for article in pubmed.parse('30003000,30003001,30003002'):
    print(article)        # Article<30003002>
    print(article.data)   # dict object
    print(article.to_json(indent=2))   # json string
    print(article.pmid, article.title, article.abstract) # by attribute
    print(article['pmid'], article['title'], article['abstract']) # by key
```
