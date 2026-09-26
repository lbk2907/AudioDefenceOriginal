"""OpenAL Soft configuration and output device for the port.

The game's own HRTF (``assets/hrtf/audiodefence_ircam1050.mhr``, built by tools/build_hrtf.py from the set
embedded in the original binary) is made visible to OpenAL Soft through a private ``alsoft.ini`` named by the
``ALSOFT_CONF`` environment variable, so the user's own OpenAL configuration is never touched.
"""
from __future__ import annotations

import logging
import os

from .. import paths
from . import openal as oal

HRTF_NAME = 'audiodefence_ircam1050'
SAMPLE_RATE = 44100


def write_alsoft_config() -> str:
    path = os.path.join(paths.user_dir(), 'alsoft.ini')
    lines = [
        '# Written by AudioDefenceOriginal at start-up; edits are overwritten.',
        '[general]',
        'stereo-encoding = hrtf',
        'hrtf = true',
        f'hrtf-paths = {paths.HRTF_DIR}',
        f'default-hrtf = {HRTF_NAME}',
        f'frequency = {SAMPLE_RATE}',
        'output-limiter = true',
        '',
    ]
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines))
    return path


class Device:
    """Opens the default playback device with the game's HRTF enabled."""

    def __init__(self):
        os.environ['ALSOFT_CONF'] = write_alsoft_config()
        self.al = oal.AL()
        self.device = self.al.alcOpenDevice(None)
        if not self.device:
            raise oal.OpenALError('could not open the audio output device')
        attrs = {oal.ALC_FREQUENCY: SAMPLE_RATE, oal.ALC_HRTF_SOFT: oal.ALC_TRUE,
                 oal.ALC_MONO_SOURCES: 255, oal.ALC_STEREO_SOURCES: 64}
        self.context = self.al.alcCreateContext(self.device, oal.attr_list(attrs))
        if not self.context:
            raise oal.OpenALError('could not create the audio context')
        self.al.make_current(self.context)
        names = self.al.hrtf_names(self.device)
        self.hrtf_found = HRTF_NAME in names
        if self.hrtf_found:
            flat = []
            for k, v in {**attrs, oal.ALC_HRTF_ID_SOFT: names.index(HRTF_NAME)}.items():
                flat += [k, v]
            self.al.reset_device(self.device, flat)
        self.hrtf_status = self.al.get_int(self.device, oal.ALC_HRTF_STATUS_SOFT)
        if not self.hrtf_found or self.hrtf_status != 1:              # ALC_HRTF_ENABLED_SOFT
            # the built-in HRTF (or none) would sound plausible but not like the original
            logging.getLogger('s3d').error('game HRTF %s not in use (found=%s, status=%s, offered=%s)',
                                           HRTF_NAME, self.hrtf_found, self.hrtf_status, names)

    def close(self) -> None:
        self.al.make_current(None)
        if self.context:
            self.al.alcDestroyContext(self.context)
        if self.device:
            self.al.alcCloseDevice(self.device)
        self.context = self.device = None
