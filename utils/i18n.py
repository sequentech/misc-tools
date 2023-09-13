#!/usr/bin/env python3

import json
import argparse

def update_items(key, base, i18n, filtered):
    typeof = type(base[key])
    if isinstance(base[key], str):
        filtered[key] = i18n
    else:
        filtered[key] = dict()
        for key2, _ in base[key].items():
            if key2 in i18n[key]:
                update_items(key2, base[key], i18n[key], filtered[key])

def run(base_path, i18n_path, out_path):
    base = json.loads(open(base_path).read())
    i18n = json.loads(open(i18n_path).read())
    filtered = dict()
    for key, _ in base.items():
        if key in i18n:
            update_items(key, base, i18n, filtered)
    open(out_path,mode="w").write(json.dumps(filtered, indent=2,sort_keys=True))

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
