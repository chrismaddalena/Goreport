#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Name:      GoReport v2.1
Author:    Christopher Maddalena

This is part script and part class for interfacing with the GoPhish API. You provide
an API key and host (e.g. https://ip:port) in a gophish.config file for the connection.

Then provide a campaign ID as a command line argument along with your preference
for the report type: python3 goreport.py --id 36 --format word

The results will be fetched and put through additional processing. A csv or Word
.docx file is created with all of the campaign details and some of the settings
that may be of interest (e.g. SMTP hostname and other basic info). The class
also performs some analysis data points, like the browser user-agents and IP
addresses, to generate statistics for browser versions, operating systems, and
locations.
"""

from lib import banners, goreport
import click


# Setup an AliasedGroup for CLICK
class AliasedGroup(click.Group):
    """Allows commands to be called by their first unique character."""

    def get_command(self, ctx, cmd_name):
        """
        Allows commands to be called by thier first unique character
        :param ctx: Context information from click
        :param cmd_name: Calling command name
        :return:
        """
        rv = click.Group.get_command(self, ctx, cmd_name)
        if rv is not None:
            return rv
        matches = [x for x in self.list_commands(ctx)
                   if x.startswith(cmd_name)]
        if not matches:
            return None
        elif len(matches) == 1:
            return click.Group.get_command(self, ctx, matches[0])
        ctx.fail('Too many matches: %s' % ', '.join(sorted(matches)))


# Create the help option for CLICK
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
@click.group(cls=AliasedGroup, context_settings=CONTEXT_SETTINGS)

def GoReport():
    """Everything starts here."""
    pass


# Setup our CLICK arguments and help text
@GoReport.command(name='report', short_help="Generate a full report for the selected campaign \
                  -- either CSV or DOCX.")
@click.option('--id', type=click.STRING, is_flag=False, help="The target campaign's ID. You can \
              provide a comma-separated list of IDs (e.g. -id #,#,#).", required=True)
@click.option('--format', type=click.Choice(['csv', 'word', 'quick']), help="Use this option to \
              choose between report formats.", required=True)
@click.option('--combine', is_flag=True, help="Combine all results into one report. The first \
              campaign ID will be used for information such as campaign name, dates, and URL.",
              required=False)
@click.option('--complete', is_flag=True, help="Optionally mark the campaign as complete in \
              GoPhish.", required=False)
@click.option('--config', type=click.Path(exists=True, readable=True, resolve_path=True),
              help="Name an alternate config file for GoReport to use. The default is \
              gophish.config.")
@click.option('-v', '--verbose', is_flag=True, help="Sets verbose to true so GoReport will \
              display some additional feedback, such as flagging IP mis-matches.", required=False)
@click.pass_context
def parse_options(self, id, format, combine, complete, config, verbose):
    """GoReport uses the GoPhish API to connect to your GoPhish instance using the
    IP address, port, and API key for your installation. This information is provided
    in the gophish.config file and loaded at runtime. GoReport will collect details
    for the specified campaign and output statistics and interesting data for you.

    Select campaign ID(s) to target and then select a report format.\n
       * csv: A comma separated file. Good for copy/pasting into other documents.\n
       * word: A formatted docx file. A template.docx file is required (see the README).\n
       * quick: Command line output of some basic stats. Good for a quick check or client call.\n
    """
    # Print the GoPhish banner
    banners.print_banner()
    # Create a new GoReport object that will use the specified report format
    gophish = goreport.GoReport(format, config, verbose)
    # Execute reporting for the provided list of IDs
    gophish.run(id, combine, complete)

if __name__ == '__main__':
    parse_options()
