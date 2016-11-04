from datetime import datetime

from donkey.main import execute

from .conftest import mktree

async def test_multiple(tmpworkdir, caplog):
    mktree(tmpworkdir, {
        'makefile.yml': """
foo:
- sleep 0.1
- echo foo
bar:
- sleep 0.1
- echo bar
spam:
- sleep 0.1
- echo spam
    """,
    })
    start = datetime.now()
    execute('foo', 'bar', 'spam', parallel=True)
    diff = (datetime.now() - start).total_seconds()
    assert 0.1 < diff < 0.15
    log = caplog.normalised_log
    print(log)
    assert 'donkey.main: Running "foo: echo foo"...' in log
    assert 'donkey.commands: foo' in log
    assert 'donkey.commands: bar' in log
    assert 'donkey.commands: spam' in log


async def test_single_parallel(tmpworkdir, caplog):
    mktree(tmpworkdir, {
        'makefile.yml': """
foo:
  parallel: true
  run:
  - sleep 0.1
  - sleep 0.1
  - sleep 0.1
  - echo foobar
  - "echo foovalue > foo.txt"
    """})
    caplog.set_loggers('donkey.commands', fmt='%(name)s: %(message)s %(symbol)s')
    start = datetime.now()
    execute('foo', parallel=True)
    diff = (datetime.now() - start).total_seconds()
    assert 0.1 < diff < 0.15
    assert tmpworkdir.join('foo.txt').read_text('utf8') == 'foovalue\n'
    assert 'donkey.commands: foobar ●\n' == caplog.normalised_log
