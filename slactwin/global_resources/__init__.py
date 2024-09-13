"""Common functionality between simulation types that support global resources.

Global resources come in two types:
1) Resources outside of the application that must be shared between
pieces of the application. For example, job_cmds may need to get a
port to run a web server. This port must exist on the machine the
job_cmd is running on and not conflict with ports used by other
job_cmds.
2) Configuration. For example, an authentication key used by job_cmds
to communicate with another service.

Resources are unique to simulation types and possibly simulation ids.

SECURITY: One must take care not to leak sensitive information out to
the user. For example, authentication keys used by job_cmds should not
be sent to the GUI where the user can read them.


:copyright: Copyright (c) 2024 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://github.com/slaclab/slactwin/LICENSE
"""
