import pytest

from donkey.main import DonkeyError, execute

from .conftest import mktree

async def test_successful_command(tmpworkdir):
    mktree(tmpworkdir, {
        'makefile.yml': 'foo:\n- "echo foovalue > foo.txt"\n',
    })
    execute('foo')
    assert tmpworkdir.join('foo.txt').read_text('utf8') == 'foovalue\n'


async def test_script_mode(tmpworkdir):
    mktree(tmpworkdir, {
        'makefile.yml': """\
foo:
  script: true
  run:
  - VALUE="hello world"
  - echo $VALUE > foo.txt"""
    })
    execute('foo')
    assert tmpworkdir.join('foo.txt').read_text('utf8') == 'hello world\n'


async def test_arguments(tmpworkdir, caplog):
    mktree(tmpworkdir, {
        'makefile.yml': """\
foo:
- echo"""
    })
    execute('foo', args='hello world')
    assert caplog.normalised_log == """\
donkey.main: Running "foo"...
donkey.command: hello world
donkey.main: "foo" finished in 0.0Xs, return code: 0\n"""


async def test_argument_in_script_mode(tmpworkdir):
    mktree(tmpworkdir, {
        'makefile.yml': """\
foo:
  script: true
  run:
  - echo $VALUE > foo.txt
  """
    })
    with pytest.raises(DonkeyError):
        execute('foo', args='x')
    assert not tmpworkdir.join('foo.txt').exists()


async def test_default_command(tmpworkdir):
    mktree(tmpworkdir, {
        'makefile.yml': """
foo:
- "echo foovalue > foo.txt"
.default: foo
    """,
    })
    execute()
    assert tmpworkdir.join('foo.txt').read_text('utf8') == 'foovalue\n'


async def test_no_default_command(tmpworkdir):
    mktree(tmpworkdir, {
        'makefile.yml': """
foo:
- "echo foovalue > foo.txt"
    """,
    })
    with pytest.raises(DonkeyError):
        execute()


async def test_invalid_command(tmpworkdir):
    mktree(tmpworkdir, {
        'makefile.yml': """
foo:
- "echo foovalue > foo.txt"
    """,
    })
    with pytest.raises(DonkeyError):
        execute('missing')


async def test_invalid_option(tmpworkdir):
    mktree(tmpworkdir, {
        'makefile.yml': """
foo:
  bar: bad
  run:
  - echo foobar
    """,
    })
    with pytest.raises(DonkeyError):
        execute('missing')


async def test_custom_file_name(tmpworkdir):
    mktree(tmpworkdir, {
        'different.yml': 'foo:\n- "echo foovalue > foo.txt"\n',
    })
    execute('foo', definition_file='different.yml')
    assert tmpworkdir.join('foo.txt').read_text('utf8') == 'foovalue\n'
