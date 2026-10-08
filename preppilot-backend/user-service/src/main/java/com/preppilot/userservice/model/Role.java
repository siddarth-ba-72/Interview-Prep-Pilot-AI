package com.preppilot.userservice.model;

/** What a user may reach. ADMIN opens the read-only admin dashboard; it is only ever granted
 * by hand in the database, never through the API. */
public enum Role {
    USER,
    ADMIN
}
