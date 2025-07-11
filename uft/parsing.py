
import abc
import dataclasses
import pymupdf
import re
import hashlib 



@dataclasses.dataclass
class Document:
    body: str
    headline: str
    source: str
    date: str
    hash: str

    def __str__(self):
        def _tabindent_lines(x):
            return "\n".join(["\t"+ln for ln in x.split("\n")])
        elements = [
            f"Source:\t{self.source}",
            f"Date:\t{self.date}",
            f"Headline:\n{_tabindent_lines(self.headline)}\n"
            f"Body:\n{_tabindent_lines(self.body)}"
        ]
        return "\n".join(elements)

class Parse(abc.ABC):
    @abc.abstractmethod
    def parse_source(self, raw:str) -> list[Document]:
        ...

def reremove(pattern,x):
    return re.sub(pattern,"",x)

class ClassicRegexParse(Parse):
    separator_pattern: str = "Do[ck]ument [A-Za-z0-9]{25}"
    sl_separator_pattern: str = "(?:[0-9]{1,2},)?[0-9]{1,3} +(?:Wörter|Words|words)"
    date_pattern: str = "(?P<day>[0-9]{1,2}) (?P<month>(January|February|March|April|May|June|July|August|September|October|November|December|Januar|Februar|Mars|April|Mai|Juni|Juli|August|September|Oktober|November|Desember)) (?P<year>([0-9]{4}))"
    source_pattern: str = "([A-Z][A-Za-z]* ?){2,}"
    rinse_pattern: str = "Page +[0-9]{1,4} +of +[0-9]{1,4} ©? +[0-9]{4} +Factiva, +Inc. +(All|Alle) +(rights|Rechte) +(reserved|vorbehalten)."
    author_pattern: str = "By [A-Za-z ]+"
    residual_header_pattern: str = r"^(©|\(c\)|Copyright|\(C\)).*$"

    def parse_source(self, raw:str) -> list[Document]:
        docs = re.split(self.separator_pattern,raw)
        docs.pop()
        return [result for result in [self._parse_doc(doc) for doc in docs] if result]

    def _parse_doc(self, raw: str) -> Document|None:
        doc = reremove(self.rinse_pattern,raw)
        row = {"hash": hashlib.md5(raw.encode()).hexdigest()}
        
        date = re.search(self.date_pattern,doc)
        if date is None:
            return None
        row["date"] = date.group(0)

        splitdoc = re.split(self.sl_separator_pattern,doc)

        if len(splitdoc) < 2:
            return None
        lead = splitdoc[0]
        bod = splitdoc[1]
    
        body_lines =  bod.strip().split("\n")
        for i in (range(len(body_lines)) if len(body_lines) < 10 else range(10)):
            try:
                if re.search(self.residual_header_pattern,body_lines[i]):
                    body_lines = body_lines[i+1:]
            except IndexError:
                break

        page_line = lambda ln: re.search("Page [0-9]{1,4} of [0-9]{1,4}", ln)
        body_lines = [ln for ln in body_lines if ln and not page_line(ln)]
        
        row["body"] = "\n".join(body_lines).strip("\n")

        leadlines = lead.split("\n")
        if len(leadlines) > 5:
            headline = leadlines[4]
            row['headline'] = leadlines[4]
        else:
            headline = "\n".join(leadlines) 

        row["headline"] = reremove(self.author_pattern,headline).strip()


        source = re.search(self.source_pattern,bod)
        if source is None:
            return None
        row["source"] = source.group(0)
        return Document(**row)

class SourceFile:
    def __init__(self, raw_content, parser = None):
        self._parser = parser or ClassicRegexParse()
        self._raw_content = raw_content

    @property
    def documents(self) -> list[Document]:
        return self._parser.parse_source(self._raw_content)

    @classmethod
    def read_path(cls,filename):
        doc = pymupdf.open(filename)
        whole_text = "\n".join([p.get_text() for p in doc.pages()])
        return cls(whole_text)
