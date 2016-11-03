import logging
import logging.config
import re

import click

MAIN_LOG_FORMAT = {
    logging.DEBUG: {'fg': 'white', 'dim': True},
    logging.INFO: {'fg': 'white', 'dim': True},
    logging.WARN: {'fg': 'yellow', 'dim': True},
}


class MainHandler(logging.Handler):
    def emit(self, record):
        log_entry = self.format(record)
        if hasattr(record, 'symbol'):
            symbol = click.style(record.symbol, fg=record.colour)
            log_entry = '%s %s' % (log_entry, symbol)
        click.secho(log_entry, **MAIN_LOG_FORMAT.get(record.levelno, {'fg': 'red'}))


class CommandLogHandler(logging.Handler):
    def emit(self, record):
        log_entry = self.format(record)
        m = re.match('^\d\d:\d\d:\d\d ', log_entry)
        msg = click.style('%s %s' % (record.symbol, log_entry[m.end():]), fg=record.colour)
        prefix = click.style(m.group(), fg='magenta')
        click.echo(prefix + msg)

SYMBOLS = ['●', '◆', '▼', '◼', '◖', '◗', '◯', '◇', '▽', '□']
COLOURS = ['green', 'yellow', 'blue', 'magenta', 'cyan']
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
    return FORMATS[format_index % len(FORMATS)]


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
                'format': '%(asctime)s (%(fd)d) %(message)s',
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
