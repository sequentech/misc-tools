# Config updates

Sometimes, you have an election running, and unfortunately, you need to change the configuration. That shouldn't happen, but in practice it can happen. Usually, that means you need to start the election from the begining. That's a reasonable solution, but because in Agora Voting we want to be flexible, we want to provide alternatives in case you need them.

These are the actions that we currently support:
* Change question's maximum number of candidates that a user can choose and the number of winners candidates (1)
* Remove candidate (2)
* Add candidate (2)
* Change candidate's category (2)
* Verify the results of an election

More actions can be easily incorporated in the future as needed.

Options marked with (1) mean that the change can be applied without creating a new election. This means that what needs to change is only the election configuration in for agora_elections, and the configuration used for calculating the results with agora-results.

Options marked with (2) mean that a new election is needed. In that case, the results of the two elections need to be consolidated to obtain the final results.

# Processing

The config_updates.py script allows you to:

* check that the CSV with the updates has been correctly applied

This is useful if you have manually applied some updates. This script will check if the updates you have registered in the "updates CSV" are exactly the only updates applied, and if they have been applied.

* generate or list the actions, commands, or configuration files to apply the updates in agora_election and agora-results

Given an "updates CSV", it can generate list of actions that need to be taken for the yet unapplied changes. It can also generate the configuration files associated with the actions, and even list commands that need to be executed.

# The updates CSV format

The updates CSV format needs to be strictly followed in order for the script to function correctly. Using a CSVs format allows you to generate it using any tool you want (google docs, another tool, libreoffice, etc), and allows you to register the changes with completitude and in an effective way. You can even use the same file yourself to automatically generate a document describing the updates.

The format is very simple: A single table, with a list of columns describing some data, and each update is written in a single row. The file is processed by taking each row.

# Usage

    mkvirtualenv agora-tools -p $(which python3)
    workon agora-tools
    pip install -r requirements.txt
    config_updates.py -u updates.csv -c config.json --action check
    config_updates.py -u updates.csv -c config.json --action show_agora_elections_commands
    config_updates.py -u updates.csv -c config.json --action write_agora_results_files --dest-dir /tmp/agora-results-config

# Election results verification

Config updates also enables authorities to verify of the results of an election with the command 'verify_results'. It requires a folder as parameter, and in that folder there needs to be a number of files. For simplification, imagine that we have an election process that consists on a single election, with election id 27. Then the folder will contain:

* election_ids.txt
* election_config.json
* 27.config.json
* 27.config.results.json
* 27.results.json

**election_ids.txt**

The contents of this file will be the list of election ids.

**election_config.json**

Configuration for agora-results. There is an example on agora-tools/config/config_example.json

**27.config.json**

Election description. It can be obtained using config_updates.py command 'download_elections' on an agora server. For example: 
    config_updates.py -c config/config_example.json -C config/empty_corrections.tsv -e /srv/data/$PROCESS-json -i /srv/data/$PROCESS-ids.txt -a download_elections

**27.config.results.json**

Agora-results pipes configuration required to do the tally. These files can normally be found on agora servers, on a folder similar to /home/agoraelections/datastore/private/27/config.json

**27.results.json**

These are the results of the election that we want to verify. These files can normally be found on agora servers, on a folder similar to /home/agoraelections/datastore/private/27/results-18bfef57-fa96-42e1-9abb-bf0b44ffeff5/27.results.json

An example verification call would be:

    $ python3 config_updates.py -e ~/data/verify-id27-json -a verify_results

If the verification is successful, a message "27 election VERIFIED" will be shown (one of those messages per election id). If there is a verification error for an election id, a message like "27 election FAILED verification" will be shown.