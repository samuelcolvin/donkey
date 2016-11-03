import re

from click.testing import CliRunner

from donkey.cli import cli

from .conftest import mktree


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(cli, ['--help'])
    assert result.exit_code == 0
    assert 'Like make but for the 21st century.' in result.output


async def test_successful_command(tmpworkdir):
    mktree(tmpworkdir, {
        'makefile.yml': 'foo:\n- echo foo\n',
    })
    runner = CliRunner()
    result = runner.invoke(cli, ['foo'])
    assert result.exit_code == 0
    print(repr(result.output))
    assert re.sub('\d\d:\d\d:\d\d', 'TI:MM:ME', result.output) == """\
Running "foo"...
TI:MM:ME foo
"foo" finished in 0.00s, return code: 0\n"""
