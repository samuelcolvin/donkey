from click.testing import CliRunner

from donkey.cli import cli

from .conftest import mktree, normalise_log


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(cli, ['--help'])
    assert result.exit_code == 0
    assert 'Like make but for the 21st century.' in result.output


files = {
    'makefile.yml': """
foo:
- echo foo
bar:
- echo bar
to-stderr:
- echo "this goes to standard error" >&2
no-newline:
  - printf "hello"
fails:
  interpreter: python
  script: true
  run:
  - import sys
  - print('hello')
  - sys.exit(123)
  - print('good bye')
"""}


def test_single_command(tmpworkdir):
    mktree(tmpworkdir, files)
    runner = CliRunner()
    result = runner.invoke(cli, ['foo'])
    assert result.exit_code == 0
    assert """\
Running "foo"...
TI:XX:ME 1: foo
"foo" finished in 0.0Xs, return code: 0\n""" == normalise_log(result.output)


def test_stderr(tmpworkdir):
    mktree(tmpworkdir, files)
    runner = CliRunner()
    result = runner.invoke(cli, ['to-stderr'])
    assert result.exit_code == 0
    assert """\
Running "to-stderr"...
TI:XX:ME 2: this goes to standard error
"to-stderr" finished in 0.0Xs, return code: 0\n""" == normalise_log(result.output)


def test_no_newline(tmpworkdir):
    mktree(tmpworkdir, files)
    runner = CliRunner()
    result = runner.invoke(cli, ['no-newline'])
    assert result.exit_code == 0
    assert """\
Running "no-newline"...
TI:XX:ME 1: hello
"no-newline" finished in 0.0Xs, return code: 0\n""" == normalise_log(result.output)


def test_multiple_commands(tmpworkdir):
    mktree(tmpworkdir, files)
    runner = CliRunner()
    result = runner.invoke(cli, ['foo', 'bar'])
    assert result.exit_code == 0
    assert """\
Running "foo"... ●
TI:XX:ME ● 1: foo
"foo" finished in 0.0Xs, return code: 0 ●
Running "bar"... ●
TI:XX:ME ● 1: bar
"bar" finished in 0.0Xs, return code: 0 ●\n""" == normalise_log(result.output)


def test_no_file(tmpworkdir):
    runner = CliRunner()
    result = runner.invoke(cli)
    assert result.exit_code == 2
    assert result.output == ('Error: Unable to find definition file with standard name "donkey.yml" or "makefile.yml" '
                             'in the current working directory or any parent directory\n')


def test_failed_command(tmpworkdir):
    mktree(tmpworkdir, files)
    runner = CliRunner()
    result = runner.invoke(cli, ['fails'])
    assert result.exit_code == 123
    print(result.output)
    assert """\
Running "fails"...
TI:XX:ME 1: hello
"fails" finished in 0.XXs, return code: 123
Error: commands failed, return codes: 123\n""" == normalise_log(result.output, True)


def test_dots(tmpworkdir):
    mktree(tmpworkdir, {
        'makefile.yaml': """
print-dots:
  interpreter: python
  script: true
  run:
  - "import sys, time"
  - "for i in range(5):"
  - "    sys.stdout.write('.')"
  - "    time.sleep(0.01)"
  - "    sys.stdout.flush()"
"""})
    runner = CliRunner()
    result = runner.invoke(cli, ['print-dots'])
    print(result.output)
    assert result.exit_code == 0
    assert """\
Running "print-dots"...
TI:XX:ME 1: .....
"print-dots" finished in 0.XXs, return code: 0\n""" == normalise_log(result.output, True)
