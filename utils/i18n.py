#!/usr/bin/env python3

import json
import argparse

def update_items(key, base, i18n):
    if isinstance(base[key], str):
        base[key] = i18n
    else:
        for key, _ in base.items():
            if key in i18n:
                update_items(key, base, i18n[key])

def run(base_path, i18n_path, out_path):
    base = json.loads(open(base_path).read())
    i18n = json.loads(open(i18n_path).read())
    for key, _ in base.items():
        if key in i18n:
            update_items(key, base, i18n[key])
    open(out_path,mode="w").write(json.dumps(base, indent=2,sort_keys=True))

def main():
    '''
    Main function
    '''
    parser = argparse.ArgumentParser(prog='i18n.py')
    parser.add_argument(
        "--base",
        help="Base translation file path"
    )
    parser.add_argument(
        "--i18n",
        help="i18n translation file path"
    )
    parser.add_argument(
        "--out",
        help="Output translation file path"
    )
    pargs = parser.parse_args()

    run(pargs.base, pargs.i18n, pargs.out)

main()
