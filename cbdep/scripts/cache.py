"""
Cache
"""

import hashlib
import logging
import os
import pathlib
import re
import requests
import shutil
import urllib.parse

# Set up logging and handler
logger = logging.getLogger('cbdep')


class Cache:
    """
    Class to store downloaded files in a local cache
    """

    def __init__(self, directory):
        """
        Initialize a cache based at the specified directory
        """
        self.directory = pathlib.Path(directory)

    def get(self, url, recache=False):
        """
        Downloads url (if necessary), saves in local cache. If recache is
        True, will always re-download the url.
        """

        # Local cache directory structure is keyed on an MD5 checksum of the
        # URL, and contains directories named:
        #   <first 2 chars of checksum> / <checksum> /
        # In each directory will be three files:
        #     url - contains the input URL
        #     filename - contains the filename associated with the download
        #                (currently just for human reference)
        #     [filename] - contains the downloaded contents

        md5 = hashlib.md5(url.encode('utf-8')).hexdigest()
        cachedir = self.directory / md5[0:2] / md5
        cachefilename = cachedir / "filename"

        # If "filename" file exists, it's a hit; read the actual filename
        # from there and return the cached content file
        if cachefilename.exists() and not recache:
            logger.debug(f"Cache hit for {url}")
            with open(cachefilename) as f:
                filename = f.readline()
                return cachedir / filename

        # Cache miss; initialize cache directory
        if not cachedir.exists():
            cachedir.mkdir(parents=True)
            with open(cachedir / "url", 'w') as f:
                f.write(url)

        # Download the URL
        with requests.get(url, allow_redirects=True, stream=True,
                          timeout=30.0) as r:
            r.raise_for_status()

            # Determine download filename
            filename = None
            cd = r.headers.get('content-disposition')
            if cd:
                filenames = re.findall('filename=(.+)', cd)
                if len(filenames) > 0:
                    filename = filenames[0]
            if filename is None:
                filename = os.path.basename(urllib.parse.urlparse(url).path)
            logger.info(f"Caching {url} ({filename})")

            cachefile = cachedir / filename
            try:
                with open(cachefile, 'wb') as fd:
                    for chunk in r.iter_content(chunk_size=1024):
                        fd.write(chunk)
                with open(cachefilename, 'w') as f:
                    f.write(filename)
            except:
                if cachefile.exists():
                    os.unlink(cachefile)
                if cachefilename.exists():
                    os.unlink(cachefilename)
                raise

        logger.debug("Downloaded file")
        return cachefile

    def report(self, url):
        """
        Output the full path to the file in the cache
        """

        print(self.get(url))

    def save(self, url, output):
        """
        Save a local copy of a file in the cache
        """

        shutil.copyfile(self.get(url), output)