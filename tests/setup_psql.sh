#!/usr/bin/env bash

# Shell script to set up PostgreSQL roles and privileges for testing.

# It creates three roles (users) and grants them privileges on a set of
# PostgreSQL databases (one schema: public). The roles are:

# 1. Role: weewx   (password: weewx)
# 2. Role: weewx_tester  (password: weewx_tester)
# 3. Role: weewx_tester2  (password: weewx_tester2)

# NB: role weewx_tester2 is more restrictive than weewx_tester

# Connection:
# - Uses standard libpq environment variables: PGHOST, PGPORT, PGUSER, PGPASSWORD
#   (PGUSER should typically be a superuser, e.g., postgres). You can also set
#   PGDATABASE to an admin DB (default is often 'postgres').
# - Non-interactive by default; to prompt, simply rely on psql's normal behavior
#   (e.g., omit PGPASSWORD and ensure a password prompt is allowed).
#
# Putting this together, a typical invocation looks like:
#    PGHOST=192.168.1.13 PGUSER=admin PGDATABASE=postgres ./setup_psql.sh


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
DROP DATABASE weewx_test WITH (FORCE);

-- Drop users if they exist
DROP USER IF EXISTS weewx;
DROP USER IF EXISTS weewx_tester;
DROP USER IF EXISTS weewx_tester2;

-- Create users with passwords
CREATE USER weewx WITH PASSWORD 'weewx';
CREATE USER weewx_tester WITH PASSWORD 'weewx_tester';
CREATE USER weewx_tester2 WITH PASSWORD 'weewx_tester2';

-- Give permissions to create a database
ALTER USER weewx CREATEDB;
ALTER USER weewx_tester CREATEDB;
SQL

echo "Finished setting up PostgreSQL roles and privileges."
