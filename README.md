# import_election_csv.py script

This scripts allows to import an election from diferent easily interchangable
formats.

For example, you can use a google forms to get a rough configuration of multiple
elections in CSV, and then just provide this file as an input, and the output
will be a directory where multiple configuration files will be created per
election:

    python3 import_election_csv.py --config config/config_example.json -i config/test.csv -o config/test-dir -f csv-google-forms

# sequent-admin.py script

## Introduction

Script to manage elections using both ballot-box and iam together. It
allows to:
  - create an election with a census
  - start or stop the election in iam
  - send auth messages to the census

This script does not (currently) pretend to allow to do all the actions related
to ballot-box or iam, only those related to iam. In cases those
actions are also related to ballot-box and if it makes sense, like creating
an election in both, then it allows that. But the admin/admin.py script from
ballot-box still manages other ballot-box specific tasks like doing
a tally, for example.

## Plugin system

The plugin system is simple, you need to create a file witch startwith **plugin_**, and added
arguments and functions that execute this arguments. There is a example in plugin_plugin.py

## Usage

For any of the actions, you need to provide the --config file (see
config/config_example.json for an example):

    ./sequent-admin --config config/config_example.json

This configuration file format is shared/global with other misc-tools commands
like import_election_csv.py or config_updates.py

Then you execute any of the actions:

### Create elections

To create an election with a census both in ballot-box and iam, you
need to provide a directory with numbered files so that for each election you
have 3 files: **id**.json, **id**.census.json and **id**.config.json. These
files can be generated with the  import_election_csv.py script or by other
means. For example:

    $ ls data/example
    781.json 781.json 781.config.json

    $ ./sequent-admin.py --config config/config_example.json --create data/example

Note that the ids of the files are only to attach the files together, because
the id is actually set on creation by iam and printed on screen.

# Start or stop an election

You can start or stop an election in iam following this example:

    $ ./sequent-admin.py --config config/config_example.json --start id
    $ ./sequent-admin.py --config config/config_example.json --stop id

# Send authentication codes to census

To send the authentication codes to the census using the message format
specified in the config file, use:

    $ ./sequent-admin.py --config config/config_example.json --send-auth-codes id

### Agora admin complete election:

    $ ./sequent-admin.py -C vota1.config.json -c data/vota1/
    $ ./sequent-admin.py -C vota1.config.json --start ID
    $ ./sequent-admin.py -C vota1.config.json --send-auth-codes ID
    $ ./sequent-admin.py -C vota1.config.json --stop ID
    $ ./sequent-admin.py -C vota1.config.json --tally ID
    $ ./sequent-admin.py -C vota1.config.json --calculate ID
    $ ./sequent-admin.py -C vota1.config.json --publish ID
