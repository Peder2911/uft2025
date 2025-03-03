
import dataclasses
import argparse
import sys
import sqlite3
import pymupdf
import re
import pprint
import hashlib 
import os


@dataclasses.dataclass
class Document:
    body: str
    headline: str
    source: str
    date: str
    hash: str

def create_file_formatter(
        separator_pattern: str = "Do[ck]ument [A-Za-z0-9]{25}",
        sl_separator_pattern: str = "(?:[0-9]{1,2},)?[0-9]{1,3} +(?:Wörter|Words|words)",
        date_pattern: str = "(?P<day>[0-9]{1,2}) (?P<month>(January|February|March|April|May|June|July|August|September|October|November|December|Januar|Februar|Mars|April|Mai|Juni|Juli|August|September|Oktober|November|Desember)) (?P<year>([0-9]{4}))",
        source_pattern: str = "([A-Z][A-Za-z]* ?){2,}",
        rinse_pattern: str = "Page +[0-9]{1,4} +of +[0-9]{1,4} +[0-9]{4} +Factiva, +Inc. +(All|Alle) +(rights|Rechte) +(reserved|vorbehalten)."):

    def _parse_document(txt: str):
        doc = re.sub(rinse_pattern,' ',txt)
        row = {"hash": hashlib.md5(txt.encode()).hexdigest()}
        
        date = re.search(date_pattern,doc)
        if date is None:
            return None
        row["date"] = date.group(0)

        splitdoc = re.split(sl_separator_pattern,doc)

        if len(splitdoc) < 2:
            return None
        lead = splitdoc[0]
        bod = splitdoc[1]
    
        body_lines =  bod.strip().split("\n")
        for i in (range(len(body_lines)) if len(body_lines) < 10 else range(10)):
            try:
                if body_lines[i].startswith("Copyright"):
                    body_lines = body_lines[i+1:]
            except IndexError:
                break

        page_line = lambda ln: re.search("Page [0-9]{1,4} of [0-9]{1,4}", ln)
        body_lines = [ln for ln in body_lines if ln and not page_line(ln)]
        
        row["body"] = "\n".join(body_lines)
        leadlines = lead.split("\n")
        if len(leadlines) > 5:
            row['headline'] = leadlines[4]
        else:
            row["headline"] = "\n".join(leadlines)


        source = re.search(source_pattern,bod)
        if source is None:
            return None
        row["source"] = source.group(0)
        return Document(**row)

    def _call(txt: str):
        docs = re.split(separator_pattern,txt)
        docs.pop()
        return [result for result in [_parse_document(doc) for doc in docs] if result]

    return _call

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

def main(args):
    con = sqlite3.connect(os.path.expanduser("~/.local/state/uft.sqlite"))
    match args:
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

if __name__ == "__main__":
    main(sys.argv[1:])
