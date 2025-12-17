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
DROP DATABASE IF EXISTS test;
DROP DATABASE IF EXISTS test_alt_weewx;
DROP DATABASE IF EXISTS test_scratch;
DROP DATABASE IF EXISTS test_sim;
DROP DATABASE IF EXISTS test_weedb;
DROP DATABASE IF EXISTS test_weewx;
DROP DATABASE IF EXISTS test_weewx1;
DROP DATABASE IF EXISTS test_weewx2;
DROP DATABASE IF EXISTS weewx;

-- Create roles (users)
DROP ROLE IF EXISTS weewx;
DROP ROLE IF EXISTS weewx1;
DROP ROLE IF EXISTS weewx2;
CREATE ROLE weewx  LOGIN PASSWORD 'weewx';
CREATE ROLE weewx1 LOGIN PASSWORD 'weewx1';
CREATE ROLE weewx2 LOGIN PASSWORD 'weewx2';

-- Create new databases with specific ownerships
CREATE DATABASE test;
CREATE DATABASE test_alt_weewx;
CREATE DATABASE test_scratch;
CREATE DATABASE test_sim;
CREATE DATABASE test_weedb;
CREATE DATABASE test_weewx;
CREATE DATABASE test_weewx1 OWNER weewx1;
CREATE DATABASE test_weewx2;
CREATE DATABASE weewx;

-- Apply database-level CONNECT grants mirroring the MySQL grants
-- weewx: broad access
GRANT CONNECT ON DATABASE test           TO weewx;
GRANT CONNECT ON DATABASE test_alt_weewx TO weewx;
GRANT CONNECT ON DATABASE test_scratch   TO weewx;
GRANT CONNECT ON DATABASE test_sim       TO weewx;
GRANT CONNECT ON DATABASE test_weedb     TO weewx;
GRANT CONNECT ON DATABASE test_weewx     TO weewx;
GRANT CONNECT ON DATABASE test_weewx1    TO weewx;
GRANT CONNECT ON DATABASE test_weewx2    TO weewx;
GRANT CONNECT ON DATABASE weewx          TO weewx;

-- weewx1: subset
GRANT CONNECT ON DATABASE test_alt_weewx TO weewx1;
GRANT CONNECT ON DATABASE test_sim       TO weewx1;
GRANT CONNECT ON DATABASE test_weedb     TO weewx1;
GRANT CONNECT ON DATABASE test_weewx     TO weewx1;
GRANT CONNECT ON DATABASE test_weewx1    TO weewx1;
GRANT CONNECT ON DATABASE test_weewx2    TO weewx1;

-- weewx2: only test_weewx2
GRANT CONNECT ON DATABASE test_weewx2    TO weewx2;

\echo Applying schema/table grants per database...

-- For each database, connect and apply per-schema grants for applicable roles
\connect test
GRANT USAGE, CREATE ON SCHEMA public TO weewx;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO weewx;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO weewx;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO weewx;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO weewx;

\connect test_alt_weewx
GRANT USAGE, CREATE ON SCHEMA public TO weewx;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO weewx;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO weewx;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO weewx;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO weewx;
GRANT USAGE, CREATE ON SCHEMA public TO weewx1;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO weewx1;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO weewx1;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO weewx1;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO weewx1;

\connect test_scratch
GRANT USAGE, CREATE ON SCHEMA public TO weewx;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO weewx;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO weewx;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO weewx;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO weewx;

\connect test_sim
GRANT USAGE, CREATE ON SCHEMA public TO weewx;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO weewx;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO weewx;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO weewx;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO weewx;
GRANT USAGE, CREATE ON SCHEMA public TO weewx1;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO weewx1;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO weewx1;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO weewx1;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO weewx1;

\connect test_weedb
GRANT USAGE, CREATE ON SCHEMA public TO weewx;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO weewx;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO weewx;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO weewx;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO weewx;
GRANT USAGE, CREATE ON SCHEMA public TO weewx1;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO weewx1;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO weewx1;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO weewx1;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO weewx1;

\connect test_weewx
GRANT USAGE, CREATE ON SCHEMA public TO weewx;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO weewx;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO weewx;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO weewx;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO weewx;
GRANT USAGE, CREATE ON SCHEMA public TO weewx1;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO weewx1;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO weewx1;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO weewx1;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO weewx1;

\connect test_weewx1
GRANT USAGE, CREATE ON SCHEMA public TO weewx;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO weewx;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO weewx;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO weewx;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO weewx;
GRANT USAGE, CREATE ON SCHEMA public TO weewx1;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO weewx1;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO weewx1;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO weewx1;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO weewx1;

\connect test_weewx2
GRANT USAGE, CREATE ON SCHEMA public TO weewx;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO weewx;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO weewx;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO weewx;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO weewx;
GRANT USAGE, CREATE ON SCHEMA public TO weewx1;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO weewx1;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO weewx1;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO weewx1;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO weewx1;
GRANT USAGE, CREATE ON SCHEMA public TO weewx2;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO weewx2;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO weewx2;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO weewx2;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO weewx2;

\connect weewx
GRANT USAGE, CREATE ON SCHEMA public TO weewx;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO weewx;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO weewx;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO weewx;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO weewx;

\echo Done.
SQL

echo "Finished setting up PostgreSQL roles and privileges."
