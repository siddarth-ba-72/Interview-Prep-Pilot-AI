package com.preppilot.userservice.model;

/** Answer to the onboarding question "current experience". Carried in the access token so
 * downstream services can tailor content (students get campus-placement level material). */
public enum ExperienceLevel {
    STUDENT,
    YEARS_0_3,
    YEARS_3_5,
    YEARS_5_8,
    YEARS_8_13,
    YEARS_13_PLUS
}
