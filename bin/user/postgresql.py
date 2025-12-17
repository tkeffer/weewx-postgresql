#
#    Copyright (c) 2009-2025 Tom Keffer <tkeffer@gmail.com>
#
#    See the file LICENSE.txt for your full rights.
#
"""weedb driver for the PostgreSQL database"""

# Require psycopg (v3)
import psycopg
from psycopg import DatabaseError as PGDatabaseError
from psycopg import InterfaceError as PGInterfaceError

import weedb
from weeutil.weeutil import to_bool


# Map SQLSTATE error codes to weedb exceptions
_exception_map = {
    '42P04': weedb.DatabaseExistsError,   # duplicate_database
    '3D000': weedb.NoDatabaseError,       # invalid_catalog_name
    '42501': weedb.PermissionError,       # insufficient_privilege
    '28P01': weedb.BadPasswordError,      # invalid_password
    '42P01': weedb.NoTableError,          # undefined_table
    '42703': weedb.NoColumnError,         # undefined_column
    '23505': weedb.IntegrityError,        # unique_violation
    '08001': weedb.CannotConnectError,    # sqlclient_unable_to_establish_sqlconnection
    '08006': weedb.DisconnectError,       # connection_failure
    '08003': weedb.DisconnectError,       # connection_does_not_exist
    None: weedb.DatabaseError,
}


def _pg_guard(fn):
    """Decorator converting psycopg exceptions into weedb exceptions."""

    def guarded_fn(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except PGDatabaseError as e:  # type: ignore
            # Extract SQLSTATE code if available
            sqlstate = getattr(e, 'sqlstate', None)
            if not sqlstate:
                sqlstate = getattr(e, 'pgcode', None)
            klass = _exception_map.get(sqlstate, weedb.DatabaseError)
            raise klass(e)
        except PGInterfaceError as e:  # type: ignore
            raise weedb.DisconnectError(e)

    return guarded_fn


@_pg_guard
def connect(host='localhost', user='', password='', database_name='',
            driver='', port=5432, autocommit=True, **kwargs):
    """Connect to the specified PostgreSQL database."""
    conn = psycopg.connect(
        host=host or None,
        user=user or None,
        password=password or None,
        dbname=database_name or None,
        port=int(port) if port else None,
    )
    try:
        conn.autocommit = to_bool(autocommit)
    except Exception:
        pass

    return Connection(connection=conn, database_name=database_name)


@_pg_guard
def create(host='localhost', user='', password='', database_name='',
           driver='', port=5432, autocommit=True, **kwargs):
    """Create the specified database. If it already exists, raise DatabaseExistsError."""
    # Connect to the maintenance DB (postgres) to run CREATE DATABASE
    maint_db = kwargs.get('maintenance_db', 'postgres')
    conn = psycopg.connect(host=host or None, user=user or None, password=password or None,
                           dbname=maint_db, port=int(port) if port else None)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute("CREATE DATABASE %s" % database_name)
    finally:
        conn.close()


@_pg_guard
def drop(host='localhost', user='', password='', database_name='',
         driver='', port=5432, autocommit=True, **kwargs):
    """Drop (delete) the specified database."""
    maint_db = kwargs.get('maintenance_db', 'postgres')
    conn = psycopg.connect(host=host or None, user=user or None, password=password or None,
                           dbname=maint_db, port=int(port) if port else None)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute("DROP DATABASE %s" % database_name)
    finally:
        conn.close()


class Connection(weedb.Connection):
    """A wrapper around a psycopg connection object."""

    @_pg_guard
    def __init__(self, connection, database_name=''):
        self.connection = connection
        weedb.Connection.__init__(self, connection, database_name, 'postgresql')

    def cursor(self):
        """Return a cursor object."""
        return Cursor(self)

    @_pg_guard
    def tables(self):
        """Returns a list of tables in the database (public and user schemas)."""
        table_list = []
        with self.connection.cursor() as cur:
            cur.execute(
                """
                SELECT tablename
                FROM pg_catalog.pg_tables
                WHERE schemaname NOT IN ('pg_catalog','information_schema');
                """
            )
            while True:
                row = cur.fetchone()
                if row is None:
                    break
                table_list.append(str(row[0]))
        return table_list

    @_pg_guard
    def genSchemaOf(self, table):
        """Yield schema tuples for the given table.

        Returns (i, column_name, column_type, can_be_null, default_value, is_primary)
        """
        # Build a set of primary key columns
        pk_cols = set()
        with self.connection.cursor() as cur:
            cur.execute(
                """
                SELECT a.attname
                FROM pg_index i
                JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                JOIN pg_class c ON c.oid = i.indrelid
                WHERE i.indisprimary = TRUE AND c.relname = %s;
                """,
                (table,)
            )
            for r in cur:
                pk_cols.add(str(r[0]))

        with self.connection.cursor() as cur:
            cur.execute(
                """
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position;
                """,
                (table,)
            )
            i = 0
            while True:
                row = cur.fetchone()
                if row is None:
                    break
                colname = str(row[0])
                dtype = str(row[1]).upper()
                if dtype in ('DOUBLE PRECISION', 'REAL', 'NUMERIC', 'DECIMAL'):
                    coltype = 'REAL'
                elif 'INT' in dtype:
                    coltype = 'INTEGER'
                elif 'CHAR' in dtype or dtype == 'TEXT' or 'CHARACTER' in dtype:
                    coltype = 'STR'
                else:
                    coltype = dtype
                can_be_null = True if (str(row[2]).upper() == 'YES') else False
                default_val = row[3]
                is_primary = colname in pk_cols
                yield (i, colname, coltype, can_be_null, default_val, is_primary)
                i += 1

    @_pg_guard
    def columnsOf(self, table):
        column_list = [row[1] for row in self.genSchemaOf(table)]
        if not column_list:
            # Mirror sqlite behavior
            raise weedb.ProgrammingError("No such table %s" % table)
        return column_list

    @_pg_guard
    def get_variable(self, var_name):
        # PostgreSQL has SHOW for some variables
        with self.connection.cursor() as cur:
            try:
                cur.execute("SHOW %s;" % var_name)
            except PGDatabaseError:
                return None
            row = cur.fetchone()
            return None if row is None else (var_name, row[0])

    @_pg_guard
    def begin(self):
        try:
            self.connection.autocommit = False
        except Exception:
            pass
        with self.connection.cursor() as cur:
            cur.execute("BEGIN")

    @_pg_guard
    def commit(self):
        self.connection.commit()

    @_pg_guard
    def rollback(self):
        self.connection.rollback()

    @property
    def has_math(self):
        # PostgreSQL supports math functions
        return True


class Cursor(weedb.Cursor):
    """A simple wrapper around the psycopg cursor object."""

    @_pg_guard
    def __init__(self, connection):
        self._conn = connection
        self._cursor = connection.connection.cursor()

    @_pg_guard
    def execute(self, sql_string, sql_tuple=()):
        # PostgreSQL uses %s placeholders; replace '?' with '%s'
        pg_string = sql_string.replace('?', '%s')
        self._cursor.execute(pg_string, tuple(sql_tuple))
        return self

    @property
    def rowcount(self):
        return getattr(self._cursor, 'rowcount', -1)

    def fetchone(self):
        return self._cursor.fetchone()

    def drop_columns(self, table, column_names):
        for column_name in column_names:
            self.execute("ALTER TABLE %s DROP COLUMN IF EXISTS %s;" % (table, column_name))

    def close(self):
        try:
            self._cursor.close()
            del self._cursor
        except AttributeError:
            pass

    def __iter__(self):
        return self

    def __next__(self):
        result = self.fetchone()
        if result is None:
            raise StopIteration
        return result

    def __enter__(self):
        return self

    def __exit__(self, etyp, einst, etb):
        self.close()
