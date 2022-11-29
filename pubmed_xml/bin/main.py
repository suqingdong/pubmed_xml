import sys
import click

from pubmed_xml import version_info, Pubmed_XML_Parser, util


CONTEXT_SETTINGS = dict(help_option_names=['-?', '-h', '--help'])

__epilog__ = click.style('''

\b
example:
    {prog} --help
    {prog} 30003000
    {prog} 30003000,30003001,30003002
    {prog} 30003000 30003001 30003002
    {prog} 30003000,30003001,30003002 -o out.jl
    {prog} tests/pubmed22n1543.xml.gz -o out.jl

contact: {author} <{author_email}>
''', fg='cyan').format(**version_info)


@click.command(
    name=version_info['prog'],
    help=click.style(version_info['desc'], italic=True, fg='bright_green', bold=True),
    context_settings=CONTEXT_SETTINGS,
    epilog=__epilog__,
    no_args_is_help=True,
)
@click.argument('infile', nargs=-1)
@click.option('-o', '--outfile', help='the output filename')
@click.version_option(version=version_info['version'], prog_name=version_info['prog'])
def cli(**kwargs):
    outfile = kwargs['outfile']
    out = util.safe_open(outfile, 'w') if outfile else sys.stdout
    pubmed = Pubmed_XML_Parser()
    with out:
        for xml in kwargs['infile']:
            for article in pubmed.parse(xml):
                out.write(article.to_json() + '\n')
    if outfile:
        pubmed.logger.debug(f'save file to: {outfile}')


def main():
    cli()


if __name__ == '__main__':
    main()
