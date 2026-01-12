"""
Command line interface for stockie. The CLI currently implements two commands
for creating and dropping a stockie database. Over time additional commands
will be added to facilitate the management of stockie installations.

The two commands currently supported are:
1) stockie create database <arguments>
2) stockie drop database <arguments>

where <arguments> are one of the following:
--host <host>                         Database host (default: localhost)
--port <port>                         Database port (default: 5432)
--database <database>                 Database name to create
--admin-user <admin-user>             Database admin user
--admin-password <admin-password>     Database admin password
--user <user>                         Database user to create
--password <password>                 Database password
--data-path <data-path>               Data tablespace file system path
--index-path <index-path>             Index tablespace file system path

NB: 
- data-path and index-path are only needed for database creation and will be ignored for stockie 
  database dropping.
- tablespace hard-coded naming conventions: data ts=<user>_data_ts and index ts=<user>_index_ts
- schema_definitions.py relies on these tablespace naming conventions (a hard dependency)
- before running the create database command the following prerequisites are met: 
  (1) create the admin role in postgres with appropriate permissions:
      create role '<user>_admin' with login '<user>_admin' superuser
  (2) the specified data-path and index-path directories must exist and that PostgreSQL has read/write 
      permissions to them. Use the following commands as a template to create the directories:
      $ sudo -u postgres mkdir -p /mnt/pgdb/<user>/data
      $ sudo -u postgres mkdir -p /mnt/pgdb/<user>/index

  The code will fail if these pre-requisites are not met.

The general command structure is:

stockie <action> <action_object> [<arguments>]

where action := create || drop and action_object:=database. Over time additional actions and action 
objects will be added to the command line interface.
"""

import argparse
import sys
import logging

from stockie.db.database_connection import DatabaseConnection
from stockie.db.creators import CreateDatabase, CreateTablespaces, CreateSchema
from stockie.db.droppers import DropDatabase, DropTablespaces, DropSchema


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments and return a list of processed arguments."""
    parser = argparse.ArgumentParser(description='Stockie command line interface (CLI)')

    # Positional arguments
    parser.add_argument('action', help='Action to perform (create or drop)')
    parser.add_argument('action_object', help='Object to perform action on (database)')

    # Database connection parameters
    parser.add_argument('--host', default='localhost', help='Database host (default: localhost)')
    parser.add_argument('--port', type=int, default=5432, help='Database port (default: 5432)')
    parser.add_argument('--database', required=True, help='Database name to create')
    parser.add_argument('--admin-user', required=True, help='Database admin user')
    parser.add_argument('--admin-password', required=True, help='Database admin password')
    parser.add_argument('--user', required=True, help='Database user to create')
    parser.add_argument('--password', required=True, help='Database password')

    # Tablespace parameters
    parser.add_argument('--data-path', help='Data tablespace file system path')
    parser.add_argument('--index-path', help='Index tablespace file system path')
    
    return parser.parse_args()

def validate_arguments(action: str, action_object: str, args: argparse.Namespace) -> None:
    """Validate command line arguments."""

    if action == 'create' and action_object == 'database':
        if not args.data_path or not args.index_path:
            logging.error("Both data and index paths are required for creating stockie database")
            sys.exit(1)
    

def create_stockie_database(args: argparse.Namespace) -> None:
    """Create a stockie database using the provided CLI arguments."""

    admin_connection = DatabaseConnection(
        host=args.host,
        port=args.port,
        dbname='postgres',
        user=args.admin_user,
        password=args.admin_password
    )

    CreateDatabase(
        database_connection=admin_connection,
        database=args.database,
        user=args.user,
        password=args.password
    )    

    CreateTablespaces(
        database_connection=admin_connection,
        user=args.user,
        data_path=args.data_path,
        index_path=args.index_path
    )

    admin_connection.disconnect()
    user_connection = DatabaseConnection(
        host=args.host,
        port=args.port,
        dbname=args.database,
        user=args.user,
        password=args.password
    )

    CreateSchema(
        database_connection=user_connection,
        owner=args.user
    )
    
    user_connection.disconnect()

def drop_stockie_database(args: argparse.Namespace) -> None:
    """Drop a stockie database using the provided CLI arguments."""

    user_connection = DatabaseConnection(
        host=args.host,
        port=args.port,
        dbname=args.database,
        user=args.user,
        password=args.password
    )

    DropSchema(
        database_connection=user_connection,
    )

    user_connection.disconnect()
    admin_connection = DatabaseConnection(
        host=args.host,
        port=args.port,
        dbname='postgres',
        user=args.admin_user,
        password=args.admin_password
    )

    DropTablespaces(
        database_connection=admin_connection,
        owner=args.user
    )

    DropDatabase(
        database_connection=admin_connection,
        database=args.database,
        user=args.user
    )

    admin_connection.disconnect()

def cli_processor() -> None:
    """Command line interface processor for stockie."""
    args = parse_arguments()
    action = args.action
    action_object = args.action_object
    validate_arguments(action, action_object, args)

    commands = { 
        ('create', 'database'):create_stockie_database, 
        ('drop', 'database'): drop_stockie_database 
    }
    for cmd in commands.keys():
        if action == cmd[0] and action_object == cmd[1]:
            commands[cmd](args)
            return

    print(f"Invalid {action=} or {action_object=}. Supported actions: create database, drop database")
    sys.exit(1)

if __name__ == "__main__":
    """
    To test code use the following commands to add all relevant stockie components to the 
    postgres database. The following command create a database user abc, database abc_db, 2 tablespaces, 
    and a set of stockie tables and indexes (tables go into the data tablespace and the indexes go into the
    index tablespace).

    # create stockie database
    python stockie create database --database abc_db \
        --admin-user abc_admin --admin-password abc_admin \
        --user abc --password abc \
        --data-path /mnt/pgdb/abc/data --index-path /mnt/pgdb/abc/index

    # drop stockie database
    python stockie drop database --database abc_db \
        --admin-user abc_admin --admin-password abc_admin \
        --user abc --password abc
    """
    cli_processor()