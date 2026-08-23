.PHONY: check android-build android-install p0-doctor p0-run p0-test p0-stop

check:
	./gradlew --no-daemon :app:testDebugUnitTest :app:lintDebug :app:assembleDebug

android-build:
	./gradlew --no-daemon :app:assembleDebug

android-install: android-build
	./desktop/linux/teather-p0 install

p0-doctor:
	./desktop/linux/teather-p0 doctor

p0-run: android-build
	./desktop/linux/teather-p0 install
	./desktop/linux/teather-p0 start

p0-test:
	./desktop/linux/teather-p0 test

p0-stop:
	./desktop/linux/teather-p0 stop
