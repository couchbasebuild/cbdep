#!/bin/bash

for unix in cbdep-darwin cbdep-darwin-arm64 cbdep-darwin-x86_64 cbdep-linux cbdep-linux-aarch64 cbdep-linux-x64-musl cbdep-linux-x86_64; do
    aws s3 cp --acl public-read cbdep s3://packages.couchbase.com/cbdep/$unix
done

if [ ! -e cbdep-windows.exe ]; then
    ./make_win_wrapper.sh
fi
for win in cbdep-windows-x86_64.exe cbdep-windows.exe cbdep-windows_x86_64.exe cbdep.exe; do
    aws s3 cp --acl public-read cbdep-windows.exe s3://packages.couchbase.com/cbdep/$win
done
aws cloudfront create-invalidation --distribution-id E1U7LG5JV48KNP --paths '/cbdep/*'
