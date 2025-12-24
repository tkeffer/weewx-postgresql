Adds PostgreSQL support via new driver `user.postgresql`. It follows the same
weedb interface used by SQLite and MySQL, including transaction and schema
helpers.

## Requirements
- Python 3.7 or later.
- WeeWX 5.3 or later.
- PostgreSQL to which you have admin privileges. Tested on PostgreSQL v16.
- `psycopg` v3. This is the client library for PostgreSQL.

## Installation

### Set up the PostgreSQL database

Using `psql`, create a user for WeeWX. The username and
password can be whatever you like. Here, we'll use `weewx` for both.

You will also need to create a database for WeeWX to use. Here we name it
`weewx_data`. Its owner should be the user you created. Here's how you
would do it with `psql`:

```shell
psql -h localhost - U postgres -d postgres
CREATE USER weewx WITH PASSWORD 'weewx';
CREATE DATABASE weewx_data OWNER weewx;
```

### Prerequisites

Activate your WeeWX virtual environment, then install 
the [`psycopg`](https://pypi.org/project/psycopg/) (v3) package.

```aiignore
source ~/weewx-venv/bin/activate
pip install psycopg
```

### Install the extension

Now install the extension itself:

```shell
weectl extension install weewx-postgresql.zip
```

### Tell WeeWX to use PostgreSQL

The previous step added the capability to use the PostgreSQL driver.
Now you must tell WeeWX to actually use it. Look inside your `weewx.conf` for
the `[DataBindings]` section, then the `[[wx_binding]]` subsection. Edit the 
`database` option to `archive_postgresql`. When you're done, the section should
look something like this:

```text
[DataBindings]

    ...
    
    [[wx_binding]]
        # The database must match one of the sections in [Databases].
        # This is likely to be the only option you would want to change.
        database = archive_postgresql
        ...
```

