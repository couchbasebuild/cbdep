import os
import sys
import zipfile
from shutil import ReadError, _ensure_directory, copyfileobj, register_unpack_format, unregister_unpack_format

"""
Works around two failings in the Python standard library:
1. shutil.extract_archive() does custom handling for zips rather than
   just calling zipfile.extractall()
2. zipfile itself makes note of file permissions in the .zip but does
   not apply them on unpacking
"""

class ZipFileWithPermissions(zipfile.ZipFile):
    """
    Custom ZipFile class handling file permissions.
    """
    def _extract_member(self, member, targetpath, pwd):
        if not isinstance(member, zipfile.ZipInfo):
            member = self.getinfo(member)

        targetpath = super()._extract_member(member, targetpath, pwd)

        # Only attempt permission fixes if the zip file reports itself
        # as being created on a Unix-like system
        if member.create_system == 3:
            attr = member.external_attr >> 16
            if attr != 0:
                os.chmod(targetpath, attr)

        return targetpath

def _unpack_zipfile_with_permissions(filename, extract_dir):
    """
    Unpack zip `filename` to `extract_dir`
    """
    if not zipfile.is_zipfile(filename):
        raise ReadError("%s is not a zip file" % filename)

    with ZipFileWithPermissions(filename) as zip:
        zip.extractall(path=extract_dir)

def register():
    """
    Configures shutil.unpack_archive to use our custom unzipper
    """
    if sys.platform != "win32":
        unregister_unpack_format('zip')
        register_unpack_format('zip', ['.zip'], _unpack_zipfile_with_permissions)
