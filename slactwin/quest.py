"""Quest wrapper

:copyright: Copyright (c) 2024 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: See LICENSE file for details.
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp, pkdexc
import contextlib
import pykern.quest

_attr_classes = []


def attr_classes():
    return tuple(_attr_classes)


def register_attr(attr_class):
    if attr_class in _attr_classes:
        raise AssertionError(f"duplicate class={attr_class}")
    _attr_classes.append(attr_class)


def import_and_start():
    from slactwin import modules

    modules.import_and_init()
    return start()


def start():
    from slactwin import quest

    return pykern.quest.start(API, _attr_classes)


class API(pykern.quest.API):
    pass


class Attr(pykern.quest.Attr):
    pass
