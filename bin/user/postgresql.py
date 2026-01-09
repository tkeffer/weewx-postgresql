#
#    Copyright (c) 2009-2026 Tom Keffer <tkeffer@gmail.com>
#
#    See the file LICENSE.txt for your full rights.
#
"""weedb driver for the PostgreSQL database

Variables:
  host: the host name of the PostgreSQL server. Default is 'localhost'.
  user: the user name to connect as. Default is empty string, which will cause PostgreSQL to
    use the PGUSER environment variable.
  password: the password to use when connecting. Default is empty string, which will cause
    PostgreSQL to use the PGPASSWORD environment variable.
  database_name: the name of the database to connect to. Default is empty string, which will
    cause PostgreSQL to use the PGDATABASE environment variable.
  port: the port number to connect to (default 5432)
  autocommit: whether to automatically commit transactions (default True)
  real_as_double: whether to convert REAL columns to DOUBLE PRECISION (default True)
  maintenance_db: the name of the database to use for maintenance operations (default 'postgres')
"""

import re

# Require psycopg (v3)
import psycopg
from psycopg import DatabaseError as PGDatabaseError
from psycopg import InterfaceError as PGInterfaceError
from psycopg.types.numeric import FloatLoader

import weedb
from weeutil.weeutil import to_bool

# This tells psycopg3 to return float instead of decimal.Decimal.
# OID 1700 is the standard internal ID for NUMERIC in PostgreSQL
psycopg.adapters.register_loader(1700, FloatLoader)

# Map SQLSTATE error codes to weedb exceptions
_exception_map = {
    '42P04': weedb.DatabaseExistsError,   # duplicate_database
    '3D000': weedb.NoDatabaseError,       # invalid_catalog_name
    '42501': weedb.PermissionError,       # insufficient_privilege
    '28P01': weedb.BadPasswordError,      # invalid_password
    '42P01': weedb.NoTableError,          # undefined_table
    '42P07': weedb.TableExistsError,      # table already exists
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
        except PGDatabaseError as e:
            # Look for a specific SQLSTATE code. If not found, then try to
            # decipher from the error message
            sqlstate = getattr(e, 'sqlstate', None)
            if sqlstate:
                klass = _exception_map.get(sqlstate, weedb.DatabaseError)
            elif "failed to resolve host" in str(e):
                klass = weedb.CannotConnectError
            elif "password authentication failed" in str(e):
                klass = weedb.BadPasswordError
            # Pattern for a non-existent database
            elif re.search(r'database "[^"]*" does not exist', str(e)):
                klass = weedb.NoDatabaseError
            else:
                # Default to DatabaseError
                klass = weedb.DatabaseError
            raise klass(e)
        except PGInterfaceError as e:
            raise weedb.DisconnectError(e)

    return guarded_fn


@_pg_guard
def connect(host='localhost', user='', password='', database_name='',
            driver='', port=5432, autocommit=True, real_as_double=True, **kwargs):
    """Connect to the specified PostgreSQL database."""
    conn = psycopg.connect(
        host=host or None,
        user=user or None,
        password=password or None,
        dbname=database_name or None,
        port=int(port) if port else None,
        **kwargs
    )
    try:
        conn.autocommit = to_bool(autocommit)
    except Exception:
        pass

    return Connection(connection=conn, database_name=database_name, real_as_double=real_as_double)


@_pg_guard
def create(host='localhost', user='', password='', database_name='',
           driver='', port=5432, **kwargs):
    """Create the specified database. If it already exists, raise DatabaseExistsError."""

    # Open up a connection to the "maintenance" database (usually 'postgres'), then create the
    # new database:
    maint_db = kwargs.get('maintenance_db', 'postgres')
    with psycopg.connect(host=host or None, user=user or None, password=password or None,
                         dbname=maint_db or None, port=int(port) if port else None) as conn:
        conn.autocommit = True
        conn.execute(f"CREATE DATABASE {database_name};")
    # Now connect to the new database and create the metadata table:
    with psycopg.connect(host=host or None, user=user or None, password=password or None,
                         dbname=database_name) as conn:
        conn.execute("CREATE TABLE weewx_db__metadata (table_name TEXT, column_name TEXT);")


@_pg_guard
def drop(host='localhost', user='', password='', database_name='',
         driver='', port=5432, **kwargs):
    """Drop (delete) the specified database."""
    maint_db = kwargs.get('maintenance_db', 'postgres')
    with psycopg.connect(host=host or None, user=user or None, password=password or None,
                         dbname=maint_db, port=int(port) if port else None) as conn:
        conn.autocommit = True
        conn.execute(f"DROP DATABASE {database_name}")


class Connection(weedb.Connection):
    """A wrapper around a psycopg connection object."""

    @_pg_guard
    def __init__(self, connection, database_name='', real_as_double=True):
        super().__init__(connection, database_name, 'postgresql')
        self.real_as_double = to_bool(real_as_double)

    def cursor(self):
        """Return a cursor object."""
        return Cursor(self)

    @_pg_guard
    def tables(self):
        """Returns a list of tables in the database. This version uses metadata for table names"""
        with self.connection.cursor() as cur:
            results = cur.execute("SELECT DISTINCT table_name FROM weewx_db__metadata").fetchall()
        return [row[0] for row in results]

    def list_tables(self):
        """This returns a list of the actual tables in the database. It does not use
        metadata. This is an extension to the regular weedb API that could
        potentially be useful."""
        table_list = []
        with self.connection.cursor() as cur:
            cur.execute(
                """
                SELECT tablename
                FROM pg_catalog.pg_tables
                WHERE schemaname NOT IN ('pg_catalog', 'information_schema');
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
                         JOIN pg_attribute a
                              ON a.attrelid = i.indrelid AND a.attnum = ANY (i.indkey)
                         JOIN pg_class c ON c.oid = i.indrelid
                WHERE i.indisprimary = TRUE
                  AND c.relname = %s;
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
        """Return a list of column names for the given table. We actually retrive the list
        from a separate metadata table. This insures that the column names reflect the original
        mixed-case names."""
        column_list = []
        with self.connection.cursor() as cur:
            for column_name in cur.execute("SELECT column_name "
                                           "FROM weewx_db__metadata "
                                           "WHERE table_name = %s;", (table,)):
                column_list.append(column_name[0])
        # If the list is empty, that means the table doesn't exist. Raise an exception.
        if not column_list:
            raise weedb.NoTableError(f'Table {table} does not exist.')

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

    group_defs = {
        #        'day': "GROUP BY date_trunc('day', to_timestamp(dateTime)) ",
        'day': "GROUP BY FLOOR((EXTRACT(EPOCH FROM date_trunc('day', to_timestamp(dateTime))) "
               "- EXTRACT(EPOCH FROM date_trunc('day', to_timestamp(%(sod)s)))) "
               "/ (%(agg_days)s * 86400)) ",
        'month': "GROUP BY to_char(to_timestamp(dateTime), 'YYYY-MM') ",
        'year': "GROUP BY to_char(to_timestamp(dateTime), 'YYYY') ",
    }

    @staticmethod
    def get_group_by(group_name):
        """Return a GROUP BY clause suitable for PostgreSQL."""
        # Fail hard if we're given a bad group name:
        return Connection.group_defs[group_name]

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
        self._cursor = connection.connection.cursor()
        self.real_as_double = connection.real_as_double

    @_pg_guard
    def execute(self, sql_string, sql_tuple=()):
        # pyscopg uses %s placeholders: replace '?' with '%s'.
        pg_string = sql_string.replace('?', '%s')
        self._cursor.execute(pg_string, tuple(sql_tuple))
        return self

    @property
    def rowcount(self):
        return getattr(self._cursor, 'rowcount', -1)

    def fetchone(self):
        return self._cursor.fetchone()

    def create_table(self, table_name, schema):
        """Create a new table with the specified schema.

        This version explicitly stores the original column names in a separate metadata table.

        table_name: The name of the table to be created.
        schema: The schema of the table in the form of a list of tuples:
                [(column_name, column_type), ...]
        """
        if self.real_as_double:
            final_schema = [(col_name, col_type.upper().replace('REAL', 'DOUBLE PRECISION')) \
                            for col_name, col_type in schema]
        else:
            final_schema = schema
        # Have my superclass create the table
        super().create_table(table_name, final_schema)

        # Now insert the original mixed-case table and column names into the metadata table
        for column_name, _ in final_schema:
            self.execute("INSERT INTO weewx_db__metadata (table_name, column_name) "
                         "VALUES (%s, %s);",
                         (table_name, column_name))

    def drop_table(self, table_name):
        """Drop an existing table. Specialized to handle metadata cleanup."""
        # Have my superclass drop the table
        super().drop_table(table_name)
        # Then delete the metadata
        self.execute("DELETE FROM weewx_db__metadata WHERE table_name = %s;", (table_name,))

    def add_column(self, table_name, column_name, column_type):
        """Add a single new column to an existing table."""

        # Have my superclass add the column to the table
        super().add_column(table_name, column_name, column_type)
        # Then add it to the metadata table
        self.execute("INSERT INTO weewx_db__metadata (table_name, column_name) "
                     "VALUES (%s, %s);",
                     (table_name, column_name))

    def rename_column(self, table_name, old_column_name, new_column_name):
        """Rename a column in the main archive table."""
        # Have my superclass rename the column in the main table
        super().rename_column(table_name, old_column_name, new_column_name)
        # Then update the metadata table
        self.execute("UPDATE weewx_db__metadata SET column_name = %s "
                     "WHERE table_name = %s AND column_name = %s;",
                     (new_column_name, table_name, old_column_name))

    def drop_columns(self, table, column_names):
        """Drop one or more columns from an existing table.

        PostgreSQL supports dropping multiple columns in one command.
        """
        if not column_names:
            return

        # First drop the columns from the main table
        sql_stmt = f'ALTER TABLE {table} DROP COLUMN ' + ', DROP COLUMN '.join(column_names)
        self.execute(sql_stmt)

        # Now delete the metadata. Create a string like "%s, %s" based on the length of column_names
        placeholders = ', '.join(['%s'] * len(column_names))
        sql_stmt = (f"DELETE FROM weewx_db__metadata "
                    f"WHERE table_name = %s AND column_name IN ({placeholders});")

        # Pass the table name followed by all the column names
        self.execute(sql_stmt, (table, *column_names))

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
