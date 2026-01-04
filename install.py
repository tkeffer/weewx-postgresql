#
#    Copyright (c) 2026 Tom Keffer <tkeffer@gmail.com>
#
#    See the file LICENSE.txt for your full rights.
#
"""Installer for the WeeWX PostgreSQL database driver"""

from io import StringIO

import configobj
from weecfg.extension import ExtensionInstaller

CONFIG = """
[Databases]

     # PostgreSQL database
     [[archive_postgresql]]
        database_name = weewx_data
        database_type = PostgreSQL

[DatabaseTypes]
    
    # Defaults for PostgreSQL databases
    [[PostgreSQL]]
        driver = user.postgresql
        # The host where the database is located. Alternatively, delete and use environment
        # variable PGHOST.
        host = localhost
        # The user name for logging in to the host. Alternatively, delete and use environment
        # variable PGUSER.
        user = weewx
        # If necessary, use quotes around the password to guard against parsing errors. Alternatively,
        # delete and use environment variable PGPASSWORD.
        password = weewx
        # The name of the database for WeeWX to use. Alternatively, delete and use environment variable
        # PGDATABASE.
        database_name = weewx_data
        # If True, use DOUBLE PRECISION for REAL columns.
        real_as_double = true
"""

postgresql_dict = configobj.ConfigObj(StringIO(CONFIG))


def loader():
    return PostgreSQLInstaller()


class PostgreSQLInstaller(ExtensionInstaller):
    def __init__(self):
        super(PostgreSQLInstaller, self).__init__(
            version="1.0",
            name='PostgreSQL',
            description='WeeWX driver for the PostgreSQL database',
            author="Thomas Keffer",
            author_email="tkeffer@gmail.com",
            config=postgresql_dict,
            files=[('bin/user', ['bin/user/postgresql.py'])]
            )