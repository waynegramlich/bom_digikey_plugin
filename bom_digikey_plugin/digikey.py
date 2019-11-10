# # BOM Manager Digi-Key Plugin
#
# ## License
#
# MIT License
#
# Copyright (c) 2019 Wayne C. Gramlich
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# # Coding Standars:
#
# <------------------------------------------- 100 characters -----------------------------------> #
# * All code and docmenation lines must be on lines of 100 characters or less.
# * In general, the coding guidelines for PEP 8 are used.
# * Comments:
#   * All code comments are written in [Markdown](https://en.wikipedia.org/wiki/Markdown).
#   * Code is organized into blocks are preceeded by comment that explains the code block.
#   * For methods, a comment of the form `# CLASS_NAME.METHOD_NAME():` is before each method
#     definition.  This is to disambiguate overloaded methods that implemented in different classes.
# * Class/Function standards:
#   * Indentation levels are multiples of 4 spaces and continuation lines have 2 more spaces.
#   * All classes are listed alphabetically.
#   * All methods within a class are listed alphabetically.
#   * No duck typing!  All function/method arguments are checked for compatibale types.
#   * Inside a method, *self* is usually replaced with more descriptive variable name.
#   * Generally, single character strings are in single quotes (`'`) and multi characters in double
#     quotes (`"`).  Empty strings are represented as `""`.  Strings with multiple double quotes
#     can be enclosed in single quotes.
#   * Lint with:
#
#       flake8 --max-line-length=100 digikey.py | fgrep -v :3:1:

from argparse import ArgumentParser
from bom_manager.node_view import (BomManager, Collection, Directory, Node, Table)
from bom_manager.tracing import trace, trace_level_get, trace_level_set, tracing_get
import bs4   # type: ignore
from bs4 import BeautifulSoup
from bs4 import element as Element
# import glob
# import os
from pathlib import Path
import requests
# import time
from typing import Any, Dict, List, IO, Optional, Tuple
# Match = Tuple[str, str, int, str, str, str]


# main():
# @trace(1)
def main() -> int:
    """bom_digikey command line entry point.

    The `bom_digikey` command is the command used to setup the Digi-Key collection
    directory/file structures.  It is not meant to be executed by end-users, just
    the keeper fo the Digi-Key collection.  The results of this operation are checked
    into `github.com` repository and uploaded to `https:pypi.org`.  After that people
    can access the Digi-Key collection by simply running `pip`:

         pip install bom_digikey_plugin

    The syntax of the command line is:

         bom_digikey [--home HOME] [-v]

    The `--home` option specifies where the data structures are to be stored.
    The `-v` option increases the verbosity of tracing information for debugging purposes.
    """
    # The `bom_digikey` command is configured in the `setup.py` for this package.
    # The key lines are:
    #
    #      entry_points={
    #          "console_scripts": ["bom_digikey=bom_digikey_plugin:main"],
    #          ...
    #      }
    #
    # This instructs the `pip` installer to construct a command line executable file and ensure
    # that it is accessable via the `$PATH` execution path envirnoment variable.  The executable
    # file invokes the *main* function in the `__init__.py`  mododule in the package.  That
    # `main` function, in turn, calls this main function.

    # Start by creating the command line *parser*, configuring it, and parsing the command
    # line arguments:
    parser: ArgumentParser = ArgumentParser(description="Digi-Key Collection Constructor.")
    parser.add_argument("-v", "--verbose", action="count",
                        help="Set tracing level (defaults to 0 which is off).")
    parser.add_argument("--home",
                        help="Specify the HOME directory for the collection files.")
    parsed_arguments: Dict[str, Any] = vars(parser.parse_args())

    # Extract the command line options:
    verbose: int = 0 if parsed_arguments["verbose"] is None else parsed_arguments["verbose"]
    home: Optional[str] = parsed_arguments["home"]

    # Convert the *home* string into *home_path*:
    home_path: Path
    if home is None:
        # The *home* option was not specified, so we default to the package directory:
        digikey_py_file_name: str = __file__
        digikey_py_path: Path = Path(digikey_py_file_name)
        home_path = digikey_py_path.parent
    else:
        home_path = Path(home)

    # Perform any requested *tracing*:
    trace_level_set(verbose)
    tracing: str = tracing_get()
    if tracing:  # pragma: no cover
        print(f"{tracing}home_path='{home_path}'")

    # Create the *digikey* object and process it:
    digikey: Digikey = Digikey(home_path)
    digikey.process()
    result: int = 0
    return result


# Match:
class Match:
    """Represents an HRef match.

    This is a helper class that contains information that was extracted
    from the `.html` file.  It is place before the *Digikey* class
    declaration to eliminate confusion with `flake8`.
    """

    def __init__(self, href: str, base: str, nonce: int,
                 a_content: str, li_content: str, url: str) -> None:
        """Initialize a match object."""
        # match: Match = self
        self.href: str = href
        self.base: str = base
        self.nonce: int = nonce
        self.a_content: str = a_content
        self.li_content: str = li_content
        self.url: str = url

    def __str__(self):
        """Return a string representation of a match object."""
        match: Match = self
        result: str = "Match(???)"
        if hasattr(match, "base"):
            href: str = match.href
            base: str = match.base
            nonce: int = match.nonce
            a_content: str = match.a_content
            li_content: str = match.li_content
            url: str = match.url
            result = f"'Match('{href}', '{base}', {nonce}, '{a_content}', '{li_content}', '{url}')"
        return result

    def key(self) -> Tuple[str, str, int, str, str, str]:
        """Return a key suitable for sorting matches."""
        match: Match = self
        href: str = match.href
        base: str = match.base
        nonce: int = match.nonce
        a_content: str = match.a_content
        li_content: str = match.li_content
        url: str = match.url
        tuple: Tuple[str, str, int, str, str, str] = (href, base, nonce, a_content, li_content, url)
        return tuple


# Digikey:
class Digikey:
    """The gloabal class used to construct the Digikey collection."""

    # Digikey.__init__():
    # @trace(1)
    def __init__(self, home_path: Path) -> None:
        """Initialize the *Digikey* object.

        Initialize *digikey* (i.e. *self*) using *home_path* to specify
        the location to find all of the `.csv` and `.xml` files.

        Args:
            *home_path* (*Path*): The path to the directory that
                contains the various files.  In particular, this
                directory contains both the `ROOT` and `MISC`
                sub-directories.

        """
        # Compute the various file paths:
        root_path: Path = home_path / "ROOT"
        miscellaneous_path: Path = home_path / "MISC"
        products_html_path: Path = miscellaneous_path / "www.digikey.com_products_en.html"

        # Perform any requested *tracing*:
        tracing: str = tracing_get()
        if tracing:  # pragma: no cover
            print(f"{tracing}home_path='{home_path}'")
            print(f"{tracing}root_path='{root_path}'")
            print(f"{tracing}miscellaneous_path='{miscellaneous_path}'")
            print(f"{tracing}products_html_path='{products_html_path}'")

        # Make sure everything exists:
        root_path.mkdir(parents=True, exist_ok=True)
        miscellaneous_path.is_dir(), f"'{miscellaneous_path}' is not a directory"
        products_html_path.is_file(), f"'{products_html_path} is not a file'"

        # Create *bom_manager* to hold all of the *Node* based data structures:
        bom_manager: BomManager = BomManager()

        # Stuff various file names into *digikey* (i.e. *self*):
        # digikey: Digikey = self
        self.bom_manager: BomManager = bom_manager
        self.products_html_path: Path = products_html_path
        self.root_path: Path = root_path

    # Digikey.__str__():
    def __str__(self):
        """Return a string representation."""
        return "Digikey()"

    # Digikey.collection_extract():
    # @trace(1)
    def collection_extract(self, hrefs_table: Dict[str, List[Match]]) -> Collection:
        """
        """
        # Now we construct *collection* which is a *Collection* that contains a set of
        # *Directory*'s.  Each of these nested *Directory*'s contains a further list
        # of *Table*'s.
        #
        # The sorted keys from *hrefs_table* are alphabetized by '*base*/*nonce*' to look basically
        # as follows:
        #
        #        None/-1                                          # Null => Root directory
        #        audio-products/10                                # *items* < 0 => directory
        #        audio-product/accessories/159
        #        audio-products-buzzers-and-sirends/157
        #        audio-products-buzzer-ellements-piezo-benders/160
        #        audio-products-microphones/159
        #        audio-products-speakers/156
        #        battery-products/6                               # *items* < 0 => directory
        #        battery-products-accessories/87
        #        battery-products-batteries-non-rechargeable-primary/90
        #        battery-products-batteries-rechargeable-secondary/91
        #        battery-products-battery-chargers/85
        #        battery-products-battery-holders-clips-contacts/86
        #        battery-products-battery-packas/89
        #        battery-products-cigarette-ligheter-assemblies/88
        #        boxes-enclosures-rackes/27
        #        boxes-enclosures-rackes-backplanes/587
        #        ....
        #
        # We need to group all the entries that match "audio-products" together,
        # all the entries that matach *battery-products* together, etc.
        #
        # Drilling down another level, each *key* (i.e. '*base*/*nonce*') can have multiple
        # entries.  We scan through these entries to extract the information we want:
        #
        #     HRef[0]:key=''
        #      Match[0]: '', -1,
        #                 'See All', '',
        #                 'https://www.digikey.com/products/en/')
        #     HRef[1]:key='audio-products/10'
        #      Match[0]: 'audio-products', 10,
        #                 'Audio Products', '',
        #                 'https://www.digikey.com/products/en/audio-products/10')
        #      Match[1]: 'audio-products', 10,
        #                 'Audio Products', '',
        #                 'https://www.digikey.com/products/en/audio-products/10')
        #      Match[2]: 'audio-products', 10,
        #                 'Audio Products', '',
        #                 'https://www.digikey.com/products/en/audio-products/10')
        #      Match[3]: 'audio-products', 10,
        #                 'Audio Products', '',
        #                 'https://www.digikey.com/products/en/audio-products/10')
        #      Match[4]: 'audio-products', 10,
        #                 'Audio Products', '',
        #                 'https://www.digikey.com/products/en/audio-products/10')
        #      Match[5]: 'audio-products', 10,
        #                 '613 New Products', '',
        #                 'https://www.digikey.com/products/en/audio-products/10')
        #     HRef[2]:key='audio-products/accessories/159'
        #      Match[0]: 'audio-products-accessories', 159,
        #                 'Accessories', '',
        #                 'https://www.digikey.com/products/en/audio-products/accessories/159')
        #      Match[1]: 'audio-products-accessories', 159,
        #                 'Accessories', '(295 items)',
        #                 'https://www.digikey.com/products/en/audio-products/accessories/159')
        #     ...

        # Grab some values from *digikey* (i.e. *self*):
        digikey: Digikey = self
        bom_manager: BomManager = digikey.bom_manager
        collections_root_path: Path = digikey.root_path
        searches_root_path: Path = Path()  # TODO: Fixme:

        # Create the *collection*:
        collection: Collection = Collection(bom_manager, "Digi-Key",
                                            collections_root_path, searches_root_path)

        # Create the sorted *hrefs_table_keys*:
        hrefs_table_keys: List[Tuple[int, str]] = list(enumerate(sorted(hrefs_table.keys())))

        # Sweep through sorted *hrefs* and process each *matches* lists:
        tracing: str = tracing_get()
        current_directory: Optional[Directory] = None
        href_index: int
        hrefs_key: str
        trace_level: int = trace_level_get()
        for href_index, hrefs_key in hrefs_table_keys:
            matches: List[Match] = hrefs_table[hrefs_key]
            if tracing:
                print(f"{tracing}HRef[{href_index}]: '{hrefs_key}' len(matches)={len(matches)}")

            # There are one or more *matches*.  We'll take the first *a_content* that is non-null
            # and treat that as the *name*.  The number of *items* is taken from the first
            # *li_content* that end with " items)".  We visit *matches* in reverse order to work
            # around an obscure issue that is not worth describing.  If you feel like figuring it
            # out, please remove the call to `reversed()`:
            name: Optional[str] = None
            items: int = -1
            url: Optional[str] = None
            match_index: int
            match: Match
            for match_index, match in enumerate(reversed(sorted(matches, key=Match.key))):
                # Unpack *match*:
                if tracing and trace_level >= 2:
                    print(f"Match[{match_index}]: {match}")
                href: str = match.href
                base: str = match.base
                nonce: int = match.nonce
                a_content: str = match.a_content
                li_content: str = match.li_content
                url = match.url
                assert href == "" or href == hrefs_key, f"href='{href}' hrefs_key='{hrefs_key}'"

                # Fill in *name* and *items*:
                if name is None and not a_content.startswith("See"):
                    name = a_content.strip(" \t\n")
                    items_pattern: str = " items)"
                    if items < 0 and li_content.endswith(" items)"):
                        open_parenthesis_index: int = li_content.find('(')
                        items = int(li_content[open_parenthesis_index+1:-len(items_pattern)])
                    break

            # Dispatch based on *name* and *items*:
            if name is None:
                # We already created *root_directory* so there is nothing to do here:
                if tracing:
                    print(f"{tracing}name is None")
                pass
            elif items < 0:
                # We have a new *DigikeyDirectory* to create and make the *current_directory*.
                if tracing:
                    print(f"{tracing}new directory '{name}'")
                assert isinstance(url, str)
                current_directory = Directory(bom_manager, name, url, nonce)
                assert isinstance(current_directory, Directory)
                collection.directory_insert(current_directory)
            else:
                # We create a new *DigikeyTable* that is appended to *current_directory*.
                # Note: the initializer automatically appends *table* to *current_directory*:
                assert current_directory is not None
                assert isinstance(url, str)
                collection_key: Tuple[int, int] = (-1, -1)
                table: Table = Table(bom_manager, name, collection_key, url, nonce, base)
                current_directory.table_insert(table)

        # *collection* is in its first incarnation and ready for reorganization:
        return collection

    # Digikey.collection_reorganize():
    # @trace(1)
    def collection_reorganize(self, collection: Collection) -> None:
        """Recursively reorganize a collection.

        The catagory organziation from the Digi-Key web site has a bunch
        of tables that should be grouped into a sub-table.  This code
        recusively analyizes *collection*, finds those grouping, and
        restructures the collection to have those sub-directories.

        Args:
            *collection* (*Collection*): The *collection* to
                reorganize.

        """
        # Use *digikey* instead of *self*:
        digikey: Digikey = self
        tracing: str = tracing_get()

        # Extract a sorted list of *directories* from *collection*:
        directories: List[Directory] = collection.directories_get(True)

        # Sweep though the *directoires* of *collection*:
        directory_index: int
        directory: Directory
        for directory_index, directory in enumerate(directories):
            if tracing:  # pragma: no cover
                print(f"Directory[{directory_index}]: '{directory.name}'")
            digikey.directory_reorganize(directory)

    # Digikey.collection_verify():
    # @trace(1)
    def collection_verify(self, collection: Collection,
                          hrefs_table: Dict[str, List[Match]]) -> None:
        """Verify that collection reorganization worked.

        The *Digikey.collection_reorganize*() method is sufficiently
        complicated that it is useful to do a sanity check to ensure
        that no tables got lost.

        Args:
            *collection* (*Collection*): The collection to verify
            *hrefs_table* (*Dict*[*str*, *List*[*Match*]]): The
                hrefs table that lists each table.
        """
        # Recursively grab all of the *directories* from *collection* and compute
        # *directories_size*:
        directory_nodes: List[Node] = list()
        collection.nodes_collect_recursively(Directory, directory_nodes)
        directory_node: Node
        directories: List[Directory] = [directory_node.directory_cast()
                                        for directory_node in directory_nodes]
        directories_size = len(directories)

        # Recursively grab all of the *tables* from *collection* and compute *tables_size*:
        table_nodes: List[Node] = list()
        collection.nodes_collect_recursively(Table, table_nodes)
        table_node: Node
        tables: List[Table] = [table_node.table_cast() for table_node in table_nodes]
        tables_size = len(tables)

        # Compute the number of values in *hrefs_table*:
        hrefs_table_size: int = len(hrefs_table)

        # Perform any requested *tracing*:
        tracing: str = tracing_get()
        if tracing:  # pragma: no cover
            print(f"{tracing}directories_size={directories_size}")
            print(f"{tracing}tables_size={tables_size}")
            print(f"{tracing}hrefs_table_size={hrefs_table_size}")

        # If the various sizes do not match exactly, we have a bug and do some debugging code:
        if hrefs_table_size != directories_size + tables_size:
            # We failed to match, so we start by making a *hrefs_table_copy*:
            hrefs_table_copy: Dict[str, List[Match]] = hrefs_table.copy()

            # Remove all of the *tables* from *hrefs_table_copy*:
            errors: int = 0
            url_prefix: str = "https://www.digikey.com/products/en/"
            url_prefix_size: int = len(url_prefix)
            table: Table
            for table in tables:
                table_key: str = table.url[url_prefix_size:]
                if table_key in hrefs_table_copy:
                    del hrefs_table_copy[table_key]
                else:
                    errors += 1
                    print(f"{tracing}table_key='{table_key}' not found")

            # Remove all of the *directories* from * *hrefs_table_copy*:
            directory: Directory
            for directory in directories:
                directory_key: str = directory.url[url_prefix_size:]
                if directory_key in hrefs_table_copy:
                    del hrefs_table_copy[directory_key]
                else:
                    errors += 1
                    print(f"{tracing}directory_key='{directory_key}' not found")

            # Print out the remaining unumatched keys:
            print(f"{tracing}hrefs_table_copy.keys={list(hrefs_table_copy.keys())}")

            # Now we can fail:
            assert errors == 0, f"{errors} Error found"

    # # Digikey.collection_csvs_download():
    # def collection_csvs_download(self, collection: Collection) -> int:
    #     # Grab the *csvs_directory* from *digikey* (i.e. *self*):
    #     digikey: Digikey = self
    #     bom_manager: BomManager = digikey.bom_manager
    #     root_path: Path = digikey.root_path
    #
    #     # Create *digikey_collection_file_name* (hint: it is simply "Digikey"):
    #     collection_name: str = collection.name
    #     to_file_name: Callable[[str], str] = bom_manager.to_file_name
    #     collection_file_name = to_file_name(collection_name)
    #
    #     # Create the *collection_root_path* which is an extra directory with
    #     # the collection name.  This is consistent with the organization of the
    #     # searches directories, where first directies specify a collection name:
    #     collection_root_path: Path = root_path / collection_file_name
    #
    #     # Fetch example `.csv` files for each table in *collection*:
    #     downloads_count: int = 0
    #     directories: List[Directory] = collection.directories_get(True)
    #     directory: Directory
    #     for directory in directories:
    #         # Create the *from_root_path* to the corresponding *directory* location
    #         # in the file system:
    #         directory_name: str = directory.name
    #         directory_file_name: str = to_file_name(directory_name)
    #         from_root_path: Path = collection_root_path / directory_file_name

    #         # Now recursively visit each of the *digikey_directory*:
    #         downloads_count += digikey.directory_csvs_download(directory,
    #                                                            from_root_path, downloads_count)
    #     return downloads_count

    # Digikey.csv_fetch():
    # @trace(1)
    # def csv_fetch(self, search_url: str, csv_file_name: str) -> bool:
    #     # Construct the header values that need to be sent with the *search_url*:
    #     authority_text: str = "www.digikey.com"
    #     accept_text: str = (
    #         "text/html,application/xhtml+xml,application/xml;"
    #         "q=0.9,image/webp,image/apng,*/*;"
    #         "q=0.8,application/signed-exchange;"
    #         "v=b3"
    #     )
    #     accept_encoding_text: str = "gzip, deflate, br"
    #     cookie_text: str = (
    #         "i10c.bdddb=c2-f0103ZLNqAeI3BH6yYOfG7TZlRtCrMwzKDQfPMtvESnCuVjBtyWjJ1l"
    #         "kqXtKsvswxDrjRHdkESNCtx04RiOfGqfIlRUHqt1qPnlkPolfJSiIRsomx0RhMqeKlRtT3"
    #         "jxvKEOjKMDfJSvUoxo6uXWaGVZkqoAhloxqQlofPwYkJcS6fhQ6tzOgotZkQMtHDyjnA4lk"
    #         "PHeIKNnroxoY8XJKBvefrzwFru4qPnlkPglfJSiIRvjBTuTfbEZkqMupstsvz8qkl7wWr3i"
    #         "HtspjsuTFBve9SHoHqjyTKIPfPM3uiiAioxo6uXOfGvdfq4tFloxqPnlkPcxyESnCuVjBt1"
    #         "VmBvHmsYoHqjxVKDq3fhvfJSiIRsoBsxOftucfqRoMRjxVKDq3BuEMuNnHoyM9oz3aGv4ul"
    #         "RtCrMsvP8tJOPeoESNGw2q6tZSiN2ZkQQxHxjxVOHukKMDjOQlCtXnGt4OfqujoqMtrpt3y"
    #         "KDQjVMffM3iHtsolozT7WqeklSRGloXqPDHZHCUfJSiIRvjBTuTfQeKKYMtHlpVtKDQfPM2"
    #         "uESnCuVm6tZOfGK1fqRoIOjxvKDrfQvYkvNnuJsojozTaLW"
    #     )

    #     # Construct *headers*:
    #     headers: Dict[str, str] = {
    #         "authority": authority_text,
    #         "accept": accept_text,
    #         "accept-encoding": accept_encoding_text,
    #         "cookie": cookie_text
    #     }

    #     # Attempt the fetch the contents of *search_url* using *headers*:
    #     try:
    #         response: requests.Response = requests.get(search_url, headers=headers)
    #         response.raise_for_status()
    #     except requests.exceptions.HTTPError as http_error:
    #         assert False, f"HTTP error occurred '{http_error}'"
    #     except Exception as error:
    #         assert False, f"Other exception occurred: '{error}'"

    #     # Now parse the resulting *html_text* using a *soup* to find the *csv_url*:
    #     html_text: str = str(response.content)

    #     soup: Optional[BeautifulSoup] = BeautifulSoup(html_text, features="lxml")
    #     assert soup is not None
    #     tracing: str = tracing_get()
    #     # print(f"{tracing}type(soup)=", type(soup))
    #     pairs: List[str] = []
    #     pairs_text: Optional[str] = None
    #     if tracing:
    #         print(f"{tracing}here 2b")
    #     formtag: Element.Tag
    #     for form_tag in soup.find_all("form"):
    #         name: str = form_tag.get("name")
    #         if name == "downloadform":
    #             # We found it:
    #             if tracing:
    #                 print(f"{tracing}form_tag={form_tag}")
    #             index: int
    #             input_tag: Element.Tag
    #             for index, input_tag in enumerate(form_tag.children):
    #                 # print(input_tag)
    #                 input_tag_name: Optional[str] = input_tag.name
    #                 if isinstance(input_tag_name, str) and input_tag_name.lower() == "input":
    #                     input_name: str = input_tag.get("name")
    #                     input_value: str = input_tag.get("value")
    #                     input_value = input_value.replace(",", "%2C")
    #                     input_value = input_value.replace('|', "%7C")
    #                     input_value = input_value.replace(' ', "+")
    #                     pair: str = f"{input_name}={input_value}"
    #                     if tracing:
    #                         print(f"{tracing}input_name='{input_name}'")
    #                         print(f"{tracing}input_value='{input_value}'")
    #                         print(f"{tracing}pair='{pair}'")
    #                     pairs.append(pair)
    #             pairs_text = '&'.join(pairs)
    #             if tracing:
    #                 print(f"{tracing}pairs_text='{pairs_text}'")
    #     assert isinstance(pairs_text, str)

    #     # Construct the *csv_url*:
    #     csv_url: str = "https://www.digikey.com/product-search/download.csv?" + pairs_text
    #     if tracing:
    #         print(f"{tracing}csv_url='{csv_url}'")

    #     # Construct the text strings fort the *headers*:
    #     authority_text = "www.digikey.com"
    #     accept_text = (
    #         "text/html,application/xhtml+xml,application/xml;"
    #         "q=0.9,image/webp,image/apng,*/*;"
    #         "q=0.8,application/signed-exchange;"
    #         "v=b3"
    #     )
    #     accept_encoding_text = "gzip, deflate, br"
    #     cookie_text = (
    #         "i10c.bdddb="
    #         "c2-94990ugmJW7kVZcVNxn4faE4FqDhn8MKnfIFvs7GjpBeKHE8KVv5aK34FQDgF"
    #         "PFsXXF9jma8opCeDMnVIOKCaK34GOHjEJSFoCA9oxF4ir7hqL8asJs4nXy9FlJEI"
    #         "8MujcFW5Bx9imDEGHDADOsEK9ptrlIgAEuIjcp4olPJUjxXDMDVJwtzfuy9FDXE5"
    #         "sHKoXGhrj3FpmCGDMDuQJs4aLb7AqsbFDhdjcF4pJ4EdrmbIMZLbAQfaK34GOHbF"
    #         "nHKo1rzjl24jP7lrHDaiYHK2ly9FlJEADMKpXFmomx9imCGDMDqccn4fF4hAqIgF"
    #         "JHKRcFFjl24iR7gIfTvaJs4aLb4FqHfADzJnXF9jqd4iR7gIfz8t0TzfKyAnpDgp"
    #         "8MKEmA9og3hdrCbLvCdJSn4FJ6EFlIGEHKOjcp8sm14iRBkMT8asNwBmF3jEvJfA"
    #         "DwJtgD4oL1Eps7gsLJaKJvfaK34FQDgFfcFocAAMr27pmCGDMD17GivaK34GOGbF"
    #         "nHKomypOTx9imDEGHDADOsTpF39ArqeADwFoceWjl24jP7gIHDbDPRzfwy9JlIlA"
    #         "DTFocAEP"
    #     )

    #     # Construct *headers*:
    #     headers = {
    #         "authority": authority_text,
    #         "accept": accept_text,
    #         "accept-encoding": accept_encoding_text,
    #         "cookie": cookie_text
    #     }

    #     # Attempt the fetch the contents of *csv_fetch_url* using *headers*:
    #     if tracing:
    #         print(f"{tracing}A:Fetching '{csv_url}' extracted '{search_url}' contents:")
    #     try:
    #         response = requests.get(csv_url, headers=headers)
    #         response.raise_for_status()
    #     except requests.exceptions.HTTPError as http_error:
    #         assert False, f"HTTP error occurred '{http_error}'"
    #     except Exception as error:
    #         assert False, f"Other exception occurred: '{error}'"

    #     # Now write *csv_text* out to *csv_file_name*:
    #     csv_text: str = str(response.content)
    #     csv_file: TextIO
    #     with open(csv_file_name, "w") as csv_file:
    #         csv_file.write(csv_text)
    #     if tracing:
    #         print(f"{tracing}Wrote out '{csv_file_name}'")

    #     # Wrap up any requested *tracing* and return *result*;
    #     result: bool = True
    #     return result

    # Digikey.directory_reorganize():
    @trace(1)
    def directory_reorganize(self, directory: Directory) -> None:
        # This lovely piece of code takes a *Directory* and attempts
        # to further partition it into some smaller directories.

        # A *title* can be of form:
        #
        #        "Level 1 Only"
        #        "Level 1 - Level 2"
        #        "Level 1 - Level 2 - Level 3"
        #        ...
        # This routine finds all *title*'s that have the initial " - " and rearranges the
        # *digikey_directory* so that all the tables that have the same "Level 1" prefix
        # in their *title* are grouped together.

        # Step 1: The first step is to build *groups_table* than is a table that contains a list
        # of "Level 1" keys with a list of *DigikeyTable*'s as the value.  Thus,
        #
        #        "Level 1a"
        #        "Level 1b - Level2a"
        #        "Level 1c - Level2b"
        #        "Level 1c - Level2c"
        #        "Level 1d"
        #        "Level 1e - Level2d"
        #        "Level 1e - Level2e"
        #        "Level 1e - Level2f"
        #        "Level 1e
        #
        # Will basically generate the following table:
        #
        #        {"Level 1b": ["Level2a"]
        #         "Level 1c": ["Level2b", "Level2c"],
        #         "Level 1e": ["Level2d", "Level2e", "Level2f"}
        #
        # Where the lists actually contain the appropriate *DigikeyTable* objects rather
        # than simple strings.  Notice that we throw the "Level 1b" entry out since it
        # only has one match.  This operation takes place in Step3.

        # Start with *digikey_directory* (i.e. *self*) and construct *groups_table*
        # by scanning through *children*:
        digikey: Digikey = self
        bom_manager: BomManager = digikey.bom_manager
        # name: str = digikey_directory.name
        groups_table: Dict[str, List[Table]] = dict()
        tables: List[Table] = directory.tables_get(True)
        table_index: int
        table: Table
        tracing: str = tracing_get()
        for table_index, table in enumerate(tables):
            # Grab some values from *digikey_table*:
            name: str = table.name
            nonce: int = table.nonce
            base: str = table.base
            url: str = table.url

            # Search for the first " - " in *name*.:
            hypen_index: int = name.find(" - ")
            if hypen_index >= 0:
                # We found "Level1 - ...", so split it into *group_name* (i.e. "Level1")
                # and *sub_group_name* (i.e. "...")
                group_name: str = name[:hypen_index].strip()
                sub_group_name: str = name[hypen_index+3:].strip()
                if tracing:
                    print(f"{tracing}[{table_index}]:"
                          f"'{name}'=>'{group_name}'/'{sub_group_name}")

                # Load *group_title* into *groups_table* and make sure we have a *tables_list*
                # in there:
                if group_name in groups_table:
                    tables_list = groups_table[group_name]
                else:
                    tables_list = list()
                    groups_table[group_name] = tables_list

                # Finally, tack *table* onto *tables_list*:
                tables_list.append(table)

        # This deals with a fairly obscure case where it is possible to have both a table and
        # directory with the same name.  This is called the table/directory match problem.
        # An example would help:
        #
        #        Fiber Optic Connectors
        #        Fiber Optic Connectors - Accessories
        #        Fiber Optic Connectors - Contacts
        #        Fiber Optic Connectors - Housings
        #
        # Conceptually, we want to change the first line to "Fiber Optic_Connectors - Others".
        # The code does this by finding the table, and just adding it to the appropriate
        # group list in *groups_table*.  Later below, we detect that there is no hypen in the
        # title and magically add " - Others" to the title.  Yes, this is obscure:
        tables = directory.tables_get(True)
        for table in tables:
            table_name: str = table.name
            if table_name in groups_table:
                tables_list = groups_table[table_name]
                tables_list.append(table)
                # print("Print '{0}' is a table/directory matach".format(table_title))

        # Ignore any *group_title* that only has one match (i.e *len(tables_list)* <= 1):
        group_titles_to_delete = list()
        for group_title, tables_list in groups_table.items():
            if len(tables_list) <= 1:
                # print("groups_table['{0}'] only has one match; delete it".format(group_title))
                group_titles_to_delete.append(group_title)
        for group_title in group_titles_to_delete:
            del groups_table[group_title]

        # Now sweep through *digikey_directory* deleting the *tables* that are going to
        # be reinserted in the *sub_directories*:
        for group_title, tables_list in groups_table.items():
            for table_index, table in enumerate(tables_list):
                directory.remove(table)

        # Now create a *sub_directory* for each *group_title* in *groups_table*:
        for index, group_name in enumerate(sorted(groups_table.keys())):
            tables_list = groups_table[group_name]
            # Convert *group_title* to *directory_name*:
            # directory_name = digikey_directory.title2file_name(group_title)
            # print("  Group_Title[{0}]'{1}':".format(group_title_index, group_title))

            # Create the *sub_directory*:
            # sub_directory_path = digikey_directory.path + "/" + directory_name
            sub_directory: Directory = Directory(bom_manager, group_name, nonce, url)
            directory.node_insert(sub_directory)
            # Note: *DigikeyDirectory()* automatically appends to the
            # *digikey_directory* parent:

            # Now create a new *sub_table* for each *table* in *tables_list*:
            tables_list.sort(key=lambda table: table.name)
            for table_index, table in enumerate(tables_list):
                assert isinstance(table, Table)

                # Extract the *sub_group_title* again:
                name = table.name
                hyphen_index = name.find(" - ")

                # When *hyphen_index* is < 0, we are dealing with table/directory match problem
                # (see above); otherwise, just grab the stuff to the right of the hyphen:
                if hyphen_index >= 0:
                    # sub_group_title = name[hyphen_index+3:].strip()
                    pass
                else:
                    # sub_group_title = "Others"
                    # print("  Creating 'Others' title for group '{0}'".format(title))
                    pass

                # Create the new *sub_table*:
                # path = sub_directory_path
                # url = table.url
                collection_key: Tuple[int, int] = (-1, -1)
                table = Table(bom_manager, name, collection_key, url, nonce, base)
                sub_directory.table_insert(table)

            # Sort *sub_directory* just for fun.  It probably does not do much of anything:
            # sub_directory.sort(lambda title: title.name)

        # Again, sort *digikey_directory* even though it is unlikely to change anything:
        # digikey_directory.sort(lambda table: table.name)
        # digikey_directory.show("  ")

    @staticmethod
    # Digikey.hrefs_table_show():
    def hrefs_table_show(hrefs_table: Dict[str, List[Match]], limit: int) -> None:
        # Iterate over a sorted *hrefs_table_keys*:
        hrefs_table_keys: List[str] = sorted(hrefs_table.keys())
        index: int
        hrefs_table_key: str
        tracing: str = tracing_get()
        for index, hrefs_table_key in enumerate(hrefs_table_keys):
            matches: List[Match] = hrefs_table[hrefs_table_key]
            print(f"{tracing}HRef[{index}]:key='{hrefs_table_key}'")
            match_index: int
            match: Match
            for match_index, match in enumerate(matches):
                # Unpack *match*:
                href: str = match.href
                base: str = match.base
                nonce: int = match.nonce
                a_content: str = match.a_content
                li_content: str = match.li_content
                url: str = match.url
                print(f"{tracing} Match[{match_index}]: '{href}', '{base}', {nonce},")
                print(f"{tracing}            '{a_content}', '{li_content}',")
                print(f"{tracing}            '{url}')")
            if index >= limit:
                break

    # Digikey.process():
    # @trace(1)
    def process(self) -> None:
        """Read in the example `.csv` files for each collection table.

        The top level products HTML page at
        `https://www.digikey.com/products/en` is parsed to identify the
        overall structure of the collection.  If the require directories
        and sub-directories do not exist, they are created.  Each table
        has an associated `.csv` file and `.xml` file stored in the
        directory structure.  The `.csv` file contains a partial list of
        the parts associated with the the table.  If this file is not
        present in the directory structure, it is downloaded and stored
        into the data structure.  After that, all of the `.csv` files
        are analyzed to guess column types.  The result of the analysis
        is the table `.xml` file that is stored into the directory
        structure.
        """
        # Grab some values from *digikey*:
        digikey: Digikey = self
        tracing: str = tracing_get()

        # Read the `.html` file that contains the top level origanziation and convert it
        # into a Beautiful *soup* tree:
        beautiful_soup: BeautifulSoup = digikey.soup_read()

        # Sweep through the *soup* tree and get href information stuffed into *href_tables*:
        hrefs_table: Dict[str, List[Match]] = digikey.soup_extract(beautiful_soup)

        # Sweep of the data stored in *href_tables* to construct the initial organization
        # of the *collection*:
        if tracing:
            print(f"{tracing}***************************************************************")
        collection: Collection = digikey.collection_extract(hrefs_table)

        # Set to *True* to perform a *show_lines*:
        if False:
            show_lines: List[str] = list()
            collection.show_lines_append(show_lines, "")
            show_lines.append("")
            show_lines_text = "\n".join(show_lines)
            print(show_lines_text)

        # Perform a verification step to see if we screwed up:
        digikey.collection_verify(collection, hrefs_table)

        # Reorganize the *collection* to have a little better structure than what is
        # provided by the Digikey site:
        digikey.collection_reorganize(collection)

        # Make sure we have an example `.csv` file for each table in *digikey_collection*:
        if tracing:
            print(f"{tracing}&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&")
        root_path: Path = digikey.root_path
        downloads_count: int = collection.csvs_download(root_path, Digikey.csv_fetch)
        if tracing:
            print(f"{tracing}downloads_count={downloads_count}")

        # Perform the analysis of the `.csv` files and generate the table `.xml` files:
        if tracing:
            print(f"{tracing}================================================================")
        collection.csvs_read_and_process(True)

    # Digikey.soup_extract():
    def soup_extract(self, beautiful_soup: BeautifulSoup) -> Dict[str, List[Match]]:
        # Now we use the *bs4* module to screen scrape the information we want from *soup*.
        # We are interested in sections of HTML that looks as follows:
        #
        #        <LI>
        #            <A class="..." href="*href*">
        #                *a_content*
        #            </A>
        #          *li_content*
        #        </LI>
        #
        # where:
        #
        # * *href*: is a hypertext link reference of the form:
        #
        #        /products/en/*base*/*nonce*?*search*
        #
        #   * "*?search*": *?search* is some optional search arguments that can safely be ignored.
        #   * "*nonce*": *nonce* is a decimal number that is 1-to-1 with the *base*.  The *nonce*
        #     is used by Digikey for specifying were to start.  When the *href* specifies a
        #     directory this is simply not present.
        #   * "*base*": *base* is a hyphen separeted list of words (i.e. "audio-products",
        #     "audio_products-speakers", etc.)  Note: most of the words are lower case, but
        #     there are a few that are mixed upper/lower case.
        #   * The prefix "/products/en" is present for each *href* and can be ignored.
        #
        # * *a_content*: *a_content* is the human readable name for the *href* and is typically
        #   of the form "Audio Products", "Audio Products - Speakers", etc.  This is typically
        #   considerd to be the *title* of the table or directory.
        #
        # * *li_content*: *li_content* is frequently empty, but sometimes specifies the
        #   number of items in the associated table.  It is of the form "(*items* Items)"
        #   where *items* is a decimal number.  We only care about the decimal number.
        #
        # The output of scanning the *soup* is *hrefs_table*, which is a list *matches*, where the
        # each *Match* is a 6-tuple containing:
        #
        #    (*href*, *base*, *nonce*, *a_content_text*, *li_content_text*, *url*)
        #
        # *nonce* is -1 if there was no "/*nonce*" present in the *href*.

        # print("  =>Digikey.soup_extract(...)")

        # Start with an empty *hrefs_table*:
        hrefs_table: Dict[str, List[Match]] = dict()
        url_prefix: str = "/products/en/"
        url_prefix_size: int = len(url_prefix)
        match: Match
        matches: List[Match]

        # Find all of the <A HRef="..."> tags in *soup*:
        a: Element
        for a in beautiful_soup.find_all("a"):
            # We are only interested in *href*'s that start with *url_prefix*:
            href: Optional[str] = a.get("href")
            if href is not None and href.startswith(url_prefix) and href != url_prefix:
                # Strip off the "?*search" from *href*:
                question_mark_index: int = href.find('?')
                if question_mark_index >= 0:
                    href = href[:question_mark_index]

                # Strip the *url_prefix* from the beginning of *href*:
                href = href[url_prefix_size:]

                # Split out the *base* and *nonce* (if it exists):
                # print("href3='{0}'".format(href))
                slash_index: int = href.rfind('/')
                base: str
                nonce: int = -1
                if slash_index >= 0:
                    # *nonce* exists, so store it as a positive integer:
                    base = href[:slash_index].replace('/', '-')
                    # print("href[slash_index+1:]='{0}'".format(href[slash_index+1:]))
                    nonce = int(href[slash_index+1:])
                else:
                    # *nonce* does not exist, so store -1 into *nonce*:
                    base = href
                    nonce = -1

                # Construct *a_contents_text* from the contents of *a* tag.  In general this
                # text is a reasonable human readable summary of what the table/directory is about:
                a_contents_text: str = ""
                a_content: Element
                for a_content in a.contents:
                    if isinstance(a_content, Element.NavigableString):
                        a_contents_text += a_content.string
                a_contents_text = a_contents_text.strip()

                # Construct the *li* content which is the text between the end of the </A>
                # tag and the </LI> tag.  In general, we only care if there is a class
                # attribute in the <A> tag (i.e. <A class="..." href="...".)
                # Sometimes the <A> tag is nested in an <LI> tag.  This text when present
                # will frequently have the basic form of "...(*items* items)...".
                li_contents_text: str = ""
                xclass: Element.Tag = a.get("class")
                if xclass is not None:
                    # We have a `class="..."` attribute, so now look for the *parent* *li* tag:
                    parent: bs4.element = a.parent
                    assert isinstance(parent, Element.Tag)
                    if parent.name == "li":
                        # We have an *li* tag, so extract its contents into *li_contents_text*:
                        li_contents: bs4.element = parent.contents
                        li_content: bs4.element.NavigableString
                        for li_content in li_contents:
                            if isinstance(li_content, Element.NavigableString):
                                li_contents_text += li_content.string
                        li_contents_text = li_contents_text.strip()

                # Now stuff *base*, *nonce*, *a_contents_text*, *li_contents_text*, and *url*
                # into *hrefs_table* using *href* as the key.  Since same *href* can occur multiple
                # times in the *soup* we store everything in a the *matches* list containing
                # a *match* of 5-tuples:
                # href_key = f"{base}/{nonce}"
                if href in hrefs_table:
                    matches = hrefs_table[href]
                else:
                    matches = list()
                    hrefs_table[href] = matches
                url: str = "https://www.digikey.com/products/en/" + href
                # if base.startswith("capacitors"):
                #     print("url='{0}'".format(url))
                match = Match(href, base, nonce, a_contents_text, li_contents_text, url)
                matches.append(match)
        # We are done scraping information out of the the *soup*.  Everything we need is
        # now in *hrefs_table*.
        # print("  <=Digikey.soup_extract(...)")

        return hrefs_table

    # Digikey.soup_read():
    def soup_read(self) -> BeautifulSoup:
        # Read in the *digikey_product_html_file_name* file into *html_text*.  This
        # file is obtained by going to `https://www.digkey.com/` and clickd on the
        # `[View All]` link next to `Products`.  This page is saved from the web browser
        # in the file named *digikey_product_html_file_name*:

        # Grab some values from *digikey* (i.e. *self*):
        digikey: Digikey = self
        products_html_path: Path = digikey.products_html_path

        # Read *products_html_file_name* in and convert it into *soup*:
        html_file: IO[Any]
        soup: Optional[BeautifulSoup] = None
        with products_html_path.open() as html_file:
            html_text: str = html_file.read()

            # Parse *html_text* into a *soup*:
            soup = BeautifulSoup(html_text, features="lxml")

            # To aid in reading the HTML, write the *soup* back out to the `/tmp` directory
            # in a prettified form:
            prettified_html_file_name: str = "/tmp/prettified.html"
            with open(prettified_html_file_name, "w") as html_file:
                html_file.write(soup.prettify())
        assert isinstance(soup, BeautifulSoup)
        return soup

    # Digikey.csv_fetch():
    @staticmethod
    def csv_fetch(table: Table, csv_path: Path, downloads_count: int) -> int:
        """TODO"""
        # Grab some values from *digikey_table* (i.e. *self*):
        name: str = table.name
        nonce: int = table.nonce
        fv: str = f"-8|{nonce}"
        tracing: str = tracing_get()
        if tracing:
            print(f"{tracing}name='{name}'")
            print(f"{tracing}nonce='{nonce}'")
            print(f"{tracing}fv='{fv}'")
        print(f"Downloading '{csv_path}'")

        # Compute the *url*, *parameters*, and *headers* needed for the *request*:
        url: str = "https://www.digikey.com/product-search/download.csv"
        parameters: Dict[str, str] = {
            "FV": fv,
            "quantity": "0",
            "ColumnSort": "0",
            "page": "1",
            "pageSize": "500"
        }
        headers: Dict[str, str] = {
            "authority": "www.digikey.com",
            "accept-encoding": "gzip, deflate, br",
            "cookie": ("i10c.bdddb="
                       "c2-94990ugmJW7kVZcVNxn4faE4FqDhn8MKnfIFvs7GjpBeKHE8KVv5aK34FQDgF"
                       "PFsXXF9jma8opCeDMnVIOKCaK34GOHjEJSFoCA9oxF4ir7hqL8asJs4nXy9FlJEI"
                       "8MujcFW5Bx9imDEGHDADOsEK9ptrlIgAEuIjcp4olPJUjxXDMDVJwtzfuy9FDXE5"
                       "sHKoXGhrj3FpmCGDMDuQJs4aLb7AqsbFDhdjcF4pJ4EdrmbIMZLbAQfaK34GOHbF"
                       "nHKo1rzjl24jP7lrHDaiYHK2ly9FlJEADMKpXFmomx9imCGDMDqccn4fF4hAqIgF"
                       "JHKRcFFjl24iR7gIfTvaJs4aLb4FqHfADzJnXF9jqd4iR7gIfz8t0TzfKyAnpDgp"
                       "8MKEmA9og3hdrCbLvCdJSn4FJ6EFlIGEHKOjcp8sm14iRBkMT8asNwBmF3jEvJfA"
                       "DwJtgD4oL1Eps7gsLJaKJvfaK34FQDgFfcFocAAMr27pmCGDMD17GivaK34GOGbF"
                       "nHKomypOTx9imDEGHDADOsTpF39ArqeADwFoceWjl24jP7gIHDbDPRzfwy9JlIlA"
                       "DTFocAEP"),
            "upgrade-insecure-requests": "1",
            "accept": ("text/html,application/xhtml+xml,application/xml;"
                       "q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3"),
            "sec-fetch-user": "?1",
            "sec-fetch-mode": "navigate",
            "accept-language": "en-US,en;q=0.9",
            }

        # Perform the download:
        if tracing:
            print(f"{tracing}Fetching the '{name}':{nonce}")
        response: requests.Response = requests.get(url, params=parameters, headers=headers)
        if tracing:
            print(f"{tracing}response.headers={response.headers}")
            print(f"{tracing}response.content='{response.content}")
            print(f"{tracing}response.encoding='{response.encoding}")
        csv_content: str = response.text
        # print(csv_content)
        # if tracing:
        #     print(csv_content)

        # First, make sure that the *csv_path_path* directory exists, than write the
        # *csv_content* out to the *csv_path* file:
        if tracing:
            print(f"{tracing}Write out fetched .csv file out to '{csv_path}'.")
        csv_path_parent: Path = csv_path.parent
        csv_path_parent.mkdir(parents=True, exist_ok=True)
        csv_path.write_text(csv_content)

        downloads_count += 1
        return downloads_count


if __name__ == "__main__":
    main()
