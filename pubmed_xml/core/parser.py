# -*- coding=utf-8 -*-
import os
import re
import datetime

try:
    import lxml.etree as ET
except ImportError:
    import xml.etree.cElementTree as ET

import click
from simple_loggers import SimpleLogger

from pubmed_xml import util
from pubmed_xml.core.article import ArticleObject
from pubmed_xml.core.abstract import parse_abstract


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

        if tree.find('PubmedArticle') is None:
            self.logger.warning('no article found')
            yield None
        else:
            for PubmedArticle in tree.iterfind('PubmedArticle'):
                context = {}
                MedlineCitation = PubmedArticle.find('MedlineCitation')
                Article = MedlineCitation.find('Article')

                context['pmid'] = int(MedlineCitation.findtext('PMID'))
                self.logger.debug('>>> PMID: {}'.format(context['pmid']))

                context['e_issn'] = Article.findtext('Journal/ISSN[@IssnType="Electronic"]')
                context['issn'] = Article.findtext('Journal/ISSN[@IssnType="Print"]')

                context['journal'] = Article.findtext('Journal/Title')
                context['iso_abbr'] = Article.findtext('Journal/ISOAbbreviation')

                context['med_abbr'] = MedlineCitation.findtext('MedlineJournalInfo/MedlineTA')
                context['med_issn'] = MedlineCitation.findtext('MedlineJournalInfo/ISSNLinking')
                context['nlm_id'] = MedlineCitation.findtext('MedlineJournalInfo/NlmUniqueID')

                context['pubdate'] = ' '.join(Article.xpath('Journal/JournalIssue/PubDate/*/text()'))

                pubmed_pubdate = year = ''
                for status in ('pubmed', 'entrez', 'medline'):
                    ymd = PubmedArticle.xpath(f'PubmedData/History/PubMedPubDate[@PubStatus="{status}"]/*/text()')
                    if ymd:
                        pubmed_pubdate = datetime.datetime(*map(int, ymd))
                        year = pubmed_pubdate.year
                        pubmed_pubdate = pubmed_pubdate.strftime('%Y-%m-%d')
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
                
                author_mails = []
                author_list = []
                for author in Article.xpath('AuthorList/Author'):
                    names = [each.text for each in author.xpath('*')][:3]  # LastName, ForeName, Initials
                    names = [n for n in names if n]
                    fullname = names[0] if len(names) == 1 else ' '.join([names[1], names[0]])
                    author_list.append(fullname)     # fullname = ForeName LastName

                    affiliation = '\n'.join(author.xpath('AffiliationInfo/Affiliation/text()'))
                    mail = util.check_email(affiliation)
                    if mail:
                        author_mails.append(f'{fullname}:{mail}')

                context['author_mails'] = author_mails

                context['affiliations'] = list(set(Article.xpath('AuthorList/Author/AffiliationInfo/Affiliation/text()')))

                context['authors'] = author_list

                context['pub_types'] = Article.xpath('PublicationTypeList/PublicationType/text()')

                context['doi'] = PubmedArticle.findtext('PubmedData/ArticleIdList/ArticleId[@IdType="doi"]')
                context['pmc'] = PubmedArticle.findtext('PubmedData/ArticleIdList/ArticleId[@IdType="pmc"]')
                context['pii'] = PubmedArticle.findtext('PubmedData/ArticleIdList/ArticleId[@IdType="pii"]')

                ref_list = PubmedArticle.xpath('PubmedData/ReferenceList/Reference/ArticleIdList/ArticleId[@IdType="pubmed"]/text()')
                context['references'] = list(map(int, ref_list))

                yield ArticleObject(**context)
