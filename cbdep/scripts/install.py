"""
Install
"""

import logging
import os
import pathlib
import re
import shutil
import string
import sys
import yaml

logger = logging.getLogger("cbdep")

class Installer:
    """
    Manages caching installation files and unpacking them based on an
    installation template yaml file
    """

    def __init__(self, yamlfile, cache, platforms):
        with open(yamlfile) as y:
            self.descriptor = yaml.load(y)
        self.cache = cache
        self.platforms = platforms
        # Populated by do_downloads to be the final single downloaded installer
        self.installer_file = None
        # Populated by do_downloads to be the platform-specific YAML entry for
        # the downloaded file
        self.plat_directives = None

    @staticmethod
    def get_by_key(objects, key, value, any=False):
        """
        Given a list of objects, returns the first object with a key 'key'
        whose value is either 'value' or a list containing 'value'.
        """
        for obj in objects:
            if key not in obj:
                continue
            if isinstance(obj[key], list):
                if value in obj[key]:
                    return obj
            else:
                if obj[key] == value:
                    return obj
        return None

    def install(self, package, version, dir):
        """
        Entry point to install a named package
        """
        pkg = self.get_by_key(self.descriptor["packages"], "name", package)
        if pkg is None:
            logger.error(f"Unknown package: {package}")
            sys.exit(1)
        if "downloads" in pkg:
            self.do_downloads(pkg["downloads"], package, version)
            if "exec" in self.plat_directives:
                self.exec(dir)
            else:
                self.unarchive(dir)

    def scrape_html(self, localfile, regexp):
        """
        Reads localfile looking for a particular regexp, which is presumed
        to be a valid URL; cache that URL and return the newly-downloaded file
        """

        matcher = re.compile(regexp)
        with open(localfile) as f:
            logger.debug(f"Searching {localfile} for {regexp}...")
            for line in f:
                match = matcher.search(line)
                if match:
                    url = match.group(1)
                    logger.debug(f"...found {url}")
                    return str(self.cache.get(url))

        logger.error("Scraped HTML did not find {regexp}")
        sys.exit(1)

    def do_downloads(self, downloads, package, version):
        """
        Handles a downloads directive
        """
        platforms = self.platforms if isinstance(self.platforms, list) else [ self.platforms ]
        for platform in platforms:
            logger.debug(f"Looking for {package} on {platform}...")
            plat = self.get_by_key(downloads, "platform", platform)
            if plat is not None:
                break

        if plat is None:
            logger.error(f"Package {package} not available on any of {platforms}")
            sys.exit(1)

        self.plat_directives = plat

        template = string.Template(plat["url"])
        url = template.substitute(VERSION=version, PLATFORM=platform)
        localfile = str(self.cache.get(url))

        # Handle strange redirects
        if "scrape_html" in plat:
            localfile = self.scrape_html(localfile, plat["scrape_html"])

        self.installer_file = localfile

    def execute(self, dir):
        """
        Runs a downloaded executable installer, ideally installing into
        specified dir
        """
        pass

    def unarchive(self, dir):
        """
        Unarchives the downloaded file
        """
        installdir = self.plat_directives.get("override_dir", dir)
        if installdir != dir:
            logger.info(f"NOTE: overriding installation directory to {installdir}")

        if "add_dir" in self.plat_directives:
            template = string.Template(self.plat_directives["add_dir"])
            new_dir = pathlib.Path(installdir) / template.substitute(VERSION=version, PLATFORM=platform)
            os.makedirs(new_dir, exist_ok=True)
            installdir = str(new_dir)

        logger.info(f"Unpacking archive into {installdir}")
        shutil.unpack_archive(self.installer_file, installdir)