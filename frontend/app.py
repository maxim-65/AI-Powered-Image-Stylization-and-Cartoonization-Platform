from pathlib import Path
from datetime import datetime, timedelta
import re
import sys
import time
from uuid import uuid4

import cv2
import numpy as np
import streamlit as st
from PIL import Image

try:
    import extra_streamlit_components as stx

    COOKIE_MANAGER_AVAILABLE = True
except ImportError:
    COOKIE_MANAGER_AVAILABLE = False

try:
    from streamlit_image_comparison import image_comparison

    IMAGE_COMPARISON_AVAILABLE = True
except ImportError:
    IMAGE_COMPARISON_AVAILABLE = False

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from backend.auth import (
    create_user_session,
    get_user_by_session_token,
    login_user,
    register_user,
    revoke_user_session,
)
from backend.dashboard import (
    delete_user_account,
    get_user_payment_history,
    get_user_profile,
    get_user_image_history,
    save_image_history,
    save_uploaded_file,
)
from backend.payment import (
    create_payment_order,
    get_subscription_plans,
    verify_payment_and_update_transaction,
)
from backend.image_processing.artistic import hdr as hdr_fx
from backend.image_processing.cartoon import advanced_pixar, basic as cartoon_basic, comic
from backend.image_processing.filters import pop_art, posterize, vintage
from backend.image_processing.fun import mosaic, pixel_art
from backend.image_processing.sketch import charcoal, pencil
from utilities.image_filters import generate_comparison_image


st.set_page_config(page_title="Auth App", page_icon="🔐", layout="wide")

TEMP_DIR = PROJECT_ROOT / "utilities" / "temp"
TEMP_DIR.mkdir(parents=True, exist_ok=True)
AUTH_COOKIE_NAME = "auth_session_token"
AUTH_COOKIE_KEY = "auth_session_cookie"

if "current_user" not in st.session_state:
    st.session_state["current_user"] = None
if "auth_token" not in st.session_state:
    st.session_state["auth_token"] = None
if "selected_page" not in st.session_state:
    st.session_state["selected_page"] = "Home"
if "processing_style" not in st.session_state:
    st.session_state["processing_style"] = "Classic"
if "login_popup_text" not in st.session_state:
    st.session_state["login_popup_text"] = None

cookie_manager = stx.CookieManager(key="cookie_manager") if COOKIE_MANAGER_AVAILABLE else None


def _set_auth_cookie(token: str, remember_me: bool = True) -> None:
    if not cookie_manager:
        return
    expires_at = datetime.utcnow() + timedelta(days=7 if remember_me else 1)
    cookie_manager.set(AUTH_COOKIE_NAME, token, expires_at=expires_at, key=AUTH_COOKIE_KEY)


def _delete_auth_cookie() -> None:
    if not cookie_manager:
        return
    cookie_manager.delete(AUTH_COOKIE_NAME, key=AUTH_COOKIE_KEY)


def _try_auto_login_from_cookie() -> None:
    if st.session_state.get("current_user") or not cookie_manager:
        return

    session_token = cookie_manager.get(AUTH_COOKIE_NAME)
    if not session_token:
        return

    success, result = get_user_by_session_token(session_token)
    if success:
        st.session_state["current_user"] = result
        st.session_state["auth_token"] = session_token
    else:
        _delete_auth_cookie()


_try_auto_login_from_cookie()


def _navigate_to(page: str) -> None:
    st.session_state["selected_page"] = page
    st.rerun()


def render_navigation_bar() -> None:
    login_popup_text = st.session_state.get("login_popup_text")
    if login_popup_text:
        st.toast(login_popup_text, icon="✅")
        st.session_state["login_popup_text"] = None

    st.markdown(
        """
        <style>
        .stButton > button {
            border-radius: 12px;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
            font-weight: 600;
        }
        .stButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 6px 18px rgba(0, 0, 0, 0.10);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    pages = [
        ("Home", "🏠"),
        ("Login", "🔑"),
        ("Sign Up", "📝"),
        ("Processing", "🖼️"),
        ("Dashboard", "📊"),
    ]

    current_page = st.session_state.get("selected_page", "Home")
    cols = st.columns(len(pages))
    for col, (page_name, icon) in zip(cols, pages):
        with col:
            if st.button(
                f"{icon} {page_name}",
                key=f"top_nav_{page_name.lower().replace(' ', '_')}",
                use_container_width=True,
                type="primary" if current_page == page_name else "secondary",
            ):
                if current_page != page_name:
                    _navigate_to(page_name)

    status_col, action_col = st.columns([5, 1])
    with status_col:
        if st.session_state.get("current_user"):
            st.caption(f"User: {st.session_state['current_user']['username']}")
        else:
            st.info("Not logged in")
    with action_col:
        if st.session_state.get("current_user"):
            if st.button("Logout", key="top_nav_logout", use_container_width=True):
                if st.session_state.get("auth_token"):
                    revoke_user_session(st.session_state["auth_token"])
                _delete_auth_cookie()
                st.session_state["auth_token"] = None
                st.session_state["current_user"] = None
                _navigate_to("Home")

    st.divider()


def _password_strength(password: str) -> tuple[int, int, str, str]:
    checks = [
        len(password) >= 8,
        bool(re.search(r"[A-Z]", password)),
        bool(re.search(r"[a-z]", password)),
        bool(re.search(r"\d", password)),
        bool(re.search(r"[^\w\s]", password)),
    ]

    score = sum(checks)
    percent = int((score / 5) * 100)

    red = int(255 * (1 - score / 5))
    green = int(255 * (score / 5))
    color = f"rgb({red}, {green}, 0)"

    if score <= 2:
        label = "Weak"
    elif score <= 4:
        label = "Medium"
    else:
        label = "Strong"

    return score, percent, color, label


def _ensure_same_size(original_rgb: np.ndarray, processed_rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    original_height, original_width = original_rgb.shape[:2]
    processed_height, processed_width = processed_rgb.shape[:2]

    if (original_height, original_width) != (processed_height, processed_width):
        processed_rgb = cv2.resize(
            processed_rgb,
            (original_width, original_height),
            interpolation=cv2.INTER_AREA,
        )

    return original_rgb, processed_rgb


def _add_subtle_watermark(image_rgb: np.ndarray, text: str = "PREVIEW") -> np.ndarray:
        watermarked = image_rgb.copy()
        overlay = watermarked.copy()

        height, width = watermarked.shape[:2]
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = max(0.6, min(width, height) / 1000)
        thickness = 2

        text_size, _ = cv2.getTextSize(text, font, font_scale, thickness)
        text_width, text_height = text_size
        x = width - text_width - 20
        y = height - 20

        cv2.putText(overlay, text, (x, y), font, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)
        alpha = 0.35
        cv2.addWeighted(overlay, alpha, watermarked, 1 - alpha, 0, watermarked)
        return watermarked


def _format_file_size(size_in_bytes: int) -> str:
    if size_in_bytes < 1024:
        return f"{size_in_bytes} B"
    if size_in_bytes < 1024 * 1024:
        return f"{size_in_bytes / 1024:.2f} KB"
    return f"{size_in_bytes / (1024 * 1024):.2f} MB"


def _compute_image_statistics(image_rgb: np.ndarray) -> dict[str, float]:
    gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)
    brightness = float(np.mean(gray))
    contrast = float(np.std(gray))

    mean_r = float(np.mean(image_rgb[:, :, 0]))
    mean_g = float(np.mean(image_rgb[:, :, 1]))
    mean_b = float(np.mean(image_rgb[:, :, 2]))
    mean_total = max(mean_r + mean_g + mean_b, 1e-6)

    red_dist = (mean_r / mean_total) * 100
    green_dist = (mean_g / mean_total) * 100
    blue_dist = (mean_b / mean_total) * 100

    return {
        "brightness": brightness,
        "contrast": contrast,
        "red_dist": red_dist,
        "green_dist": green_dist,
        "blue_dist": blue_dist,
    }


def render_login_page() -> None:
    st.title("Login")
    if st.button("Back to Home", use_container_width=True, key="login_back_home"):
        _navigate_to("Home")

    show_password = st.checkbox("Show Password", key="login_show_password")
    password_input_type = "default" if show_password else "password"

    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type=password_input_type)
        remember_me = st.checkbox("Remember Me", value=True)
        submitted = st.form_submit_button("Login")

    if submitted:
        success, result = login_user(email=email, password=password)
        if success:
            user = result
            st.session_state["current_user"] = user
            session_token = create_user_session(user["id"])
            st.session_state["auth_token"] = session_token
            _set_auth_cookie(session_token, remember_me=remember_me)
            st.session_state["login_popup_text"] = f"Logged in as {user['username']}"
            _navigate_to("Home")
        else:
            st.error(str(result))


def render_home_page() -> None:
    st.title("Home")
    st.write("Welcome to the AI-Powered Image Stylization platform.")
    st.markdown(
        "Upload an image, apply advanced stylization effects, compare before/after results, "
        "and save your processing history securely."
    )

    if st.session_state.get("current_user"):
        st.caption(f"Signed in as {st.session_state['current_user']['username']}")
    else:
        st.info("Sign in or create an account to save history and unlock downloads.")

    feature_col_1, feature_col_2, feature_col_3 = st.columns(3)
    with feature_col_1:
        st.markdown("### Fast Processing")
        st.write("High-performance OpenCV pipelines with automatic resizing for large images.")
    with feature_col_2:
        st.markdown("### Secure Access")
        st.write("Hashed passwords, session tokens, and payment-gated downloads for paid content.")
    with feature_col_3:
        st.markdown("### Styled Results")
        st.write("Classic cartoon, sketch, HDR, pop art, vintage, and fun effects in one place.")

    st.subheader("Quick Navigation")

    nav_col_1, nav_col_2, nav_col_3 = st.columns(3)
    with nav_col_1:
        if st.button("Go to Login", use_container_width=True, key="home_go_login"):
            _navigate_to("Login")
    with nav_col_2:
        if st.button("Go to Sign In", use_container_width=True, key="home_go_signin"):
            _navigate_to("Login")
        if st.button("Go to Sign Up", use_container_width=True, key="home_go_signup"):
            _navigate_to("Sign Up")
    with nav_col_3:
        if st.button("Go to Processing", use_container_width=True, key="home_go_processing"):
            _navigate_to("Processing")
        if st.button("Go to Dashboard", use_container_width=True, key="home_go_dashboard"):
            _navigate_to("Dashboard")

    st.subheader("Open Source Style Inspirations")
    st.markdown("Explore visual references that inspire the platform's stylization effects.")

    card_col_1, card_col_2, card_col_3 = st.columns(3)

    with card_col_1:
        st.markdown("#### Dreamy Color Fields")
        st.image(
            "https://upload.wikimedia.org/wikipedia/commons/e/ea/The_Starry_Night.jpg",
            use_container_width=True,
        )
        st.caption("Post-Impressionist reference for bold brush-like color movement.")

    with card_col_2:
        st.markdown("#### Strong Line Energy")
        st.image(
            "https://upload.wikimedia.org/wikipedia/commons/0/0a/The_Great_Wave_off_Kanagawa.jpg",
            use_container_width=True,
        )
        st.caption("High-contrast line structure that maps well to comic and cartoon filters.")

    with card_col_3:
        st.markdown("#### Natural Texture")
        st.image(
            "https://upload.wikimedia.org/wikipedia/commons/9/9a/Gull_portrait_ca_usa.jpg",
            use_container_width=True,
        )
        st.caption("Real-world texture reference useful for sketch and painterly effects.")

    st.caption(
        "Image sources: Wikimedia Commons public-domain/openly licensed works used for landing-page structure."
    )


def render_signup_page() -> None:
    st.title("Sign Up")
    if st.button("Back to Home", use_container_width=True, key="signup_back_home"):
        _navigate_to("Home")

    show_password = st.checkbox("Show Password", key="signup_show_password")
    password_input_type = "default" if show_password else "password"

    username = st.text_input("Username", key="signup_username")
    email = st.text_input("Email", key="signup_email")
    password = st.text_input("Password", type=password_input_type, key="signup_password")

    if password:
        _, percent, color, label = _password_strength(password)
        st.markdown(
            (
                "<div style='margin-top:8px;'>"
                "<div style='font-size:13px; margin-bottom:4px;'>Password Strength: "
                f"<b>{label}</b> ({percent}%)"
                "</div>"
                "<div style='width:100%; background:#e5e7eb; height:10px; border-radius:6px;'>"
                f"<div style='width:{percent}%; background:{color}; height:10px; border-radius:6px;'></div>"
                "</div>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )

    accepted_terms = st.checkbox("I agree to the Terms and Conditions", key="signup_terms")
    submitted = st.button("Register", disabled=not accepted_terms, key="signup_register")

    if submitted:
        success, message = register_user(username=username, email=email, password=password)
        if success:
            st.success(message)
        else:
            st.error(message)


def render_processing_page() -> None:
    st.title("Processing")
    if st.button("Back to Home", use_container_width=True, key="processing_back_home"):
        _navigate_to("Home")

    uploaded_file = st.file_uploader(
        "Upload an image (max 10MB)",
        type=["png", "jpg", "jpeg", "webp"],
    )

    if uploaded_file is None:
        st.info("Please upload an image to continue.")
        return

    if uploaded_file.size > 10 * 1024 * 1024:
        st.error("File size exceeds 10MB limit.")
        return

    tab_cartoon, tab_sketch, tab_filters, tab_ai, tab_fun = st.tabs(
        [
            "🎨 Cartoon Styles",
            "✏️ Sketch Styles",
            "🌈 Color Filters",
            "🧠 AI/HDR Effects",
            "🎮 Fun Effects",
        ]
    )

    with tab_cartoon:
        col1, col2, col3 = st.columns(3)
        if col1.button("Classic", use_container_width=True):
            st.session_state["processing_style"] = "Classic"
        if col2.button("Advanced", use_container_width=True):
            st.session_state["processing_style"] = "Advanced"
        if col3.button("Comic", use_container_width=True):
            st.session_state["processing_style"] = "Comic"

    with tab_sketch:
        col1, col2, col3 = st.columns(3)
        if col1.button("Pencil", use_container_width=True):
            st.session_state["processing_style"] = "Pencil"
        if col2.button("Charcoal", use_container_width=True):
            st.session_state["processing_style"] = "Charcoal"
        if col3.button("Colored Sketch", use_container_width=True):
            st.session_state["processing_style"] = "Colored Sketch"

    with tab_filters:
        col1, col2, col3 = st.columns(3)
        if col1.button("Vintage/Sepia", use_container_width=True):
            st.session_state["processing_style"] = "Vintage/Sepia"
        if col2.button("Pop Art", use_container_width=True):
            st.session_state["processing_style"] = "Pop Art"
        if col3.button("Posterize", use_container_width=True):
            st.session_state["processing_style"] = "Posterize"

    with tab_ai:
        col1, col2 = st.columns(2)
        if col1.button("Detail Enhance", use_container_width=True):
            st.session_state["processing_style"] = "Detail Enhance"
        if col2.button("Glow", use_container_width=True):
            st.session_state["processing_style"] = "Glow"

    with tab_fun:
        col1, col2 = st.columns(2)
        if col1.button("Pixel Art", use_container_width=True):
            st.session_state["processing_style"] = "Pixel Art"
        if col2.button("Mosaic", use_container_width=True):
            st.session_state["processing_style"] = "Mosaic"

    style = st.session_state["processing_style"]
    st.info(f"Selected Style: {style}")

    intensity = st.slider("Effect Intensity", min_value=1, max_value=100, value=50)
    k_value = None
    comic_k = None
    edge_thickness = 2

    if style in {"Classic", "Advanced"}:
        k_value = st.slider("Color Quantization (K)", min_value=8, max_value=16, value=10)
        edge_thickness = st.slider("Edge Thickness", min_value=1, max_value=4, value=2)
    elif style == "Comic":
        comic_k = st.slider("Comic Color Bands", min_value=2, max_value=4, value=3)

    file_bytes = np.frombuffer(uploaded_file.getvalue(), dtype=np.uint8)
    image_bgr = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

    if image_bgr is None:
        st.error("Unable to read the uploaded image.")
        return

    with st.spinner("Processing image..."):
        processing_start = time.perf_counter()

        if style == "Classic":
            processed_bgr = cartoon_basic.apply(image_bgr, intensity=intensity, k=k_value or 10)
            if edge_thickness > 1:
                edges = cv2.Canny(cv2.cvtColor(processed_bgr, cv2.COLOR_BGR2GRAY), 60, 160)
                edges = cv2.dilate(edges, np.ones((edge_thickness, edge_thickness), dtype=np.uint8), iterations=1)
                processed_bgr[edges > 0] = (0, 0, 0)
        elif style == "Advanced":
            processed_bgr = advanced_pixar.apply(image_bgr, intensity=intensity, k=k_value or 12)
        elif style == "Comic":
            processed_bgr = comic.apply(image_bgr, intensity=intensity, k=comic_k or 3)
        elif style == "Pencil":
            processed_bgr = pencil.apply(image_bgr, intensity=intensity)
        elif style == "Charcoal":
            processed_bgr = charcoal.apply(image_bgr, intensity=intensity)
        elif style == "Colored Sketch":
            processed_bgr = pencil.apply_colored(image_bgr, intensity=intensity)
        elif style == "Vintage/Sepia":
            processed_bgr = vintage.apply(image_bgr, intensity=intensity)
        elif style == "Pop Art":
            processed_bgr = pop_art.apply(image_bgr, intensity=intensity)
        elif style == "Posterize":
            processed_bgr = posterize.apply(image_bgr, intensity=intensity)
        elif style == "Detail Enhance":
            processed_bgr = hdr_fx.apply_detail_enhance(image_bgr, intensity=intensity)
        elif style == "Glow":
            processed_bgr = hdr_fx.apply_glow(image_bgr, intensity=intensity)
        elif style == "Pixel Art":
            processed_bgr = pixel_art.apply(image_bgr, intensity=intensity)
        else:
            processed_bgr = mosaic.apply(image_bgr, intensity=intensity)

        processing_time_ms = (time.perf_counter() - processing_start) * 1000

    original_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    processed_rgb = cv2.cvtColor(processed_bgr, cv2.COLOR_BGR2RGB)
    original_rgb, processed_rgb = _ensure_same_size(original_rgb, processed_rgb)
    preview_processed_rgb = _add_subtle_watermark(processed_rgb)

    col_original, col_processed = st.columns(2)
    with col_original:
        st.subheader("Original")
        st.image(original_rgb, use_container_width=True)
    with col_processed:
        st.subheader("Cartoonized")
        st.image(preview_processed_rgb, use_container_width=True)

    st.subheader("Interactive Comparison")
    if IMAGE_COMPARISON_AVAILABLE:
        image_comparison(
            img1=Image.fromarray(original_rgb),
            img2=Image.fromarray(preview_processed_rgb),
            label1="Original",
            label2="Processed",
            width=700,
            starting_position=50,
            make_responsive=True,
        )
    else:
        show_after = st.toggle("Before/After", value=True)
        if show_after:
            st.image(preview_processed_rgb, caption="After", use_container_width=True)
        else:
            st.image(original_rgb, caption="Before", use_container_width=True)

    comparison_image_bytes = generate_comparison_image(original_rgb, preview_processed_rgb)
    st.download_button(
        label="Download Comparison",
        data=comparison_image_bytes,
        file_name="comparison_original_processed.png",
        mime="image/png",
    )

    encode_success, processed_buffer = cv2.imencode(".png", cv2.cvtColor(processed_rgb, cv2.COLOR_RGB2BGR))
    processed_size_bytes = len(processed_buffer.tobytes()) if encode_success else 0

    original_stats = _compute_image_statistics(original_rgb)
    processed_stats = _compute_image_statistics(processed_rgb)

    st.subheader("Image Metadata & Statistics")
    meta_col_original, meta_col_processed = st.columns(2)

    with meta_col_original:
        st.markdown("**Original Image**")
        st.write(f"Dimensions: {original_rgb.shape[1]} x {original_rgb.shape[0]}")
        st.write(f"File Size: {_format_file_size(uploaded_file.size)}")
        st.write("Processing Time: 0.00 ms")
        st.write(f"Average Brightness: {original_stats['brightness']:.2f}")
        st.write(f"Contrast: {original_stats['contrast']:.2f}")
        st.write(
            "Color Distribution (R/G/B): "
            f"{original_stats['red_dist']:.2f}% / "
            f"{original_stats['green_dist']:.2f}% / "
            f"{original_stats['blue_dist']:.2f}%"
        )

    with meta_col_processed:
        st.markdown("**Processed Image**")
        st.write(f"Dimensions: {processed_rgb.shape[1]} x {processed_rgb.shape[0]}")
        st.write(f"File Size: {_format_file_size(processed_size_bytes)}")
        st.write(f"Processing Time: {processing_time_ms:.2f} ms")
        st.write(f"Average Brightness: {processed_stats['brightness']:.2f}")
        st.write(f"Contrast: {processed_stats['contrast']:.2f}")
        st.write(
            "Color Distribution (R/G/B): "
            f"{processed_stats['red_dist']:.2f}% / "
            f"{processed_stats['green_dist']:.2f}% / "
            f"{processed_stats['blue_dist']:.2f}%"
        )

    current_user = st.session_state.get("current_user")
    if current_user:
        if st.button("Save To Gallery"):
            unique_id = uuid4().hex
            original_path = save_uploaded_file(uploaded_file.getvalue(), uploaded_file.name)
            processed_path = TEMP_DIR / f"processed_{unique_id}.png"

            cv2.imwrite(str(processed_path), processed_bgr)

            _, result = save_image_history(
                user_id=current_user["id"],
                original_path=original_path,
                processed_path=str(processed_path),
                style=style.lower(),
            )
            st.success(f"Saved to gallery (ID: {result}).")
    else:
        st.info("Login to save processed images to your dashboard gallery.")


def render_dashboard_page() -> None:
    st.title("User Dashboard")
    if st.button("Back to Home", use_container_width=True, key="dashboard_back_home"):
        _navigate_to("Home")

    current_user = st.session_state.get("current_user")
    if not current_user:
        st.warning("Please login to access the dashboard.")
        return

    user_id = current_user["id"]
    profile = get_user_profile(user_id=user_id)
    display_username = profile["username"] if profile else current_user.get("username", "User")
    last_login = profile.get("last_login") if profile else None

    st.subheader(f"Welcome, {display_username}")
    if last_login:
        st.caption(f"Last Login: {last_login}")
    else:
        st.caption("Last Login: Not available")

    subscription_status = (profile or {}).get("subscription_status") or "inactive"
    subscription_plan_name = (profile or {}).get("subscription_plan_name") or "None"
    subscription_expires_at = (profile or {}).get("subscription_expires_at")
    st.caption(f"Subscription Status: {subscription_status.title()}")
    st.caption(f"Current Plan: {subscription_plan_name}")
    if subscription_expires_at:
        st.caption(f"Subscription Expires At: {subscription_expires_at}")

    st.subheader("Subscription Plans")
    subscription_plans = get_subscription_plans()
    subscription_options = {
        code: (
            f"{details['name']} - Rs. {details['amount']:.0f}"
            f" / {details['duration_days']} days"
        )
        for code, details in subscription_plans.items()
    }

    selected_subscription_code = st.selectbox(
        "Choose a plan",
        options=list(subscription_options.keys()),
        format_func=lambda code: subscription_options[code],
        key="subscription_plan_select",
    )

    selected_plan_details = subscription_plans[selected_subscription_code]
    if st.button("Subscribe", key="subscribe_now"):
        try:
            success, result = create_payment_order(
                user_id=user_id,
                amount=float(selected_plan_details["amount"]),
                transaction_type="subscription",
                plan_code=selected_subscription_code,
                receipt=f"sub_{user_id}_{uuid4().hex[:8]}",
                notes={
                    "user_id": str(user_id),
                    "subscription_code": selected_subscription_code,
                },
            )
        except Exception as error:
            success, result = False, f"Could not create subscription order: {error}"
        if success:
            st.session_state["subscription_payment"] = {
                "transaction_id": result["transaction_id"],
                "order_id": result["order"]["id"],
                "plan_name": selected_plan_details["name"],
            }
            st.success("Subscription order created. Complete payment and verify below.")
        else:
            st.error(str(result))

    subscription_payment_state = st.session_state.get("subscription_payment")
    if subscription_payment_state:
        st.info(
            f"Subscription Order ID: {subscription_payment_state['order_id']} "
            f"for {subscription_payment_state['plan_name']}"
        )
        sub_payment_id = st.text_input("Subscription razorpay_payment_id", key="sub_payment_id")
        sub_signature = st.text_input("Subscription razorpay_signature", key="sub_signature")

        if st.button("Verify Subscription Payment", key="verify_subscription_payment"):
            with st.spinner("Verifying subscription payment..."):
                try:
                    success, message = verify_payment_and_update_transaction(
                        transaction_id=subscription_payment_state["transaction_id"],
                        razorpay_order_id=subscription_payment_state["order_id"],
                        razorpay_payment_id=sub_payment_id,
                        razorpay_signature=sub_signature,
                    )
                except Exception as error:
                    success, message = False, f"Could not verify subscription payment: {error}"
            if success:
                st.session_state.pop("subscription_payment", None)
                st.success(message)
                st.rerun()
            else:
                st.error(message)

    st.subheader("My History")
    history = get_user_image_history(user_id=user_id)

    if not history:
        st.info("No images found in your gallery yet.")
    else:
        for item in history:
            image_id = item["id"]
            st.markdown(f"### Image #{image_id}")

            gallery_col, details_col = st.columns([1, 2])
            with gallery_col:
                if Path(item["processed_path"]).exists():
                    processed_dashboard_bgr = cv2.imread(item["processed_path"], cv2.IMREAD_COLOR)
                    if processed_dashboard_bgr is not None:
                        processed_dashboard_rgb = cv2.cvtColor(processed_dashboard_bgr, cv2.COLOR_BGR2RGB)
                        if int(item.get("is_paid", 0)) == 1 and item.get("payment_status") == "success":
                            st.image(processed_dashboard_rgb, use_container_width=True)
                        else:
                            st.image(_add_subtle_watermark(processed_dashboard_rgb), use_container_width=True)
                    else:
                        st.warning("Processed image could not be loaded.")
                else:
                    st.warning("Processed image file missing.")

            with details_col:
                st.caption(f"Style: {item['style'].title()}")
                payment_label = "Paid" if int(item.get("is_paid", 0)) == 1 and item.get("payment_status") == "success" else "Free Preview"
                st.caption(f"Payment Status: {payment_label}")

            if int(item.get("is_paid", 0)) == 1 and item.get("payment_status") == "success":
                processed_file_path = Path(item["processed_path"])
                if processed_file_path.exists():
                    st.download_button(
                        label="Download",
                        data=processed_file_path.read_bytes(),
                        file_name=processed_file_path.name,
                        mime="image/png",
                        key=f"download_{image_id}",
                    )
                else:
                    st.error("Cannot download. Processed image file not found.")
            else:
                if st.button("Unlock", key=f"unlock_{image_id}"):
                    try:
                        success, result = create_payment_order(
                            user_id=user_id,
                            amount=49.0,
                            image_history_id=image_id,
                            transaction_type="image_unlock",
                            receipt=f"img_{image_id}_{uuid4().hex[:8]}",
                            notes={"image_history_id": str(image_id)},
                        )
                    except Exception as error:
                        success, result = False, f"Could not create unlock order: {error}"
                    if success:
                        st.session_state[f"payment_{image_id}"] = {
                            "transaction_id": result["transaction_id"],
                            "order_id": result["order"]["id"],
                        }
                        st.success("Order created. Complete payment, then verify below.")
                    else:
                        st.error(str(result))

                payment_state = st.session_state.get(f"payment_{image_id}")
                if payment_state:
                    st.info(f"Razorpay Order ID: {payment_state['order_id']}")
                    razorpay_payment_id = st.text_input("razorpay_payment_id", key=f"payment_id_{image_id}")
                    razorpay_signature = st.text_input("razorpay_signature", key=f"signature_{image_id}")

                    if st.button("Verify Payment", key=f"verify_{image_id}"):
                        with st.spinner("Verifying payment..."):
                            try:
                                success, message = verify_payment_and_update_transaction(
                                    transaction_id=payment_state["transaction_id"],
                                    razorpay_order_id=payment_state["order_id"],
                                    razorpay_payment_id=razorpay_payment_id,
                                    razorpay_signature=razorpay_signature,
                                    image_history_id=image_id,
                                )
                            except Exception as error:
                                success, message = False, f"Could not verify payment: {error}"
                        if success:
                            st.session_state.pop(f"payment_{image_id}", None)
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)

            st.divider()

    st.subheader("Payment History")
    payment_history = get_user_payment_history(user_id=user_id)
    if not payment_history:
        st.info("No payment records found yet.")
    else:
        st.dataframe(
            payment_history,
            use_container_width=True,
            hide_index=True,
        )

    if st.button("Delete Account", type="primary"):
        if st.session_state.get("auth_token"):
            revoke_user_session(st.session_state["auth_token"])
        _delete_auth_cookie()
        success, message = delete_user_account(user_id=user_id)
        if success:
            st.session_state["current_user"] = None
            st.session_state["auth_token"] = None
            st.success(message)
            st.rerun()
        else:
            st.error(message)


render_navigation_bar()
selected_page = st.session_state.get("selected_page", "Home")

if selected_page == "Home":
    render_home_page()
elif selected_page == "Login":
    render_login_page()
elif selected_page == "Sign Up":
    render_signup_page()
elif selected_page == "Processing":
    render_processing_page()
else:
    render_dashboard_page()
