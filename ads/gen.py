import os
import yaml
import ads #ads.sandbox as ads

PAPERS_PATH = os.path.abspath("../_data/papers.yml")

def abbreviate_name(name):
    splitchar = "." if name.count(".") >= 2 else " "
    abb_name = " ".join([
        f"{n.strip()[0]}."
        for n in name.strip().split(splitchar)
        if n.strip() != ""
    ])

    return abb_name

class Paper:
    def __init__(self, shortname=None, title=None, doi=None, bibcode=None, 
                 year=None, authors=None, journal=None, code_link=None, tags=[], **kwargs):

        if shortname is None:
            raise ValueError(f"shortname can't be None for {title}!")

        if doi is None and bibcode is None:
            raise ValueError(f"No doi or ADS bibcode provided for {title}!")

        if doi is not None and journal is None:
            raise ValueError(f"DOI found, but no journal provided for {title}, {doi}!")

        self.shortname = shortname
        self.title = title
        self.doi = doi
        self.bibcode = bibcode
        self.year = int(year)
        self.journal = journal
        self.code_link = code_link
        self.tags = tags

        self._authors = authors

    def __iter__(self):
        yield from dict(
            shortname = self.shortname,
            title = self.title,
            doi = self.doi,
            bibcode = self.bibcode,
            year = self.year,
            authors = self.authors,
            authors_html = self.authors_html,
            journal = self.journal,
            journal_html = self.journal_html,
            ads_link = self.ads_link,
            code_link = self.code_link,
            tags = self.tags,
        ).items()

    @property
    def authors(self):
        if type(self._authors) == list:
            lastnames = []
            firstnames = []
            for fullname in self._authors:
                lname, fname = fullname.split(",")
                lastnames.append(lname.strip())
                firstnames.append(abbreviate_name(fname))
        elif type(self._authors) == str:
            authors = self._authors.strip()
            lastnames = [ lname.strip() for lname in authors.split(",")[0::2] ]
            firstnames = [ abbreviate_name(fname) for fname in authors.split(",")[1::2] ]
        else:
            raise TypeError(f"Type {type(self._authors)} not supported for self._authors!")

        return( ", ".join([ 
            f"{lname}, {fname}" 
            for (fname, lname) in zip(firstnames, lastnames) 
        ]) )
    
    @property
    def ads_link(self):
        if self.bibcode is not None:
            return f"https://ui.adsabs.harvard.edu/abs/{self.bibcode}/abstract"
        else:
            return None
      
    @property
    def journal_html(self):
        if "Letter" in self.journal:
            return f"<u>{self.journal}</u>"
        else:
            return self.journal

    @property
    def authors_html(self):
        # bold your name in the author list
        with open("./my_author_names.txt", "r") as f:
            authors = self.authors

            my_author_names = sorted([
                n.strip() for n in f.readlines()], 
            key=len)
            my_author_names.reverse()

            for name in my_author_names:
                if name in authors:
                    idx1 = authors.index(name)
                    idx2 = idx1 + len(name)
                    break 

            authors_html = f"{authors[:idx1]}<b>{authors[idx1:idx2]}</b>{authors[idx2:]}"
            return authors_html

    def update(self, paper_dict):
        shortname = paper_dict.get("shortname", None)
        title = paper_dict.get("title", None)
        doi = paper_dict.get("doi", None)
        bibcode = paper_dict.get("bibcode", None)
        year = paper_dict.get("year", None)
        authors = paper_dict.get("authors", None)
        journal = paper_dict.get("journal", None)
        code_link = paper_dict.get("code_link", None)
        tags = paper_dict.get("tags", None)

        self.shortname = shortname if shortname is not None else self.shortname
        self.title = title if title is not None else self.title
        self.doi = doi if doi is not None else self.doi
        self.bibcode = bibcode if bibcode is not None else self.bibcode
        self.year = int(year) if year is not None else self.year
        self.journal = journal if journal is not None else self.journal
        self.code_link = code_link if code_link is not None else self.code_link
        self.tags = tags if tags is not None else self.tags

        self._authors = authors if authors is not None else self._authors

# load in existing paper records
if os.path.isfile(PAPERS_PATH):
    with open(PAPERS_PATH, "r") as papers_file:
        my_papers = [
            Paper(**paper_dict) 
            for paper_dict in yaml.load(papers_file, Loader=yaml.CLoader)
        ]
else:
    my_papers = []

# grab records from ADS, for cross-checking or adding new records
with open("./orcid.txt", "r") as f: orcid = f.read()
ads_papers = ads.SearchQuery(
    orcid=orcid, 
    fl=["doi", "bibcode", "title", "year", "author", "pub", "property"]
)

# check if any of the ads records are already locally recorded
for ads_paper in ads_papers:
    if "ARTICLE" not in ads_paper.property:
        continue

    found_in_pubs = False
    paper_dict = ads_paper.__dict__
    paper_dict["title"] = ads_paper.title[0]
    paper_dict["journal"] = ads_paper.pub
    paper_dict["authors"] = ads_paper.author
    paper_dict["doi"] = ads_paper.doi[0] if ads_paper.doi is not None else None
    
    for my_paper in my_papers:
        if paper_dict["doi"] == my_paper.doi or paper_dict["bibcode"] == my_paper.bibcode:
            my_paper.update(paper_dict)
            found_in_pubs = True
            break

    if not found_in_pubs:
        shortname = input(f"Shortname for '{paper_dict['title']}': ").strip()
        paper_dict["shortname"] = shortname
        my_papers.append( Paper(**paper_dict) )

# prompt the user for a link to code, tags for each paper if they don't exist
for paper in my_papers:

    pretty_input_display = paper.code_link == None or len(paper.tags) == 0
    if pretty_input_display:
        print(f"{paper.title}")
        print("".join(["=" for i in range(len(paper.title))]))

    if paper.code_link == None:
        code_link = input(f"Code link: ").strip()

        if code_link != "":
            paper.code_link = code_link

    if len(paper.tags) == 0:
        rawtags = input(f"Tags (comma-sep): ").strip()
        if rawtags != "":
            paper.tags = [ t.strip() for t in rawtags.split(",") ]

    if pretty_input_display:
        print("\n")
   
# sort papers by year (descending) and by name (alphabetical)
my_papers.sort(key=lambda paper: (-int(paper.year), paper.authors))

# dump the paper records to a .yml file
with open(PAPERS_PATH, "w") as papers_file:
    for paper in my_papers:
        papers_file.write(
            yaml.dump([dict(paper)], sort_keys=False)
        )
        papers_file.write("\n")