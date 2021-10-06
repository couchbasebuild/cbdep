#!/bin/bash -ex

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &>/dev/null && pwd )"

PRODUCTS=$(yq e ".classic-cbdeps.packages" "${SCRIPT_DIR}/../../cbdep.config" | sed "s/^- //g" | grep -v "^#")
WD=$(mktemp -d)
mkdir -p ${WD}/unpack
cp ../../dist/cbdep "${WD}"

CMAKE_MANIFEST="https://raw.githubusercontent.com/couchbase/tlm/master/deps/manifest.cmake"
curl -fL -o "manifest.cmake" "${CMAKE_MANIFEST}"
ALL_DEPS=$(grep "^DECLARE_DEP" manifest.cmake)
V1_DEPS=$(echo "${ALL_DEPS}" | grep -v V2 | awk '{print substr($2,2,length($2)), $4}')

function log() {
    echo "$*" >> ${WD}/log
}

function introspect() {
    echo "Checking environment"
    if [ "$(uname)" = "Darwin" ]
    then
        PLATFORM="macosx"
    fi
    ARCH=$(uname -m)
}

function check_dep() {
    PRODUCT=${1}
    VERSION=${2}
    FILENAME="${PRODUCT}-${PLATFORM}-${ARCH}-${VERSION}.tgz"
    URL="https://packages.couchbase.com/couchbase-server/deps/${PRODUCT}/${VERSION}/${FILENAME}"
    MD5=$(echo -n "${URL}" | md5sum | awk '{print $1}')
    [ "${MD5}" != "" -a -d "~/.cbdepcache/${MD5:0:2}" ] && rm -rf "~/.cbdepcache/${MD5:0:2}"
    ./cbdep install -d $(pwd)/unpack -n $PRODUCT $VERSION
    curl -fLO ${URL}
    if [ "$(md5sum ${FILENAME} | sed 's/ .*//')" != "$(md5sum ~/.cbdepcache/${MD5:0:2}/${MD5}/${FILENAME} | sed 's/ .*//')" ]
    then
      echo "ERROR: ${PRODUCT} md5s didn't match!"
      rm -f ${FILENAME}
      exit 1
    else
      log "  ${PRODUCT} ${VERSION}"
      rm -f ${FILENAME}
    fi
}

function check_all_deps() {
    log "Tested Packages:"
    echo "$V1_DEPS" | while IFS= read -r dep
    do
        IFS=" " read PRODUCT VERSION <<< ${dep}
        if echo ${PRODUCTS} | grep ${PRODUCT}
        then
            check_dep $PRODUCT $VERSION
        fi
    done
}

introspect
pushd ${WD}
check_all_deps
cat log
