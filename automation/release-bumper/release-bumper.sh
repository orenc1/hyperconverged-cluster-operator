#!/bin/bash

CONFIG_FILE="hack/config"

function main {
  declare -A CURRENT_VERSIONS
  declare -A UPDATED_VERSIONS
  declare SHOULD_UPDATED

  echo "Getting Components current versions..."
  get_current_versions

  echo "Getting Components updated versions..."
  get_updated_versions

  echo "Comparing Versions..."
  compare_versions

  if [ ${#SHOULD_UPDATED[@]} == 0 ]; then
    echo "All components are already in latest version.";
    exit 0;
  fi

  update_versions
}

function get_current_versions {
  CURRENT_VERSIONS=(
    ["KUBEVIRT"]=""
    ["CDI"]=""
    ["NETWORK_ADDONS"]=""
    ["SSP"]=""
    ["NMO"]=""
    ["HPPO"]=""
    ["HPP"]=""
#    ["CONVERSION_CONTAINER"]=""
#    ["VMWARE_CONTAINER"]=""
  )

  for component in "${!CURRENT_VERSIONS[@]}"; do
    CURRENT_VERSIONS[$component]=$(grep "$component"_VERSION ${CONFIG_FILE} | cut -d "=" -f 2)
    done;
}

function get_updated_versions {
  declare -A COMPONENTS_REPOS=(
    ["KUBEVIRT"]="kubevirt/kubevirt"
    ["CDI"]="kubevirt/containerized-data-importer"
    ["NETWORK_ADDONS"]="kubevirt/cluster-network-addons-operator"
    ["SSP"]="MarSik/kubevirt-ssp-operator"
    ["NMO"]="kubevirt/node-maintenance-operator"
    ["HPPO"]="kubevirt/hostpath-provisioner-operator"
    ["HPP"]="kubevirt/hostpath-provisioner"
#    ["CONVERSION_CONTAINER"]=""
#    ["VMWARE_CONTAINER"]=""
  )

  UPDATED_VERSIONS=()
  for component in "${!COMPONENTS_REPOS[@]}"; do
    UPDATED_VERSIONS[$component]=\"$(get_latest_release "${COMPONENTS_REPOS[$component]}")\";
    done;
}

function get_latest_release() {
#  curl -s -L --silent "https://api.github.com/repos/$1/releases/latest" | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/'
  curl --silent -H "Authorization: token 57c6f8756df37b549ee0f42c1f9364a06f83dba4" https://api.github.com/repos/$1/releases/latest | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/'
}

function compare_versions() {
  for component in "${!UPDATED_VERSIONS[@]}"; do
    if [ ! "${UPDATED_VERSIONS[$component]}" == "${CURRENT_VERSIONS[$component]}" ]; then
      echo $component is outdated. current: "${CURRENT_VERSIONS[$component]}", updated: "${UPDATED_VERSIONS[$component]}"
      SHOULD_UPDATED+=( $component )
    fi;
  done;
}

function update_versions() {
  for component in "${SHOULD_UPDATED[@]}"; do
    echo $component;
    sed -E -i "s/(""$component""_VERSION=).*/\1${UPDATED_VERSIONS[$component]}/" ${CONFIG_FILE}
  done;

  ./hack/build-manifests.sh
}

main