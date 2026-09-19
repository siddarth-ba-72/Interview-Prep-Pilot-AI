# syntax=docker/dockerfile:1
FROM eclipse-temurin:21-jdk-alpine AS build
WORKDIR /app

# Fetch the Gradle distribution in its own layer. If this sat after `COPY . .` every source
# edit would re-download ~130MB, and one slow connect fails the whole build.
COPY gradlew ./
COPY gradle gradle
RUN chmod +x ./gradlew && ./gradlew --version --no-daemon

# Copy the whole monorepo (settings.gradle.kts, all modules)
COPY . .

RUN --mount=type=cache,target=/root/.gradle/caches \
    ./gradlew :user-service:bootJar --no-daemon

FROM eclipse-temurin:21-jre-alpine
WORKDIR /app
COPY --from=build /app/user-service/build/libs/*.jar app.jar
EXPOSE 8081
ENTRYPOINT ["java", "-XX:MaxRAMPercentage=75.0", "-jar", "app.jar"]
