#!/usr/bin/env bash

# Shell script to set up PostgreSQL roles and privileges for testing.

# It creates three roles (users) and grants them privileges on a set of
# PostgreSQL databases (one schema: public). The roles are:

# 1. Role: weewx   (password: weewx)
# 2. Role: weewx1  (password: weewx1)
# 3. Role: weewx2  (password: weewx2)

# NB: role weewx2 is more restrictive than weewx1, which, in turn, is more restrictive than weewx.

# Connection:
# - Uses standard libpq environment variables: PGHOST, PGPORT, PGUSER, PGPASSWORD
#   (PGUSER should typically be a superuser, e.g., postgres). You can also set
#   PGDATABASE to an admin DB (default is often 'postgres').
# - Non-interactive by default; to prompt, simply rely on psql's normal behavior
#   (e.g., omit PGPASSWORD and ensure a password prompt is allowed).
#
# Putting this together, a typical invocation looks like:
#    PGHOST=192.168.1.13 PGUSER=admin PGDATABASE=postgres ./setup_psql.sh

# Databases created:
#   test
#   test_alt_weewx
#   test_scratch
#   test_sim
#   test_weedb
#   test_weewx
#   test_weewx1
#   test_weewx2
#   weewx

# Grants mapping (per database):
#   - weewx   : broad access to all listed databases
#   - weewx1  : access to a subset (see below)
#   - weewx2  : access only to test_weewx2

# For each database granted to a role, we apply typical Postgres equivalents of
# MySQL's table-level privileges:
#   - GRANT CONNECT ON DATABASE <db>
#   - In DB (schema public): GRANT USAGE, CREATE ON SCHEMA public
#   - In DB (schema public): GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES
#   - In DB (schema public): GRANT USAGE, SELECT ON ALL SEQUENCES
#   - In DB (schema public): ALTER DEFAULT PRIVILEGES to grant the same on future objects

set -euo pipefail

# Set PSQL_NO_OPTS to allow programmatic invocation.
if [ "${PSQL_NO_OPTS:-0}" = "1" ]; then
  CMD="psql -v ON_ERROR_STOP=1"
else
  echo "If prompted, enter the PostgreSQL superuser password (or set PGPASSWORD)."
  CMD="psql"
fi

# Helper function to run a psql heredoc safely
run_psql() {
  # shellcheck disable=SC2086
  ${CMD} "$@"
}

# Create roles and databases, then apply grants
run_psql <<'SQL'
-- Drop old databases
DROP DATABASE weewx_data WITH (FORCE);
DROP DATABASE test_weewx WITH (FORCE);
DROP DATABASE test_weewx1 WITH (FORCE);

-- Drop users if they exist
DROP USER IF EXISTS weewx;
DROP USER IF EXISTS weewx1;
DROP USER IF EXISTS weewx2;

-- Create users with passwords
CREATE USER weewx WITH PASSWORD 'weewx';
CREATE USER weewx1 WITH PASSWORD 'weewx1';
CREATE USER weewx2 WITH PASSWORD 'weewx2';

-- Give permissions to create a database
ALTER USER weewx CREATEDB;
ALTER USER weewx1 CREATEDB;
SQL

echo "Finished setting up PostgreSQL roles and privileges."
