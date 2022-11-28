import sys
import click

from pubmed_xml import version_info, Pubmed_XML_Parser, util


CONTEXT_SETTINGS = dict(help_option_names=['-?', '-h', '--help'])

@click.command(
    name=version_info['prog'],
    help=click.style(version_info['desc'], italic=True, fg='cyan', bold=True),
    context_settings=CONTEXT_SETTINGS,
    no_args_is_help=True,
)
@click.argument('infile')
@click.option('-o', '--outfile', help='the output filename')
def cli(**kwargs):
    outfile = kwargs['outfile']
    out = util.safe_open(outfile, 'w') if outfile else sys.stdout
    pubmed = Pubmed_XML_Parser(kwargs['infile'])
    with out:
        for article in pubmed.parse():
            out.write(article.to_json() + '\n')
    if outfile:
        pubmed.logger.debug(f'save file to: {outfile}')


def main():
    cli()


if __name__ == '__main__':
    main()
