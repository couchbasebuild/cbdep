"""
Functions for determining current platform information
"""

import platform

_platforms = None

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

    # Initialize list
    _platforms = [system]

    # OS-specific stuff
    if system == "linux":
        import distro

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


    elif system == "darwin":
        _platforms.insert(0, "macosx")
        _platforms.insert(0, "macos")
        _platforms.insert(0, "mac")
        _platforms.insert(0, "osx")

    elif system == "windows":
        # QQQ Somehow introspect MSVC version?
        _platforms.insert(0, "windows_msvc2015")
        _platforms.insert(0, "windows_msvc2017")
        _platforms.insert(0, "win")

    return _platforms

def get_arches():
    """
    Returns a list of possible architectures based on the current system
    """

    # Start from "machine" type, and add some synonyms
    arches = []

    arch = platform.machine().casefold()

    if arch == "amd64" or arch == "x86_64":
        arches.extend(["x86_64", "amd64", "x64"])
    elif arch == "aarch64" or arch == "arm64":
        arches.extend(["aarch64", "arm64"])

    return arches

def get_default_arches():
    """
    Returns a platform-dependent value suitable for if_arch directives.
    Important: this is a list of arch names most frequently used in *package*
    filenames for a given OS. It should *not* contain any "synonyms", like
    "arm64" and "aarch64", or "x86_64" and "amd64", because given the way
    if_arch works, only the first will ever get matched. Basically these
    should contain just the most common name (if any) for "32-bit Intel",
    "64-bit Intel", and "64-bit ARM" on each OS.
    """

    if "linux" in get_platforms():
        return ["x86", "x86_64", "aarch64"]
    elif "windows" in get_platforms():
        return ["x86", "x86_64"]
    elif "darwin" in get_platforms():
        return ["x86_64", "arm64"]
    else:
        # Probably shouldn't happen, but we definitely don't know any defaults
        return []
