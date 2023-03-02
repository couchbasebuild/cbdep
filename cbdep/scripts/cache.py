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
    Class to store downloaded files in a local cache, keyed by URL.

    Local cache directory structure is keyed on an MD5 checksum of the
    URL, and contains directories named:
        <first 2 chars of checksum> / <checksum> /
    In each directory will be three files:
        url - contains the input URL
        filename - contains the filename associated with the download
        [filename] - contains the downloaded contents
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

        cachedir = self._cachedir(url)
        cachefilename = self._cachefilename(cachedir)

        # If "filename" file exists, it's a hit; read the actual filename
        # from there and return the cached content file
        if cachefilename.exists() and not recache:
            logger.debug(f"Cache hit for {url}")
            with open(cachefilename) as f:
                filename = f.readline()
                return cachedir / filename

        # Cache miss; attempt to download the URL
        with requests.get(url, allow_redirects=True, stream=True,
                          timeout=30.0) as r:
            r.raise_for_status()

            # Determine download filename
            filename = None
            cd = r.headers.get('content-disposition')
            if cd:
                filenames = re.findall('filename=([^;]+)', cd)
                if len(filenames) > 0:
                    filename = filenames[0]
            if filename is None:
                filename = os.path.basename(urllib.parse.urlparse(url).path)
            logger.info(f"Caching {url} ({filename})")

            cachefile = cachedir / filename
            try:
                # Download file
                with open(cachefile, 'wb') as fd:
                    for chunk in r.iter_content(chunk_size=1024):
                        fd.write(chunk)

                self._writefilename(cachedir, filename)

            except:
                if cachefile.exists():
                    cachefile.unlink()
                if cachefilename.exists():
                    cachefilename.unlink()
                raise

        logger.debug("Downloaded file")
        return cachefile

    def put(self, url, localfile):
        """
        Copies the specified local pathlib handle into the cache keyed by the
        specified URL.
        Returns pathlib handle to cached file.
        """

        cachedir = self._cachedir(url)
        filename = localfile.name

        logger.debug(f"Storing {localfile} in cache for {url}")
        shutil.copy2(localfile, cachedir / filename)
        self._writefilename(cachedir, filename)

    def report(self, url):
        """
        Output the full path to the file in the cache
        """

        print(self.get(url))

    def save(self, url, output):
        """
        Save a local copy of a file in the cache
        """

        shutil.copy2(self.get(url), output)

    def _cachedir(self, url):
        """
        Returns pathlib handle to cache directory for given URL. Creates cachedir
        if necessary, with initial "url" file entry.
        """

        md5 = hashlib.md5(url.encode('utf-8')).hexdigest()
        cachedir = self.directory / md5[0:2] / md5

        if not cachedir.exists():
            logger.debug(f"Creating cache directory {cachedir}")
            cachedir.mkdir(parents=True)
            with open(cachedir / "url", 'w') as f:
                f.write(url)

        return cachedir

    def _writefilename(self, cachedir, filename):
        """
        Writes the "filename" file into the appropriate cache directory. As a
        side effect, if "filename" already exists and references a different
        file, that (now stale) file will be removed.
        """

        cachefilename = self._cachefilename(cachedir)
        if cachefilename.exists():
            with open(cachefilename) as f:
                currentfilename = f.readline()
            if currentfilename != filename:
                cachedfile = cachedir / currentfilename
                if cachedfile.exists():
                    cachedfile.unlink()

        logger.debug(f"Recording filename {filename}")
        with open(cachefilename, 'w') as f:
            f.write(filename)

    def _cachefilename(self, cachedir):
        """
        Returns pathlib handle to the "filename" file in cachedir
        """

        return cachedir / "filename"
