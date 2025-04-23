# cbdep wrapper scripts

Starting with 1.3.0, `cbdep` is deployed using `uv`. If it is installed
this way on an agent, it will work the same as before. However, a number
of CI jobs didn't expect to find `cbdep` on `$PATH`, and hence they
downloaded the executable every time from `packages.couchbase.com`.

To support this use case, this directory contains a script (for Linux
and MacOS) and a Go program (for Windows) that can be downloaded and run
directly. The general algorithm of both implementations is as follows:

    add `$HOME/.local/bin` to PATH
    if `$HOME/.local/bin/cbdep` does not exist:
        if `$HOME/.local/bin/uv` does not exist:
            install uv using downloaded installation script
        run `uv tool install cbdep`
    elif `$HOME/.local/bin/cbdep` is more than a couple days old:
        run `uv tool install --reinstall cbdep`
    run `$HOME/.local/bin/cbdep` passing through all arguments

That way, this script will automatically pick up new released versions
of cbdep.

## Installing uv

`uv` is a single binary file with no dependencies, so we could just
download it. However, it has a `curl | sh` recommended installer script
that handles a lot of things automatically such as picking the newest
version, downloading the correct platform/architecture, and so on, so it
made sense to just use that.

This script installs `uv` into `$HOME/.local/bin` on all platforms (or
the equivalent `%USERPROFILE%\.local\bin` on Windows), and
`uv tool install` also creates the installed `cbdep` binary there.

## Windows

On Linux/Mac, the above logic was a brief shell script, so the download
from `packages.couchbase.com` is under 1k now. On Windows, however, it
was far trickier (shocking, I know).

First and foremost, the Windows download needs to be called `cbdep.exe`
and it needs to actually be an `.exe` file, so writing a `.bat` or
`.ps1` script wouldn't be sufficient. Since I don't know C/C++ well
enough to implement that safely on Windows, I instead wrote a brief Go
program.

This Go program implements roughly the same logic as above, with one
small wrinkle: the `cbdep.exe` created by `uv` in
`%USERPROFILE\.local\bin` doesn't actually get modified when you run
`uv tool install --reinstall`. So if the Go program determines that file is
too old, it actually deletes it first, and then re-installs it with
`uv`.

Also, for reasons I'm not entirely clear on, the recommended Powershell
incantation to install `uv` fails with an SSL error on several Windows
systems. The workaround is to explicitly enable TLS1.2, which the Go
program does by passing additional commands to `powershell`.

I originally implemented this by having most of the logic in an
`install-cbdep.ps1` script, and having the Go program only download that
script and run it. However, while I got it working, this was far
trickier than I expected, mostly because Powershell is really awkward.
In particular, the `.ps1` file had to be completely on one line, or else
piping the download into `powershell` failed in very hard-to-predict
ways. Also, it turns out that after removing the `net/http` parts of the
Go program, the resulting `cbdep.exe` is 1/3 the size, which is good
since it will be downloaded from `packages.couchbase.com` repeatedly.

## Releasing wrapper scripts

I wrote `release-wrappers.sh` as a convenience to upload the wrapper
script/program to all the historical filenames on S3. Ideally, this
should only need to be run once, as these same wrappers should work
"forever". But, in case they need to be modified again, we can re-run
that script.
