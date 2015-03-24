add_arguments = [
        ['--plugins', {'action': 'store_true', 'help': 'Show too active plugins.'}]
]


def plugins(args):
    print("Active plugins:")
    for p in PLUGINS:
        print("* ", p)


def check_arguments(args, glo, loc):
    globals().update(glo)
    locals().update(loc)
    if args.plugins:
        plugins(args)
    else:
        return False
    return True
