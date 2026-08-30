.PHONY: check android-build android-install p0-doctor p0-run p0-test p0-stop p1-check p1-dbus-smoke p1-package

check:
	./gradlew --no-daemon :app:testDebugUnitTest :app:lintDebug :app:assembleDebug :app:assembleRelease
	$(MAKE) p1-check

p1-check:
	python3 -m unittest discover -s desktop/linux/tests -v
	$(MAKE) p1-dbus-smoke

p1-dbus-smoke:
	./desktop/linux/tests/dbus_smoke.sh

p1-package:
	./packaging/scripts/build-deb.sh

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
