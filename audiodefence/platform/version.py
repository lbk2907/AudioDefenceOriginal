"""PORT ADDITION: what build this is, and which of two builds is newer.

The iOS original has a version - `CFBundleShortVersionString` in `Info.plist` - but it is the phone
game's, not this port's, and the App Store did the updating.  A Windows build has to carry its own.

The number is written in one place, the repository's `VERSION` file.  It holds the release tag exactly as
GitHub has it, so cutting a release is copy-and-paste rather than a conversion.  Run from source, the game
reads that file, and makes it when there is none (see `today`).  A build carries the number inside the executable instead: `compiler.py` writes it into
a small module, `BAKED_MODULE`, which PyInstaller compiles in.  Nothing beside the executable is read, so
a file there cannot be edited to change what the game thinks it is - and the `VERSION` file an older build
left beside the executable is ignored.

The format is `YY.MM.DD-XX`: the last two digits of the year, the month, the day, and the build number
within that day, counting from 1.  `26.09.20-1` is the first release of the 20th of September 2026 and
`26.09.20-2` the second.

Comparison reads the digits and ignores everything between them, so dots and dashes compare alike and a
shorter number is padded with zeroes - `26.09.20` is older than `26.09.20-1`.  A version that holds no
digits at all is unknown, and compares as older than any known one.
"""
from __future__ import annotations

import importlib
import logging
import os
import time

from .. import paths

log = logging.getLogger('platform.version')

FILENAME = 'VERSION'
UNKNOWN = ''
#: the module compiler.py writes into a build, holding the VERSION it was built from as `VERSION`
BAKED_MODULE = '_audiodefence_build'


def today() -> str:
    """The first release of today, '26.09.21-1' on the 21st of September 2026: what a missing VERSION file
    is started at, by a release build in compiler.py and by the game run from source."""
    return time.strftime('%y.%m.%d') + '-1'


def current() -> str:
    """This build's version, or '' when it has none: a build made with no VERSION file in the repository,
    or a checkout with none where one cannot be made."""
    if paths.FROZEN:
        try:
            text = str(getattr(importlib.import_module(BAKED_MODULE), 'VERSION', '') or '').strip()
        except ImportError:
            text = UNKNOWN
        if not text:
            log.info('this build was made without a version, so it never offers an update')
        return text
    path = os.path.join(paths.ROOT, FILENAME)
    try:
        with open(path, encoding='utf-8') as fh:
            text = fh.read().strip()
    except OSError:
        text = ''
    if text:
        return text.splitlines()[0].strip()
    # a checkout without one: start it at today's first release, as a release build would
    started = today()
    try:
        with open(path, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(started + '\n')
    except OSError as exc:
        log.warning('there is no %s file, and one could not be made (%s)', FILENAME, exc)
        return UNKNOWN
    log.info('there was no %s file, so it has been started at %s', FILENAME, started)
    return started


def parse(version: str) -> tuple:
    """'26.09.20-1' and '26-09-20-1' both -> (26, 9, 20, 1); '' -> ()."""
    digits, number, seen = [], 0, False
    for ch in str(version):
        if ch.isdigit():
            number, seen = number * 10 + int(ch), True
        elif seen:
            digits.append(number)
            number, seen = 0, False
    if seen:
        digits.append(number)
    return tuple(digits)


def is_newer(remote: str, local: str) -> bool:
    """Is `remote` a later build than `local`?  Unknown versions compare as not newer."""
    a, b = parse(remote), parse(local)
    if not a or not b:
        return False
    width = max(len(a), len(b))
    return a + (0,) * (width - len(a)) > b + (0,) * (width - len(b))


def text(version: str = None) -> str:
    """What a screen reader should say for a version.

    The number is a date and a build - `26.09.20-1` is the first release of the 20th of September 2026 -
    so it is said as one: "26.09.20, build 1".  Read straight off the tag a synthesiser makes the dash
    into "minus", and spelling every part out as "point" buries the build number among the date.  The
    date keeps its two digits, the way it is written down."""
    version = current() if version is None else version
    parts = parse(version)
    if not parts:
        return 'unknown'
    date = '.'.join('%02d' % p for p in parts[:3])
    build = parts[3] if len(parts) > 3 else None
    return '%s, build %d' % (date, build) if build is not None else date
