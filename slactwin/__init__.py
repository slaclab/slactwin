""":mod:`slactwin` package

:copyright: Copyright (c) 2024 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: See LICENSE file for details.
"""

import pkg_resources

try:
    # We only have a version once the package is installed.
    __version__ = pkg_resources.get_distribution("slactwin").version
except pkg_resources.DistributionNotFound:
    pass
