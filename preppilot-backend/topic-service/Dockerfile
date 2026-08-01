FROM eclipse-temurin:21-jdk-alpine AS build
WORKDIR /app

# Copy the whole monorepo (settings.gradle.kts, gradlew, all modules)
COPY . .

RUN ./gradlew :topic-service:bootJar --no-daemon

FROM eclipse-temurin:21-jre-alpine
WORKDIR /app
COPY --from=build /app/topic-service/build/libs/*.jar app.jar
EXPOSE 8082
ENTRYPOINT ["java", "-XX:MaxRAMPercentage=75.0", "-jar", "app.jar"]