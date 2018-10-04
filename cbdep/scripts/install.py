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

        # Things that will be substituted in all templates
        self.symbols = {}
        self.symbols["HOME"] = str(pathlib.Path.home())

        # Populated by install()
        self.package = None
        self.version = None
        self.installdir = None

        # Populated by do_url() to be the final single downloaded installer
        self.installer_file = None

    def install(self, package, version, dir):
        """
        Entry point to install a named package
        """
        self.package = package
        self.symbols['PACKAGE'] = package
        self.version = version
        self.symbols['VERSION'] = version

        # Make install dir absolute
        # QQQ Should use .resolve() rather than .absolute() since the latter
        # is semi-documented and semi-deprecated. However .resolve() doesn't
        # actually work as documented on Windows (doesn't return an absolute
        # path), where .absolute() does. So...
        self.installdir = str(pathlib.Path(dir).absolute())
        self.symbols['INSTALL_DIR'] = self.installdir

        pkgs = self.descriptor.get("packages")
        if pkgs is None:
            logger.error("Malformed configuration file (missing 'packages')")
            sys.exit(1)

        blocks = pkgs.get(package)
        if blocks is None:
            logger.error(f"Unknown package: {package}")
            sys.exit(1)

        logger.debug(f"Starting install for package {package}")

        block = self.find_block(blocks)
        if block is None:
            logger.error(f"No blocks for package {package} are appropriate for current system")
            sys.exit(1)

        self.execute_block(block)

    def find_block(self, blocks):
        """
        Searches for first block (dictionary) in the list "blocks" which
        is appropriate for the current system, based on its if_platform,
        if_version, etc. keys
        Returns: Said block, or None if none match
        """

        for block in blocks:
            if self.match_platform(block) and self.match_version(block):
                return block

        return None

    def match_platform(self, block):
        """
        If the block contains an if_platform key, return true if the current
        platform is one of the values for that key, else false.
        If the block does not contain an if_platform key, return true
        """
        if "if_platform" not in block:
            return True

        if_platform = block["if_platform"]
        if isinstance(self.platforms, list):
            local_platforms = self.platforms
        else:
            local_platforms = [ self.platforms ]

        matched_platform = False
        for local_platform in local_platforms:
            if isinstance(if_platform, list):
                if local_platform in if_platform:
                    matched_platform = True
                    break
            else:
                if if_platform == local_platform:
                    matched_platform = True
                    break

        if matched_platform:
            self.symbols['PLATFORM'] = local_platform
            logger.debug(f"Identified platform {local_platform}")
            return True

        return False

    def match_version(self, block):
        """
        If the block contains an if_version key, return true if the current
        version matches the value expression, else false.
        If the block does not contain an if_version key, return true
        """
        if "if_version" not in block:
            return True

        if_version = block["if_version"]
        # QQQ
        return True

    def execute_block(self, block):
        """
        Given a single block from the config, execute all actions
        sequentially
        """
        actions = block.get("actions")
        if actions is None:
            logger.error("Malformed configuration file (missing 'actions')")
            sys.exit(1)

        for action in actions:

            # Special option "fixed_dir" may cause action to be skipped
            if "fixed_dir" in action:
                if self.handle_fixed_dir(action):
                    continue

            if "url" in action:
                self.do_url(action)
            elif "unarchive" in action:
                self.do_unarchive(action)
            elif "run" in action:
                self.do_run(action)
            else:
                logger.error("Malformed configuration file (missing action directive)")
                sys.exit(1)

    def handle_fixed_dir(self, action):
        """
        Handler for 'fixed_dir' option. If this references a directory that
        already exists, presume this action has been completed previously.
        """

        fixed_dir = self.templatize(action["fixed_dir"])
        self.symbols["FIXED_DIR"] = fixed_dir

        return pathlib.Path(fixed_dir).exists()

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

    def do_url(self, action):
        """
        Handles a 'url' directive
        """

        template = string.Template(action["url"])
        url = template.substitute(**self.symbols)
        localfile = str(self.cache.get(url))

        # Handle strange redirects
        if "scrape_html" in action:
            localfile = self.scrape_html(localfile, action["scrape_html"])

        # Remember the downloaded file
        self.installer_file = localfile
        self.symbols['DL'] = localfile

    def do_unarchive(self, action):
        """
        Unarchives the downloaded file
        """

        unarchive_dir = self.installdir

        if "add_dir" in action:
            new_dir = pathlib.Path(self.installdir) / self.templatize(action["add_dir"])
            os.makedirs(new_dir, exist_ok=True)
            unarchive_dir = str(new_dir)

        logger.info(f"Unpacking archive into {unarchive_dir}")
        shutil.unpack_archive(self.installer_file, unarchive_dir)

    def do_run(self, action):
        """
        Runs a sequence of local commands from a 'run' directive
        """

        command_string = self.templatize(action["run"])
        environment = os.environ.copy()

        # PyInstaller binaries get LD_LIBRARY_PATH set for them, and that
        # can have unwanted side-effects for our own subprocesses. Remove
        # that here - it can still be set by an env: entry in cbdep.config.
        environment.pop("LD_LIBRARY_PATH", None)

        environment.update(action.get("env", {}))

        for command in command_string.splitlines():
            logger.debug(f"Running local command: {command}")
            run(command, shell=True, check=True, env=environment)

    def templatize(self, template):
        """
        Utility function for doing template substitution
        """

        return string.Template(template).substitute(**self.symbols)