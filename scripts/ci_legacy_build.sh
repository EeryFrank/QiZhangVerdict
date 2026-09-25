#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
set -euo pipefail

# Run from the repository root. CI supplies actual JDK locations on its runner.
: "${QV_MC:?Set QV_MC to a supported development target}"
: "${QV_JDK8:?Set QV_JDK8 to a full Java 8 JDK}"
: "${QV_JDK17:?Set QV_JDK17 to a full Java 17 JDK}"
: "${QV_JDK21:?Set QV_JDK21 to a full Java 21 JDK}"
for qv_jdk in "$QV_JDK8" "$QV_JDK17" "$QV_JDK21"; do
  test -x "$qv_jdk/bin/javac"
done

qv_loaders=(fabric forge)
qv_wrapper=./gradlew
gradle_options=(--no-daemon --console=plain --stacktrace --max-workers=2)
case "$QV_MC" in
  1.12.2)
    export JAVA_HOME="$QV_JDK8"
    qv_loaders=(forge)
    ;;
  1.16.5|1.18.2|1.19.4)
    export JAVA_HOME="$QV_JDK21"
    gradle_options+=("-Porg.gradle.java.installations.paths=$QV_JDK8,$QV_JDK17,$QV_JDK21"
      -Porg.gradle.java.installations.auto-detect=false
      -Porg.gradle.java.installations.auto-download=false)
    ;;
  *) printf 'Unsupported Minecraft development target: %s\n' "$QV_MC" >&2; exit 2 ;;
esac
# 1.19.4 intentionally shares the repository's Gradle 8.14.1 wrapper.
if [[ "$QV_MC" == 1.19.4 ]]; then qv_wrapper=../../gradlew; fi
export PATH="$JAVA_HOME/bin:$PATH"
export CI=true
mkdir -p "ci-logs/legacy-$QV_MC" "ci-artifacts/legacy-$QV_MC"
"$JAVA_HOME/bin/java" -version
(cd "platforms/$QV_MC" && sh "$qv_wrapper" "${gradle_options[@]}" build) \
  2>&1 | tee "ci-logs/legacy-$QV_MC/gradle.log"
for qv_loader in "${qv_loaders[@]}"; do
  cp "platforms/$QV_MC/$qv_loader/build/libs/qizhangverdict-$qv_loader-$QV_MC-0.2.0-dev.jar" \
    "ci-artifacts/legacy-$QV_MC/"
done
(cd "ci-artifacts/legacy-$QV_MC" && sha256sum ./*.jar > SHA256SUMS)
