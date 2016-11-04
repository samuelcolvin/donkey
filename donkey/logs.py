import logging
import logging.config
import re

import click

MAIN_LOG_FORMAT = {
    logging.DEBUG: {'fg': 'white', 'dim': True},
    logging.INFO: {'fg': 'white', 'dim': True},
    logging.WARN: {'fg': 'yellow'},
}


class MainHandler(logging.Handler):
    def emit(self, record):
        log_entry = self.format(record)
        symbol = getattr(record, 'symbol', '')
        if symbol:
            symbol = ' ' + click.style(symbol, fg=record.colour)
        msg = click.style(log_entry, **MAIN_LOG_FORMAT.get(record.levelno, {'fg': 'red'}))
        click.secho(msg + symbol)


class CommandLogHandler(logging.Handler):
    def emit(self, record):
        if record.getMessage() == '<nl>':
            # '<nl>' is a special value used to print new line after a command with ended without one
            click.echo('')
            return
        if not record.prev_nl:
            # if the previous line ended without a newline we print the raw message with symbol or time etc.
            # eg. for test output "........"
            click.secho(record.getMessage(), fg=record.colour, nl=record.nl)
            return
        log_entry = self.format(record)
        m = re.match('^.*?:\d\d ', log_entry)
        symbol = getattr(record, 'symbol')
        if symbol:
            msg = '%s %s' % (record.symbol, log_entry[m.end():])
        else:
            msg = log_entry[m.end():]
        msg = click.style(msg, fg=record.colour)
        prefix = click.style(m.group(), fg='magenta')
        click.echo(prefix + msg, nl=record.nl)

SYMBOLS = ['●', '◆', '▼', '◼', '◖', '◗', '◯', '◇', '▽', '□']
COLOURS = ['green', 'cyan', 'blue', 'yellow']
FORMATS = []
for symbol in SYMBOLS:
    for colour in COLOURS:
        FORMATS.append({'symbol': symbol, 'colour': colour})

format_index = None


def reset_log_format():
    global format_index
    format_index = -1


def get_log_format():
    global format_index
    format_index += 1
    return dict(FORMATS[format_index % len(FORMATS)])


def setup_logging(verbose):
    """
    Setup main logging
    :param verbose: level: DEBUG if True, INFO if False
    """
    log_level = 'DEBUG' if verbose else 'INFO'
    log_config = {
        'version': 1,
        'disable_existing_loggers': True,
        'formatters': {
            'main': {
                'format': '%(message)s',
            },
            'commands': {
                'format': '%(asctime)s %(fd)d: %(message)s',
                'datefmt': '%H:%M:%S',
            },
        },
        'handlers': {
            'main': {
                'level': log_level,
                'class': 'donkey.logs.MainHandler',
                'formatter': 'main'
            },
            'commands': {
                'level': 'INFO',
                'class': 'donkey.logs.CommandLogHandler',
                'formatter': 'commands'
            },
        },
        'loggers': {
            'donkey.main': {
                'handlers': ['main'],
                'level': log_level,
                'propagate': False,
            },
            'donkey.commands': {
                'handlers': ['commands'],
                'level': 'INFO',
                'propagate': False,
            },
        },
    }
    logging.config.dictConfig(log_config)
