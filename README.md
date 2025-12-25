Adds PostgreSQL support via new driver `user.postgresql`. It follows the same
weedb interface used by SQLite and MySQL, including transaction and schema
helpers.

## Requirements
- Python 3.7 or later.
- WeeWX 5.3 or later. Note that as of 12/24/2025, this version has not been
  released yet, so you will have to run out of the branch `development` in the
  WeeWX repository. See the WeeWX documentation on
  [running from a git repository](https://www.weewx.com/docs/5.2/quickstarts/git/#install-pre-requisites)
  for more information.
- PostgreSQL to which you have admin privileges. Tested on PostgreSQL v16.
- `psycopg` v3. This is the client library for PostgreSQL.

## Installation

### Set up the PostgreSQL database

Using `psql`, create a user for WeeWX. The username and password can be whatever
you like. You will also need to give permission for the user to create
databases. 

In this example, we login using the client tool `psql`, then create a user named
`weewx` with the password `weewx`. We then allow the user to create databases.


```shell
# This is how you typically log in as the superuser postgres. Details may differ
# on your system.
sudo -u postgres psql
CREATE USER weewx WITH PASSWORD 'weewx';
ALTER USER weewx CREATEDB;
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
weectl extension install https://github.com/tkeffer/weewx-postgresql/archive/refs/heads/master.zip
```

### Check settings in weewx.conf

Take a look at your `weewx.conf` file. In particular, sections `[Databases]` and
`[DataTypes]`. Make sure they reflect the choices you made above.

### Tell WeeWX to use PostgreSQL

The previous steps added the capability to use the PostgreSQL driver.
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
