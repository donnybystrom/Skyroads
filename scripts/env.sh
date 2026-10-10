#!/bin/bash
# Source this file from the other launchers; paths do not depend on shell PATH.
SRE_ROOT=/Users/donnybystrom/code/SRE
export JAVA_HOME=/Library/Java/JavaVirtualMachines/jdk-21.jdk/Contents/Home
export GHIDRA_INSTALL_DIR="$SRE_ROOT/tools/ghidra_12.1.4_PUBLIC"
export REA_ANALYSIS_PROVIDER=ghidra
export REA_GHIDRA_STARTUP_TIMEOUT_MS=180000
export GHIDRA_MCP_URL=http://127.0.0.1:8089
export GHIDRA_MCP_FILE_ROOT="$SRE_ROOT"
export XDG_RUNTIME_DIR="$SRE_ROOT/runtime/sockets"
export PATH="/Users/donnybystrom/.nvm/versions/node/v22.21.1/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
