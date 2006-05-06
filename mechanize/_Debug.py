import sys

def warn(text):
    warnings.warn(text, stacklevel=2)

import logging
from logging import getLogger, StreamHandler, INFO, DEBUG, NOTSET
