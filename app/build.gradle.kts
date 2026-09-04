import java.io.FileInputStream
import java.util.Properties

plugins {
    id("com.android.application")
}

// Release signing (D-030). Active only when a gitignored keystore.properties
// exists at the repo root, or the TEATHER_KEYSTORE* env vars are set. Without
// it, `assembleRelease` falls back to the debug key so the build still produces
// an installable APK — that APK must not be distributed. keystore.properties
// keys: storeFile, storePassword, keyAlias, keyPassword.
val keystorePropsFile = rootProject.file("keystore.properties")
val releaseSigning: Properties? = when {
    keystorePropsFile.exists() ->
        Properties().apply { FileInputStream(keystorePropsFile).use { load(it) } }
    System.getenv("TEATHER_KEYSTORE") != null -> Properties().apply {
        setProperty("storeFile", System.getenv("TEATHER_KEYSTORE"))
        setProperty("storePassword", System.getenv("TEATHER_KEYSTORE_PASSWORD") ?: "")
        setProperty("keyAlias", System.getenv("TEATHER_KEY_ALIAS") ?: "teather")
        setProperty(
            "keyPassword",
            System.getenv("TEATHER_KEY_PASSWORD")
                ?: System.getenv("TEATHER_KEYSTORE_PASSWORD") ?: "",
        )
    }
    else -> null
}

android {
    namespace = "io.github.vel71184.teather"
    compileSdk = 37

    defaultConfig {
        applicationId = "io.github.vel71184.teather"
        minSdk = 26
        targetSdk = 36
        versionCode = 7
        versionName = "0.1.0-p1.5"

    }

    signingConfigs {
        if (releaseSigning != null) {
            create("release") {
                storeFile = rootProject.file(releaseSigning.getProperty("storeFile"))
                storePassword = releaseSigning.getProperty("storePassword")
                keyAlias = releaseSigning.getProperty("keyAlias")
                keyPassword = releaseSigning.getProperty("keyPassword")
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )
            signingConfig = if (releaseSigning != null) {
                signingConfigs.getByName("release")
            } else {
                logger.warn("Teather: no release key configured; release APK will be debug-signed and is not for distribution")
                signingConfigs.getByName("debug")
            }
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    testOptions {
        unitTests.all {
            it.useJUnit()
        }
    }
}

dependencies {
    testImplementation("junit:junit:4.13.2")
}
