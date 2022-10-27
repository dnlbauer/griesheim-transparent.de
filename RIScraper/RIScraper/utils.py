import argparse
import multiprocessing
import os
from datetime import date
from pprint import pprint

import yaml
import re


def chunks(lst, n):
    if len(lst) % 2 != 0:
        lst = lst[:-1]
    return (lst[i:i + n] for i in range(0, len(lst), n))


def clean_string(s):
    return re.sub(r"\s+", " ", s).strip()

def _month_from_now(add=0):
    month = date.today().month
    year = date.today().year
    month += add
    while (month > 12):
        month -= 12
        year += 1
    return f"{month}/{year}"


def parse_args():
    parser = argparse.ArgumentParser("RIScraper")
    parser.add_argument("--db", dest="db", action="store")
    parser.add_argument("--tika", dest="tika", action="store")
    parser.add_argument("--scrape", dest="scrape", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--organizations", dest="organizations", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--persons", dest="persons", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--systematic", dest="systematic", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--analyze", dest="analyze", action="store", default="new", choices=["all", "new", "none"])
    parser.add_argument("--start", dest="start", action="store", default=_month_from_now(-3))
    parser.add_argument("--end", dest="end", action="store", default=_month_from_now(3))
    parser.add_argument("--nscraper", dest="nscraper", action="store", type=int, default=multiprocessing.cpu_count())
    parser.add_argument("--nanalyzer", dest="nanalyzer", action="store", type=int, default=max(1, int(multiprocessing.cpu_count() / 4)))
    parser.add_argument("--meeting", dest="meeting", action="store", default=None)
    args = parser.parse_args()
    return args


def parse_config_and_args(filename, args):
    with open(filename, "r") as f:
        config = yaml.safe_load(f)
    if "DATABASE_CONN" in os.environ:
        config['database_url'] = os.environ.get('DATABASE_CONN')
    elif "POSTGRES_USER" in os.environ and "POSTGRES_PASSWORD" in os.environ and "POSTGRES_DB" in os.environ and "POSTGRES_HOST" in os.environ:
        config['database_url'] = f"postgresql+psycopg2://{os.environ.get('POSTGRES_USER')}:{os.environ.get('POSTGRES_PASSWORD')}@{os.environ.get('POSTGRES_HOST')}/{os.environ.get('POSTGRES_DB')}"
    if "TIKA" in os.environ:
        config["tika"] = os.environ.get("TIKA")

    if args is not None:
        config["scrape"] = args.scrape
        config["organizations"] = args.organizations
        config["persons"] = args.persons
        config['meeting'] = args.meeting
        config["systematic"] = args.systematic
        config["analyze"] = args.analyze
        config["start_year"] = int(args.start.split("/")[-1])
        config["start_month"] = int(args.start.split("/")[0])
        config["end_year"] = int(args.end.split("/")[-1])
        config["end_month"] = int(args.end.split("/")[0])
        config["nscraper"] = args.nscraper
        config["nanalyzer"] = args.nanalyzer
        if "db" in args and args.db is not None:
            config["database_url"] = args.db
        if "tika" in args and args.tika is not None:
            config["tika"] = args.tika
    return config