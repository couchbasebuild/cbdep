#!/bin/bash -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &>/dev/null && pwd )"

CBDEP_PRODUCTS=$(yq e ".cbdeps.packages" "${SCRIPT_DIR}/../../cbdep.config" | sed "s/^- //g" | grep -v "^#")
WD=$(mktemp -d)
mkdir -p ${WD}/unpack
cp ../../dist/cbdep "${WD}"

CMAKE_MANIFEST="https://raw.githubusercontent.com/couchbase/tlm/master/deps/manifest.cmake"
curl -fL -o "manifest.cmake" "${CMAKE_MANIFEST}"

ALL_DEPS=$(grep "^DECLARE_DEP" manifest.cmake)
AMZN2_V1_DEPS=$(echo "${ALL_DEPS}" | grep -v V2 | grep amzn2 | awk '{print substr($2,2,length($2)), $4}')
LINUX_V1_DEPS=$(echo "${ALL_DEPS}" | grep -v V2 | grep linux | awk '{print substr($2,2,length($2)), $4}')
AMZN2_V2_DEPS=$(echo "${ALL_DEPS}" | grep 'DECLARE_DEP.*V2' | grep amzn2 | awk '{print substr($2,2,length($2)), $5, $7}')
LINUX_V2_DEPS=$(echo "${ALL_DEPS}" | grep 'DECLARE_DEP.*V2' | grep linux | awk '{print substr($2,2,length($2)), $5, $7}')

function log() {
    echo "$*" | tee -a ${WD}/log
}

function partial_log() {
    printf "$*" | tee -a ${WD}/log
}

function introspect() {
    echo "Checking environment"
    if [ "$(uname)" = "Darwin" ]
    then
        PLATFORM="macosx"
    else
        PLATFORM="linux"
    fi
    ARCH=$(uname -m)
}

function check_v1_dep() {
    PRODUCT=${1}
    VERSION=${2}
    PLATFORM=${3}
    FILENAME="${PRODUCT}-${PLATFORM}-${ARCH}-${VERSION}.tgz"
    URL="https://packages.couchbase.com/couchbase-server/deps/${PRODUCT}/${VERSION}/${FILENAME}"
    MD5=$(echo -n "${URL}" | md5sum | awk '{print $1}')
    [ "${MD5}" != "" -a -d "~/.cbdepcache/${MD5:0:2}" ] && rm -rf "~/.cbdepcache/${MD5:0:2}"
    partial_log "Installing ${PRODUCT} ${VERSION} (${PLATFORM})... "
    ./cbdep -p ${PLATFORM} install -d $(pwd)/unpack -n $PRODUCT $VERSION &>/dev/null
    curl -fLO ${URL} &>/dev/null
    if [ "$(md5sum ${FILENAME} | sed 's/ .*//')" != "$(md5sum ~/.cbdepcache/${MD5:0:2}/${MD5}/${FILENAME} | sed 's/ .*//')" ]
    then
      echo "ERROR: ${PRODUCT} md5s didn't match!"
      rm -f ${FILENAME}
      exit 1
    else
      log "success!"
      rm -f ${FILENAME}
    fi
}

function check_v2_dep() {
    PRODUCT=${1}
    VERSION=${2}
    BLD_NUM=${3}
    PLATFORM=${4}
    FILENAME="${PRODUCT}-${PLATFORM}-${ARCH}-${VERSION}-${BLD_NUM}.tgz"
    URL="https://packages.couchbase.com/couchbase-server/deps/${PRODUCT}/${VERSION}/${BLD_NUM}/${FILENAME}"
    MD5=$(echo -n "${URL}" | md5sum | awk '{print $1}')
    [ "${MD5}" != "" -a -d "~/.cbdepcache/${MD5:0:2}" ] && rm -rf "~/.cbdepcache/${MD5:0:2}"
    partial_log "Installing ${PRODUCT} ${VERSION} ${BLD_NUM} (${PLATFORM})... "
    ./cbdep -p ${PLATFORM} install -d $(pwd)/unpack -n $PRODUCT $VERSION-$BLD_NUM &>/dev/null
    curl -fLO ${URL} &>/dev/null
    if [ "$(md5sum ${FILENAME} | sed 's/ .*//')" != "$(md5sum ~/.cbdepcache/${MD5:0:2}/${MD5}/${FILENAME} | sed 's/ .*//')" ]
    then
      echo "ERROR: ${PRODUCT} md5s didn't match!"
      rm -f ${FILENAME}
      exit 1
    else
      log "success!"
      rm -f ${FILENAME}
    fi
}

function check_all_v1_cbdeps() {
    PLATFORM=$1
    LIST=$2
    log "Testing $1 v1 cbdeps:"
    echo "$2" | while IFS= read -r dep
    do
        IFS=" " read PRODUCT VERSION <<< ${dep}
        if echo ${CBDEP_PRODUCTS} | grep ${PRODUCT} &>/dev/null
        then
            check_v1_dep $PRODUCT $VERSION $PLATFORM
        fi
    done
}

function check_all_v2_cbdeps() {
    PLATFORM=$1
    LIST=$2
    log "Testing $1 v2 cbdeps:"
    echo "$2" | while IFS= read -r dep
    do
        IFS=" " read PRODUCT VERSION BLD_NUM <<< ${dep}
        if echo ${CBDEP_PRODUCTS} | grep ${PRODUCT} &>/dev/null
        then
            check_v2_dep $PRODUCT $VERSION $BLD_NUM $PLATFORM
        fi
    done
}

function check_one_package() {
    local PACKAGE=$1
    local VERSION=$2
    local PLATFORM=${3:-$PLATFORM}
    partial_log "Installing ${PACKAGE} ${VERSION} (${PLATFORM})... "
    if ! ./cbdep -p ${PLATFORM} install -d ./installs/ ${PACKAGE} ${VERSION} &>/dev/null; then
        echo
        echo "FATAL: ${PACKAGE} ${VERSION} install failed"
        exit 1
    else
        log "success!"
    fi
}

function check_all_packages() {
    local PLATFORM=$1
    log "Testing packages"
    # This should maybe be derived from extra fields in cbdep.config
    check_one_package uv 0.4.29 unknown-linux-gnu
    check_one_package openjdk 9.0.4+11
    check_one_package openjdk 8u282-b08
    check_one_package openjdk 11.0.9.1+1
    check_one_package openjdk 11.0.9+11
    # openjdk with a dotted build number (CBD-5669)
    check_one_package openjdk 17.0.9+9.1 windows
    check_one_package openjdk-jre 9.0.4+11
    check_one_package openjdk-jre 8u282-b08
    check_one_package openjdk-jre 11.0.9.1+1
    check_one_package openjdk-jre 11.0.9+11
    check_one_package corretto 11.0.21.9.1
    check_one_package python 3.9.1
    check_one_package miniforge3 22.9.0-1
    check_one_package mambaforge 4.13.0-1
    check_one_package miniconda3-py38 4.12.0
    check_one_package miniconda3-py39 4.12.0
    check_one_package miniconda2 4.5.11
    check_one_package cmake 3.25.0-rc4
    check_one_package cmake 3.24.3
    check_one_package ninja 1.11.1
    # check_one_package wix 3.11.2 windows # windows only
    check_one_package jq 1.6
    check_one_package prometheus 2.40.1
    check_one_package golang 1.19.3
    check_one_package dotnet-core-sdk 7.0.100
    check_one_package dotnet-core-runtime 6.0.11
    check_one_package docker 20.10.21
    check_one_package nodejs 18.12.1
    # check_one_package php 7.3.4-cb1 - legacy package, can't find any installation candidates?
    check_one_package php-nts 8.1.4-cb1
    check_one_package php-zts 8.1.4-cb1
    check_one_package libcouchbase_vc11 2.9.5 windows
    check_one_package libcouchbase_vc14 3.0.0 windows
    check_one_package couchbasemock 1.5.25
    check_one_package analytics-jars 7.0.5-7643
}

introspect
pushd ${WD}

check_all_packages ${PLATFORM}

check_all_v1_cbdeps linux "$LINUX_V1_DEPS"
check_all_v2_cbdeps linux "$LINUX_V2_DEPS"

# Ensure we check a cbdep with 4 version parts
check_v2_dep erlang 24.3.4.4 4 linux
