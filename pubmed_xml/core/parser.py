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

                context['pub_mode'] = Article.attrib['PubModel']

                context['issn'] = Article.findtext('Journal/ISSN')
                context['issn_type'] = Article.find('Journal/ISSN').attrib['IssnType']

                context['journal'] = Article.findtext('Journal/Title')
                context['iso_abbr'] = Article.findtext('Journal/ISOAbbreviation')

                context['med_abbr'] = MedlineCitation.findtext('MedlineJournalInfo/MedlineTA')
                context['med_issn'] = MedlineCitation.findtext('MedlineJournalInfo/ISSNLinking')
                context['nlm_id'] = MedlineCitation.findtext('MedlineJournalInfo/NlmUniqueID')
                context['country'] = MedlineCitation.findtext('MedlineJournalInfo/Country')

                # PubDate vs ArticleDate vs PubMedPubDate?
                # https://gist.github.com/suqingdong/ad5166618b386627c0fea079215d77bb

                # convert to datetime
                mdat = util.check_date(PubmedArticle.find('MedlineCitation/DateRevised'))
                edat = util.check_date(PubmedArticle.find('PubmedData/History/PubMedPubDate[@PubStatus="pubmed"]'))
                pdat = util.check_date(Article.find('ArticleDate') if Article.find('ArticleDate') is not None else Article.find('Journal/JournalIssue/PubDate'))
                context['mdat'] = mdat.strftime('%F')
                context['edat'] = edat.strftime('%F')
                context['pdat'] = pdat.strftime('%F')

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

                references = PubmedArticle.xpath('PubmedData/ReferenceList/Reference/ArticleIdList/ArticleId[@IdType="pubmed"]/text()')
                context['references'] = ','.join(references)

                yield ArticleObject(**context)
