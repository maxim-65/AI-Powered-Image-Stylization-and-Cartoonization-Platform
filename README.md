# AI-Powered Image Stylization Platform

An end-to-end Python, OpenCV, and Streamlit product for image stylization, payment-gated downloads, and user gallery management. The application combines secure authentication, modular image-processing pipelines, SQLite persistence, and a polished web UI for both image transformation and post-processing review.

This README is intended to serve as both a technical reference and a deployment guide. It documents the architecture, runtime behavior, database schema, security model, processing pipeline, and QA strategy so the project can be understood, maintained, and extended by a future developer or reviewer.

For a deeper technical breakdown of the internals, see [docs/architecture.md](docs/architecture.md).

## Quick Start

1. Create and activate a virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Initialize the SQLite schema by running the database setup module.
4. Set your Razorpay environment variables if you want payment flows enabled.
5. Launch the app with `python -m streamlit run frontend/app.py`.

The README below explains why each of those steps matters and how the app behaves once it is running.

## Project Overview

This platform allows a user to:

- Sign up and log in securely.
- Upload images and apply a wide range of stylization effects.
- Compare original and processed results.
- Save processing history to a personal gallery.
- Unlock paid content with Razorpay test-mode payments.
- Download processed images only after payment is verified.
- Delete account data and associated image history.

The codebase is structured to support product-level maintainability, modular effect pipelines, and cloud deployment without exposing secrets in the source tree.

The design philosophy behind the project is:

- Keep the UI simple and discoverable for first-time users.
- Keep image-processing logic modular so new effects can be added without rewriting the app.
- Keep authentication and payment logic separate from processing so each concern can evolve independently.
- Keep cloud secrets outside the repository.
- Keep the database schema small, explicit, and easy to migrate.

## Core Capabilities

- Secure authentication with bcrypt password hashing.
- Account lockout after repeated failed login attempts.
- Persistent login using secure session tokens.
- Stripe-free payment flow using Razorpay test mode.
- Detailed processing pipeline with automatic resizing for large images.
- Free preview watermarking before payment is verified.
- Paid downloads in PNG, JPG, or PDF formats after verification.
- User dashboard with a gallery and payment status indicators.
- UUID-based file storage to avoid filename conflicts.

## User Journey

The product is designed around a straightforward end-to-end flow:

1. The user lands on the Home page and understands the product at a glance.
2. The user creates an account or logs in.
3. The user uploads an image in the Processing page.
4. The selected effect pipeline is applied with performance-aware preprocessing.
5. The user compares the original and stylized result.
6. The user saves the result to their gallery if signed in.
7. If the result is free, a watermarked preview is shown.
8. If the result is paid, Razorpay verification unlocks downloads.
9. The user can revisit the Dashboard to download paid content, inspect history, or delete the account.

## Technology Stack

- Python 3.x
- Streamlit
- OpenCV
- Pillow
- SQLite
- bcrypt
- Razorpay Python SDK
- extra-streamlit-components for cookie-based persistent login

## System Flow

```mermaid
flowchart LR
	A[Home Page] --> B[Login / Sign Up]
	B --> C[Persistent Session Token]
	C --> D[Processing Page]
	D --> E[OpenCV Effect Pipeline]
	E --> F[Preview / Compare]
	F --> G[Save to Gallery]
	G --> H[Dashboard]
	H --> I[Unlock Paid Content]
	I --> J[Razorpay Verification]
	J --> K[Download PNG / JPG / PDF]
```

The diagram above reflects the actual product flow: users enter through Home, authenticate once, process images through modular effect pipelines, and only pass into paid-download logic after payment verification succeeds.

## Key Design Principles

### Separation of Concerns

The system is split into independent layers:

- Authentication and session logic live in `backend/auth.py`.
- Payment order and verification logic live in `backend/payment.py`.
- Profile, gallery, and account deletion logic live in `backend/dashboard.py`.
- Effect algorithms live under `backend/image_processing/`.
- The Streamlit UI in `frontend/app.py` orchestrates the user experience.

### Performance First

Image processing can become expensive on large inputs. To keep the application responsive, the pipelines:

- Downscale large images before processing.
- Use fast OpenCV-native algorithms where possible.
- Apply median blur before stronger stylization steps.
- Reconstruct the final image at the original size when appropriate.

### Security First

The application avoids common mistakes by:

- Hashing passwords with bcrypt.
- Storing session tokens hashed in the database.
- Reading secrets from environment variables only.
- Gating paid content behind verified transactions.

### Maintainability First

The code was structured to allow:

- New filters to be added with minimal changes.
- New UI categories to be added without rewriting the backend.
- Future database migrations to be applied incrementally.

## Repository Structure

```text
backend/
	auth.py
	dashboard.py
	payment.py
	payment_config.py
	payments.py
	image_processing/
		common.py
		cartoon/
			basic.py
			advanced_pixar.py
			comic.py
		artistic/
			oil_paint.py
			watercolor.py
			hdr.py
		sketch/
			pencil.py
			charcoal.py
		filters/
			vintage.py
			pop_art.py
			posterize.py
		fun/
			pixel_art.py
			mosaic.py

database/
	db_manager.py

frontend/
	app.py

utilities/
	file_handler.py
	image_filters.py
	cartoon_engine.py
	temp/

tests/
	test_platform_e2e.py

uploads/
```

### Why this structure works

- `backend/image_processing/common.py` contains shared helpers so pipelines do not duplicate resize or quantization logic.
- The effect folders group styles by category, which makes both code navigation and UI grouping easier.
- `utilities/file_handler.py` centralizes file validation and UUID-based upload storage.
- `frontend/app.py` remains the only user-facing page entry point.

## Application Pages

The Streamlit app contains the following pages:

- Home
- Login
- Sign Up
- Processing
- Dashboard

### Home

The Home page acts as the landing page and includes:

- Short product description.
- Feature cards.
- Quick navigation buttons.
- Open-source style inspiration cards.

The Home page also serves as a soft onboarding layer. It introduces the product, shows the major capabilities, and provides direct routes into the rest of the application.

### Login

The Login page includes:

- Email and password fields.
- Show/Hide password toggle.
- Remember Me option for persistent login.

The login flow also integrates:

- Account lockout protection.
- Session token generation.
- Cookie-based persistence for refresh-safe login behavior.

### Sign Up

The Sign Up page includes:

- Username, email, and password fields.
- Show/Hide password toggle.
- Live password-strength indicator.
- Terms and Conditions checkbox.

The sign-up form includes a live password-strength indicator so users can adjust their password before submission. The visual strength indicator maps to the actual password rules enforced by the backend.

### Processing

The Processing page includes:

- Image upload with a 10 MB limit.
- Categorized style tabs.
- Effect intensity control.
- Additional style-specific controls such as K values and edge thickness.
- Original and processed image preview.
- Comparison view.
- Metadata and statistics section.
- Save-to-gallery option.

The Processing page is intentionally category-driven rather than a single dropdown. That decision makes the interface more approachable and better aligned with how users think about output style families:

- Cartoon
- Sketch
- Artistic
- Filters
- Fun

### Dashboard

The Dashboard page includes:

- Personalized welcome message.
- Last login timestamp.
- My History gallery.
- Payment status indicators.
- Unlock and Download actions.
- Delete Account action.

The Dashboard is also the control center for paid downloads. It exposes both the gallery and the payment state so the user can understand what is free preview content and what is already unlocked.

## Navigation Model

The application uses a Home-first navigation design.

- The sidebar always provides page-level navigation.
- The Home page provides explicit buttons for direct routes.
- Each page includes a Back to Home action.
- Session state keeps the selected page stable across reruns.
- Persistent login ensures the user is not forced back to the login page on refresh when Remember Me is enabled.

This model is important in Streamlit because reruns are frequent and state must be handled carefully to avoid confusing page jumps.

## Image Processing Modules

The image-processing system is modular and grouped by effect family.

### Cartoon Styles

- Basic classic cartoon pipeline.
- Advanced Pixar-style cartoon pipeline.
- Comic/ink style with strong outlines and aggressive quantization.

### Artistic Styles

- Oil painting.
- Watercolor.
- HDR/detail enhance.

### Sketch Styles

- Pencil sketch.
- Charcoal sketch.

### Color Filters

- Vintage / sepia.
- Pop art.
- Posterize.

### Fun Effects

- Pixel art.
- Mosaic.

### Module behavior

Each module exposes a simple `apply(...)` interface. This keeps the frontend logic consistent regardless of the chosen effect and allows a future developer to add more filters with very little UI work.

The most important patterns used by the modules are:

- `resize_for_speed(...)` to keep processing under control.
- `restore_size(...)` to preserve user-facing output dimensions.
- `clamp_k(...)` to keep quantization stable.
- `quantize_kmeans(...)` to enforce a common color-reduction behavior.

### Cartoon modules

#### Basic cartoon

The classic cartoon pipeline is designed to produce clean, stylized lines and flattened colors. It combines:

- Median blur for noise suppression.
- Bilateral filtering for edge-preserving smoothing.
- K-Means color quantization.
- Edge masking using Canny lines.

#### Advanced Pixar

The advanced cartoon path improves the classic version by using adaptive threshold edges to create a sharper, animated-film-style aesthetic.

#### Comic

The comic filter intentionally reduces colors more aggressively and overlays bolder outlines for a print-comic feel.

### Artistic modules

#### Oil painting

Uses `cv2.xphoto.oilPainting` when available and gracefully falls back when the contrib module is missing.

#### Watercolor

Uses `cv2.stylization` to create soft, painterly edges.

#### HDR detail enhance

Uses `cv2.detailEnhance` to emphasize fine texture and produce a more dramatic, high-contrast output.

### Sketch modules

#### Pencil

Uses OpenCV pencil sketch routines for grayscale and colored sketch outputs.

#### Charcoal

Combines grayscale sketching, blur inversion, and edge suppression for a heavier drawing-like look.

### Filter modules

#### Vintage

Applies a sepia-toned transform to simulate an old-photo aesthetic.

#### Pop Art

Boosts saturation and brightness for a more graphic look.

#### Posterize

Reduces the number of visible color levels to create a flattened color design.

### Fun modules

#### Pixel Art

Downscales and rescales with nearest-neighbor interpolation to create pixel blocks.

#### Mosaic

Uses larger block-based resampling to produce a mosaic-like abstraction.

## Processing Logic

The project uses a performance-aware pipeline to keep processing fast and stable.

- Images larger than a 1080p pixel budget are resized before transformation.
- Median blur is used first in cartoon workflows to reduce noise.
- Bilateral filtering preserves edges while smoothing color regions.
- K-Means color quantization is used to flatten color palettes.
- Adaptive threshold and Canny edge masks are used for outlines.
- Output images are resized back to original dimensions when necessary.

## Detailed Processing Pipeline

The actual image-processing sequence typically follows this pattern:

1. The image is uploaded and validated.
2. A format check ensures only allowed file types are accepted.
3. The image is decoded into an OpenCV array.
4. The chosen effect category and style are selected in the UI.
5. The image is preprocessed for speed if its resolution is large.
6. The selected effect pipeline is applied.
7. The output is restored to the original resolution where needed.
8. The preview is watermarked when the content is unpaid.
9. The user can compare the before/after result.
10. The processed version can be saved to history.

This sequence is intentionally consistent across styles so the UX stays predictable even when the underlying style changes.

## Secure Download Flow

Downloads are protected by payment verification.

- Preview images are watermarked before payment is confirmed.
- Razorpay signature verification must succeed before a transaction is marked as paid.
- Paid images can be downloaded in the selected output format.
- Unpaid images remain visible only as free previews.

### Download formats

The post-payment flow is designed so the user can choose a downloaded file format such as PNG, JPG, or PDF, depending on the available export path in the UI and the server-side download logic. The platform treats the paid state as the authorization gate.

### Watermark removal

Watermarks are only applied to the free-preview version shown before payment verification. The stored paid image remains the unwatermarked processed output, so the user receives a clean version after payment.

## Database Design

SQLite is used for local persistence.

### Users Table

- `id`
- `username`
- `email`
- `password_hash`
- `failed_login_attempts`
- `account_locked`
- `lock_until`
- `last_login`
- `created_at`

### Transactions Table

- `id`
- `user_id`
- `amount`
- `status`
- `image_history_id`

### ImageHistory Table

- `id`
- `user_id`
- `original_path`
- `processed_path`
- `style`
- `is_paid`

### UserSessions Table

- `id`
- `user_id`
- `token_hash`
- `expires_at`
- `created_at`

### Relationship notes

- `Users` is the parent table for all user-owned records.
- `Transactions.user_id` references `Users.id`.
- `ImageHistory.user_id` references `Users.id`.
- `Transactions.image_history_id` links a payment to a specific image record.
- `UserSessions.user_id` links persistent login tokens to the owning user.

These relationships keep the system simple while still allowing the app to answer questions like:

- Which image belongs to which user?
- Which transaction unlocked which image?
- Which sessions are currently valid?

## Security Features

- Passwords are hashed with bcrypt and never stored as plain text.
- Email validation is enforced before registration and login.
- Login lockout is triggered after five consecutive failed attempts.
- Session tokens are stored hashed in the database.
- Razorpay credentials are read only from environment variables.
- Secret files are ignored through `.gitignore`.
- Download access is tied to verified payment status.

### Authentication controls in practice

- The login form does not expose passwords in plain text.
- Passwords are validated before storage.
- Failed logins are tracked in the database.
- Repeated failures trigger a lockout period.
- On successful login, the system records `last_login`.
- Persistent login relies on a token stored in a cookie and hashed in the database.

### Payment security in practice

- Razorpay API keys are never hardcoded.
- Verification uses Razorpay’s signature validation before a transaction is marked successful.
- The dashboard download button is only shown when payment is confirmed.
- The UI continues to show only the free preview until the database state changes.

## File Upload Handling

Uploaded files are validated and stored safely.

- Accepted formats: JPG, PNG, BMP.
- Maximum file size: 10 MB.
- Files are saved using UUID names to avoid collisions.
- Metadata returned for display includes dimensions, file size, and format.
- Temporary files older than 24 hours can be cleaned automatically.

### Why UUID-based filenames matter

UUIDs prevent collisions when two users upload files with the same name. This is important because the app is multi-user and history records must remain deterministic and safe.

### Cleanup policy

Temporary files are kept only as long as needed. A cleanup helper removes old files after 24 hours so the server does not accumulate unnecessary image artifacts.

## Environment Variables

Set these environment variables before running the app or deploying it:

- `RAZORPAY_KEY_ID`
- `RAZORPAY_KEY_SECRET`

Example for PowerShell:

```powershell
$env:RAZORPAY_KEY_ID="your_key_id"
$env:RAZORPAY_KEY_SECRET="your_key_secret"
```

For local development, you can also use a `.env` file, but do not commit real secrets.

### Deployment note

In cloud deployment, set these values through your provider’s secret manager or environment-variable interface. Avoid placing production secrets in the source repository or in public deployment manifests.

## Installation

### 1. Clone or open the project

Open the repository root:

```text
c:\Users\LENOVO\Documents\infosys springboard internship
```

### 2. Install dependencies

Use Python and pip:

```powershell
python -m pip install -r requirements.txt
```

### 3. Initialize the database

Run the database setup script:

```powershell
python database/db_manager.py
```

This creates or updates the SQLite schema.

If you are deploying in a fresh environment, running the initializer before starting the app helps avoid missing-column or missing-table issues.

### 4. Set Razorpay environment variables

For payment support, set the Razorpay test credentials in your terminal or cloud environment.

```powershell
$env:RAZORPAY_KEY_ID="your_key_id"
$env:RAZORPAY_KEY_SECRET="your_key_secret"
```

### 5. Run the app

Use the Python module form to avoid PATH issues on Windows:

```powershell
python -m streamlit run frontend/app.py
```

## How to Use the App

### Sign Up

- Open the Home page.
- Go to Sign Up.
- Enter username, email, and password.
- Confirm the Terms and Conditions checkbox.
- Register.

### Login

- Go to Login.
- Enter your email and password.
- Optionally enable Remember Me.
- Submit the form.

### Process an Image

- Go to Processing.
- Upload an image.
- Pick a style category.
- Adjust intensity and filter-specific controls.
- Preview the result.
- Save the output to your gallery if signed in.

Behind the scenes, the app applies a style-specific helper from `backend/image_processing/` and tracks the processing time for UI feedback and QA validation.

### View History

- Go to Dashboard.
- Review your previously processed images.
- Paid images can be downloaded.
- Free previews remain watermarked until payment is verified.

The history gallery also helps users re-download previous paid content without needing to reprocess the image.

### Delete Account

- Open Dashboard.
- Click Delete Account.
- All user data, transactions, and image history are removed.

## Payment Flow

The payment flow uses Razorpay test mode.

- A user unlocks a paid image from the Dashboard.
- The app creates a Razorpay order.
- After payment, the signature is verified.
- On success, the image is marked paid in the database.
- The download button becomes available.

The payment flow is intentionally stateless from the browser perspective and stateful in the database. That means the app can recover from refreshes or reruns without losing the record of a verified purchase.

## Account Management

The dashboard includes a Delete Account action that removes the user and the associated transactional history.

When invoked, the application deletes:

- The user row from `Users`
- The user’s rows from `Transactions`
- The user’s rows from `ImageHistory`
- The user’s session tokens from `UserSessions` when revoked through logout or account deletion flow

This makes the account removal behavior clear and deterministic.

## QA and Testing

The project includes automated end-to-end tests in [tests/test_platform_e2e.py](tests/test_platform_e2e.py).

The test suite covers:

- Registration with valid credentials.
- Login with correct and incorrect passwords.
- Unique UUID-based upload naming.
- Cartoon pipeline execution and output validation.
- Mocked Razorpay order creation and signature verification.
- Database updates for Transactions and ImageHistory.
- UI checks for comparison slider and payment-gated download logic.

### Additional QA scope

The project is also intended to be checked for:

- Weak password rejection.
- Duplicate email rejection.
- Razorpay test-mode order creation.
- Signature verification behavior.
- Unauthorized access to paid download paths.
- Image-processing performance under large inputs.
- Basic memory behavior during processing.

### Suggested manual QA checklist

You can also manually confirm:

- New users can register successfully.
- Incorrect login attempts increment the failure counter.
- The account locks after repeated failures.
- The Home page links to every route correctly.
- Paid images are downloadable after verification.
- Free previews remain watermarked.
- Deleting an account removes its gallery records.

You can run the tests with:

```powershell
python -m unittest tests.test_platform_e2e -v
```

## Performance Notes

- Standard and large images are automatically resized during processing.
- This keeps the transformation pipeline responsive.
- The image-processing helpers are designed to keep total transformation time under five seconds for normal inputs.
- The codebase includes timed helper paths and memory-conscious resizing for practical deployment.

### Practical performance expectations

For standard images, the platform is designed to remain responsive enough for interactive use in Streamlit. Exact runtime depends on image resolution, selected effect, and local hardware, but the resizing strategy is intended to keep the processing workload under control for typical user inputs.

## Cloud Deployment Notes

This project is safe to deploy to cloud environments if you follow these steps:

- Keep Razorpay keys in cloud secrets or environment variables.
- Do not commit `.env` files.
- Let the database file live only in environments where local disk persistence is acceptable.
- For production, consider replacing local SQLite with a managed database.
- Use the `python -m streamlit run frontend/app.py` launch pattern in hosted environments when supported.

### Recommended cloud checklist

- Set environment variables for Razorpay.
- Persist the SQLite file only if your platform supports durable storage.
- If the deployment platform is ephemeral, replace SQLite with a managed database.
- Use HTTPS in production.
- Ensure uploaded file storage is backed by persistent storage if you want history to survive restarts.

### Production caution

The current implementation is fully usable as a prototype or small deployment, but production systems usually need:

- Managed database storage
- Object storage for uploads
- Logging and monitoring
- Rate limiting
- Centralized secret management

## Troubleshooting

### Streamlit command not found

Use:

```powershell
python -m streamlit run frontend/app.py
```

### Razorpay credentials missing

Set:

- `RAZORPAY_KEY_ID`
- `RAZORPAY_KEY_SECRET`

### Images not downloading

- Confirm payment verification completed successfully.
- Check that the image is marked as paid in the dashboard.
- Verify the processed file still exists on disk.

### Session lost on refresh

- Use Remember Me during login.
- Ensure cookies are allowed in the browser.
- Verify `extra-streamlit-components` is installed.

### Payment button not working

- Confirm the Razorpay environment variables are set.
- Verify the browser is not blocking cookies.
- Confirm the user is logged in before trying to unlock content.
- Make sure the Razorpay test credentials are active.

### Images do not show in history

- Verify the processed files still exist on disk.
- Confirm the image was saved to the gallery after processing.
- Check that the database file is writable.

### Download button not visible

- Confirm the transaction status is `success`.
- Confirm `is_paid` is set in `ImageHistory`.
- Refresh the Dashboard after verification so the UI reads the updated state.

## Notes on Open Source Images

The Home page uses public Wikimedia Commons image URLs as landing-page inspirations. They are included for UI presentation and structure only.

## Development Notes

### Adding a new effect

To add a new effect category or style:

1. Create a new module under the appropriate folder in `backend/image_processing/`.
2. Expose a simple `apply(image, intensity, ...)` function.
3. Ensure the module resizes large images before processing.
4. Add the style to the Streamlit tab group in `frontend/app.py`.
5. Save the `style` name to `ImageHistory` when storing output.

### Keeping the frontend maintainable

The frontend works best when the UI layer only coordinates actions and the backend modules do the image-heavy lifting. This prevents the Streamlit file from becoming a monolith.

### Keeping QA aligned with code

Whenever a new filter or page is added, update:

- `tests/test_platform_e2e.py`
- README usage notes
- database migrations if new fields are needed

## Known Constraints

- SQLite is convenient for development but not ideal for highly concurrent production traffic.
- Local image files in `uploads/` and `utilities/temp/` need persistent storage if deployed in an ephemeral cloud environment.
- Some OpenCV contrib features may vary by environment; fallback logic exists where possible.
- Streamlit reruns require careful session-state handling, which is why navigation and auth use session and cookie helpers.

## Future Enhancements

## Future Enhancements

- Add a richer mobile-responsive gallery view.
- Switch SQLite to a managed production database for cloud scale.
- Add more advanced shader-like or diffusion-inspired effects.
- Add user profile editing and avatar support.
- Add downloadable PDF contact sheets for processing history.
- Add admin dashboards and usage analytics.

## Summary

This project is a product-style image stylization system with secure authentication, paid download gating, modular effect pipelines, and a user-friendly Streamlit UI. The repository is arranged so that new effects, new UI pages, and improved deployment infrastructure can be added incrementally without rewriting the whole application.

The current implementation is especially suited to:

- Demonstrating applied computer vision skills.
- Showcasing secure user flows and payment integration.
- Presenting a realistic multi-page Streamlit product.
- Serving as a foundation for a more complete cloud-hosted visual editing platform.

## License

This project is currently documented as a working product prototype. Add a license file before public release if you intend to publish it externally.
