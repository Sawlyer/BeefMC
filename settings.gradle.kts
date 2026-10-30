rootProject.name = "beefmc"

includeBuild("build-logic")

fun setupSubproject(name: String, dir: String) {
    include(":$name")
    project(":$name").projectDir = file(dir)
}

setupSubproject("beefmc-server", "BeefMC-Server")
setupSubproject("beefmc-api", "BeefMC-API")
setupSubproject("paperclip", "paperclip")
