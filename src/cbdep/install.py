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

from packaging.specifiers import SpecifierSet
from subprocess import run

import cbdep.zipfile_with_permissions as zipfile_with_permissions
from cbdep.platform_introspection import get_default_arches

logger = logging.getLogger("cbdep")
zipfile_with_permissions.register()


class Installer:
    """
    Manages caching installation files and unpacking them based on an
    installation template yaml file
    """

    def __init__(self, config, cache, platforms, arches):
        """
        Base constructor for class. "config" is a YAML object,
        "cache" is the cache directory, "platforms" is a list of
        platform names; "arches" is a list of architecture names.
        """

        # These fields are immutable and define the installation environment
        self.descriptor = config
        self.cache = cache
        self.platforms = platforms
        if not isinstance(self.platforms, list):
            self.platforms = [self.platforms]
        self.arches = arches
        if not isinstance(self.arches, list):
            self.arches = [self.arches]

        # Things that will be substituted in all templates
        self.symbols = dict()
        self.symbols["HOME"] = str(pathlib.Path.home())

        # Populated by install()
        self.package = None
        self.version = None
        self.safe_version = None
        self.base_url = None
        self.installdir = None

        # Default, can be overridden by self.set_cache_only()
        self.cache_only = False

        # Default, can be overridden by self.set_recache()
        self.recache = False

        # Default, can be overridden by self.set_from_local_file()
        self.from_local_file = None

        # Populated by do_url() to be the final single downloaded installer
        self.installer_file = None

        # Create a temp directory that action blocks can use
        self.temp_dir = tempfile.mkdtemp()
        self.symbols["TEMP_DIR"] = self.temp_dir

    def __del__(self):
        """
        Clean up
        """
        shutil.rmtree(self.temp_dir)

    @classmethod
    def fromYaml(cls, yamltext, cache, platforms, arches):
        """
        Constructor from a YAML configuration file
        """

        config = yaml.safe_load(yamltext)
        return cls(config, cache, platforms, arches)

    def copy(self):
        """
        Creates a new Installer object with the same configuration
        as this Installer. Necessary to call a nested install().
        """

        return Installer(
            self.descriptor, self.cache, self.platforms, self.arches
        )

    def set_cache_only(self, cache_only):
        """
        If set to true, then calling install() will only execute any
        'url' directives in the corresponding package
        """

        self.cache_only = cache_only

    def set_recache(self, recache):
        """
        If set to true, then calling install() will ignore any previously-
        cached installer files and re-download them (and add the new files
        to the cache, replacing old ones)
        """

        self.recache = recache

    def set_from_local_file(self, from_local_file):
        """
        If a filename is specified here, "cbdep install" will cache and use
        that file rather than downloading anything from the internet. Disables
        recaching.
        """

        self.from_local_file = pathlib.Path(from_local_file)
        self.set_recache(False)
        if not self.from_local_file.exists():
            logger.error(
                f"Specified local file {from_local_file} does not exist!")
            sys.exit(1)

    def get_installer_file(self):
        """
        Returns the (most recent) installer_file, ie, the resulting
        local filename of the most recent 'url' directive
        """

        return self.installer_file

    def install(self, package, version, base_url, inst_dir, force_cbdeps=False):
        """
        Entry point to install a version of named package
        """

        self.package = package
        self.symbols['PACKAGE'] = package
        self.version = version
        self.symbols['VERSION'] = version
        self.base_url = base_url

        # Make install inst_dir absolute
        # QQQ Should use .resolve() rather than .absolute() since the latter
        # is semi-documented and semi-deprecated. However .resolve() doesn't
        # actually work as documented on Windows (doesn't return an absolute
        # path), where .absolute() does. So...
        self.installdir = str(pathlib.Path(inst_dir).absolute())
        self.symbols['INSTALL_DIR'] = self.installdir

        # Determine descriptor block to use for package
        pkgs = self.descriptor.get("packages")
        if pkgs is None:
            logger.error("Malformed configuration file (missing 'packages')")
            sys.exit(1)
        blocks = pkgs.get(package)

        is_cbdeps = False
        if blocks is None:
            # Possibly a cbdeps package, try there
            cbdeps = self.descriptor.get("cbdeps")
            if cbdeps is not None:
                if package in cbdeps['packages'] or force_cbdeps:
                    blocks = cbdeps['descriptor']
                    is_cbdeps = True

        if blocks is None:
            logger.error(f"Unknown package: {package}")
            sys.exit(1)

        # Version number handling. We want the following variables available for
        # templates:
        #
        #  VERSION - exactly what was typed at the command line
        #
        #  VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH, VERSION_BUILD - up to
        #    four numeric components of VERSION
        #
        #  VERSION_MAJORMINORPATCH - the first three numeric components of
        #    VERSION joined with '.' characters
        #
        # We achieve this by splitting VERSION on any non-numeric characters,
        # and then populating an array "version_bits" with up to the first four
        # numbers. In general we do so strictly in order, padding with empty
        # strings; ie, the version is just "1.2", then "version_bits" will be
        # ['1', '2', '', ''].
        #
        # If there are more than four numeric components, for historic reasons
        # we consolidate the excess components into VERSION_PATCH, so that
        # VERSION_BUILD is always a single number.
        #
        # There are two exceptions to those overall rules: OpenJDK and classic
        # cbdeps, which will be handled in-line.
        is_openjdk = package.startswith("openjdk")
        if is_openjdk:
            # OpenJDK has two main exceptions:

            # 1. The build number is always separated with a '+'
            #    character or, in JDK 8, by "-b". Occasionally they also
            #    have a rebuild number, which is represented as an extra
            #    .X after the build number. This rebuild number is only
            #    for occasional repackaging and is not part of the
            #    "real" version, so we do not put it into version_bits.
            #    It is only available via VERSION, which remains exactly
            #    what was typed at the command line - fortunately that
            #    is the only place we need it.
            base_ver, build = re.split(r'\+|-b', self.version)
            build_bits = build.split('.')

            # 2. JDK 8 used "u" to separate MAJOR_VERSION and
            #    MINOR_VERSION, so split on non-numerics rather than
            #    non-alphanumerics.
            version_bits = re.split(r'[^0-9]+', f"{base_ver}+{build_bits[0]}")

        elif is_cbdeps:
            # A few cbdeps packages have version numbers with a "profile"
            # extension, which is separated by a _ character. So for those, we
            # don't want to split on that.
            version_bits = re.split(r'[^A-Za-z0-9_]+', self.version)

        elif package == "java":
            # "java" is a slight exception. Its versioning scheme is
            # truly bizarre; however, cbdep.config actually only cares
            # about VERSION, VERSION_MAJOR, and (only for JDK 8)
            # VERSION_MINOR which needs to be the part after "u" in the
            # JDK 8 versioning system. As above for openjdk, we split on
            # only non-numerics rather than non-alphanumerics. We don't
            # need to do anything different later, so we don't have an
            # is_java boolean here.
            version_bits = re.split(r'[^0-9]+', self.version)

        else:
            # Otherwise, split on any non-alphanumeric characters.
            version_bits = re.split(r'[^A-Za-z0-9]+', self.version)

        # When more than 4 version components are found, we need to do some
        # manipulation to ensure BUILD does not contain the additional info.
        # Instead, we dot-join anything between MINOR and BUILD and treat
        # the combined string as the PATCH component
        if len(version_bits) > 4:
            version_bits[2] = ".".join(version_bits[2:-1])
            version_bits[3] = version_bits[-1]
            version_bits = version_bits[:4]

        # Save a pkg_resources-compatible variant of the version number. Note
        # this will not contain the OpenJDK "rebuild" number if one exists.
        self.safe_version = '.'.join(version_bits)
        logger.debug(f"Safe version is {self.safe_version}")

        # OpenJDK versions were explained earlier. Cbdeps version numbers always
        # have a build number after a hyphen, eg. 71.1-1 or 54.1-cb10. For both
        # OpenJDK and Cbdeps, we want to make sure the final version component
        # is in the "build" slot.
        #
        # For non-OpenJDK/Cbdeps versions, just pad version_bits out to exactly
        # 4 slots.
        num_bits = len(version_bits)
        offset = num_bits - 1 if (is_openjdk or is_cbdeps) else num_bits
        version_bits[offset:0] = [''] * (4 - num_bits)

        self.symbols['VERSION_MAJOR'] = version_bits[0]
        self.symbols['VERSION_MINOR'] = version_bits[1]
        self.symbols['VERSION_PATCH'] = version_bits[2]
        self.symbols['VERSION_BUILD'] = version_bits[3]

        # Also provide single field of major.minor.patch with the appropriate
        # number of dots
        self.symbols['VERSION_MAJORMINORPATCH'] = '.'.join(
            [x for x in version_bits[:3] if x]
        )
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
            if self.match_platform(block) and \
               self.match_arch(block) and \
               self.match_version(block):
                return block

        return None

    def _match_system(self, block, if_directive, system_values, symbol):
        """
        Common implementation for if_platform and if_arch.
        """
        if if_directive not in block:
            return True

        # Create case-insensitive map of if_directive values
        if_directive_values = block[if_directive]
        if not isinstance(if_directive_values, list):
            if_directive_values = [if_directive_values]
        lc_directive_values = {x.casefold(): x for x in if_directive_values}

        matched_value = None
        for system_value in system_values:
            if system_value in lc_directive_values:
                matched_value = lc_directive_values[system_value]
                break

        if matched_value is not None:
            self.symbols[symbol] = matched_value
            logger.debug(f"Matched {symbol} {matched_value}")

            # Default value for PLATFORM_EXT - kind of a hack to put this here
            # QQQ Allow overriding in config
            if symbol == "PLATFORM":
                if matched_value.startswith(("win", "pc-win")):
                    self.symbols['PLATFORM_EXT'] = "zip"
                else:
                    self.symbols['PLATFORM_EXT'] = "tar.gz"

            return True

        return False

    def match_platform(self, block):
        """
        If the block contains an if_platform key, return true if the current
        platform is one of the values for that key, else false.
        If the block does not contain an if_platform key, return true
        """

        return self._match_system(
            block,
            "if_platform",
            self.platforms,
            "PLATFORM"
        )

    def match_arch(self, block):
        """
        If the block contains an if_arch key, return true if the current
        architecture is one of the values for that key, else false.
        If the block contains a default_arches or default_cbdeps_arches key,
        behave as though if_arch existed with a platform-dependent default
        set of arches.
        If the block does not contain either key, return true.
        """

        arches = None
        if "default_arches" in block:
            arches = get_default_arches()
        elif "default_cbdeps_arches" in block:
            arches = get_default_arches(cbdeps_arches=True)
        if arches is not None:
            block["if_arch"] = arches
            logger.debug(f"Set if_arch: {block['if_arch']}")

        return self._match_system(
            block,
            "if_arch",
            self.arches,
            "ARCH"
        )

    def match_version(self, block):
        """
        If the block contains an if_version key, return true if the current
        version matches the value expression, else false.
        If the block does not contain an if_version key, return true
        """
        if "if_version" not in block:
            return True

        # Read the if_version directive
        if_version = block.get("if_version", None)
        if not if_version:
            return True

        return SpecifierSet(if_version).__contains__(self.safe_version)

    def execute_block(self, block):
        """
        Given a single block from the config, execute all actions
        sequentially
        """

        # Set BASE_URL in the symbol table
        if "base_url" in block:
            self.handle_base_url(block.get("base_url"))

        # Enable any environment overrides
        if "set_env" in block:
            self.handle_set_env(block.get("set_env"))

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
            elif "cbdep" in action:
                self.do_cbdep(action)
            elif "install_dir" in action:
                self.do_install_dir(action)
            elif "unarchive" in action:
                self.do_unarchive(action)
            elif "run" in action:
                self.do_run(action)
            else:
                logger.error(
                    "Malformed configuration file (missing action directive)"
                )
                sys.exit(1)

    def handle_set_env(self, env_args):
        """
        Sets values in the cbdep process's environment
        """

        for env_arg in env_args:
            value = self.templatize(env_args[env_arg])
            logger.debug(f"Setting env {env_arg} to {value}")
            os.environ[env_arg] = value

    def handle_base_url(self, url):
        """
        Handles a 'base_url' directive
        """

        # If the user specified a base URL, use that; otherwise use the
        # default base URL specified by the config file
        if self.base_url is not None:
            base_url = self.base_url
            logger.debug(f"Using user-provided base URL {base_url}")
        else:
            base_url = url
            logger.debug(f"Using default base URL {base_url}")
        template = string.Template(base_url)
        self.symbols['BASE_URL'] = template.substitute(**self.symbols)

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
        with open(localfile, encoding='utf-8') as f:
            logger.debug(f"Searching {localfile} for {regexp}...")
            for line in f:
                match = matcher.search(line)
                if match:
                    url = match.group(1)
                    logger.debug(f"...found {url}")
                    return str(self.cache.get(url, self.recache))

        logger.error(f"Scraped HTML did not find {regexp}")
        sys.exit(1)

    def do_url(self, action):
        """
        Handles a 'url' directive
        """

        # Iterate through available URLs; use first successful download.
        # TODO This probably should somehow cache the result using the
        # first URL as a key, or similar. As it is now, if the second URL
        # is the "right" one, then any subsequent runs of cbdep will hit
        # the network first before discovering the right package in the cache.
        urls = action["url"]
        if not isinstance(urls, list):
            urls = [urls]

        exception = None
        for url in urls:
            template = string.Template(url)
            real_url = template.substitute(**self.symbols)

            # If we've been asked to use a local file, here is where we
            # pre-populate the cache
            if self.from_local_file is not None:
                self.cache.put(real_url, self.from_local_file)

            try:
                localfile = str(self.cache.get(real_url, self.recache))
                break
            except Exception as e:
                exception = e
        else:
            raise exception

        # Handle strange redirects
        if "scrape_html" in action:
            try:
                localfile = self.scrape_html(localfile, action["scrape_html"])
            except:
                # Try again just in case we've cached a bad HTML file
                logger.debug(
                    "Error parsing HTML, trying to get a fresh copy..")
                localfile = str(self.cache.get(real_url, True))
                localfile = self.scrape_html(localfile, action["scrape_html"])

        # Remember the downloaded file
        self.installer_file = localfile
        self.symbols['DL'] = localfile

    def do_install_dir(self, action):
        """
        Handles an 'install_dir' directive, which resets self.installdir
        """

        template = string.Template(action["install_dir"])
        self.installdir = template.substitute(**self.symbols)
        self.symbols['INSTALL_DIR'] = self.installdir
        logger.info(f"Overriding install dir to {self.installdir}")

    def do_unarchive(self, action):
        """
        Unarchives the downloaded file
        """

        install_dir = pathlib.Path(self.installdir)
        install_dir.mkdir(exist_ok=True, parents=True)

        args = action["unarchive"]

        # The standardized final location for the package. This
        # may already exist!
        if args and "target_dir" in args:
            target_dir_name = self.templatize(args["target_dir"])
        else:
            target_dir_name = f"{self.package}-{self.version}"
        target_dir = install_dir / target_dir_name

        # We extract the archive to a temporary directory
        temp_dir_handle = tempfile.TemporaryDirectory(dir=install_dir)
        temp_dir = pathlib.Path(temp_dir_handle.name)
        unpack_dir = temp_dir / 'unpack'
        unpack_dir.mkdir()
        logger.info(f"Unpacking archive to {target_dir}")

        try:
            shutil.unpack_archive(self.installer_file, unpack_dir)
        except UnicodeEncodeError as e:
            print("ERROR: Extraction failed - please check LANG/LC_ALL in your environment are pointing at character sets inclusive of UTF-8")
            sys.exit(1)

        # Now we want to find the single directory containing the
        # contents we care about from the unpacked archive.
        if args and "toplevel_dir" in args:
            toplevel_dir = self.templatize(args["toplevel_dir"])
            contents_dir = unpack_dir / toplevel_dir
            if not contents_dir.is_dir():
                logger.error(f"Archive does not contain directory {toplevel_dir}!")
                sys.exit(2)
        else:
            # The unpacked directory *itself* is the contents dir
            contents_dir = unpack_dir

        # Sometimes the contents dir needs to be wrapped in a new
        # directory, often "bin"
        if args and "create_toplevel_dir" in args:
            wrap_dir = temp_dir / 'wrap_dir'
            wrap_dir.mkdir()
            contents_dir.rename(
                wrap_dir / self.templatize(args["create_toplevel_dir"]))
            contents_dir = wrap_dir

        # Finally as atomically as possible, move the existing
        # target directory out of the way (if it exists) and move
        # the contents directory to the target directory.
        if target_dir.exists():
            target_dir.rename(temp_dir / "recycle")
        contents_dir.rename(target_dir)

    def do_cbdep(self, action):
        """
        Runs a nested "cbdep install" command
        """

        package = action["cbdep"]
        version = action["version"]
        install_dir = self.templatize(
            action.get("install_dir", self.installdir))

        installer = self.copy()
        logger.info(
            f"Calling nested cbdep install -d {install_dir} {package} {version}")
        installer.install(package, str(version), self.base_url, install_dir)

    def do_run(self, action):
        """
        Runs a sequence of local commands from a 'run' digrective
        """

        command_string = self.templatize(action["run"])

        for command in command_string.splitlines():
            logger.debug(f"Running local command: {command}")
            run(command, shell=True, check=True)

    def templatize(self, template):
        """
        Utility function for doing template substitution
        """

        return string.Template(template).substitute(**self.symbols)
