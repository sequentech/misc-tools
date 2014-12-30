# Config updates

Sometimes, you have an election running, and unfortunately, you need to change the configuration. That shouldn't happen, but in practice it can happen. Usually, that means you need to start the election from the begining. That's a reasonable solution, but because in Agora Voting we want to be flexible, we want to provide alternatives in case you need them.

These are the actions that we currently support:
* Change question's maximum number of candidates that a user can choose and the number of winners candidates (1)
* Remove candidate (2)
* Add candidate (2)
* Change candidate's category (2)

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