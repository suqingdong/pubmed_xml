#!/usr/bin/env python
#-*- encoding: utf8 -*-
import re
import os
import sys
import json
import time
import signal

import lxml.etree as ET
from w3lib import html
from dateutil.parser import parse as date_parse


PY3 = sys.version_info.major == 3

if not PY3:
    reload(sys)
    sys.setdefaultencoding('utf-8')


signal.signal(signal.SIGPIPE, signal.SIG_DFL)


def safe_open(filename, mode='r'):

    if filename.endswith('.gz'):
        import gzip
        return gzip.open(filename, mode)
    return open(filename, mode)


def parse_xml(infile):

    tree = ET.parse(infile)

    entities_pattern = re.compile(r'&[^\s]+?;')  # 实体字符串  &gt; &#8819;

    special_chars_1 = u'\u2009|\u202f'    # ' '
    special_chars_2 = u'\u2217'           # '*'
    special_pattern_1 = re.compile(special_chars_1)
    special_pattern_2 = re.compile(special_chars_2)

    if tree.find('PubmedArticle') is None:
        yield None
    else:
        for PubmedArticle in tree.iterfind('PubmedArticle'):
            MedlineCitation = PubmedArticle.find('MedlineCitation')

            pmid = int(MedlineCitation.find('PMID').text)

            Article = MedlineCitation.find('Article')

            e_issn = ''.join(Article.xpath('Journal/ISSN[@IssnType="Electronic"]/text()')) or '.'
            issn = ''.join(Article.xpath('Journal/ISSN[@IssnType="Print"]/text()')) or '.'
            if issn == '.':
                issn = ''.join(MedlineCitation.xpath('MedlineJournalInfo/ISSNLinking/text()')) or '.'

            journal = ''.join(Article.xpath('Journal/Title/text()')) or '.'
            journal_abbr = ''.join(Article.xpath('Journal/ISOAbbreviation/text()')) or '.'
            if journal_abbr != '.':
                journal_abbr = journal_abbr.replace('.', '')

            pubdate = ' '.join(Article.xpath('Journal/JournalIssue/PubDate/*/text()'))

            title = Article.find('ArticleTitle').text

            # ==============================================
            # 1 没有Abstract
            # 2 只有1个AbstractText
            # 3 有多个AbstractText，获取Label
            #
            # * 待解决：编码问题
            # ==============================================
            AbstractTexts = Article.xpath('Abstract/AbstractText')
            if not AbstractTexts:
                abstract = '.'
            elif len(AbstractTexts) == 1:
                abstract = ''.join(AbstractTexts[0].itertext()) or '.'
            else:
                abstract = []
                for each in AbstractTexts:
                    label = each.attrib.get('Label')
                    text = ''.join(each.itertext())
                    if label:
                        abstract.append('{}: {}'.format(label, text))
                    else:
                        abstract.append(text)
                abstract = '\n'.join(abstract)

            # =================================================================
            # 移除HTML标签
            abstract = html.remove_tags(abstract)   # 返回unicode字符串

            # 替换实体字符串
            # 特殊情况 - 多重转移：a &amp;gt; b == a &gt; b == a > b
            n = 0
            while entities_pattern.findall(abstract):
                abstract = html.replace_entities(abstract)
                n += 1
                if n >= 3:
                    sys.stderr.write('with multiple entities for pmid: {}\n'.format(pmid))
                    break

            # 特殊Unicode字符处理
            if special_pattern_1.findall(abstract):
                abstract = special_pattern_1.sub(' ', abstract)
            if special_pattern_2.findall(abstract):
                abstract = special_pattern_2.sub('*', abstract)

            # =================================================================

            author_list = []
            for author in Article.xpath('AuthorList/Author'):
                lastname = author.xpath('LastName/text()')
                initials = author.xpath('Initials/text()')
                suffix = author.xpath('Suffix/text()')
                author_list.append(' '.join(lastname + initials + suffix))

            publication_types = Article.xpath('PublicationTypeList/PublicationType/text()')

            pmc = doi = '.'
            ArticleIds = PubmedArticle.xpath('PubmedData/ArticleIdList/ArticleId')
            if ArticleIds:
                for each in ArticleIds:
                    if each.attrib['IdType'] == 'pmc':
                        pmc = each.text
                    elif each.attrib['IdType'] == 'doi':
                        doi = each.text

            fields = '''
                pmid issn journal journal_abbr pubdate title abstract
                author_list publication_types pmc doi e_issn'''.split()

            tmpdict = locals()
            context = {field: tmpdict[field] for field in fields}

            yield context


def main():

    start_time = time.time()
    out = safe_open(args['output'], 'w') if args['output'] else sys.stdout
    with out:
        for infile in args['infile']:
            sys.stderr.write('>>> dealing file: {} ...\n'.format(infile))
            for n, context in enumerate(parse_xml(infile), 1):
                line = json.dumps(context, ensure_ascii=False) + '\n'
                if PY3:
                    line = line.encode('utf-8')
                out.write(line)
                sys.stderr.write('\033[Kwrite {} lines\r'.format(n))
                sys.stderr.flush()
            print

    if args['output']:
        sys.stderr.write('\nsave file to: {output}'.format(**args))
    sys.stderr.write('\ntime used: {:.1f}s\n'.format(time.time() - start_time))


if __name__ == '__main__':

    import argparse

    parser = argparse.ArgumentParser(
        prog='pubmed_xml_parser',
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('infile', help='the input pubmed xml file', nargs='+')

    parser.add_argument('-o', '--output', help='the output file [stdout]')

    args = vars(parser.parse_args())

    main()

