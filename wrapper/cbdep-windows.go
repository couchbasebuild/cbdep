package main

import (
	"fmt"
	"io"
	"os"
	"os/exec"
	"time"
)

// Set the path to cbdep and uv
var cbdep = fmt.Sprintf("%s\\.local\\bin\\cbdep.exe", os.Getenv("USERPROFILE"))
var uv = fmt.Sprintf("%s\\.local\\bin\\uv.exe", os.Getenv("USERPROFILE"))

func installCbdep() {
	cmd := exec.Command(uv, "tool", "install", "--reinstall", "--python-preference=only-managed", "cbdep")
	cmd.Stdout = io.Discard
	cmd.Stderr = io.Discard

	err := cmd.Run()
	if err != nil {
		panic(err)
	}
}

func main() {

	// Check if cbdep exists
	if cbdep_info, err := os.Stat(cbdep); os.IsNotExist(err) {

		// Check if uv exists
		if _, err = os.Stat(uv); os.IsNotExist(err) {
			cmd := exec.Command("powershell", "-ExecutionPolicy", "Bypass",
				"-Command", "[Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12; irm https://astral.sh/uv/install.ps1 | iex")
			cmd.Stdout = io.Discard
			cmd.Stderr = io.Discard

			err = cmd.Run()
			if err != nil {
				panic(err)
			}
		}

		installCbdep()

	} else {

		// If cbdep exists, check if it's older than 48 hours
		cutoff := time.Now().Add(-48 * time.Hour)
		if cbdep_info.ModTime().Before(cutoff) {
			// If it's old, delete it and re-install - don't just re-install
			// because that doesn't actually change the modification time of
			// this uv-provided cbdep.exe
			err := os.Remove(cbdep)
			if err != nil {
				panic(err)
			}

			installCbdep()
		}
	}

	// Run cbdep, passing all of our arguments
	cmd := exec.Command(cbdep, os.Args[1:]...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	err := cmd.Run()
	if err != nil {
		// panic unless the error is just that the command exited with a
		// non-zero status
		exitErr, isExitError := err.(*exec.ExitError)
		if isExitError {
			os.Exit(exitErr.ExitCode())
		} else {
			panic(err)
		}
	}
}
