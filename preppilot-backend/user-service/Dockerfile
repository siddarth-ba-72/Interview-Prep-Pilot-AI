FROM eclipse-temurin:21-jdk-alpine AS build
WORKDIR /app

# Copy the whole monorepo (settings.gradle.kts, gradlew, all modules)
COPY . .

RUN ./gradlew :user-service:bootJar --no-daemon

FROM eclipse-temurin:21-jre-alpine
WORKDIR /app
COPY --from=build /app/user-service/build/libs/*.jar app.jar
EXPOSE 8081
ENTRYPOINT ["java", "-XX:MaxRAMPercentage=75.0", "-jar", "app.jar"]