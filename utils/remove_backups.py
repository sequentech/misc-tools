#!/usr/bin/env python3

import json
import argparse
import subprocess
from datetime import datetime, timedelta, timezone

def get_days_old(date, now):
    return (now - datetime.fromisoformat(date)).days

def use_backups(pargs, parser):
    vol_id = pargs.vol_id
    vol_list_file = pargs.vol_list_file
    print_only = pargs.print_only
    base_arn = pargs.base_arn
    aws_bin_path = pargs.aws_bin_path
    maintain_days = pargs.maintain_days

    now = datetime.now(timezone.utc)
    oldest_allowed_date = now - timedelta(days=maintain_days)

    if not vol_id and not vol_list_file:
        parser.print_help()
        exit(1)
    if vol_id:
        vol_list = [vol_id]
    else:
        with open(vol_list_file, 'r') as f:
            vol_list = [
                line.replace("\n", "")
                for line in open("vol-ids.txt", "r").readlines()
                if len(line) > 0
            ]
    
    for vol_id in vol_list:
        recovery_points_list_json = subprocess.check_output(
            [
                aws_bin_path,
                "backup",
                "list-recovery-points-by-backup-vault",
                "--backup-vault-name",
                "Default",
                "--by-resource-arn",
                "%s%s" % (
                    base_arn,
                    vol_id
                )
            ]
        )
        recovery_points_list = json.loads(recovery_points_list_json)['RecoveryPoints']

        to_remove_recovery_points_list = [
            point
            for point in recovery_points_list
            if datetime.fromisoformat(point['CreationDate']) <= oldest_allowed_date
        ]
        to_maintain_recovery_points_list = [
            point
            for point in recovery_points_list
            if datetime.fromisoformat(point['CreationDate']) > oldest_allowed_date
        ]
        print("To remove:")
        for point in to_remove_recovery_points_list:
            days_old = get_days_old(point['CreationDate'], now)
            arn = point['RecoveryPointArn']
            print(f"- {arn} ({days_old} days old)")

        print("\nTo maintain:")
        for point in to_maintain_recovery_points_list:
            days_old = get_days_old(point['CreationDate'], now)
            arn = point['RecoveryPointArn']
            print(f"- {arn} ({days_old} days old)")

        print("\nStarting to remove..")

        # remove short recovery points
        if print_only:
            print("..not removing anything as we are in print only mode. Finished.")
            exit(0)
        for point in to_remove_recovery_points_list:
            cmd = [
                aws_bin_path,
                "backup",
                "delete-recovery-point",
                "--backup-vault-name",
                "Default",
                "--recovery-point-arn",
                point['RecoveryPointArn']
            ]
            ret = subprocess.check_call(cmd)
            if ret == 0:
                print("removed point %s" % point)
            else:
                print("error removing point %s, command = cmd" % (
                    (point['RecoveryPointArn'], " ".join(cmd))
                ))

def use_snapshots(pargs, _parser):
    vol_id = pargs.vol_id
    vol_list_file = pargs.vol_list_file
    print_only = pargs.print_only
    base_arn = pargs.base_arn
    aws_bin_path = pargs.aws_bin_path
    maintain_days = pargs.maintain_days

    now = datetime.now(timezone.utc)
    oldest_allowed_date = now - timedelta(days=maintain_days)

    if vol_id:
        vol_list = [vol_id]
    else:
        with open(vol_list_file, 'r') as f:
            vol_list = [
                line.replace("\n", "")
                for line in open("vol-ids.txt", "r").readlines()
                if len(line) > 0
            ]
    
    if len(vol_list) > 0:
        vol_list_str = "[?contains(" + json.dumps(vol_list) + ", VolumeId)]&&"
    else:
        vol_list_str = ""

    oldest_date_str = oldest_allowed_date.isoformat()

    command = [
        aws_bin_path,
        "ec2",
        "describe-snapshots",
        "--output",
        "json",
        "--query",
        f"Snapshots{vol_list_str}[?StartTime<\"{oldest_date_str}\"].[SnapshotId,StartTime]"
    ]
    print(f"executing: {command}..")
    snapshots_ids_json = subprocess.check_output(command)
    print("command output: {snapshots_ids_json}")

    snapshot_ids = json.loads(snapshots_ids_json)
    print("To remove:")
    for snapshot in snapshot_ids:
            days_old = get_days_old(snapshot['CreationDate'], now)
            snapshot_id = snapshot['SnapshotId']
            print(f"- {snapshot_id} ({days_old} days old)")

    print("\nStarting to remove..")

    # remove short recovery points
    if print_only:
        print("..not removing anything as we are in print only mode. Finished.")
    exit(0)
    for snapshot in snapshot_ids:
        '''cmd = [
            aws_bin_path,
            "backup",
            "delete-recovery-point",
            "--backup-vault-name",
            "Default",
            "--recovery-point-arn",
            point['RecoveryPointArn']
        ]
        ret = subprocess.check_call(cmd)
        if ret == 0:
            print("removed point %s" % point)
        else:
            print("error removing point %s, command = cmd" % (
                (point['RecoveryPointArn'], " ".join(cmd))
            ))'''

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
        "--aws-bin-path",
        help="Path to aws binary",
        default="/usr/bin/aws"
    )
    parser.add_argument(
        "--base-arn",
        help="Base ARN",
        default="arn:aws:ec2:eu-west-1:498439606504:volume/"
    )
    parser.add_argument(
        "--vol-list-file",
        help="File with a list of volumes, one per line, example: file.csv"
    )
    parser.add_argument(
        "--print-only",
        help="Do not execute any action, just print what would be done",
        action="store_true"
    )
    parser.add_argument(
        "--use-snapshots",
        help="Instead of using backups, use snapshots",
        action="store_true"
    )
    parser.add_argument(
        "--maintain-days",
        help="number of days to maintain",
        type=int,
        default=365
    )
    pargs = parser.parse_args()
    
    if pargs.use_snapshots:
        use_snapshots(pargs, parser)
    else:
        use_backups(pargs, parser)

main()
