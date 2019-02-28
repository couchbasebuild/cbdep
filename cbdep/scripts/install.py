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

from pkg_resources import Requirement
from subprocess import run

logger = logging.getLogger("cbdep")


class Installer:
    """
    Manages caching installation files and unpacking them based on an
    installation template yaml file
    """

    def __init__(self, config, cache, platforms):
        """
        Base constructor for class. "config" is a YAML object,
        "cache" is the cache directory, "platforms" is a list of
        platform names.
        """

        # These fields are immutable and define the installation environment
        self.descriptor = config
        self.cache = cache
        self.platforms = platforms
        if not isinstance(self.platforms, list):
            self.platforms = [self.platforms]

        # Things that will be substituted in all templates
        self.symbols = dict()
        self.symbols["HOME"] = str(pathlib.Path.home())

        # Populated by install()
        self.package = None
        self.version = None
        self.safe_version = None
        self.installdir = None

        # Default, can be overridden by self.cacheOnly()
        self.cache_only = False

        # Populated by do_url() to be the final single downloaded installer
        self.installer_file = None

        # Create a temp directory that action blocks can use
        self.temp_dir = tempfile.mkdtemp()
        self.symbols["TEMP_DIR"] = self.temp_dir
        self.x32 = None

    def __del__(self):
        """
        Clean up
        """
        shutil.rmtree(self.temp_dir)

    @classmethod
    def fromYaml(cls, yamlfile, cache, platforms):
        """
        Constructor from a YAML configuration file
        """

        with open(yamlfile) as y:
            config = yaml.load(y)
        return cls(config, cache, platforms)

    def copy(self):
        """
        Creates a new Installer object with the same configuration
        as this Installer. Necessary to call a nested install().
        """

        return Installer(
            self.descriptor, self.cache, self.platforms
        )

    def set_cache_only(self, cache_only):
        """
        If set to true, then calling install() will only execute any
        'url' directives in the corresponding package
        """

        self.cache_only = cache_only

    def get_installer_file(self):
        """
        Returns the (most recent) installer_file, ie, the resulting
        local filename of the most recent 'url' directive
        """

        return self.installer_file

    def install(self, package, version, x32, inst_dir):
        """
        Entry point to install a version of named package
        """

        self.package = package
        self.symbols['PACKAGE'] = package
        self.version = version
        self.symbols['VERSION'] = version
        self.x32 = x32

        # Make install inst_dir absolute
        # QQQ Should use .resolve() rather than .absolute() since the latter
        # is semi-documented and semi-deprecated. However .resolve() doesn't
        # actually work as documented on Windows (doesn't return an absolute
        # path), where .absolute() does. So...
        self.installdir = str(pathlib.Path(inst_dir).absolute())
        self.symbols['INSTALL_DIR'] = self.installdir

        # Provide version components separately - split on any non-numeric
        # characters; set up to four components (major, minor, patch, build)
        split_re = re.compile('[^0-9]+')
        version_bits = split_re.split(self.version)

        # Save a pkg_config-compatible variant of the version number
        self.safe_version = '.'.join(version_bits)
        logger.debug(f"Safe version is {self.safe_version}")

        # Make sure version_bits is 4 elements long
        version_bits = (version_bits + 4 * [''])[:4]

        # Special nonsense for Java - version numbers have either 1 or 3
        # component (eg. "11" followed by "11.0.1"), but then also have
        # a build number after a + (eg., "11+28" followed by "11.0.1+13").
        # So if this is Java/OpenJDK and "patch" and "build" are empty,
        # re-arrange the numbers.
        if package.startswith("java") or package.startswith("openjdk"):
            if not version_bits[2] and not version_bits[3]:
                version_bits[3] = version_bits[1]
                version_bits[1] = ''

        self.symbols['VERSION_MAJOR'] = version_bits[0]
        self.symbols['VERSION_MINOR'] = version_bits[1]
        self.symbols['VERSION_PATCH'] = version_bits[2]
        self.symbols['VERSION_BUILD'] = version_bits[3]

        # Also provide single field of major.minor.patch with the appropriate
        # number of dots
        self.symbols['VERSION_MAJORMINORPATCH'] = '.'.join(
            [x for x in version_bits[:3] if x]
        )

        pkgs = self.descriptor.get("packages")
        if pkgs is None:
            logger.error("Malformed configuration file (missing 'packages')")
            sys.exit(1)

        blocks = pkgs.get(package)
        if blocks is None:
            classics = self.descriptor.get("classic-cbdeps")
            if classics is not None:
                # Possibly a "classic" cbdeps package
                if package in classics['packages']:
                    blocks = classics['descriptor']

        if blocks is None:
            logger.error(f"Unknown package: {package}")
            sys.exit(1)

        logger.debug(f"Starting install for package {package}")

        block = self.find_block(blocks)
        if block is None:
            logger.error(f"No blocks for package {package} {version} "
                         f"are appropriate for current system")
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

        # Create case-insensitive map of if_platform values
        if_platform = block["if_platform"]
        if not isinstance(if_platform, list):
            if_platform = [if_platform]
        lc_platforms = {x.casefold(): x for x in if_platform}

        matched_platform = None
        for local_platform in self.platforms:
            if local_platform in lc_platforms:
                matched_platform = lc_platforms[local_platform]
                break

        if matched_platform is not None:
            self.symbols['PLATFORM'] = matched_platform
            logger.debug(f"Identified platform {matched_platform}")

            # Default value for PLATFORM_EXT
            # QQQ Allow overriding in config
            if local_platform == "windows":
                self.symbols['PLATFORM_EXT'] = "zip"
            else:
                self.symbols['PLATFORM_EXT'] = "tar.gz"

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

        # Read the if_version directive, and ensure it is a list
        if_version = block["if_version"]
        if not isinstance(if_version, list):
            if_version = [if_version]

        for requirement in if_version:
            # Create a Requirement for this directive. The package name in the
            # Requirement spec is not actually used, but may as well use the
            # package name we have
            req = Requirement.parse(self.package + requirement)

            # And check the version we're installing against the Requirement
            if req.__contains__(self.safe_version):
                return True

        # If we had an if_version directive and none of them matches the
        # version being installed, this block doesn't apply
        return False

    def execute_block(self, block):
        """
        Given a single block from the config, execute all actions
        sequentially
        """

        # Set ARCH in the symbol table
        if "set_arch" in block:
            self.handle_set_arch(block.get("set_arch"))

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
            elif self.cache_only:
                # Skip any other actions if doing cache-only
                continue
            elif "unarchive" in action:
                self.do_unarchive(action)
            elif "cbdep" in action:
                self.do_cbdep(action)
            elif "run" in action:
                self.do_run(action)
            elif "rename_dir" in action:
                self.do_rename_dir(action)
            else:
                logger.error(
                    "Malformed configuration file (missing action directive)"
                )
                sys.exit(1)

    def handle_set_arch(self, arch_args):
        """
        Sets ARCH in the symbol table based on the current value of x32
        """
        self.symbols['ARCH'] = arch_args[0] if self.x32 else arch_args[1]

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
            new_dir = (pathlib.Path(self.installdir) /
                       self.templatize(action["add_dir"]))
            os.makedirs(new_dir, exist_ok=True)
            unarchive_dir = str(new_dir)

        logger.info(f"Unpacking archive into {unarchive_dir}")
        shutil.unpack_archive(self.installer_file, unarchive_dir)

    def do_cbdep(self, action):
        """
        Runs a nested "cbdep install" command
        """

        package = action["cbdep"]
        version = action["version"]
        install_dir = self.templatize(action["install_dir"])
        x32 = action.get("x32", False)

        installer = self.copy()
        installer.install(package, version, x32, install_dir)

    def do_run(self, action):
        """
        Runs a sequence of local commands from a 'run' directive
        """

        command_string = self.templatize(action["run"])
        environment = os.environ.copy()
        environment.update(action.get("env", {}))

        for command in command_string.splitlines():
            logger.debug(f"Running local command: {command}")
            run(command, shell=True, check=True, env=environment)

    def do_rename_dir(self, action):
        """
        Renames a specified top-level directory to the standardized
        ${PACKAGE}-${VERSION}
        """

        top_dir = (pathlib.Path(self.installdir) /
                   self.templatize(action["rename_dir"]))
        top_dir.rename(pathlib.Path(self.installdir) /
                       f"{self.package}-{self.version}")

    def templatize(self, template):
        """
        Utility function for doing template substitution
        """

        return string.Template(template).substitute(**self.symbols)
