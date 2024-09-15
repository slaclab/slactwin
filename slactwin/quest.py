"""Context for a web or command line operation (think: request object)

A quest is an instance of `API` and contains several attributes (`Attr`):

db
    an instance of `slactwin.db` providing calls to the database

:copyright: Copyright (c) 2024 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp, pkdexc
import contextlib
import pykern.quest

_attr_classes = []


def attr_classes():
    """Classes instantiated automatically on every `start`

    Returns:
        tuple: class objects
    """
    return tuple(_attr_classes)


def register_attr(attr_class):
    """Called by modules to add their classes to `attr_classes`

    Args:
        attr_class (class): implements `pykern.quets.Attr`
    """
    if attr_class in _attr_classes:
        raise AssertionError(f"duplicate class={attr_class}")
    _attr_classes.append(attr_class)


def import_and_start():
    """Import `slactwin.modules`, initialize them, and call `start`

    Returns:
        asyncio.task: instantiated coroutine
    """
    from slactwin import modules

    modules.import_and_init()
    return start()


def start():
    """Calls `pykern.quest.start` with `attr_classes`

    Returns:
        asyncio.task: instantiated coroutine
    """
    from slactwin import quest

    return pykern.quest.start(API, _attr_classes)


class API(pykern.quest.API):
    """Superclass of quest entry points"""

    pass


class Attr(pykern.quest.Attr):
    """Superclass of quest context objects"""

    pass
