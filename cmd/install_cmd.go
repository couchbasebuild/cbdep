package cmd

import (
	"bytes"
	"errors"
	"fmt"
	"io/ioutil"
	"log"
	"os"

	"github.com/codeclysm/extract"
	"github.com/couchbase/cbdep"

	cli "github.com/jawher/mow.cli"
)

func init() {
	RootApp.Command("install", "Install", func(cmd *cli.Cmd) {
		pkg := cmd.StringArg("PACKAGE", "", "Package to install")
		ver := cmd.StringArg("VERSION", "", "Version to install")
		dir := cmd.StringOpt("dir d", cbdep.DefaultInstallDir, "Directory to unpack into (not applicable for all packages)")
		platform := cmd.StringOpt("platform p", cbdep.Platform, "Local platform / distribution for downloading")
		cmd.Action = func() {
			var doFunc func(string, string, string) error
			switch *pkg {
			// QQQ Obviously these shouldn't be hard-coded
			case "golang":
				doFunc = doGolang
			case "python":
				doFunc = doPython
			default:
				log.Fatalf("Unknown package %s", *pkg)
				os.Exit(1)
			}

			if err := doFunc(*ver, *platform, *dir); err != nil {
				log.Fatalf("Error installing %s %s: %s", *pkg, *ver, err)
				os.Exit(1)
			}
		}
	})
}

// QQQ obviously this logic shouldn't be hardcoded
func doGolang(ver string, platform string, dir string) error {
	var ext string
	switch platform {
	case "windows":
		ext = "zip"
	default:
		ext = "tar.gz"
	}
	url := fmt.Sprintf("https://dl.google.com/go/go%s.%s-amd64.%s", ver, cbdep.Platform, ext)
	return doPackage("golang", ver, url, dir)
}

func doPython(ver string, platform string, dir string) error {
	// Error check - QQQ Linux-specific
	if dir != "/opt/cbdeps" {
		return errors.New("Python can only be installed in /opt/cbdeps")
	}

	url := fmt.Sprintf("http://latestbuilds.service.couchbase.com/builds/latestbuilds/cbdeps/python/%s/python-%s-x86_64-%s-cb1.tgz", ver, platform, ver)

	return doPackage("python", ver, url, dir)
}

func doPackage(pkg string, ver string, url string, dir string) error {
	ce, err := cbdep.Cache(url)
	if err != nil {
		return err
	}

	fmt.Printf("Unpacking %s %s into %s...\n", pkg, ver, dir)
	data, err := ioutil.ReadFile(ce.Filename)
	if err != nil {
		return err
	}
	buffer := bytes.NewBuffer(data)
	if err = extract.Archive(buffer, dir, nil); err != nil {
		return err
	}

	return nil
}
