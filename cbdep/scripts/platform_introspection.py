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
    platforms = [ system ]

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
            # Use only the major version number
            dist_ver = distro.major_version()

        platforms.insert(0, dist_id + dist_ver)

    elif system == "darwin":
        platforms.insert(0, "macosx")
        platforms.insert(0, "macos")

    return platforms
