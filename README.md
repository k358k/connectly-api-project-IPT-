**Connectly API - Milestone 2**

**Project Overview**
This repository contains the Connectly API, a social media backend built with Django REST Framework. Milestone 2 focuses on user interactions, secure third-party authentication, and optimized content delivery.


**Final Version Specification**
Target Branch: The latest and final version of this project for Milestone 2 is contained in the ms2 branch.


**Implemented Features**
**Homework 5: User Interactions**
Models: Implemented Like and Comment models with ForeignKey relationships to Users and Posts.

**Endpoints:**
POST /posts/{id}/like/: Toggle functionality to like/unlike a post.

POST /posts/{id}/comment/: Allows users to add comments to specific posts.

Advanced: Integrated like_count and comment_count into serialized post data.


**Homework 6: Google OAuth Integration**
Authentication: Integrated Google OAuth login to allow secure access using school-provided accounts.

Validation: Implemented domain-restricted login for @mmdc.mcl.edu.ph and handled user profile linking.

Endpoint: POST /auth/google/login/.


**Homework 7: News Feed**
Endpoint: GET /posts/feed/.

Sorting: Posts are retrieved in reverse-chronological order (newest first) using Django ORM.

Pagination: Implemented PageNumberPagination to handle large datasets efficiently.

Error Handling: Configured graceful 404 responses for invalid pagination parameters.


**Testing & Validation**
Testing was performed via Postman to validate CRUD operations, authentication flows, and edge cases.

Postman Collection: The exported v2.1 collection file is included in the repository root.

Screenshots: Visual proof of successful requests and error handling are provided in the submission drive.

**AI Disclosure Statement**
AI Disclosure: This project utilized AI assistance (Gemini) as a technical consultant to streamline the architectural planning of the News Feed and to ensure best practices during the merging of multiple development branches into the final ms2 branch. AI was also used to help generate standardized testing documentation and validation scenarios.
