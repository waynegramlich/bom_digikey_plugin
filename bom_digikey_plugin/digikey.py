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
from bom_manager import bom
from bom_manager.tracing import trace, trace_level_set, tracing_get
import bs4   # type: ignore
import glob
import os
import requests
import time
from typing import Any, Dict, List, Optional, TextIO, Tuple, Union
Match = Tuple[str, str, int, str, str, str]


# main():
def main() -> int:
    # Create the *digikey* object and process it:

    # Parse the command line:
    parser: ArgumentParser = ArgumentParser(description="Digi-Key Collection Constructor.")
    parser.add_argument("-v", "--verbose", action="count",
                        help="Set tracing level (defaults to 0 which is off).")
    parsed_arguments: Dict[str, Any] = vars(parser.parse_args())
    verbose_count: int = 0 if parsed_arguments["verbose"] is None else parsed_arguments["verbose"]
    trace_level_set(verbose_count)

    gui: bom.Gui = bom.Gui()
    digikey: Digikey = Digikey()
    digikey.process(gui)
    result: int = 0
    return result


# Is this used any more??!!!
# url_load():
@trace(1)
def collection_get(collections: bom.Collections, searches_root: str,
                   gui: bom.Gui) -> "DigikeyCollection":
    digikey_collection: DigikeyCollection = DigikeyCollection(collections, searches_root, gui)
    return digikey_collection


# Digikey:
class Digikey:

    # Digikey.__init__():
    @trace(1)
    def __init__(self) -> None:
        # Extract the *digikey_package_directory* name:
        #  top_directory = "/home/wayne/public_html/projects/bom_digikey_plugin"
        digikey_py_file_name = __file__
        tracing: str = tracing_get()
        if tracing:
            print(f"{tracing}__file__='{__file__}'")
        assert digikey_py_file_name.endswith("digikey.py")
        digikey_package_directory: str = os.path.split(digikey_py_file_name)[0]
        init_py_file_name: str = os.path.join(digikey_package_directory, "__init__.py")
        if tracing:
            print(f"{tracing}digikey_py_file_name='{digikey_py_file_name}'")
            print(f"{tracing}digikey_package_directory='{digikey_package_directory}'")
            print(f"{tracing}init_py_file_name='{init_py_file_name}'")

        # Compute the various needed directory and file names:
        assert os.path.isfile(init_py_file_name)
        root_directory: str = os.path.join(digikey_package_directory, "ROOT")
        # csvs_directory: str = os.path.join(digikey_package_directory, "CSVS")
        csvs_directory: str = "/home/wayne/public_html/projects/bom_digikey_plugin/CSVS"
        miscellaneous_directory: str = os.path.join(digikey_package_directory, "MISC")
        products_html_file_name: str = os.path.join(miscellaneous_directory,
                                                    "www.digikey.com_products_en.html")
        if tracing:
            print(f"{tracing}root_directory='{root_directory}'")
            print(f"{tracing}csvs_directory='{csvs_directory}'")
            print(f"{tracing}products_html_file_name='{products_html_file_name}'")

        # Make sure everything exists:
        assert os.path.isdir(root_directory)
        assert os.path.isdir(miscellaneous_directory)
        assert os.path.isfile(products_html_file_name)

        # If *csvs_directory* does not exits, create it:
        if not os.path.isdir(csvs_directory):
            os.makedirs(csvs_directory)

        # Stuff various file names into *digikey* (i.e. *self*):
        # digikey = self
        self.products_html_file_name: str = products_html_file_name
        self.root_directory: str = root_directory
        self.csvs_directory: str = csvs_directory

    # Digikey.__str__():
    def __str__(self):
        return "Digikey()"

    # Digikey.collection_extract():
    def collection_extract(self, hrefs_table: Dict[str, List[Match]]) -> bom.Collection:
        # Now we construct *collection* which is a *bom.Collection* that contains a list of
        # *DigkeyDirectory*'s (which are sub-classed from *bom.Directory*.  Each of those
        # nested *DigikeyDirectory*'s contains a further list of *DigikeyTable*'s.
        #

        # The sorted keys from *hrefs_table* are alphabetized by '*base*/*id*' an look basically
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
        # Drilling down another level, each *key* (i.e. '*base*/*id*') can have multiple
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
        root_directory: str = digikey.root_directory
        searches_root: str = ""
        gui: bom.Gui = bom.Gui()

        # Create the *collection* (*collections* is temporary and is not really used):
        collection_directories: List[str] = list()
        partial_load: bool = False
        collections: bom.Collections = bom.Collections("Collections", collection_directories,
                                                       searches_root, partial_load, gui)
        collection: bom.Collection = bom.Collection("Digi-Key", collections, root_directory,
                                                    searches_root, gui)
        # parent = collection
        assert collections.has_child(collection)

        # Create the sorted *hrefs_table_keys*.  The first 20 entries look like:
        hrefs_table_keys: List[Tuple[int, str]] = list(enumerate(sorted(hrefs_table.keys())))

        # Sweep through sorted *hrefs* and process each *matches* lists:
        current_directory: Optional[DigikeyDirectory] = None
        href_index: int
        hrefs_key: str
        tracing: str = tracing_get()
        for href_index, hrefs_key in hrefs_table_keys:
            matches: List[Match] = hrefs_table[hrefs_key]
            if tracing:
                print(f"{tracing}HRef[{href_index}]: '{hrefs_key}' len(matches)={len(matches)}")

            # There are one or more *matches*.  We'll take the first *a_content* that is non-null
            # and treat that as the *name*.  The number of *items* is taken from the first
            # *li_content* that end with " items)".  We visit *matches* in reverse order to work
            # around an obscure issue that is not worth describing.  If you feeling figuring it
            # out, please remove the call to `reversed()`:
            name: Optional[str] = None
            items: int = -1
            url: Optional[str] = None
            match_index: int
            match: Match
            for match_index, match in enumerate(reversed(sorted(matches))):
                # Unpack *match*:
                href: str
                base: str
                id: int
                a_conent: str
                li_content: str
                href, base, id, a_content, li_content, url = match
                assert href == "" or href == hrefs_key, f"href='{href}' hrefs_key='{hrefs_key}'"
                if tracing:
                    print(f"Match[{match_index}]: "
                          f"'{base}', {id}, '{a_content}', '{li_content}', '{url}'")

                # Fill in *name* and *items*:
                if name is not None and not a_content.startswith("See"):
                    name = a_content.strip(" \t\n")
                    items_pattern: str = " items)"
                    if items < 0 and li_content.endswith(" items)"):
                        open_parenthesis_index: int = li_content.find('(')
                        items = int(li_content[open_parenthesis_index+1:-len(items_pattern)])
                    break

            # Dispatch based on *name* and *items*:
            if name is None:
                # We already created *root_directory* so there is nothing to do here:
                pass
            elif items < 0:
                # We have a new *DigikeyDirectory* to create and make the *current_directory*.
                assert isinstance(url, str)
                current_directory = DigikeyDirectory(name, collection, id, url)
            else:
                # We create a new *DigikeyTable* that is appended to *current_directory*.
                # Note: the initializer automatically appends *table* to *current_directory*:
                assert current_directory is not None
                assert isinstance(url, str)
                DigikeyTable(name, current_directory, base, id, href, url)

        # *collection* is in its first incarnation and ready for reorganization:
        return collection

    # Digikey.collection_reorganize():
    @trace(1)
    def collection_reorganize(self, collection: bom.Collection) -> None:
        # Verify argument types:
        assert isinstance(collection, bom.Collection)

        # Extract a sorted list of *directories* from *collection*:
        directories: List[bom.Node] = collection.children_get()
        directories.sort(key=lambda directory: directory.name)

        # print("len(directories)={0}".format(len(directories)))
        directory_index: int
        directory: bom.Node
        tracing: str = tracing_get()
        for directory_index, directory in enumerate(directories):
            assert isinstance(directory, DigikeyDirectory)
            if tracing:
                print(f"Directory[{directory_index}]: '{directory.name}'")
            directory.reorganize()

    # Digikey.collection_verify():
    @trace(1)
    def collection_verify(self, digikey_collection: bom.Collection,
                          hrefs_table: Dict[str, List[Match]]) -> None:
        # For testing only, grab all of the *directories* and *tables* from *root_directory*,
        # count them up, and validate that the sizes all match:
        directories: List[bom.Directory] = digikey_collection.directories_get()
        directories_size: int = len(directories)
        tables: List[bom.Table] = digikey_collection.tables_get()
        tables_size: int = len(tables)
        hrefs_table_size: int = len(hrefs_table)

        # Verify that we did not loose anything during extraction:
        tracing: str = tracing_get()
        if tracing:
            print(f"{tracing}directories_size={directories_size}")
            print(f"{tracing}tables_size={tables_size}")
            print(f"{tracing}hrefs_table_size={hrefs_table_size}")

        # For debugging only:
        if hrefs_table_size != directories_size + tables_size:
            # Make a copy of *hrefs_table*:
            hrefs_table_copy: Dict[str, List[Match]] = hrefs_table.copy()

            # Remove all of the *tables* from *hrefs_table_copy*:
            errors: int = 0
            url_prefix: str = "https://www.digikey.com/products/en/"
            url_prefix_size: int = len(url_prefix)
            table: bom.Table
            for table in tables:
                table_key: str = table.url[url_prefix_size:]
                if table_key in hrefs_table_copy:
                    del hrefs_table_copy[table_key]
                else:
                    errors += 1
                    print(f"{tracing}table_key='{table_key}' not found")

            # Remove all of the *directories* from * *hrefs_table_copy*:
            directory: bom.Directory
            for directory in directories:
                assert isinstance(directory, DigikeyDirectory)
                directory_key: str = directory.url[url_prefix_size:]
                if directory_key in hrefs_table_copy:
                    del hrefs_table_copy[directory_key]
                else:
                    errors += 1

                    print(f"{tracing}directory_key='{directory_key}' not found")

            # Print out the remaining unumatched keys:
            print(f"{tracing}hrefs_table_copy.keys={list(hrefs_table_copy.keys())}")

            assert errors == 0, f"{errors} Error found"

    # Digikey.csvs_download():
    @trace(1)
    def csvs_download(self, collection: bom.Collection, tracing: str = "") -> int:
        # Grab the *csvs_directory* from *digikey* (i.e. *self*):
        digikey: Digikey = self
        csvs_directory: str = digikey.csvs_directory

        # Fetch example `.csv` files for each table in *collection*:
        downloads_count: int = 0
        for directory in collection.children_get():
            downloads_count = directory.csvs_download(csvs_directory, downloads_count)
        return downloads_count

    # Digikey.read_and_process():
    @trace(1)
    def csvs_read_and_process(self, collection: bom.Collection, bind: bool, gui: bom.Gui) -> None:
        # Grab the *csvs_directory* from *digikey* (i.e. *self*):
        digikey: Digikey = self
        csvs_directory: str = digikey.csvs_directory

        # Fetch example `.csv` files for each table in *collection*:
        directory: bom.Node
        for directory in collection.children_get():
            assert isinstance(directory, bom.Directory)
            directory.csv_read_and_process(csvs_directory, bind, gui)

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
                href: str
                base: str
                id: int
                a_content: str
                li_content: str
                url: str
                href, base, id, a_content, li_content, url = match
                print(f"{tracing} Match[{match_index}]: '{href}', '{base}', {id},")
                print(f"{tracing}            '{a_content}', '{li_content}',")
                print(f"{tracing}            '{url}')")
            if index >= limit:
                break

    # Digikey.process():
    @trace(0)
    def process(self, gui: bom.Gui) -> None:
        # This starts with the top level page from Digi-Key.com:
        #
        #   https://www.digikey.com/products/en
        #
        # Which is manually copied qout of the web browser and stored into the file named
        # *digikey_products_html_file_name*:

        # Read the `.html` file that contains the top level origanziation and convert it
        # into a Beautiful *soup* tree:
        digikey: Digikey = self
        soup: bs4.BeautifulSoup = digikey.soup_read()

        # Sweep through the *soup* tree and get a href information stuffed into *href_tables*:
        hrefs_table: Dict[str, List[Match]] = digikey.soup_extract(soup)

        # Extract the *digikey_collection* structure using *hrefs_table*:
        collection: bom.Collection = digikey.collection_extract(hrefs_table)
        digikey.collection_verify(collection, hrefs_table)

        # Reorganize and verify *collection*:
        digikey.collection_reorganize(collection)

        # Make sure we have an example `.csv` file for each table in *collection*:
        tracing: str = tracing_get()
        print(f"{tracing}&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&")
        downloads_count: int = digikey.csvs_download(collection)
        if tracing:
            print(f"{tracing}downloads_count={downloads_count}")

        # Clear out the root directory and repoulate it with updated tables:
        digikey.root_directory_clear()
        digikey.csvs_read_and_process(collection, True, gui)

    # Digikey.root_directory_clear():
    @trace(1)
    def root_directory_clear(self) -> None:
        # Scan the *root_directory* of *digikey* (i.e. *self*) for all sub files and directories:
        digikey: Digikey = self
        root_directory: str = digikey.root_directory
        file_names: List[str] = glob.glob(root_directory + "/**", recursive=True)

        # Sort *file_name* them so that the longest names come first (i.e. -negative length).
        file_names.sort(key=lambda file_name: -len(file_name))

        # Visit each *file_name* in *file_names* and delete them (if appropriate):
        file_name_index: int
        file_name: str
        tracing: str = tracing_get()
        for file_name_index, file_name in enumerate(file_names):
            # Hang onto the `README.md` and the top level directory (i.e. *file_name[:-1]*):
            delete: bool = not (file_name.endswith("README.md") or file_name[:-1] == root_directory)

            # *delete* *file_name* if appropiate:
            if delete:
                # *file_name* is a directory:
                if os.path.isdir(file_name):
                    if tracing:
                        print(f"{tracing}File[file_name_index]: Remove file '{file_name}'")
                    os.rmdir(file_name)
                else:
                    # *file_name* is a file:
                    if tracing:
                        print(f"{tracing}File[{file_name_index}]: Remove directory '{file_name}'")
                    os.remove(file_name)
            else:
                # *file_name* is to be kept:
                if tracing:
                    print(f"{tracing}[{file_name_index}]: Keep '{file_name}'")

    # Digikey.soup_extract():
    def soup_extract(self, soup: bs4.BeautifulSoup) -> Dict[str, List[Match]]:
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
        #        /products/en/*base*/*id*?*search*
        #
        #   * "*?search*": *?search* is some optional search arguments that can safely be ignored.
        #   * "/*id*": *id* is a decimal number that is 1-to-1 with the *base*.  The *id* is used
        #     by Digikey for specifying were to start.  When the *href* specifies a directory
        #     this is simply not present.
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
        # each *match* is a 5-tuple containing:
        #
        #    (*base*, *id*, *a_content_text*, *li_content_text*, *url*)
        #
        # *id* is -1 if there was no "/*id*" present in the *href*.

        # print("  =>Digikey.soup_extract(...)")

        # Start with an empty *hrefs_table*:
        hrefs_table: Dict[str, List[Match]] = dict()
        url_prefix: str = "/products/en/"
        url_prefix_size: int = len(url_prefix)
        match: Match
        matches: List[Match]

        # Find all of the <A HRef="..."> tags in *soup*:
        a: bs4.element.Tag
        for a in soup.find_all("a"):
            # We are only interested in *href*'s that start with *url_prefix*:
            href: Optional[str] = a.get("href")
            if href is not None and href.startswith(url_prefix) and href != url_prefix:
                # Strip off the "?*search" from *href*:
                question_mark_index: int = href.find('?')
                if question_mark_index >= 0:
                    href = href[:question_mark_index]

                # Strip the *url_prefix* from the beginning of *href*:
                href = href[url_prefix_size:]

                # Split out the *base* and *id* (if it exists):
                # print("href3='{0}'".format(href))
                slash_index: int = href.rfind('/')
                base: str
                id: int = -1
                if slash_index >= 0:
                    # *id* exists, so store it as a positive integer:
                    base = href[:slash_index].replace('/', '-')
                    # print("href[slash_index+1:]='{0}'".format(href[slash_index+1:]))
                    id = int(href[slash_index+1:])
                else:
                    # *id* does not exist, so store -1 into *id*:
                    base = href
                    id = -1

                # Construct *a_contents_text* from the contents of *a* tag.  In general this
                # text is a reasonable human readable summary of what the table/directory is about:
                a_contents_text: str = ""
                a_conent: bs4.element.Tag
                for a_content in a.contents:
                    if isinstance(a_content, bs4.element.NavigableString):
                        a_contents_text += a_content.string
                a_contents_text = a_contents_text.strip()

                # Construct the *li* content which is the text between the end of the </A>
                # tag and the </LI> tag.  In general, we only care if there is a class
                # attribute in the <A> tag (i.e. <A class="..." href="...".)
                # Sometimes the <A> tag is nested in an <LI> tag.  This text when present
                # will frequently have the basic form of "...(*items* items)...".
                li_contents_text: str = ""
                xclass: bs4.element.Tag = a.get("class")
                if xclass is not None:
                    # We have a `class="..."` attribute, so now look for the *parent* *li* tag:
                    parent: bs4.element = a.parent
                    assert isinstance(parent, bs4.element.Tag)
                    if parent.name == "li":
                        # We have an *li* tag, so extract its contents into *li_contents_text*:
                        li_contents: bs4.element = parent.contents
                        li_content: bs4.element.NavigableString
                        for li_content in li_contents:
                            if isinstance(li_content, bs4.element.NavigableString):
                                li_contents_text += li_content.string
                        li_contents_text = li_contents_text.strip()

                # Now stuff *base*, *id*, *a_contents_text*, *li_contents_text*, and *url*
                # into *hrefs_table* using *href* as the key.  Since same *href* can occur multiple
                # times in the *soup* we store everything in a the *matches* list containing
                # a *match* of 5-tuples:
                # href_key = f"{base}/{id}"
                if href in hrefs_table:
                    matches = hrefs_table[href]
                else:
                    matches = list()
                    hrefs_table[href] = matches
                url: str = "https://www.digikey.com/products/en/" + href
                # if base.startswith("capacitors"):
                #     print("url='{0}'".format(url))
                match = (href, base, id, a_contents_text, li_contents_text, url)
                matches.append(match)
        # We are done scraping information out of the the *soup*.  Everything we need is
        # now in *hrefs_table*.
        # print("  <=Digikey.soup_extract(...)")

        return hrefs_table

    # Digikey.soup_read():
    def soup_read(self) -> bs4.BeautifulSoup:
        # Read in the *digikey_product_html_file_name* file into *html_text*.  This
        # file is obtained by going to `https://www.digkey.com/` and clickd on the
        # `[View All]` link next to `Products`.  This page is saved from the web browser
        # in the file named *digikey_product_html_file_name*:

        # Grab some values from *digikey* (i.e. *self*):
        digikey: Digikey = self
        products_html_file_name: str = digikey.products_html_file_name

        # Read *products_html_file_name* in and convert it into *soup*:
        html_file: TextIO
        soup: Optional[bs4.BeautifulSoup] = None
        with open(products_html_file_name) as html_file:
            html_text: str = html_file.read()

            # Parse *html_text* into a *soup*:
            soup = bs4.BeautifulSoup(html_text, features="lxml")

            # To aid in reading the HTML, write the *soup* back out to the `/tmp` directory
            # in a prettified form:
            prettified_html_file_name: str = "/tmp/prettified.html"
            with open(prettified_html_file_name, "w") as html_file:
                html_file.write(soup.prettify())
        assert isinstance(soup, bs4.BeautifulSoup)
        return soup


# DigikeyCollection():
class DigikeyCollection(bom.Collection):

    # DigikeyCollection.__init__():
    @trace(1)
    def __init__(self, collections: bom.Collections, searches_root: str, gui: bom.Gui) -> None:
        # Compute the path to the *collection_root*:
        digikey_py_file_path: str = __file__
        digikey_directory: str
        digikey_py: str
        digikey_directory, digikey_py = os.path.split(digikey_py_file_path)
        collection_root: str = os.path.join(digikey_directory, "ROOT")
        tracing: str = tracing_get()
        if tracing:
            print(f"{tracing}digikey_py_file_path=>'{digikey_py_file_path}'")
            print(f"{tracing}digikey_directory='{digikey_directory}'")
            print(f"{tracing}collection_root='{collection_root}'")
        assert os.path.isdir(collection_root)

        # Initialize *digikey_collection* (i.e. *self*):
        super().__init__("Digi-Key", collections, collection_root, searches_root, gui)
        digikey_collection: DigikeyCollection = self
        assert digikey_collection.name == "Digi-Key"

    # DigikeyCollection.__str__():
    def __str__(self) -> str:
        # digikey_collection = self
        return f"DigikeyCollection('Digi-Key')"

    # DigikeyCollection.csv_fetch():
    @trace(1)
    def csv_fetch(self, search_url: str, csv_file_name: str) -> bool:
        # Construct the header values that need to be sent with the *search_url*:
        authority_text: str = "www.digikey.com"
        accept_text: str = (
            "text/html,application/xhtml+xml,application/xml;"
            "q=0.9,image/webp,image/apng,*/*;"
            "q=0.8,application/signed-exchange;"
            "v=b3"
        )
        accept_encoding_text: str = "gzip, deflate, br"
        cookie_text: str = (
            "i10c.bdddb=c2-f0103ZLNqAeI3BH6yYOfG7TZlRtCrMwzKDQfPMtvESnCuVjBtyWjJ1l"
            "kqXtKsvswxDrjRHdkESNCtx04RiOfGqfIlRUHqt1qPnlkPolfJSiIRsomx0RhMqeKlRtT3"
            "jxvKEOjKMDfJSvUoxo6uXWaGVZkqoAhloxqQlofPwYkJcS6fhQ6tzOgotZkQMtHDyjnA4lk"
            "PHeIKNnroxoY8XJKBvefrzwFru4qPnlkPglfJSiIRvjBTuTfbEZkqMupstsvz8qkl7wWr3i"
            "HtspjsuTFBve9SHoHqjyTKIPfPM3uiiAioxo6uXOfGvdfq4tFloxqPnlkPcxyESnCuVjBt1"
            "VmBvHmsYoHqjxVKDq3fhvfJSiIRsoBsxOftucfqRoMRjxVKDq3BuEMuNnHoyM9oz3aGv4ul"
            "RtCrMsvP8tJOPeoESNGw2q6tZSiN2ZkQQxHxjxVOHukKMDjOQlCtXnGt4OfqujoqMtrpt3y"
            "KDQjVMffM3iHtsolozT7WqeklSRGloXqPDHZHCUfJSiIRvjBTuTfQeKKYMtHlpVtKDQfPM2"
            "uESnCuVm6tZOfGK1fqRoIOjxvKDrfQvYkvNnuJsojozTaLW"
        )

        # Construct *headers*:
        headers: Dict[str, str] = {
            "authority": authority_text,
            "accept": accept_text,
            "accept-encoding": accept_encoding_text,
            "cookie": cookie_text
        }

        # Attempt the fetch the contents of *search_url* using *headers*:
        try:
            response: requests.Response = requests.get(search_url, headers=headers)
            response.raise_for_status()
        except requests.exceptions.HTTPError as http_error:
            assert False, f"HTTP error occurred '{http_error}'"
        except Exception as error:
            assert False, f"Other exception occurred: '{error}'"

        # Now parse the resulting *html_text* using a *soup* to find the *csv_url*:
        html_text: str = str(response.content)

        soup: Optional[bs4.BeautifulSoup] = bs4.BeautifulSoup(html_text, features="lxml")
        assert soup is not None
        tracing: str = tracing_get()
        # print(f"{tracing}type(soup)=", type(soup))
        pairs: List[str] = []
        pairs_text: Optional[str] = None
        if tracing:
            print(f"{tracing}here 2b")
        formtag: bs4.element.Tag
        for form_tag in soup.find_all("form"):
            name: str = form_tag.get("name")
            if name == "downloadform":
                # We found it:
                if tracing:
                    print(f"{tracing}form_tag={form_tag}")
                index: int
                input_tag: bs4.element.Tag
                for index, input_tag in enumerate(form_tag.children):
                    # print(input_tag)
                    input_tag_name: Optional[str] = input_tag.name
                    if isinstance(input_tag_name, str) and input_tag_name.lower() == "input":
                        input_name: str = input_tag.get("name")
                        input_value: str = input_tag.get("value")
                        input_value = input_value.replace(",", "%2C")
                        input_value = input_value.replace('|', "%7C")
                        input_value = input_value.replace(' ', "+")
                        pair: str = f"{input_name}={input_value}"
                        if tracing:
                            print(f"{tracing}input_name='{input_name}'")
                            print(f"{tracing}input_value='{input_value}'")
                            print(f"{tracing}pair='{pair}'")
                        pairs.append(pair)
                pairs_text = '&'.join(pairs)
                if tracing:
                    print(f"{tracing}pairs_text='{pairs_text}'")
        assert isinstance(pairs_text, str)

        # Construct the *csv_url*:
        csv_url: str = "https://www.digikey.com/product-search/download.csv?" + pairs_text
        if tracing:
            print(f"{tracing}csv_url='{csv_url}'")

        # Construct the text strings fort the *headers*:
        authority_text = "www.digikey.com"
        accept_text = (
            "text/html,application/xhtml+xml,application/xml;"
            "q=0.9,image/webp,image/apng,*/*;"
            "q=0.8,application/signed-exchange;"
            "v=b3"
        )
        accept_encoding_text = "gzip, deflate, br"
        cookie_text = (
            "i10c.bdddb="
            "c2-94990ugmJW7kVZcVNxn4faE4FqDhn8MKnfIFvs7GjpBeKHE8KVv5aK34FQDgF"
            "PFsXXF9jma8opCeDMnVIOKCaK34GOHjEJSFoCA9oxF4ir7hqL8asJs4nXy9FlJEI"
            "8MujcFW5Bx9imDEGHDADOsEK9ptrlIgAEuIjcp4olPJUjxXDMDVJwtzfuy9FDXE5"
            "sHKoXGhrj3FpmCGDMDuQJs4aLb7AqsbFDhdjcF4pJ4EdrmbIMZLbAQfaK34GOHbF"
            "nHKo1rzjl24jP7lrHDaiYHK2ly9FlJEADMKpXFmomx9imCGDMDqccn4fF4hAqIgF"
            "JHKRcFFjl24iR7gIfTvaJs4aLb4FqHfADzJnXF9jqd4iR7gIfz8t0TzfKyAnpDgp"
            "8MKEmA9og3hdrCbLvCdJSn4FJ6EFlIGEHKOjcp8sm14iRBkMT8asNwBmF3jEvJfA"
            "DwJtgD4oL1Eps7gsLJaKJvfaK34FQDgFfcFocAAMr27pmCGDMD17GivaK34GOGbF"
            "nHKomypOTx9imDEGHDADOsTpF39ArqeADwFoceWjl24jP7gIHDbDPRzfwy9JlIlA"
            "DTFocAEP"
        )

        # Construct *headers*:
        headers = {
            "authority": authority_text,
            "accept": accept_text,
            "accept-encoding": accept_encoding_text,
            "cookie": cookie_text
        }

        # Attempt the fetch the contents of *csv_fetch_url* using *headers*:
        if tracing:
            print(f"{tracing}A:Fetching '{csv_url}' extracted '{search_url}' contents:")
        try:
            response = requests.get(csv_url, headers=headers)
            response.raise_for_status()
        except requests.exceptions.HTTPError as http_error:
            assert False, f"HTTP error occurred '{http_error}'"
        except Exception as error:
            assert False, f"Other exception occurred: '{error}'"

        # Now write *csv_text* out to *csv_file_name*:
        csv_text: str = str(response.content)
        csv_file: TextIO
        with open(csv_file_name, "w") as csv_file:
            csv_file.write(csv_text)
        if tracing:
            print(f"{tracing}Wrote out '{csv_file_name}'")

        # Wrap up any requested *tracing* and return *result*;
        result: bool = True
        return result

    # DigikeyCollection.panel_update():
    @trace(1)
    def panel_update(self, gui: bom.Gui) -> None:
        digikey_collection: DigikeyCollection = self
        gui.collection_panel_update(digikey_collection)


# DigikeyDirectory:
class DigikeyDirectory(bom.Directory):

    # DigikeyDirectory.__init__():
    def __init__(self, name: str, parent: "Union[bom.Collection, DigikeyDirectory]",
                 id: int, url: str) -> None:
        # Initialize the parent class for *digikey_directory* (i.e. *self*):
        super().__init__(name, parent)

        # Stuff values into *digikey_table* (i.e. *self*):
        # digikey_directory: DigikeyDirectory = self
        self.id: int = id
        self.url: str = url

    # DigikeyDirectory.__str__():
    def __str__(self) -> str:
        digikey_directory: DigikeyDirectory = self
        name: str = "??"
        if hasattr(digikey_directory, "name"):
            name = digikey_directory.name
        return f"DigikeyDirectory('{name}')"

    # DigikeyDirectory.csvs_download():
    @trace(1)
    def csvs_download(self, csvs_directory: str, downloads_count: int) -> int:
        # Grab some values from *digikey_directory* (i.e. *self*):
        digikey_directory: DigikeyDirectory = self
        children: List[bom.Node] = digikey_directory.children_get()
        sub_node: bom.Node
        for sub_node in children:
            downloads_count += sub_node.csvs_download(csvs_directory, downloads_count)
        return downloads_count

    # DigikeyDirectory.csv_read_and_process():
    @trace(1)
    def csv_read_and_process(self, csvs_directory: str, bind: bool, gui: bom.Gui) -> None:
        # Process each *sub_node* of *digikey_directory* (i.e. *self*):
        digikey_directory: DigikeyDirectory = self
        sub_node: bom.Node
        for sub_node in digikey_directory.children_get():
            assert isinstance(sub_node, bom.Node)
            sub_node.csv_read_and_process(csvs_directory, bind, gui)

    # DigikeyDirectory.reorganize():
    @trace(1)
    def reorganize(self) -> None:
        # This lovely piece of code takes a *DigikeyDirectory* (i.e. *self*) and attempts
        # to further partition it into some smaller directories.

        # A *title* can be of form:
        #
        #        "Level 1 Only"
        #        "Level 1 - Level 2"
        #        "Level 1 - Level 2 -Level 3"
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
        digikey_directory: DigikeyDirectory = self
        # name: str = digikey_directory.name
        groups_table: Dict[str, List[bom.Table]] = dict()
        children: List[bom.Node] = sorted(digikey_directory.children_get(),
                                          key=lambda table: table.name)
        table_index: int
        table: bom.Node
        tables_list: List[bom.Table]
        tracing: str = tracing_get()
        for table_index, table in enumerate(children):
            # Grab some values from *table*:
            assert isinstance(table, DigikeyTable)
            name: str = table.name
            id: int = table.id
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
                    print(f"{tracing}[{table_index}]:'{name}'=>'{group_name}'/'{sub_group_name}")

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
        digikey_table: bom.Node
        for digikey_table in digikey_directory.children_get():
            assert isinstance(digikey_table, DigikeyTable)
            digikey_table_name: str = digikey_table.name
            if digikey_table_name in groups_table:
                tables_list = groups_table[digikey_table_name]
                tables_list.append(digikey_table)
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
                digikey_directory.remove(table)

        # Now create a *sub_directory* for each *group_title* in *groups_table*:
        for index, group_name in enumerate(sorted(groups_table.keys())):
            tables_list = groups_table[group_name]
            # Convert *group_title* to *directory_name*:
            # directory_name = digikey_directory.title2file_name(group_title)
            # print("  Group_Title[{0}]'{1}':".format(group_title_index, group_title))

            # Create the *sub_directory*:
            # sub_directory_path = digikey_directory.path + "/" + directory_name
            sub_directory = DigikeyDirectory(group_name, digikey_directory, id, url)
            # Note: *DigikeyDirectory()* automatically appends to the
            # *digikey_directory* parent:

            # Now create a new *sub_table* for each *table* in *tables_list*:
            tables_list.sort(key=lambda table: table.name)
            for table_index, table in enumerate(tables_list):
                assert isinstance(table, DigikeyTable)

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
                href = ""
                DigikeyTable(name, sub_directory, base, id, href, url)
                # Note: *DigikeyTable()* automatically appends *sub_table* to the parent
                # *sub_directory*:

            # Sort *sub_directory* just for fun.  It probably does not do much of anything:
            # sub_directory.sort(lambda title: title.name)

        # Again, sort *digikey_directory* even though it is unlikely to change anything:
        # digikey_directory.sort(lambda table: table.name)
        # digikey_directory.show("  ")

    # DigikeyDirectory.show():
    def show(self, indent: str) -> None:
        # digikey_directory: DigikeyDirectory = self
        # children: List[bom.Node] = digikey_directory.children_get()
        # node_index: int
        # node: bom.Node
        # for node_index, node in enumerate(children):
        #     if isinstance(node, DigikeyDirectory):
        #         print(f"{indent}[{node_index}] D:'{node.title}' '{node.path}'")
        #         node.show(indent + "    ")
        #     elif isinstance(node, DigikeyTable):
        #         print(f"{indent}[{node_index}] T:'{node.title}' '{node.path}'")
        #     else:
        #         assert False
        assert False, "This code is broken"

    # DigikeyDirectory.table_get():
    def table_get(self) -> str:
        digikey_directory: DigikeyDirectory = self
        assert False, "This should use Encode instead"
        return digikey_directory.file_name2title()


# DigikeyTable:
class DigikeyTable(bom.Table):

    # DigikeyTable.__init__():
    def __init__(self, name: str, parent: DigikeyDirectory, base: str, id: int,
                 href: str, url: str,) -> None:
        # Initialize the parent class:
        super().__init__(name, parent, url)

        # Stuff values into *digikey_table* (i.e. *self*):
        # digikey_table = self
        self.base: str = base
        self.id: int = id
        self.href: str = href
        self.url: str = url

    # DigikeyTable.__str__():
    def __str__(self) -> str:
        digikey_table: DigikeyTable = self
        name: str = "??"
        if hasattr(digikey_table, "name"):
            name = digikey_table.name
        return f"DigikeyTable('{name}')"

    # DigikeyTable.csvs_download():
    @trace(1)
    def csvs_download(self, csvs_directory: str, downloads_count: int) -> int:
        digikey_table: DigikeyTable = self
        base: str = digikey_table.base
        id: int = digikey_table.id
        csv_file_name: str = csvs_directory + "/" + base + ".csv"
        tracing: str = tracing_get()
        if tracing:
            print(f"{tracing}csv_file_name='{csv_file_name}'")
        if not os.path.isfile(csv_file_name):
            # The first download happens immediately and the subsequent ones are delayed by
            # 60 seconds:
            if downloads_count >= 1:
                print("Waiting 60 seconds....")
                time.sleep(60)

            # Compute the *url*, *parameters*, and *headers* needed for the *request*:
            url: str = "https://www.digikey.com/product-search/download.csv"
            parameters: Dict[str, str] = {
                "FV": "ffe{0:05x}".format(id),
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
                           "DTFocAEP")
                }

            # Perform the download:
            if tracing:
                print(f"{tracing}DigikeyTable.csvs_download: '{csv_file_name}':{id}")
            response: requests.Response = requests.get(url, params=parameters, headers=headers)
            # print(f"response.headers={response.headers}")
            # print(f"rsponse.content='{response.content}")
            # response_encoding: str = response.encoding
            content: str = response.text

            # Write the content out to *csv_file_name*:
            csv_file: TextIO
            with open(csv_file_name, "w") as csv_file:
                csv_file.write(content)
            downloads_count += 1

        return downloads_count

    # DigikeyTable.csv_full_name_get():
    @trace(1)
    def csv_full_name_get(self) -> str:
        # Grab some values from *digikey_table* (i.e. *self*):
        digikey_table = self
        base: str = digikey_table.base
        # collection = digikey_table.collection

        # Compute the *csv_full_name* and return it:
        # collection_root: str = collection.collection_root
        # csvs_root = os.path.join(collection_root, os.path.join("..", "CSVS"))
        csvs_root: str = "/home/wayne/public_html/projects/bom_digikey_plugin/CSVS"
        csv_full_name: str = os.path.join(csvs_root, base + ".csv")
        return csv_full_name

    # DigikeyTable.file_save():
    @trace(1)
    def file_save(self) -> None:
        digikey_table: DigikeyTable = self
        tracing: str = tracing_get()
        if tracing:
            comments: List[bom.TableComment] = digikey_table.comments
            parameters: List[bom.Parameter] = digikey_table.parameters
            print(f"{tracing}len(comments)={len(comments)}")
            print(f"{tracing}len(parameters)={len(parameters)}")

        # Convert *digikey_table* (i.e. *self*) into a single *xml_text* string:
        xml_lines: List[str] = list()
        digikey_table.xml_lines_append(xml_lines, "")
        xml_lines.append("")
        xml_text: str = '\n'.join(xml_lines)

        # Compute the *xml_file_name*:
        collection: Optional[bom.Collection] = digikey_table.collection
        assert isinstance(collection, bom.Collection)
        collection_root: str = collection.collection_root
        relative_path: str = digikey_table.relative_path
        xml_file_name: str = os.path.join(collection_root, relative_path + ".xml")
        if tracing:
            print(f"{tracing}collection_root='{collection_root}'")
            print(f"{tracing}relative_path='{relative_path}'")
            print(f"{tracing}xml_file_name='{xml_file_name}'")

        # Write out *xml_text* to *xml_file_name*:
        digikey_table.directory_create(collection_root)
        xml_file: TextIO
        with open(xml_file_name, "w") as xml_file:
            xml_file.write(xml_text)
        # assert False, f"XML file '{xml_file_name}' written"

    # DigikeyTable.title_get():
    def title_get(self) -> str:
        digikey_table: DigikeyTable = self
        assert False, "Should use encode instead"
        return digikey_table.file_name2title()

    # DigikeyTable.xml_lines_append():
    def xml_lines_append(self, xml_lines: List[str], indent: str) -> None:
        # Grab some values from *digikey_table* (i.e. *self*):
        digikey_table: DigikeyTable = self
        name: str = digikey_table.name
        parameters: List[bom.Parameter] = digikey_table.parameters
        url: str = digikey_table.url

        # Start with the `<DigikeyTable ... >` tag:
        xml_lines.append(f'{indent}<DigikeyTable '
                         f'name="{bom.Encode.to_attribute(name)}"'
                         f'url="{bom.Encode.to_attribute(url)}"'
                         f'>')

        # Append the *parameters*:
        xml_lines.append(f'{indent} <Parameters>')
        next_indent: str = indent + "  "
        for parameter in parameters:
            parameter.xml_lines_append(xml_lines, next_indent)
        xml_lines.append(f'{indent} </Parameters>')

        # Close out `</DigikeyTable>` tag:
        xml_lines.append(f'{indent}</DigikeyTable>')


if __name__ == "__main__":
    main()
