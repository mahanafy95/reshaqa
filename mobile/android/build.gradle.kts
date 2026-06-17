allprojects {
    repositories {
        google()
        mavenCentral()
    }
}

// مجلد البناء خارج OneDrive لتفادي قفل الملفات أثناء المزامنة (AccessDeniedException)
val externalRoot = file("C:/reshaqa_build")
rootProject.layout.buildDirectory.set(externalRoot)

subprojects {
    project.layout.buildDirectory.set(externalRoot.resolve(project.name))
}
subprojects {
    project.evaluationDependsOn(":app")
}

tasks.register<Delete>("clean") {
    delete(rootProject.layout.buildDirectory)
}
