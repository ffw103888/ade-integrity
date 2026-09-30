import argparse, json
from .core import verify_ledger


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("ledger")
    a = p.parse_args(argv)
    e = verify_ledger(a.ledger)
    print(json.dumps({"ok": not e, "errors": e}))
    return 0 if not e else 1


if __name__ == "__main__":
    raise SystemExit(main())
