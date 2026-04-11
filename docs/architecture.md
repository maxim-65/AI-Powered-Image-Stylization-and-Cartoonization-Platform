# Architecture Overview

## Purpose

This document describes the internal architecture of the AI-Powered Image Stylization Platform. It explains how the frontend, backend, database, and image-processing layers work together to deliver a secure, payment-gated stylization product.

## System Summary

The platform is organized as a Streamlit application backed by modular Python packages. The frontend orchestrates user interaction, while the backend contains the business rules, image algorithms, authentication logic, payment handling, and database interactions.

The architecture is intentionally small and explicit so it can be understood quickly, tested easily, and deployed without a large framework footprint.

## Layered Design

### 1. Presentation Layer

Location: `frontend/app.py`

Responsibilities:

- Render the Home, Login, Sign Up, Processing, and Dashboard pages.
- Handle page navigation and session-state transitions.
- Collect user inputs and display outputs.
- Render image previews, comparison views, and status messages.
- Display paid/unpaid states in the dashboard.

The frontend does not implement heavy image logic itself. It acts as the coordinator of the user experience.

### 2. Application / Business Layer

Location: `backend/`

Responsibilities:

- Authentication and session management.
- Payment order creation and verification.
- Gallery and dashboard data retrieval.
- Account deletion.
- Image-processing algorithm implementations.

The business layer is intentionally split into submodules so each feature family remains maintainable.

### 3. Data Layer

Location: `database/db_manager.py`

Responsibilities:

- Create and migrate the SQLite schema.
- Ensure foreign keys are enabled.
- Maintain user, transaction, image history, and session tables.

The SQLite schema is simple enough for local development but expressive enough to support payment-gated downloads and persistent login.

### 4. Utility Layer

Location: `utilities/`

Responsibilities:

- File upload validation.
- UUID-based image storage.
- Temporary-file cleanup.
- General image utility functions.

## Request Flow

### A. Sign Up Flow

1. The user fills out the sign-up form in Streamlit.
2. The frontend validates basic UI requirements.
3. `backend/auth.py` validates email and password complexity.
4. The password is hashed with bcrypt.
5. The record is inserted into the `Users` table.

### B. Login Flow

1. The user submits email and password.
2. The backend validates email format.
3. The stored password hash is checked with bcrypt.
4. Failed attempts are counted in the database.
5. Repeated failures trigger an account lockout.
6. On success, `last_login` is updated.
7. A persistent session token is generated and stored hashed in `UserSessions`.
8. A cookie is set so refresh does not log the user out.

### C. Processing Flow

1. The user uploads an image.
2. The image is validated for type and size.
3. The file is decoded into an OpenCV image.
4. The selected effect module is executed.
5. Large images are downscaled before processing.
6. The preview is shown in the UI.
7. The processed result can be saved to the gallery.
8. The original and processed paths are written to `ImageHistory`.

### D. Payment Flow

1. The user unlocks a paid item from the Dashboard.
2. The backend creates a Razorpay order.
3. The transaction is recorded as `created`.
4. After payment, the Razorpay signature is verified.
5. If verification succeeds, the transaction is updated to `success`.
6. The related image history row is marked `is_paid = 1`.
7. The UI allows downloads for the paid item.

## Image Processing Architecture

The image pipeline is designed around reusable primitives.

### Shared helpers

`backend/image_processing/common.py` contains utilities for:

- Ensuring BGR compatibility.
- Resizing images for performance.
- Restoring the final image size.
- Clamping K-Means values.
- Running a standardized quantization helper.

### Effect families

The effect families are grouped by the visual outcome they target:

- Cartoon
- Artistic
- Sketch
- Filters
- Fun

This grouping is mirrored in the Streamlit UI so users can browse styles by intent rather than by algorithm name.

### Performance approach

The processing modules are designed with performance in mind:

- Use 1080p-equivalent pixel budgets as the default high-water mark.
- Apply median blur early for noise reduction.
- Use bilateral filters for edge-preserving smoothing.
- Use adaptive quantization levels to keep visual quality while reducing runtime.

## Storage Architecture

### Uploaded files

- Saved with UUID-based filenames.
- Stored in `uploads/`.
- Returned path is persisted in the database.

### Processed images

- Stored as generated output files.
- Linked in `ImageHistory`.
- Re-used for paid downloads and gallery browsing.

### Temporary files

- Stored in `utilities/temp/`.
- Used for transient processing artifacts.
- Can be cleaned after 24 hours.

## Database Relationships

- One user can have many image-history entries.
- One user can have many transactions.
- One transaction can correspond to one image-history record.
- One user can have multiple session tokens over time.

These relationships make the system fit a typical multi-step consumer workflow while staying simple enough for SQLite.

## Security Architecture

### Password security

- Passwords are hashed with bcrypt.
- Plain-text passwords are never stored.

### Session security

- Persistent login uses random tokens.
- Tokens are hashed before being stored.
- Cookies are used only for token transport, not for credential storage.

### Payment security

- Razorpay keys are read from environment variables.
- Payment verification checks the Razorpay signature.
- Downloads remain disabled until payment success is recorded.

### File security

- Uploads are validated by file content.
- Files larger than 10 MB are rejected.
- Temporary files are not meant to persist indefinitely.

## Frontend Navigation Model

The frontend uses a Home-first navigation flow.

- Home acts as the landing page.
- Sidebar navigation can reach all pages.
- Home buttons link directly to core pages.
- Each page includes a Back to Home action.
- Navigation state is managed through Streamlit session state.

## Deployment Model

The project can run locally or in a cloud environment.

### Local development

- Use a virtual environment.
- Install requirements.
- Initialize the SQLite schema.
- Set Razorpay environment variables.
- Launch Streamlit with `python -m streamlit run frontend/app.py`.

### Cloud deployment

Recommended approach:

- Put Razorpay secrets into the provider’s secret manager.
- Use persistent storage if keeping SQLite.
- Prefer managed storage if the app will be used by multiple users.
- Keep `.env` out of version control.

## Extension Strategy

To add a new effect:

1. Create a new module under the appropriate effect family.
2. Expose a clean `apply(...)` function.
3. Reuse the common resize helper.
4. Add a UI control in `frontend/app.py`.
5. Persist the style name in `ImageHistory`.
6. Add QA coverage in `tests/test_platform_e2e.py`.

This is the recommended pattern for keeping the codebase coherent as it grows.

## Operational Concerns

- Streamlit reruns on interaction, so session-state handling must remain disciplined.
- SQLite is suitable for prototyping and small deployments but should be replaced for higher concurrency.
- OpenCV contrib features may not always exist in every environment; fallbacks are included where practical.
- Cloud deployments should use environment variables for secrets and persistent storage for uploads if gallery history must survive restarts.

## Summary

The project is intentionally simple in infrastructure but rich in capabilities. The layered design lets the frontend remain lightweight while the backend handles processing, persistence, and payment logic. The result is a maintainable product prototype that can be evolved into a more advanced cloud service.
