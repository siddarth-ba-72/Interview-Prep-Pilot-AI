package com.preppilot.userservice.service;

import com.mongodb.client.MongoClient;
import com.mongodb.client.MongoClients;
import com.preppilot.userservice.dto.AdminDtos.AdminUser;
import com.preppilot.userservice.dto.AdminDtos.AdminUserPage;
import com.preppilot.userservice.model.Role;
import com.preppilot.userservice.repository.UserRepository;
import org.bson.Document;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.data.mongodb.core.MongoTemplate;

import java.time.Instant;
import java.util.Date;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assumptions.assumeTrue;
import static org.mockito.Mockito.mock;

/**
 * Runs the admin user queries against MongoDB. Skipped unless TEST_MONGODB_URI is set, e.g.
 * <pre>
 * docker run -d --rm --name preppilot-test-mongo -p 27018:27017 mongo:7.0
 * TEST_MONGODB_URI=mongodb://localhost:27018 ./gradlew :user-service:test
 * </pre>
 */
class AdminUserServiceIntegrationTest {

    private static final String MONGODB_URI = System.getenv("TEST_MONGODB_URI");

    private static MongoClient client;

    private MongoTemplate mongoTemplate;
    private AdminUserService service;

    @BeforeAll
    static void connect() {
        assumeTrue(MONGODB_URI != null && !MONGODB_URI.isBlank(), "TEST_MONGODB_URI is not set");
        client = MongoClients.create(MONGODB_URI);
    }

    @AfterAll
    static void disconnect() {
        if (client != null) {
            client.close();
        }
    }

    @BeforeEach
    void setUp() {
        mongoTemplate = new MongoTemplate(client, "admin_user_test");
        mongoTemplate.dropCollection("users");
        insertUser("ann@example.com", "Ann Lee", "2026-10-01T09:00:00Z", null);
        insertUser("bob@example.com", "Bob Stone", "2026-10-02T09:00:00Z", "ADMIN");
        insertUser("carl@sample.org", "Carl Annand", "2026-10-03T09:00:00Z", null);
        insertUser("dora@example.com", "Dora", "2026-10-04T09:00:00Z", null);
        service = new AdminUserService(mongoTemplate, mock(UserRepository.class));
    }

    @Test
    void listsNewestUsersFirstOnePageAtATime() {
        AdminUserPage first = service.listUsers(null, 0, 3);
        AdminUserPage second = service.listUsers(null, 1, 3);

        assertEquals(List.of("dora@example.com", "carl@sample.org", "bob@example.com"), emails(first));
        assertEquals(List.of("ann@example.com"), emails(second));
        assertEquals(4, first.total());
    }

    @Test
    void searchMatchesPartOfTheEmailOrNameIgnoringCase() {
        AdminUserPage page = service.listUsers("  ANN ", 0, 20);

        assertEquals(List.of("carl@sample.org", "ann@example.com"), emails(page));
        assertEquals(2, page.total());
    }

    @Test
    void searchIsLiteralNotARegex() {
        assertEquals(0, service.listUsers("a.n", 0, 20).total());
        assertEquals(0, service.listUsers(".*", 0, 20).total());
        assertEquals(1, service.listUsers("@sample.org", 0, 20).total());
    }

    @Test
    void usersWithoutARoleAreUsers() {
        List<AdminUser> users = service.listUsers(null, 0, 20).users();

        assertEquals(Role.ADMIN, users.get(2).role());
        assertEquals(Role.USER, users.get(0).role());
    }

    @Test
    void pageSizeIsCapped() {
        assertEquals(AdminUserService.MAX_PAGE_SIZE, service.listUsers(null, 0, 10_000).size());
        assertEquals(1, service.listUsers(null, -5, 0).size());
    }

    private void insertUser(String email, String displayName, String createdAt, String role) {
        Document user = new Document("email", email)
                .append("displayName", displayName)
                .append("authProvider", "LOCAL")
                .append("passwordHash", "hash")
                .append("createdAt", Date.from(Instant.parse(createdAt)));
        if (role != null) {
            user.append("role", role);
        }
        mongoTemplate.getCollection("users").insertOne(user);
    }

    private static List<String> emails(AdminUserPage page) {
        return page.users().stream().map(AdminUser::email).toList();
    }
}
