# -*- coding=utf-8 -*-
import os
import re
import datetime
from collections import defaultdict

try:
    import lxml.etree as ET
except ImportError:
    import xml.etree.cElementTree as ET

import click
from simple_loggers import SimpleLogger

from pubmed_xml import util
from pubmed_xml.core.article import ArticleObject
from pubmed_xml.core.abstract import parse_abstract
 


def parse_tree(tree):
    if tree.find('PubmedArticle') is None:
        yield None
    else:
        for PubmedArticle in tree.iterfind('PubmedArticle'):
            context = {}
            MedlineCitation = PubmedArticle.find('MedlineCitation')
            Article = MedlineCitation.find('Article')

            context['pmid'] = int(MedlineCitation.findtext('PMID'))

            context['e_issn'] = Article.findtext('Journal/ISSN[@IssnType="Electronic"]')
            context['issn'] = Article.findtext('Journal/ISSN[@IssnType="Print"]') or MedlineCitation.findtext('MedlineJournalInfo/ISSNLinking')

            context['journal'] = Article.findtext('Journal/Title')
            context['iso_abbr'] = Article.findtext('Journal/ISOAbbreviation')

            context['med_abbr'] = MedlineCitation.findtext('MedlineJournalInfo/MedlineTA')

            context['pubdate'] = ' '.join(Article.xpath('Journal/JournalIssue/PubDate/*/text()'))

            pubmed_pubdate = year = ''
            for status in ('pubmed', 'entrez', 'medline'):
                ymd = PubmedArticle.xpath('PubmedData/History/PubMedPubDate[@PubStatus="{}"]/*/text()'.format(status))
                if ymd:
                    pubmed_pubdate = datetime.datetime(*map(int, ymd))
                    year = pubmed_pubdate.year
                    pubmed_pubdate = pubmed_pubdate.strftime('%Y/%m/%d')
                    break

            context['year'] = year
            context['pubmed_pubdate'] = pubmed_pubdate

            context['pagination'] = Article.findtext('Pagination/MedlinePgn')
            context['volume'] = Article.findtext('Journal/JournalIssue/Volume')
            context['issue'] = Article.findtext('Journal/JournalIssue/Issue')
            context['title'] = ''.join(Article.find('ArticleTitle').itertext())
            context['keywords'] = MedlineCitation.xpath('KeywordList/Keyword/text()')
            context['pub_status'] = PubmedArticle.findtext('PubmedData/PublicationStatus')

            context['abstract'] = parse_abstract(Article.xpath('Abstract/AbstractText'))
            
            author_mail = []

            author_list = []
            affiliation_author_map = defaultdict(list)
            for author in Article.xpath('AuthorList/Author'):

                last_name = author.findtext('LastName')
                fore_name = author.findtext('ForeName')
                # Initials = author.findtext('Initials')

                author_name = ' '.join(name for name in [fore_name, last_name] if name)
        
                author_list.append(author_name)

                for aff in author.xpath('AffiliationInfo/Affiliation/text()'):
                    affiliation_author_map[aff].append(author_name)

                affiliation_info = '\n'.join(author.xpath('AffiliationInfo/Affiliation/text()'))
                mail = re.findall(r'([^\s]+?@.+)\.', str(affiliation_info))
                if mail:
                    mail = '{}: {}'.format(author_name, mail[0])
                    author_mail.append(mail)

            context['author_mail'] = author_mail

            context['author_first'] = context['author_last'] = '.'
            if author_list:
                context['author_first'] = author_list[0]
                context['author_last'] = author_list[-1]

            context['authors'] = author_list

            # affiliation list
            affiliations = Article.xpath('AuthorList/Author/AffiliationInfo/Affiliation/text()')

            affiliation_unique_list = []
            for aff in affiliations:
                if aff not in affiliation_unique_list:
                    affiliation_unique_list.append(aff)

            context['affiliations'] = [
                f'{n}. {aff} - {affiliation_author_map.get(aff)}' 
                for n, aff in enumerate(affiliation_unique_list, 1)
            ]

            context['pub_types'] = Article.xpath('PublicationTypeList/PublicationType/text()')
            context['doi'] = PubmedArticle.findtext('PubmedData/ArticleIdList/ArticleId[@IdType="doi"]')
            context['pmc'] = PubmedArticle.findtext('PubmedData/ArticleIdList/ArticleId[@IdType="pmc"]')

            yield context


class Pubmed_XML_Parser(object):
    """PubMed XML Parser
    >>> from pubmed_xml import Pubmed_XML_Parser
    >>> pubmed = Pubmed_XML_Parser()
    >>> for article in pubmed.parse('30003000'):
    >>>     print(article)
    """

    def __init__(self):
        self.logger = SimpleLogger('Pubmed_XML_Parser')

    def get_tree(self, xml):
        if os.path.isfile(xml):
            tree = ET.parse(util.safe_open(xml))
        elif xml.startswith('<?xml '):
            tree = ET.fromstring(xml)
        else:
            tree = ET.fromstring(util.get_pubmed_xml(xml))
        return tree

    def parse(self, xml):
        """parse xml from local file or text string
        """
        try:
            tree = self.get_tree(xml)
        except Exception as e:
            raise Exception(click.style(f'[XML_PARSE_ERROR] {e}', fg='red'))
        
        for context in parse_tree(tree):
            yield ArticleObject(**context)
