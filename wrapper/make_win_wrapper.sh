#!/bin/bash -ex

export GOOS=windows
export GOARCH=amd64

go build cbdep-windows.go
