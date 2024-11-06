"""
Functions for determining current platform information
"""

import platform

_platforms = None
_arch = None

_intel_arches = ["x86_64", "amd64", "x64"]
_arm_arches = ["aarch64", "arm64", "aarch_64"]

def override_platforms(platforms):
    """
    Set platform to a specific value or values, to suppress introspection
    """

    global _platforms
    _platforms = platforms

def override_arch(arch):
    """
    Set initial architecture to specific value - additional synonyms may
    still be added
    """

    global _arch
    _arch = arch

def get_platforms():
    """
    Returns a list of increasingly-generic identifiers for the current
    system.
    """

    global _platforms
    if _platforms is not None:
        return _platforms

    # Start with the most generic - the OS
    system = platform.system().lower()

    # Initialize list with the system.
    _platforms = [system]

    # OS-specific stuff
    if system == "linux":
        import distro

        # Add distro-specific variants
        dist_id = distro.id()
        _platforms.insert(0, dist_id)

        if dist_id == "ubuntu":
            # Ubuntu "minor" versions are distinct, eg., Ubuntu 16.10
            # is potentially quite different from Ubuntu 16.04. So we
            # want to use the combined version.
            dist_ver = distro.version()
        else:
            # Other supported distros use rolling releases, so eg.
            # Centos 6.5 shouldn't differ importantly from Centos 6.9.
            # Use only the major version number.
            dist_ver = distro.major_version()

        _platforms.insert(0, f"{dist_id}{dist_ver}")
        _platforms.insert(0, f"{dist_id}-{dist_ver}")

        if dist_id == "sles" or dist_id.startswith("opensuse"):
            # Cbdeps 1.0, at least, refers to all SUSE as "suse", so offer
            # those as platform names too
            dist_id = "suse"
            _platforms.insert(0, dist_id)
            _platforms.insert(0, f"{dist_id}{dist_ver}")
            _platforms.insert(0, f"{dist_id}-{dist_ver}")

        # Add the "target triple" version
        if dist_id == "alpine":
            _platforms.insert(0, "unknown-linux-musl")
        else:
            _platforms.insert(0, "unknown-linux-gnu")

    elif system == "darwin":
        _platforms.insert(0, "apple-darwin")
        _platforms.insert(0, "macosx")
        _platforms.insert(0, "macos")
        _platforms.insert(0, "mac")
        _platforms.insert(0, "osx")

    elif system == "windows":
        # QQQ Somehow introspect MSVC version?
        _platforms.insert(0, "windows_msvc2015")
        _platforms.insert(0, "windows_msvc2017")
        _platforms.insert(0, "pc-windows-msvc")
        _platforms.insert(0, "win")

    return _platforms

def _alpine_mod(arches):
    """
    If this is Alpine Linux, append "musl" and "alpine" to each arch
    entry in arches. This appears to be a common convention (at least
    nodejs, dotnet, and Bellsoft OpenJDK use it).
    """

    if "alpine" not in get_platforms():
        return arches.copy()
    return [f"{arch}{suffix}"
        for arch in arches
        for suffix in ["-musl", "-alpine", ""]
    ]

def get_arches():
    """
    Returns a list of possible architectures based on the current system
    """

    global _arch, _intel_arches, _arm_arches

    # Start from "machine" type (possibly overridden)
    if _arch is not None:
        arch = _arch
    else:
        arch = platform.machine().casefold()

    # If we recognize this as being Intel or ARM, return a set of common
    # synonyms
    if arch in _intel_arches:
        return _alpine_mod(_intel_arches)
    if arch in _arm_arches:
        return _alpine_mod(_arm_arches)
    # Otherwise, just return what we've got
    return _alpine_mod([arch])

def get_default_arches(cbdeps_arches=False):
    """
    Returns a platform-dependent value suitable for if_arch directives.
    Important: this is a list of arch names most frequently used in *package*
    filenames for a given OS. It should *not* contain any "synonyms", like
    "arm64" and "aarch64", or "x86_64" and "amd64", because given the way
    if_arch works, only the first will ever get matched. Basically these
    should contain just the most common name (if any) for "32-bit Intel",
    "64-bit Intel", "64-bit ARM", and any other supported arches on each OS.
    """

    for plat in get_platforms():
        if plat.startswith("win"):
            if cbdeps_arches:
                return ["x86", "amd64", "arm64"]
            else:
                return ["x86", "x86_64", "arm64"]
        elif "darwin" in plat or "mac" in plat:
            return ["x86_64", "arm64"]
        elif "android" in plat:
            return ["armv7a", "aarch64", "i686", "x86_64"]

    # Didn't find anything else, so return the list for Linux, including Alpine
    return ["x86", "x86_64", "aarch64", "x64-musl"]
