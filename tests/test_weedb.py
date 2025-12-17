#
#    Copyright (c) 2009-2025 Tom Keffer <tkeffer@gmail.com>
#
#    See the file LICENSE.txt for your full rights.
#
"""Test the WeeWX postgresql weedb driver.

For this test to work, PostgreSQL user 'weewx' must have full access to database 'test':
    mysql> grant select, update, create, delete, drop, insert on test.* to weewx@localhost;
"""

import unittest
import weedb

psql_db_dict = {'database_name': 'test_weewx1', 'user': 'weewx1', 'password': 'weewx1',
                 'driver': 'user.postgresql',}

weedb.create(psql_db_dict)
with weedb.connect(psql_db_dict) as _connect:
    pass
