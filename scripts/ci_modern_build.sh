#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
set -euo pipefail

: "${QV_TARGET:?Set one exact modern CI target}"
: "${QV_JAVA_PATHS:?Set installed Java17 and Java21 toolchain paths}"
qv_project=$(python3 -B scripts/ci_modern_artifacts.py target --target "$QV_TARGET" --field project)
qv_logs="$PWD/ci-logs/$QV_TARGET"
qv_runtime="${RUNNER_TEMP:-$PWD/.ci-tests}/qizhang-modern/$QV_TARGET"
mkdir -p "$qv_logs" "$qv_runtime"
export JAVA_TOOL_OPTIONS="${JAVA_TOOL_OPTIONS:+$JAVA_TOOL_OPTIONS }-Dqzguard.testDir=$qv_runtime/core-tests"
gradle_options=(--no-daemon --max-workers=1 --console=plain --stacktrace
  "--project-cache-dir=$qv_runtime/project-cache"
  "-PqzRuntimeRoot=$qv_runtime/runtime"
  "-Porg.gradle.java.installations.paths=$QV_JAVA_PATHS"
  -Porg.gradle.java.installations.auto-detect=false
  -Porg.gradle.java.installations.auto-download=false)

if [[ "$QV_TARGET" == core-bukkit ]]; then
  bash ./gradlew "${gradle_options[@]}" build :core:securityTest 2>&1 | tee "$qv_logs/gradle.log"
  python3 -B integrations/test_integrations.py 2>&1 | tee "$qv_logs/integration-tests.log"
  python3 -B integrations/test_runtime_evidence.py 2>&1 | tee "$qv_logs/evidence-parser-tests.log"
  python3 -B -m unittest discover -s catalog -p test_catalog.py -v 2>&1 | tee "$qv_logs/catalog-tests.log"
  python3 -B -m unittest discover -s scripts -p test_ci_modern_artifacts.py -v 2>&1 | tee "$qv_logs/artifact-collection-tests.log"
else
  (cd "$qv_project" && bash ./gradlew "${gradle_options[@]}" build :fabric:commandParserSmoke) 2>&1 | tee "$qv_logs/gradle.log"
fi
python3 -B scripts/ci_modern_artifacts.py stage --target "$QV_TARGET" --output "ci-artifacts/$QV_TARGET"
