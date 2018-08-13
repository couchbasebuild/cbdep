package main

import (
	"os"

	"github.com/couchbase/cbdep/cmd"
)

func main() {
	cmd.RootApp.Run(os.Args)
}
