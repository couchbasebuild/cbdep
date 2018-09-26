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
import tempfile
import yaml

from subprocess import run

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

        # Populated by self.install
        self.package = None
        self.version = None
        # Populated by do_downloads to be the final single downloaded installer
        self.installer_file = None
        # Populated by do_downloads to be the platform-specific YAML entry for
        # the downloaded file
        self.plat_directives = None
        # Also populated by do_downloads since it's the one that figures out the
        # specific platform name being used
        self.platform = None
        # Populate by set_installdir
        self.installdir = None

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
        # QQQ This lack of encapsulation is wrong. Split into better objects.
        self.package = package
        self.version = version

        pkg = self.get_by_key(self.descriptor["packages"], "name", package)
        if pkg is None:
            logger.error(f"Unknown package: {package}")
            sys.exit(1)
        if "downloads" in pkg:
            self.do_downloads(pkg["downloads"])
            self.set_installdir(dir)

            if "install" in self.plat_directives:
                self.execute()
            else:
                self.unarchive()

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

    def do_downloads(self, downloads):
        """
        Handles a downloads directive
        """
        platforms = self.platforms if isinstance(self.platforms, list) else [ self.platforms ]
        for platform in platforms:
            logger.debug(f"Looking for {self.package} on {platform}...")
            plat = self.get_by_key(downloads, "platform", platform)
            if plat is not None:
                break

        if plat is None:
            logger.error(f"Package {self.package} not available on any of {platforms}")
            sys.exit(1)

        self.plat_directives = plat
        self.platform = platform

        template = string.Template(plat["url"])
        # QQQ See other comments about template substitution
        url = template.substitute(VERSION=self.version, PLATFORM=self.platform)
        localfile = str(self.cache.get(url))

        # Handle strange redirects
        if "scrape_html" in plat:
            localfile = self.scrape_html(localfile, plat["scrape_html"])

        self.installer_file = localfile

    def set_installdir(self, dir):
        """
        Logic for determining final installation directory
        """

        self.installdir = self.plat_directives.get("override_dir", dir)
        if self.installdir != dir:
            logger.info(f"NOTE: overriding installation directory to {self.installdir}")

        # Make install dir absolute
        # QQQ Should use .resolve() rather than .absolute() since the latter
        # is semi-documented and semi-deprecated. However .resolve() doesn't
        # actually work as documented on Windows (doesn't return an absolute
        # path), where .absolute() does. So...
        self.installdir = str(pathlib.Path(self.installdir).absolute())

        if "add_dir" in self.plat_directives:
            template = string.Template(self.plat_directives["add_dir"])
            # QQQ split template substitution out to separate place, to ensure
            # common set of variables are available everywhere reasonable
            new_dir = pathlib.Path(self.installdir) / template.substitute(
                VERSION=self.version, PLATFORM=self.platform
            )
            os.makedirs(new_dir, exist_ok=True)
            self.installdir = str(new_dir)

    def execute(self):
        """
        Runs a downloaded executable installer, installs into target dir,
        makes copy of target dir, uninstalls from target dir, then copies the
        copy-dir to target dir
        """

        logger.info(f"Installing into {self.installdir}")
        shutil.rmtree(self.installdir, ignore_errors=True)
        template = string.Template(self.plat_directives["install"])
        cmd = template.substitute(DL=self.installer_file, INSTALLDIR=self.installdir)
        logger.debug(f"Install command: {cmd}")
        run(cmd, shell=True, check=True)

        logger.info(f"Copying {self.installdir} to backup copy")
        backupdir = self.installdir + "pyfred"
        shutil.copytree(self.installdir, backupdir)

        logger.info(f"Uninstalling from {self.installdir}")
        template = string.Template(self.plat_directives["uninstall"])
        cmd = template.substitute(DL=self.installer_file)
        logger.debug(f"Uninstall command: {cmd}")
        run(cmd, shell=True, check=True)

        logger.info(f"Copying backup copy to {self.installdir}")
        shutil.copytree(backupdir, self.installdir)
        logger.info(f"Removing backup copy")
        shutil.rmtree(backupdir)


    def unarchive(self):
        """
        Unarchives the downloaded file
        """

        logger.info(f"Unpacking archive into {self.installdir}")
        shutil.unpack_archive(self.installer_file, self.installdir)