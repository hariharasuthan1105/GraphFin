"""Candidate-only logging projection: never format message/arguments/tracebacks.

Operational detail is intentionally limited. Request/exception details require a
separate access-controlled logging design; do not turn on raw access/debug logs.
"""
import logging
import re


class MetadataOnlyFormatter(logging.Formatter):
    def format(self, record):
        name = record.name if re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', record.name) else 'unknown'
        level = logging.getLevelName(record.levelno)
        if not isinstance(level, str) or not re.fullmatch(r'[A-Z]{1,20}', level):
            level = 'UNKNOWN'
        return f'{level} {name} event'
