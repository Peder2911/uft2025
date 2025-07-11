
import random
import argparse
import sys
import sqlite3
import pymupdf
import pprint
import hashlib 
import os
import functools

import parsing


def main(args):
    con = sqlite3.connect(os.path.expanduser("~/.local/state/uft.sqlite"))
    match args:
        case ("print", *args):
            print_one_doc(*args)
        case ("ingest", *args):
            ingest(con, *args)
        case ("init", *args):
            init_db(con)
        case _:
            print(_MAIN_USAGE)


_MAIN_USAGE="""UFT
Usage: ./uft.py [subcommand]
Subcommands:
    ingest: Ingest PDF files into database
    init:   Initialize the database.
"""

def print_one_doc(*args):
    print("="*32)
    files = functools.reduce(lambda a,b: a+b, [[n[0]+"/"+f for f in n[2]] for n in os.walk(os.path.expanduser("~/Documents/factiva-pdf-files"))])
    file = random.choice(files)
    print(file)
    docs = parsing.SourceFile.read_path(file).documents
    print(random.choice(docs))


def ingest(con: sqlite3.Connection, *args):
    parser = argparse.ArgumentParser(prog = "uftIngest", description = "Ingest PDF files into UFT.")
    parser.add_argument("filename")
    parser.add_argument("--force",action=argparse.BooleanOptionalAction)
    args = parser.parse_args(args)
    with open(args.filename, "rb") as f:
        checksum = hashlib.md5(f.read()).hexdigest()
    existing = con.execute("select checksum from sourcefile where checksum = ?", (checksum,)).fetchone()
    if existing and not args.force:
        print("Document exists")
        return
    doc = pymupdf.open(args.filename)
    whole_text = "\n".join([p.get_text() for p in doc.pages()])
    pprint.pprint(whole_text)
    docs = create_file_formatter()(whole_text)
    for doc in docs:
        con.execute("insert into document values (?,?,?,?)",(
                doc.headline,
                doc.body,
                doc.source,
                doc.date
            ))
    con.execute("insert or ignore into sourcefile values (?)", (checksum,))
    con.commit()
    pprint.pprint(docs)

def init_db(con: sqlite3.Connection):
    con.execute("""
    create virtual table if not exists document using fts5(
        headline, body, source, date
    )
    """)
    con.execute("""
    create table if not exists sourcefile (
        checksum text primary key
    )
    """)

