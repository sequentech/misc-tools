#!/usr/bin/env python3

import json
import argparse
import subprocess

BASE_ARN = "arn:aws:ec2:eu-west-1:498439606504:volume/"

def main():
    '''
    Main function
    '''
    parser = argparse.ArgumentParser(prog='remove_backups.py')
    parser.add_argument(
        "--vol-id",
        help="Volume Id, example: vol-194f68ea"
    )
    parser.add_argument(
        "--vol-list-file",
        help="File with a list of volumes, one per line, example: file.csv"
    )
    parser.add_argument(
        "--remove-all",
        help="Force to remove all",
        action="store_true"
    )
    pargs = parser.parse_args()
    vol_id = pargs.vol_id
    vol_list_file = pargs.vol_list_file
    remove_all = pargs.remove_all
    if not vol_id and not vol_list_file:
        parser.print_help()
        exit(1)
    if vol_id:
        vol_list = [vol_id]
    else:
        with open(vol_list_file, 'r') as f:
            vol_list = f.readlines().split('\n')
    
    for vol_id in vol_list:
        recovery_points_list_json = subprocess.check_output(
            [
                "/usr/bin/aws",
                "backup",
                "list-recovery-points-by-backup-vault",
                "--backup-vault-name",
                "Default",
                "--by-resource-arn",
                "%s%s" % (
                    BASE_ARN,
                    vol_id
                )
            ]
        )
        recovery_points_list = json.loads(recovery_points_list_json)['RecoveryPoints']

        # filter those with less than a year of expiration
        if not remove_all:
            limit = 365
        else:
            limit = 10000

        short_recovery_points_list = [
            point['RecoveryPointArn']
            for point in recovery_points_list
            if (
                isinstance(point["Lifecycle"], dict) and
                point["Lifecycle"]["DeleteAfterDays"] < 365
            )
        ]
        long_recovery_points_list = [
            point['RecoveryPointArn']
            for point in recovery_points_list
            if (
                isinstance(point["Lifecycle"], dict) and
                point["Lifecycle"]["DeleteAfterDays"] >= 365
            )
        ]
        print("To remove:")
        print("\n".join(short_recovery_points_list))
        print("\nTo maintain:")
        print("\n".join(long_recovery_points_list))

        if len(long_recovery_points_list) == 0:
            print("Failing, no recovery point would be maintained")
            exit(1)

        print("\nStarting to remove:")

        # remove short recovery points
        for point in short_recovery_points_list:
            cmd = [
                "/usr/bin/aws",
                "backup",
                "delete-recovery-point",
                "--backup-vault-name",
                "Default",
                "--recovery-point-arn",
                point
            ]
            ret = subprocess.check_call(cmd)
            if ret == 0:
                print("removed point %s" % point)
            else:
                print("error removing point %s, command = cmd" % (
                    (point, " ".join(cmd))
                ))

main()