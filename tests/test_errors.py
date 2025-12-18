#
#    Copyright (c) 2009-2025 Tom Keffer <tkeffer@gmail.com>
#
#    See the file LICENSE.txt for your full rights.
#
"""Test the weedb exception hierarchy for PostgreSQL.

Users weewx1 and weewx2 should be created in the PostgreSQL database with passwords
"weewx1" and "weewx2", respectively. The script "setup_psql.sh" will set them up
with the necessary permissions.

If the PostgreSQL server is on a remote host, the environmental variable PGHOST
should be set to the host name. Otherwise, the host name is assumed to be "localhost".
"""
import unittest
import weedb

psql1_dict = {'host': None, 'database_name': 'test_weewx1', 'user': 'weewx1', 'password': 'weewx1', 'driver': 'user.postgresql'}
psql2_dict = {'host': None, 'database_name': 'test_weewx1', 'user': 'weewx2', 'password': 'weewx2', 'driver': 'user.postgresql'}

class Tester(unittest.TestCase):

    def setUp(self):
        """Drop the old databases, in preparation for running a test."""
        try:
            weedb.drop(psql1_dict)
        except weedb.NoDatabase:
            pass

    def test_bad_host(self):
        psql_dict = dict(psql1_dict)
        psql_dict['host'] = 'foohost'
        with self.assertRaises(weedb.CannotConnectError):
            weedb.connect(psql_dict)

    def test_bad_password(self):
        psql_dict = dict(psql1_dict)
        psql_dict['password'] = 'badpw'
        with self.assertRaises(weedb.BadPasswordError):
            weedb.connect(psql_dict)

    def test_drop_nonexistent_database(self):
        with self.assertRaises(weedb.NoDatabase):
            weedb.drop(psql1_dict)

    def test_drop_nopermission(self):
        weedb.create(psql1_dict)
        with self.assertRaises(weedb.PermissionError):
            weedb.drop(psql2_dict)

    def test_create_nopermission(self):
        with self.assertRaises(weedb.PermissionError):
            weedb.create(psql2_dict)

    def test_double_db_create(self):
        weedb.create(psql1_dict)
        with self.assertRaises(weedb.DatabaseExists):
            weedb.create(psql1_dict)

    def test_open_nonexistent_database(self):
        with self.assertRaises(weedb.NoDatabaseError):
            connect = weedb.connect(psql1_dict)


    def test_select_nonexistent_table(self):
        def test(db_dict):
            weedb.create(db_dict)
            connect = weedb.connect(db_dict)
            cursor = connect.cursor()
            cursor.execute("CREATE TABLE bar (col1 int, col2 int)")
            with self.assertRaises(weedb.NoTableError) as e:
                cursor.execute("SELECT foo from fubar")
            cursor.close()
            connect.close()

        test(psql1_dict)

    def test_double_table_create(self):
        def test(db_dict):
            weedb.create(db_dict)
            connect = weedb.connect(db_dict)
            cursor = connect.cursor()
            cursor.execute("CREATE TABLE bar (col1 int, col2 int)")
            with self.assertRaises(weedb.TableExistsError) as e:
                cursor.execute("CREATE TABLE bar (col1 int, col2 int)")
            cursor.close()
            connect.close()

        test(psql1_dict)

    def test_select_nonexistent_column(self):
        def test(db_dict):
            weedb.create(db_dict)
            connect = weedb.connect(db_dict)
            cursor = connect.cursor()
            cursor.execute("CREATE TABLE bar (col1 int, col2 int)")
            with self.assertRaises(weedb.NoColumnError) as e:
                cursor.execute("SELECT foo from bar")
            cursor.close()
            connect.close()

        test(psql1_dict)

    def test_duplicate_key(self):
        def test(db_dict):
            weedb.create(db_dict)
            connect = weedb.connect(db_dict)
            cursor = connect.cursor()
            cursor.execute("CREATE TABLE test1 ( dateTime INTEGER NOT NULL PRIMARY KEY, col1 int, col2 int)")
            cursor.execute("INSERT INTO test1 (dateTime, col1, col2) VALUES (1, 10, 20)")
            with self.assertRaises(weedb.IntegrityError) as e:
                cursor.execute("INSERT INTO test1 (dateTime, col1, col2) VALUES (1, 30, 40)")
            cursor.close()
            connect.close()

        test(psql1_dict)


if __name__ == '__main__':
    unittest.main()
