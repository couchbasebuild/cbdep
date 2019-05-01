"""
Functions for determining current platform information
"""

import platform


def get_platforms():
    """
    Returns a list of increasingly-generic identifiers for the current
    system.
    """

    # Start with the most generic - the OS
    system = platform.system().lower()

    # Initialize list
    platforms = [system]

    # OS-specific stuff
    if system == "linux":
        import distro

        dist_id = distro.id()
        platforms.insert(0, dist_id)

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

        platforms.insert(0, f"{dist_id}{dist_ver}")
        platforms.insert(0, f"{dist_id}-{dist_ver}")

        if dist_id == "sles" or dist_id.startswith("opensuse"):
            # Cbdeps 1.0, at least, refers to all SUSE as "suse", so offer
            # those as platform names too
            dist_id = "suse"
            platforms.insert(0, dist_id)
            platforms.insert(0, f"{dist_id}{dist_ver}")
            platforms.insert(0, f"{dist_id}-{dist_ver}")


    elif system == "darwin":
        platforms.insert(0, "macosx")
        platforms.insert(0, "macos")
        platforms.insert(0, "mac")
        platforms.insert(0, "osx")

    elif system == "windows":
        # QQQ Somehow introspect MSVC version?
        platforms.insert(0, "windows_msvc2015")

    return platforms
