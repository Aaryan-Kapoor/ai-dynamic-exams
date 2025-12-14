# Frontend Specification — AI-Powered Adaptive Examination System

This document defines the required frontend behavior and pages for the AI-powered adaptive examination system. It is written as an implementation-oriented spec for a frontend developer.

## 1) Core principles

- The frontend must enforce **role-based navigation** (Student vs Teacher vs Admin roles), while assuming the backend remains the source of truth for authorization.
- The frontend must treat **timing and attempt limits as server-enforced** and render server-provided state; client timers are for UX only.
- The frontend must support **lecture-driven adaptive exams**: retrieval-based context, AI question generation, AI grading, stop rules, retake limits, and results presentation.
- The frontend must support an academic structure of **colleges → departments → grade levels** and teacher assignments to multiple departments.

## 2) Actors and permissions

### Roles

- Student
- Teacher
- Head of Department
- College Administrator
- System Administrator

### Permission rules (frontend routing)

- Unauthenticated users can access only:
  - Login page
  - Password/session error pages (when routed from backend)
- Students can access only:
  - Student home
  - Student exam (active attempt only)
  - Student results (own attempts only)
  - Student attempt history (own attempts only)
- Teachers can access:
  - Teacher dashboard (only assigned departments; Head/College Admin/System Admin may have broader access)
  - Lecture library management for their departments
  - Exam configuration for their departments
  - Results dashboards scoped to their departments
- System administrators can access:
  - Admin panel (users, colleges, departments, role assignment, audit)

The frontend must handle “forbidden” responses by routing the user to an access-denied page that explains the problem and offers safe navigation options.

## 3) Global app behavior

### Session and authentication

- The frontend must maintain an authenticated session using the backend’s session mechanism (cookie-based session).
- On any request that returns “unauthorized”:
  - Clear local auth state (if any)
  - Redirect to `/login`
  - Preserve the originally requested destination so the user can be returned after successful login

### Error handling

- All pages must support:
  - Network error handling (timeouts, connectivity issues)
  - Server error handling (4xx/5xx)
  - Validation error rendering from server responses
- All mutations (upload, save config, submit answer, end exam) must:
  - Disable submit controls while in-flight
  - Prevent duplicate submissions
  - Render server-confirmed outcomes

### Data freshness

- Teacher pages must revalidate after mutations so the UI reflects persisted state (config saved, upload completed, new results visible).
- Student exam page must periodically reconcile with server state:
  - If the attempt ended server-side (time limit or stop rule), transition to results
  - If the student opens multiple tabs, the UI must behave consistently (the server determines the single active attempt state)

### Auditable UX requirements

- Show the user:
  - Their identity (university ID)
  - Their role
  - Their department(s) and grade context where relevant
- Provide a logout control that invalidates the session.

## 4) Route map (pages)

### Public

- `/login`
- `/access-denied`
- `/error`

### Student

- `/student`
- `/student/exam`
- `/student/results/:attemptId`
- `/student/history`

### Teacher

- `/teacher`
- `/teacher/lectures`
- `/teacher/results`
- `/teacher/results/:attemptId`

### Admin (System Administrator)

- `/admin`
- `/admin/users`
- `/admin/users/:userId`
- `/admin/academics` (colleges + departments)
- `/admin/roles` (role assignments and department memberships)
- `/admin/audit` (exam attempts and system events)

If the product scope excludes the admin panel initially, these pages must still be planned and tracked as required deliverables for a complete system.

## 5) Shared UI modules (functional requirements)

### Navigation

- Role-aware main navigation:
  - Student: Home, History
  - Teacher: Dashboard, Lectures, Results
  - System Admin: Users, Academics, Roles, Audit
- Department + grade context selector for teacher views:
  - Must be derived from server-allowed departments for the logged-in teacher
  - Must persist the last selected department/grade per user

### Forms framework behavior

- Standardize:
  - Field validation messaging
  - Disabled/loading state
  - Submission error banners
  - Confirmation banners

### File upload handler

- Must support:
  - Selecting a file
  - Showing file name, size, and type
  - Progress indication (upload in-flight)
  - Server-side failure messaging (extraction/ocr errors, size limits)
  - Post-upload refresh of lecture list and indexing status

### Timer module (student exam)

- Must display:
  - Elapsed time
  - Allowed max duration
- Must handle:
  - Browser sleep/resume
  - Tab switching
  - Clock drift (use server timestamps as the reference; client timer is derived)
- Must prompt the UI to reconcile with the server when max time is reached (do not assume client-side end is authoritative).

### Results summary module

- Must display both:
  - Numerical score (0–100)
  - Qualitative rating (Very Good / Good / Needs Improvement / Bad)
- Must show:
  - End reason
  - Time taken
  - Attempt number (retake count)

## 6) Page specifications

### 6.1) Login (`/login`)

Requirements:

- Inputs:
  - University ID
  - Password
- Behavior:
  - Submits credentials to backend login endpoint
  - On success: route based on returned user role (Student → `/student`, Teacher+ → `/teacher`, System Admin → `/admin`)
  - On failure: show a clear invalid-credentials message
  - If already logged in: redirect to role landing page
- Security:
  - Prevent password disclosure via logging
  - Ensure the UI does not render sensitive errors returned by the backend beyond what is necessary

### 6.2) Student Home (`/student`)

Requirements:

- Must load and display:
  - Student identity, department, grade level
  - Current exam configuration for the student’s department/grade:
    - Max duration
    - Max attempts
    - Max questions
    - Stop rules (consecutive incorrect, slow-answer threshold)
  - Attempts used and attempts remaining
  - Whether there is an active attempt
- Actions:
  - Start exam (creates a new attempt if none active and attempts remain)
  - Resume exam (if an attempt is active)
  - Navigate to history
- Edge cases:
  - No exam configured for the student’s department/grade (render a clear state and next step)
  - Student has no department or grade assigned (render a clear state and next step)

### 6.3) Student Exam (`/student/exam`)

Requirements:

- Must load and display:
  - Attempt metadata: attempt number, started time
  - Timer: elapsed and max allowed duration
  - Current question number and exam max questions
  - The current question text
  - Answer input area
  - Current-understanding indicator:
    - Score-so-far (0–100) derived from server-computed logic
    - Rating-so-far derived from server-computed logic
    - Consecutive incorrect count
    - Questions answered count
- Actions:
  - Submit answer:
    - Must send the answer to the backend
    - Must render returned grading feedback (when provided)
    - Must transition to the next question if the attempt continues
    - Must transition to results if the attempt auto-ends
  - End exam:
    - Must allow user to end early
    - Must transition to results after server finalization
- Adaptive stop behavior:
  - If the backend ends the attempt (time limit / stop rules / max questions), the frontend must immediately transition to results and prevent further answer submissions.
- Resilience:
  - If the page reloads, it must restore the active attempt and current question state from the server.
  - Prevent multi-submit of the same question.

### 6.4) Student Results (`/student/results/:attemptId`)

Requirements:

- Must display:
  - Final score and rating
  - End reason (completed, ended by student, time limit, too many incorrect, too slow)
  - Total elapsed seconds
  - Questions answered
  - Max incorrect streak
- Actions:
  - Retake exam:
    - Must be enabled only when attempts remain
    - Must create a new attempt and route to `/student/exam`
  - Return to student home

### 6.5) Student History (`/student/history`)

Requirements:

- Must list the student’s attempts for their department/grade (and support multiple departments if the backend supports it).
- For each attempt show:
  - Attempt number
  - Start time, end time
  - End reason
  - Score and rating
  - Time taken
- Actions:
  - View attempt details (route to results detail view)
- Filtering:
  - By department (if student has more than one)
  - By date range

### 6.6) Teacher Dashboard (`/teacher`)

Requirements:

- Must load and display:
  - Teacher identity and role
  - Allowed departments (based on server permission)
  - Current selected department and grade
  - Current exam configuration for that department/grade
  - Summary signals for the configured exam (duration, attempts, questions, stop rules, difficulty range)
- Actions:
  - Change department/grade context (reload configuration and lecture stats)
  - Save configuration:
    - Validate numeric constraints before submit
    - Render success/failure status from the server
  - Navigate to lecture library and results
- Edge cases:
  - Teacher has no departments assigned (render clear state and next step)
  - Teacher selects a department they are not allowed to manage (must be prevented client-side and handled server-side)

### 6.7) Teacher Lecture Library (`/teacher/lectures`)

Requirements:

- Must load and display for selected department/grade:
  - List of lecture materials:
    - Original filename
    - File type
    - Upload timestamp
    - Extraction status (success/failure) and failure reason if applicable
    - Chunk count
    - Indexing status (embedded/not embedded, embedding model used)
- Actions:
  - Upload lecture file (PDF, images, text):
    - Validate file size against server-configured max
    - Submit to server and render extraction/indexing outcome
  - Delete lecture material:
    - Requires confirmation
    - Must remove dependent chunks and embeddings
  - Reindex embeddings for selected department/grade:
    - Triggers a backend job or endpoint that rebuilds embeddings
    - Shows progress and completion result
- Quality controls:
  - Show extracted text preview for a material (read-only, paginated/trimmed)
  - Show per-chunk view and allow searching within extracted content

### 6.8) Teacher Results List (`/teacher/results`)

Requirements:

- Must load and display attempts for selected department/grade:
  - Student university ID
  - Attempt number
  - End time
  - End reason
  - Time taken
  - Score
  - Rating
- Filtering:
  - Date range
  - Student ID
  - End reason
  - Score range
- Aggregations:
  - Score distribution summary
  - Pass/fail thresholds (if the institution defines them)
  - Average score, median score, average time
  - Attempt count per student

### 6.9) Teacher Attempt Detail (`/teacher/results/:attemptId`)

Requirements:

- Must display:
  - Student identity (university ID)
  - Attempt metadata and end reason
  - Per-question breakdown:
    - Question text
    - Student answer
    - Correctness score
    - Correct/incorrect flag
    - Time taken
    - Feedback
    - Context excerpt used for generation/grading (read-only)
- Actions:
  - Export attempt report (downloadable)
  - Flag attempt for review (adds an audit record)

### 6.10) Admin Home (`/admin`)

Requirements:

- Must show:
  - System counts: total users, students, teachers, active exams, attempts today
  - Recent activity: uploads, attempts, failures
- Actions:
  - Navigate to Users / Academics / Roles / Audit

### 6.11) Admin Users (`/admin/users`)

Requirements:

- List users with:
  - University ID
  - Name
  - Role
  - College
  - Departments (multi)
  - Grade level (students)
  - Active status
  - Created at
- Actions:
  - Create user (student/teacher/admin)
  - Disable/enable user
  - Reset password
  - Assign college
  - Assign department memberships (multi-select)
  - Set student grade level (1–4)
- Search/filter:
  - By role, college, department, grade level, active status

### 6.12) Admin User Detail (`/admin/users/:userId`)

Requirements:

- Must show full user profile and memberships.
- Actions:
  - Update profile fields
  - Update role
  - Update department memberships
  - Update grade level
  - View user’s attempts (students) or activity (teachers/admins)

### 6.13) Admin Academics (`/admin/academics`)

Requirements:

- CRUD for:
  - Colleges
  - Departments within a college
- Constraints:
  - Department names must be unique within the college
- Actions:
  - Bulk import colleges/departments from a structured file

### 6.14) Admin Roles (`/admin/roles`)

Requirements:

- Must support:
  - Assigning Head of Department and College Administrator privileges
  - Defining which departments a teacher belongs to
  - Defining “all departments in college” access for heads/admins
- Must show effective permissions preview for a user:
  - Which departments can they manage?
  - Which grades can they configure?

### 6.15) Admin Audit (`/admin/audit`)

Requirements:

- Must list system events:
  - Login failures and successes
  - Lecture upload events
  - Embedding reindex events
  - Exam attempt lifecycle events (start, auto-stop, end, retake)
  - Permission denials
- Filtering:
  - By event type, user, time range, department
- Actions:
  - Export audit logs
  - View linked entities (user, attempt, lecture material)

## 7) Backend interaction requirements (frontend-visible contracts)

To implement the pages above without relying on server-rendered HTML, the frontend needs stable backend contracts:

- Auth endpoints:
  - login, logout, session check (“who am I”)
- Reference endpoints:
  - colleges, departments, grade levels
  - current user’s effective permissions (departments they can manage)
- Teacher endpoints:
  - get/save exam config by department+grade
  - upload/list/delete lecture materials
  - lecture extraction status, chunk counts, embedding status
  - results listing + attempt detail
  - trigger embedding reindex scoped to department/grade
- Student endpoints:
  - get current exam config for the student’s assignment
  - start/resume active attempt
  - fetch current question
  - submit answer and receive grading feedback
  - end attempt
  - results and history listing
- Admin endpoints:
  - CRUD users, colleges, departments
  - manage memberships and role assignments
  - audit log listing/export

The frontend must treat the backend as authoritative for:

- Attempt limit enforcement
- Time limit enforcement
- Stop-rule enforcement
- Question identity and ordering
- Scoring and rating

## 8) Non-functional requirements

- Accessibility: keyboard navigable forms and controls; screen-reader-friendly labeling for all form fields and important status changes.
- Performance:
  - Lecture lists and results lists must paginate/virtualize if large.
  - Attempt detail rendering must handle many questions without blocking the main thread.
- Security:
  - Do not expose sensitive server errors.
  - Avoid storing secrets in browser storage.
  - Ensure file uploads are restricted to permitted departments/grades.
- Observability:
  - Provide structured client-side logging hooks for major actions (login, upload, start exam, submit answer, end exam).

