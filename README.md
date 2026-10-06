# PartnerAPI — Public Hotel Booking API

> A partner-facing API platform that enables travel agencies to search and book hotels programmatically.

## Overview

PartnerAPI is a public API programme for a travel booking company that currently serves customers through its website.

The company wants to allow external travel agencies to integrate directly with its hotel-booking platform instead of manually using the website.

The programme initially targets **40 partner agencies**.

The first **5 partners must be ready for production within 10 weeks**, followed by the remaining 35 partners.

The project covers API design, hotel search and booking, partner authentication, sandbox access, documentation, usage reporting, rate limiting, testing, partner onboarding, and change management.

---

## Business Problem

Partner agencies currently depend on the travel company's website to make hotel bookings.

This creates several problems:

* Manual booking workflows
* Limited automation for partner agencies
* Increased operational effort
* Difficulty scaling partner integrations
* Lack of programmatic access to hotel inventory
* Limited API-level usage monitoring

PartnerAPI addresses these problems by providing a controlled public API.

---

## Project Objectives

The project aims to:

1. Provide a secure public hotel-booking API.
2. Allow authenticated partners to search hotel availability.
3. Allow partners to create and manage bookings.
4. Provide a sandbox environment for integration testing.
5. Provide partner API keys and access control.
6. Enforce partner-specific rate limits.
7. Provide API usage reporting.
8. Provide complete API documentation.
9. Onboard the first five partners within 10 weeks.
10. Maintain an API error rate below 0.5%.
11. Keep partner onboarding below 5 working days per partner.
12. Protect the standard API from unnecessary partner-specific customisation.

---

## Project Target

| Metric                  | Target                         |
| ----------------------- | ------------------------------ |
| Initial partners        | 5                              |
| Total partners          | 40                             |
| Production deadline     | 10 weeks                       |
| API error rate          | < 0.5%                         |
| Partner onboarding time | < 5 working days/partner       |
| Custom partner requests | Managed through change control |

---

## Standard API Scope

### In Scope

* Partner registration
* Partner authentication
* API key management
* Hotel search
* Hotel availability
* Room availability
* Booking creation
* Booking retrieval
* Booking cancellation
* Rate limiting
* Access control
* Sandbox environment
* API documentation
* Usage reporting
* Partner onboarding

### Out of Scope for Initial Release

* Partner-specific business logic
* One-off partner workflows
* Custom booking rules for individual agencies
* Custom UI applications for partners
* Unapproved third-party integrations
* Features that do not provide general value to the partner ecosystem

The two existing custom requests will be processed through formal change control rather than automatically added to the standard API.

---

## Architecture

The intended architecture separates the public partner-facing interface from the internal booking system.

```text
                    Partner Agency
                           |
                           v
                  +----------------+
                  | Public API     |
                  | Gateway        |
                  +-------+--------+
                          |
             +------------+------------+
             |            |            |
             v            v            v
        Authentication  Rate Limit   Usage
             |            |          Reporting
             +------------+------------+
                          |
                          v
                  +---------------+
                  | Booking API   |
                  | Services      |
                  +-------+-------+
                          |
                          v
                  Internal Booking
                     Platform
                          |
                          v
                   Hotel Inventory
```

The public API should remain loosely coupled to the internal booking system through stable service interfaces.

---

## Main API Capabilities

### Authentication

Partners authenticate using issued API credentials.

Example:

```http
Authorization: Bearer <partner-api-key>
```

### Hotel Search

```http
GET /api/v1/hotels/search
```

Example parameters:

```text
destination
checkIn
checkOut
guests
rooms
```

### Booking

```http
POST /api/v1/bookings
```

### Booking Retrieval

```http
GET /api/v1/bookings/{bookingId}
```

### Cancellation

```http
POST /api/v1/bookings/{bookingId}/cancel
```

The final API contract will be defined in the API specification and documentation.

---

## Project Documents

| Document          | Purpose                                                     |
| ----------------- | ----------------------------------------------------------- |
| SRS               | Requirements and system scope                               |
| UML Package       | System and software design                                  |
| Project Plan      | WBS, schedule, resources and critical path                  |
| Estimation Sheet  | Three-point/Pert estimation                                 |
| Test Plan         | Test strategy, BVA, equivalence classes and decision tables |
| Risk Register     | Risk analysis, RMMM and closure                             |
| API Documentation | Partner integration reference                               |

---

## Estimation Summary

The project provides three-point estimates for five sequential activities.

PERT expected time is calculated using:

$$
TE = \frac{O + 4M + P}{6}
$$

| Activity           |  Expected Time |
| ------------------ | -------------: |
| API Design         |      6.33 days |
| Booking Endpoints  |     15.00 days |
| Sandbox            |      6.67 days |
| Documentation      |      5.17 days |
| Partner Onboarding |      8.67 days |
| **Total**          | **41.84 days** |

Using five working days per week:

$$
41.84 / 5 = 8.37\ weeks
$$

Therefore, the sequential estimate fits within the 10-week target.

---

## Custom Request Impact

Two partner-specific requests have been estimated at:

* Request 1: 12 days
* Request 2: 18 days

Additional effort:

$$
12 + 18 = 30\ days
$$

New estimate:

$$
41.84 + 30 = 71.84\ days
$$

$$
71.84 / 5 = 14.37\ weeks
$$

Estimated delay against the 10-week target:

$$
14.37 - 10 = 4.37\ weeks
$$

Therefore, accepting both requests into the initial sequential scope would jeopardise the launch target.

---

## Quality Targets

The project will monitor:

* API error rate below 0.5%
* API latency against defined percentile targets
* Partner authentication failures
* Rate-limit enforcement
* Booking consistency
* Defect density
* Defect Removal Efficiency
* Partner onboarding duration

---

## Testing

Testing will include:

* Functional testing
* Integration testing
* API contract testing
* Boundary Value Analysis
* Equivalence Class Partitioning
* Decision-table testing
* Security testing
* Rate-limit testing
* Access-control testing
* Regression testing
* Partner acceptance testing

---

## Change Management

All non-standard partner requests must pass through:

1. Capture
2. Understand reason
3. Analyse impact
4. Decide
5. Update plan
6. Implement and verify

The standard API remains protected from uncontrolled partner-specific scope expansion.

---

## Academic Deliverables

This repository contains the complete engineering artefacts required for the PartnerAPI project:

* IEEE 830-style SRS (PDF)
* UML design package (PDF & Images)
* Project plan (PDF)
* Estimation calculations (Excel & PDF)
* Test plan and evidence (PDF)
* Risk register (PDF)
* Change log (PDF)
* Closure and lessons learned (PDF)

---

## Project Status

| Area               | Status  |
| ------------------ | ------- |
| Requirements       | Completed |
| API Design         | Completed |
| UML                | Completed |
| Estimation         | Completed |
| Documentation      | Completed |
| Testing            | Completed |
| Risk Management    | Completed |

---

## Important Assumption

The provided project estimates are planning estimates rather than guaranteed delivery commitments.

Actual delivery can vary because of:

* Integration complexity
* Defects
* Security findings
* Partner readiness
* Internal system dependencies
* Requirement changes
* Testing outcomes

Therefore, the 10-week target should be treated as a managed project objective rather than an unconditional promise.

---

## Author

**PartnerAPI — Public API Programme**

Software Engineering Project
