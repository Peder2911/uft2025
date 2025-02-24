
import argparse
import sys
import sqlite3
import pymupdf
import re
import pprint

def create_file_formatter(
        separator_pattern: str = "Do[ck]ument [A-Za-z0-9]{25}",
        sl_separator_pattern: str = "(?:[0-9]{1,2},)?[0-9]{1,3} +(?:Wörter|Words)",
        date_pattern: str = "(?P<day>[0-9]{1,2}) (?P<month>(January|February|March|April|May|June|July|August|September|October|November|December|Januar|Februar|Mars|April|Mai|Juni|Juli|August|September|Oktober|November|Desember)) (?P<year>([0-9]{4}))",
        source_pattern: str = "([A-Z][A-Za-z]* ?){2,}",
        rinse_pattern: str = "Page +[0-9]{1,4} +of +[0-9]{1,4} +[0-9]{4} +Factiva, +Inc. +(All|Alle) +(rights|Rechte) +(reserved|vorbehalten)."):

    def _parse_document(txt: str):
        doc = re.sub(rinse_pattern,' ',txt)
        row = {}
        
        date = re.search(date_pattern,doc)
        if date is None:
            return None
        row["date"] = date.group(0)

        splitdoc = re.split(sl_separator_pattern,doc)

        if len(splitdoc) < 2:
            return None
        lead = splitdoc[0]
        bod = splitdoc[1]
    
        row['body'] = bod.strip() 
        row['headline'] = lead.strip()

        source = re.search(source_pattern,bod)
        if source is None:
            return None
        row["source"] = source.group(0)
        return row

    def _call(txt: str):
        docs = re.split(separator_pattern,txt)
        docs.pop()
        return [result for result in [_parse_document(doc) for doc in docs] if result]

    return _call

def ingest(*args):
    parser = argparse.ArgumentParser(prog = "uftIngest", description = "Ingest PDF files into UFT.")
    parser.add_argument("filename")
    args = parser.parse_args(args)
    doc = pymupdf.open(args.filename)
    whole_text = "\n".join([p.get_text() for p in doc.pages()])
    docs = create_file_formatter()(whole_text)
    pprint.pprint(docs)

def main(args):
    match args:
        case ("ingest", *args):
            ingest(*args)
        case _:
            print(_MAIN_USAGE)


_MAIN_USAGE="""UFT
Usage: ./uft.py [subcommand]
Subcommands:
    ingest: Ingest PDF files into database
"""

if __name__ == "__main__":
    main(sys.argv[1:])
