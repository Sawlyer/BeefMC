import java.util.Locale

pluginManagement {
    repositories {
        gradlePluginPortal()
        maven("https://repo.papermc.io/repository/maven-public/")
    }
}

plugins {
    id("org.gradle.toolchains.foojay-resolver-convention") version "1.0.0"
}

if (!file(".git").exists()) {
    // BeefMC start - project setup
    val errorText = """
        
        =====================[ ERROR ]=====================
         The BeefMC project directory is not a properly cloned Git repository.
         
         In order to build BeefMC from source you must clone
         the BeefMC repository using Git, not download a code
         zip from GitHub.
         
         Built BeefMC jars are available for download at
         https://github.com/Sawlyer/BeefMC/releases
         
         See CONTRIBUTING.md
         for further information on building and modifying Minecraft server forks.
        ===================================================
    """.trimIndent()
    // BeefMC end - project setup
    error(errorText)
}

rootProject.name = "beefmc"

for ((projectName, directoryName) in listOf("beefmc-api" to "leaf-api", "beefmc-server" to "leaf-server")) {
    include(projectName)
    project(":$projectName").projectDir = file(directoryName)
}
