#!/bin/bash
set -e

echo "🚀 Rebuilding mobile app..."

# Kill any gradle processes
pkill -f gradle || true

# Fix permissions and clean up
sudo chmod -R 777 android/ || true
sudo rm -rf android/.gradle || true
sudo rm -rf android/app/build || true

# Rebuild
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
export PATH=$JAVA_HOME/bin:$PATH

# Sync and build
npx cap sync android
cd android
./gradlew clean
./gradlew assembleDebug

echo "✅ APK built successfully!"
ls -lah app/build/outputs/apk/debug/