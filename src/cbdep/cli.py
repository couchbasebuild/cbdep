"""
Dependency Management System
"""

import argparse
import cbdep
import importlib
import logging
import os
import os.path
import pathlib
import shutil
import sys
import yaml

from cbdep.cache import Cache
from cbdep.install import Installer
from cbdep.platform_introspection import get_arches, get_platforms, override_platforms, override_arch


# Set up logging and handler
logger = logging.getLogger('cbdep')
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(levelname)s: %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
handler.setLevel(logging.INFO)
logger.addHandler(handler)


class Cbdep:
    """

    """

    def __init__(self):
        cachedir = pathlib.Path.home() / ".cbdepcache"
        self.cache = Cache(str(cachedir))

    def do_cache(self, args):
        """
        Cache a URL
        """

        self.cache.get(args.url, args.recache)

        # Output the cache filename, if requested
        if args.report is not None:
            self.cache.report(args.url)

        # Save the cached file locally, if requested
        if args.output is not None:
            self.cache.save(args.url, args.output)

    @staticmethod
    def do_platform(self, args):
        """
        Display introspected platform information
        """

        logger.debug("Determining platform and arch...")
        print(get_platforms())
        print(get_arches())

    @staticmethod
    def loadconfig(args):
        """
        Returns the contents of the config file defining the available packages
        """

        yamlfile = args.config_file
        if yamlfile is not None:
            # Load text of file
            with open(yamlfile, 'r') as y:
                return y.read()

        return (importlib.resources.files(cbdep) / "cbdep.config").read_text()

    def do_install(self, args):
        """
        Install a package based on a descriptor YAML
        """

        installdir = args.dir
        if installdir is None:
            installdir = "install"
        installdir = str(pathlib.Path(installdir).resolve())

        installer = Installer.fromYaml(
            self.loadconfig(args),
            self.cache,
            get_platforms(),
            "x86" if args.x32 else get_arches()
        )
        installer.set_cache_only(args.cache_only)
        installer.set_recache(args.recache)
        if args.cache_local_file is not None:
            installer.set_from_local_file(args.cache_local_file)
            installer.set_cache_only(True)

        installer.install(
            args.package,
            args.version,
            args.base_url,
            installdir,
            args.cbdeps
        )

        if args.output is not None:
            logger.debug(f"Copying downloaded file to {args.output}")
            shutil.copy2(installer.get_installer_file(), args.output)

    def do_list(self, args):
        """
        List available packages
        """

        config = yaml.safe_load(self.loadconfig(args))
        pkgs = list(config['packages'].keys()) \
            + config['cbdeps']['packages']
        print(
            "Available packages (not all may be available on all platforms):"
        )
        for pkg in sorted(pkgs):
            print(f"  {pkg}")
        print()


def main():
    """
    """

    # PyInstaller binaries get LD_LIBRARY_PATH set for them, and that
    # can have unwanted side-effects for our own subprocesses. Remove
    # that here - it can still be set by a set_env: entry in cbdep.config
    # for an install directive.
    # This needs to be done very early - even the call to get_platforms()
    # below indirectly shells out to lsb_release.
    os.environ.pop("LD_LIBRARY_PATH", None)

    parser = argparse.ArgumentParser(
        description='Dependency Management System'
    )
    parser.add_argument(
        "--debug", action="store_true",
        help="Enable debugging output"
    )
    parser.add_argument(
        "-p", "--platform", type=str,
        default=None,
        help="Override detected platform (may be comma-separated list)"
    )
    parser.add_argument(
        "-a", "--arch", "--processor", type=str,
        default=None,
        help="Override detected architecture"
    )
    parser.add_argument(
        "-V", "--version", action="version",
        help="Display cbdep version information",
        version=f"cbdep version {importlib.metadata.version(__package__)}"
    )

    subparsers = parser.add_subparsers()

    cache_parser = subparsers.add_parser(
        "cache", help="Add downloaded URL to local cache"
    )
    cache_parser.add_argument("url", type=str, help="URL to cache")
    cache_parser.add_argument(
        "-r", "--report", action="store_true",
        help="Report the filename in the cache"
    )
    cache_parser.add_argument(
        "--recache", action="store_true",
        help="Re-download URL, replacing files in cache"
    )
    cache_parser.add_argument(
        "-o", "--output", type=str,
        help="Output cached file to a local file"
    )
    cache_parser.set_defaults(func=Cbdep.do_cache)

    install_parser = subparsers.add_parser(
        "install", help="Install a package"
    )
    install_parser.add_argument(
        "package", type=str, help="Package to install"
    )
    install_parser.add_argument(
        "version", type=str, help="Version to install"
    )
    install_parser.add_argument(
        "-3", "--x32", action="store_true",
        help="Download 32-bit package (default false; only works on "
             "a few packages)"
    )
    install_parser.add_argument(
        "-c", "--config-file", type=str,
        help="YAML file descriptor"
    )
    install_parser.add_argument(
        "-d", "--dir", type=str,
        help="Directory to unpack into (not applicable for all packages)"
    )
    install_parser.add_argument(
        "-b", "--base-url", type=str,
        help="Alternate base URL for downloading dep (only applicable to a few packages)"
    )
    install_parser.add_argument(
        "-C", "--cbdeps", action="store_true",
        help="Force interpreting 'package' as a cbdeps package"
    )
    install_parser.add_argument(
        "-n", "--cache-only", action='store_true',
        help="Only download any installer files, do not install"
    )
    install_parser.add_argument(
        "-r", "--report", action="store_true",
        help="Report the filename in the cache (only last-downloaded file"
            "in case of multiple downloads)"
    )
    install_parser.add_argument(
        "-o", "--output", type=str,
        help="Output cached file to a local file (only last-downloaded file"
            "in case of multiple downloads)"
    )
    install_parser.add_argument(
        "--recache", action="store_true",
        help="Re-download any installer files to cache, replacing files in cache"
    )
    install_parser.add_argument(
        "--cache-local-file", type=str,
        help="Populate cache with local file rather than downloading. Implies --cache-only."
    )
    install_parser.set_defaults(func=Cbdep.do_install)

    platform_parser = subparsers.add_parser(
        "platform", help="Dump introspected platform information"
    )
    platform_parser.set_defaults(func=Cbdep.do_platform)

    list_parser = subparsers.add_parser(
        "list", help="List available cbdep packages"
    )
    list_parser.add_argument(
        "-c", "--config-file", type=str, help="YAML file descriptor"
    )
    list_parser.set_defaults(func=Cbdep.do_list)

    args = parser.parse_args()

    # Set logging to debug level on stream handler if --debug was set
    if args.debug:
        handler.setLevel(logging.DEBUG)

    # Override architecture if specified
    if args.arch is not None:
        logger.debug(f"Overriding architecture to {args.arch}")
        override_arch(args.arch)

    # Override platform if specified
    if args.platform is not None:
        logger.debug(f"Overriding platform to {args.platform}")
        override_platforms(args.platform.split(','))

    # Check that a command was specified
    if "func" not in args:
        parser.print_help()
        sys.exit(1)

    cbdep = Cbdep()
    args.func(cbdep, args)


if __name__ == '__main__':
    main()
