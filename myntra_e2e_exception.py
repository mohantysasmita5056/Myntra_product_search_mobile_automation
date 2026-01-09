
# myntra_login_otp_product search_flow.py
# Flow: Launch Myntra -> Tap Account -> Tap Login/Signup -> Type Mobile -> Tick Continue -> Click Login using OTP -> Handle post-OTP navigation -> Enter OTP (4 boxes) -> Back -> Search


import time
import re
from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# appium server url
APPIUM_SERVER_URL = "http://127.0.0.1:4723"          # if server started with plain `appium`
# APPIUM_SERVER_URL = "http://127.0.0.1:4723/wd/hub"  # if server started with `appium --base-path /wd/hub`

# --- W3C capabilities with appium: prefixes ---
CAPS = {
    "platformName": "Android",
    "appium:automationName": "UiAutomator2",
    "appium:deviceName": "emulator-5554",
    "appium:noReset": True,
    "appium:newCommandTimeout": 300,
    "appium:appPackage": "com.myntra.android",
    "appium:appActivity": "com.myntra.android.activities.SplashActivity",
    "appium:autoGrantPermissions": True,
    # Optional: helps IME changes if needed; harmless otherwise
    "appium:enableImeAutomation": True,
}
options = UiAutomator2Options().load_capabilities(CAPS)

# --- LOCATORS
ACCOUNT_ICON_XPATH = '//android.view.ViewGroup[@content-desc="ic_actionbar_profile"]/android.view.ViewGroup'

# Login/Signup container (clickable=true)
LOGIN_SIGNUP_CONTAINER_XPATH = (
    '//android.widget.ScrollView/android.view.ViewGroup/'
    'android.view.ViewGroup[1]/android.view.ViewGroup[4]/android.view.ViewGroup'
)
LOGIN_SIGNUP_BOUNDS = "[532,774][1384,921]"  # from Inspector (fallback)

# Continue checkbox (ImageView, clickable=false → tap center)
CONTINUE_CHECKBOX_XPATH = (
    '//android.widget.ScrollView/android.view.ViewGroup/'
    'android.view.ViewGroup[2]/android.view.ViewGroup[2]/android.widget.ImageView'
)
CONTINUE_CHECKBOX_BOUNDS = "[112,1643][182,1713]"  # from Inspector (fallback)

# Login using OTP button (content-desc = "form-button", clickable=true)
LOGIN_USING_OTP_ACC_ID = ("accessibility id", "form-button")
LOGIN_USING_OTP_XPATH = '//android.view.ViewGroup[@content-desc="form-button"]'

# Mobile number you want to type
MOBILE_NUMBER = "8895464285"

# --- NEW: Profile back button + Search bar (your locators) ---
PROFILE_BACK_XPATH = '//android.widget.TextView[@text=""]'
PROFILE_BACK_BOUNDS = "[37,189][121,275]"  # fallback coordinates
SEARCH_BAR_XPATH = '//android.view.ViewGroup[@content-desc="HPSearchBar"]/android.view.ViewGroup[2]'
SEARCH_QUERY = "mens denim shirts"

# --- Helpers ---
def wait_presence(driver, locator, timeout=12):
    return WebDriverWait(driver, timeout).until(EC.presence_of_element_located(locator))

def wait_visible(driver, locator, timeout=12):
    return WebDriverWait(driver, timeout).until(EC.visibility_of_element_located(locator))

def wait_click(driver, locator, timeout=12):
    el = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable(locator))
    el.click()
    return el

def tap_center_of_xpath(driver, xpath, timeout=12):
    el = wait_presence(driver, (AppiumBy.XPATH, xpath), timeout)
    r = el.rect
    driver.execute_script("mobile: clickGesture", {"x": r["x"] + r["width"]//2, "y": r["y"] + r["height"]//2})

def tap_center_by_bounds(driver, bounds_str: str):
    # Parse bounds like "[x1,y1][x2,y2]" and tap the center
    m = re.findall(r"\[(\d+),(\d+)\]", bounds_str)
    (x1, y1), (x2, y2) = map(lambda p: (int(p[0]), int(p[1])), m)
    driver.execute_script("mobile: clickGesture", {"x": (x1 + x2)//2, "y": (y1 + y2)//2})

def find_edit_text_under_container(driver, container_xpath, timeout=10):
    # Look for any EditText under your Login/Signup container
    return wait_visible(driver, (AppiumBy.XPATH, container_xpath + "//android.widget.EditText"), timeout)

# --- Add these helpers near your existing helper functions ---
def save_artifacts(driver, prefix="otp_error"):
    """Capture screenshot, page source, and logcat to help devs triage."""
    try:
        fname_png = f"{prefix}.png"
        driver.save_screenshot(fname_png)
        print(f"📸 Saved {fname_png}")
    except Exception:
        pass
    try:
        fname_xml = f"{prefix}_source.xml"
        with open(fname_xml, "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print(f"📝 Saved {fname_xml}")
    except Exception:
        pass
    # Try grabbing logcat via Appium's mobile: shell (UiAutomator2 supports this)
    try:
        out = driver.execute_script("mobile: shell", {"command": "logcat", "args": ["-d"], "timeout": 5000})
        fname_log = f"{prefix}_logcat.txt"
        with open(fname_log, "w", encoding="utf-8") as f:
            f.write(out.get("stdout", "") or "")
        print(f"📄 Saved {fname_log}")
    except Exception:
        print("ℹ️ Could not fetch logcat via driver; you can also run `adb logcat -d > logcat.txt` in a terminal.")

def saw_otp_screen(driver, timeout=8):
    """Return True if OTP screen is detected; False otherwise."""
    # Try finding a typical OTP input or label
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((AppiumBy.ID, "com.myntra.android:id/et_otp"))
        )
        return True
    except TimeoutException:
        pass
    # Fallback: look for any text containing 'OTP'
    try:
        WebDriverWait(driver, 3).until(
            EC.presence_of_element_located(
                (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textContains("OTP")')
            )
        )
        return True
    except TimeoutException:
        return False

def check_error_indicators(driver):
    """Try to read toasts or visible error labels and return a message if found."""
    # Toast (briefly visible)
    try:
        toast_el = WebDriverWait(driver, 2).until(
            EC.presence_of_element_located((AppiumBy.XPATH, "//android.widget.Toast"))
        )
        msg = toast_el.get_attribute("text") or "(toast without text)"
        return f"Toast: {msg}"
    except TimeoutException:
        pass
    # Generic text containing error keywords
    try:
        err_el = driver.find_element(
            AppiumBy.ANDROID_UIAUTOMATOR,
            'new UiSelector().textMatches("(?i)(error|failed|server)")'
        )
        return f"Error label: {err_el.get_attribute('text')}"
    except Exception:
        return None

def handle_post_otp_navigation(driver):
    """After clicking 'Login using OTP', wait for OTP screen or handle failures."""
    if saw_otp_screen(driver, timeout=8):
        print("✅ OTP screen detected.")
        return True

    # OTP screen did not appear → check error and capture artifacts
    msg = check_error_indicators(driver)
    if msg:
        print(f"⚠️ Detected issue after OTP click: {msg}")
    else:
        print("⚠️ OTP screen not detected and no explicit error label/toast found.")

    save_artifacts(driver, prefix="otp_internal_error")

    # One retry (often helps if backend blips)
    print("🔁 Retrying 'Login using OTP' once...")
    try:
        # First try accessibility id again
        wait_click(driver, (AppiumBy.ACCESSIBILITY_ID, "form-button"), timeout=5)
    except Exception:
        # Fallback to XPath
        try:
            wait_click(driver, (AppiumBy.XPATH, '//android.view.ViewGroup[@content-desc="form-button"]'), timeout=5)
        except Exception:
            print("❌ Retry click failed.")

    # Check again
    if saw_otp_screen(driver, timeout=8):
        print("✅ OTP screen detected on retry.")
        return True

    # Still failing → proceed as guest path (skip login)
    print("🚧 Still blocked by app-side error. Proceeding without login.")
    return False

# --- Accessibility overlay helper ---
def disable_accessibility_overlay(driver):
    """
    Try to disable common accessibility overlays that add floating UI (e.g., Accessibility Menu).
    Safe to call on emulator; on real devices it may require OEM/permission, so failures are ignored.
    """
    cmds = [
        ["settings", "put", "secure", "enabled_accessibility_services", ""],
        ["settings", "put", "secure", "accessibility_button_targets", ""],
        ["settings", "put", "secure", "accessibility_button_mode", "0"],
        ["settings", "put", "secure", "accessibility_display_magnification_enabled", "0"],
    ]
    for args in cmds:
        try:
            driver.execute_script("mobile: shell", {"command": args[0], "args": args[1:], "timeout": 5000})
        except Exception:
            pass
    print("🛑 Attempted to disable accessibility overlays via secure settings.")

# --- OTP (4-box) Helpers ---
def otp_box_xpath(i: int) -> str:
    """Return the XPath for the i-th OTP TextView box (as per your Inspector)."""
    # Pattern observed: (//android.widget.TextView[@text=" "])[i]
    return f'(//android.widget.TextView[@text=" "])[{i}]'

def focus_otp_input_area(driver, box_el=None, timeout=6) -> bool:
    """
    Try to focus the hidden OTP EditText first; if not found, tap the center of a box.
    Returns True if we believe focus was achieved.
    """
    try:
        et = wait_visible(driver, (AppiumBy.ID, "com.myntra.android:id/et_otp"), timeout)
        et.click()
        return True
    except Exception:
        pass

    if box_el:
        try:
            r = box_el.rect
            driver.execute_script("mobile: clickGesture", {"x": r["x"] + r["width"]//2, "y": r["y"] + r["height"]//2})
            return True
        except Exception:
            pass

    return False

def verify_otp_boxes_populated(driver, boxes) -> bool:
    """
    After typing, verify each box shows a non-empty character (digit or mask).
    """
    ok = True
    for i, el in enumerate(boxes, start=1):
        try:
            txt = (el.get_attribute("text") or "").strip()
        except Exception:
            try:
                txt = (driver.find_element(AppiumBy.XPATH, otp_box_xpath(i)).get_attribute("text") or "").strip()
            except Exception:
                txt = ""
        if not txt:
            ok = False
            print(f"⚠️ OTP box {i} is still empty.")
    return ok

# --- NEW: custom keypad typing helpers ---
DIGIT_KEYCODES = {
    "0": 7, "1": 8, "2": 9, "3": 10, "4": 11,
    "5": 12, "6": 13, "7": 14, "8": 15, "9": 16
}

def try_tap_keypad_digit(driver, d: str, timeout=2) -> bool:
    """
    Try to tap an in-app keypad digit element (Button/TextView) with text/content-desc == d.
    Returns True if tapped; False otherwise.
    """
    candidates = [
        (AppiumBy.ANDROID_UIAUTOMATOR, f'new UiSelector().text("{d}").classNameMatches(".*(Button|TextView).*")'),
        (AppiumBy.ACCESSIBILITY_ID, d),
        (AppiumBy.XPATH, f'//*[(@text="{d}" or @content-desc="{d}") and (contains(@class,"Button") or contains(@class,"TextView"))]'),
    ]
    for by, locator in candidates:
        try:
            el = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, locator)))
            r = el.rect
            driver.execute_script("mobile: clickGesture", {"x": r["x"] + r["width"]//2, "y": r["y"] + r["height"]//2})
            return True
        except Exception:
            continue
    return False

def type_digit_via_keycode(driver, d: str) -> bool:
    """Type a single digit using Android keycode (acts like real keyboard key press)."""
    try:
        driver.press_keycode(DIGIT_KEYCODES[d])
        return True
    except Exception:
        return False

def type_digit_via_adb_input(driver, d: str) -> bool:
    """Fallback: inject digit via 'adb shell input text d'."""
    try:
        driver.execute_script("mobile: shell", {"command": "input", "args": ["text", d], "timeout": 5000})
        return True
    except Exception:
        return False

def enter_otp_via_app_keypad(driver, otp: str, focus_el=None) -> bool:
    """
    Enter OTP by first focusing, then tapping keypad digits if present; fall back to keycodes/adb input.
    Returns True on success; False otherwise.
    """
    if not re.fullmatch(r"\d{4}", otp):
        print("⚠️ Invalid OTP format; expecting exactly 4 digits.")
        return False

    # Ensure focus first (tap first box or hidden EditText)
    focused = focus_otp_input_area(driver, box_el=focus_el)
    if not focused:
        print("ℹ️ Could not confirm focus; continuing to type anyway.")

    # Now type each digit robustly
    for d in otp:
        if try_tap_keypad_digit(driver, d):
            continue
        if type_digit_via_keycode(driver, d):
            continue
        if type_digit_via_adb_input(driver, d):
            continue
        print(f"❌ Could not type digit '{d}' by any method.")
        return False

    return True

# --- NEW: Back + Search using your locators ---
def tap_profile_back(driver):
    """
    Tap the profile back button using your XPath; fallback to bounds; then hardware back.
    """
    try:
        # Preferred: XPath center tap
        tap_center_of_xpath(driver, PROFILE_BACK_XPATH, timeout=4)
        print("⬅️ Profile back tapped via XPath.")
        time.sleep(0.3)
        return True
    except Exception:
        pass

    # Fallback: bounds center tap
    try:
        tap_center_by_bounds(driver, PROFILE_BACK_BOUNDS)
        print("⬅️ Profile back tapped via bounds fallback.")
        time.sleep(0.3)
        return True
    except Exception:
        pass

    # Last resort: hardware back
    try:
        driver.press_keycode(4)  # KEYCODE_BACK
        print("⬅️ Sent hardware BACK key.")
        time.sleep(0.3)
        return True
    except Exception:
        print("⚠️ Could not navigate back from profile screen.")
        return False

def open_search_and_submit_query(driver, query: str):
    """
    Click your provided search bar XPath, then type and submit the query.
    """
    # 1) Open search bar
    opened = False
    try:
        wait_click(driver, (AppiumBy.XPATH, SEARCH_BAR_XPATH), timeout=6)
        opened = True
        print("🔎 Search bar opened via XPath.")
    except Exception:
        try:
            tap_center_of_xpath(driver, SEARCH_BAR_XPATH, timeout=6)
            opened = True
            print("🔎 Search bar tapped via XPath (center).")
        except Exception:
            pass

    if not opened:
        print("❌ Could not open search bar via provided XPath.")
        save_artifacts(driver, prefix="search_bar_open_failed")
        return False

    time.sleep(0.5)

    # 2) Type query into input and submit
    typed = False
    try:
        # Common input id used by Myntra
        inp = wait_visible(driver, (AppiumBy.ID, "com.myntra.android:id/search_src_text"), timeout=6)
        inp.clear()
        inp.send_keys(query)
        typed = True
        print(f"✍️ Typed query via ID: {query}")
    except Exception:
        pass

    if not typed:
        # Try active element
        try:
            ae = driver.switch_to.active_element
            ae.send_keys(query)
            typed = True
            print(f"✍️ Typed query via active element: {query}")
        except Exception:
            pass

    if not typed:
        # Last resort: adb input text
        try:
            driver.execute_script("mobile: shell", {"command": "input", "args": ["text", query], "timeout": 5000})
            typed = True
            print(f"✍️ Typed query via adb input: {query}")
        except Exception:
            print("❌ Could not type search query.")
            save_artifacts(driver, prefix="search_query_type_failed")
            return False

    # 3) Submit (ENTER) to search
    try:
        driver.press_keycode(66)  # KEYCODE_ENTER
        print("✅ Search submitted (ENTER).")
    except Exception:
        try:
            driver.execute_script("mobile: shell", {"command": "input", "args": ["keyevent", "66"], "timeout": 3000})
            print("✅ Search submitted (shell keyevent 66).")
        except Exception:
            # As a last resort, try newline
            try:
                driver.switch_to.active_element.send_keys("\n")
                print("✅ Search submitted (newline).")
            except Exception:
                print("⚠️ Could not submit search via ENTER/newline.")
                save_artifacts(driver, prefix="search_submit_failed")
                return False

    return True

# --- Main Flow ---
def main():
    driver = None
    try:
        driver = webdriver.Remote(command_executor=APPIUM_SERVER_URL, options=options)
        time.sleep(2)

        # 0) Optional: dismiss promo cross if present
        try:
            wait_click(driver, (AppiumBy.ACCESSIBILITY_ID, "login_skip_button"), timeout=3)
            time.sleep(1)
        except Exception:
            pass

        # 1) Tap Account icon (your XPath)
        tap_center_of_xpath(driver, ACCOUNT_ICON_XPATH, timeout=10)
        print("✅ Account tapped.")

        # 2) Tap Login/Signup container (clickable=true)
        try:
            wait_click(driver, (AppiumBy.XPATH, LOGIN_SIGNUP_CONTAINER_XPATH), timeout=8)
            print("✅ Login/Signup container clicked.")
        except Exception:
            tap_center_of_xpath(driver, LOGIN_SIGNUP_CONTAINER_XPATH, timeout=8)
            print("✅ Login/Signup container tapped (center).")
        time.sleep(0.8)

        # 3) Type the mobile number
        typed = False
        # Try common accessibility id first (Myntra often exposes 'mobile')
        try:
            mobile_field = wait_visible(driver, (AppiumBy.ACCESSIBILITY_ID, "mobile"), timeout=6)
            try:
                mobile_field.clear()
            except Exception:
                mobile_field.click()
            mobile_field.send_keys(MOBILE_NUMBER)
            print("✅ Mobile typed via accessibility id: mobile")
            typed = True
        except Exception:
            pass

        # Fallback: find an EditText under the Login/Signup container
        if not typed:
            try:
                edit_field = find_edit_text_under_container(driver, LOGIN_SIGNUP_CONTAINER_XPATH, timeout=8)
                try:
                    edit_field.clear()
                except Exception:
                    edit_field.click()
                edit_field.send_keys(MOBILE_NUMBER)
                print("✅ Mobile typed via container's EditText descendant.")
                typed = True
            except Exception:
                pass

        # Last resort: focus container by bounds then type into active element
        if not typed:
            try:
                tap_center_by_bounds(driver, LOGIN_SIGNUP_BOUNDS)
                time.sleep(0.5)
                driver.switch_to.active_element.send_keys(MOBILE_NUMBER)
                print("✅ Mobile typed via active element (focused container).")
                typed = True
            except Exception:
                pass

        if not typed:
            print("⚠️ Mobile field could not be typed. Re-check locator in Inspector.")
            return

        time.sleep(0.5)

        # 4) Tick the Continue checkbox (ImageView, not directly clickable → tap center)
        try:
            tap_center_of_xpath(driver, CONTINUE_CHECKBOX_XPATH, timeout=6)
            print("✅ Continue checkbox tapped (center via rect).")
        except Exception:
            tap_center_by_bounds(driver, CONTINUE_CHECKBOX_BOUNDS)
            print("✅ Continue checkbox tapped (center via bounds fallback).")
        time.sleep(0.4)

        # 5) Click "Login using OTP" (content-desc = form-button, clickable=true)
        clicked_otp = False
        try:
            wait_click(driver, (AppiumBy.ACCESSIBILITY_ID, "form-button"), timeout=6)
            print("✅ 'Login using OTP' clicked via accessibility id.")
            clicked_otp = True
        except Exception:
            pass

        if not clicked_otp:
            try:
                wait_click(driver, (AppiumBy.XPATH, LOGIN_USING_OTP_XPATH), timeout=6)
                print("✅ 'Login using OTP' clicked via XPath.")
                clicked_otp = True
            except Exception:
                pass

        if not clicked_otp:
            print("⚠️ Could not click 'Login using OTP'. Verify locator in Inspector.")
            return

        # --- Call post-OTP navigation handler right after the OTP click ---
        success = handle_post_otp_navigation(driver)

        # Console prompt + app keypad typing ---
        if success:
            print("➡️ OTP screen detected. Capturing the 4 OTP boxes...")

            # 1) Capture the 4 TextView boxes by your XPaths (index 1..4)
            try:
                boxes = [wait_presence(driver, (AppiumBy.XPATH, otp_box_xpath(i)), timeout=10) for i in range(1, 5)]
                print("✅ OTP boxes detected via XPath indices 1..4.")
            except TimeoutException:
                print("❌ Could not find OTP boxes with the provided XPath.")
                save_artifacts(driver, prefix="otp_boxes_not_found")
                return

            # 2) Prompt in console and type via app keypad / keycodes
            otp = input("Enter the 4-digit OTP: ").strip()
            if not re.fullmatch(r"\d{4}", otp):
                print("⚠️ Invalid OTP format. Expect exactly 4 digits.")
                save_artifacts(driver, prefix="otp_invalid_format")
            else:
                # Disable overlay if any, to avoid focus steal
                disable_accessibility_overlay(driver)
                time.sleep(0.3)

                ok = enter_otp_via_app_keypad(driver, otp, focus_el=boxes[0])
                if ok:
                    print("✅ OTP typed (keypad/keycodes).")
                else:
                    print("❌ OTP typing failed. Saving artifacts for triage.")
                    save_artifacts(driver, prefix="otp_typing_failed")

            # 3) Verify that the 4 boxes show something (digit/mask)
            if verify_otp_boxes_populated(driver, boxes):
                print("✅ OTP boxes populated.")
                # Optional: submit/continue if the app needs ENTER
                try:
                    driver.press_keycode(66)  # ENTER (often triggers verification)
                except Exception:
                    pass
            else:
                print("⚠️ OTP boxes not populated as expected.")
                save_artifacts(driver, prefix="otp_verify_failed")

        else:
            # Guest path: continue to search even without being logged in
            try:
                wait_click(driver, (AppiumBy.ID, "com.myntra.android:id/search_bar"), timeout=10)
                inp = wait_visible(driver, (AppiumBy.ID, "com.myntra.android:id/search_src_text"), timeout=10)
                inp.send_keys("Running shoes")
                try:
                    driver.press_keycode(66)  # ENTER
                except Exception:
                    inp.send_keys("\n")
                print("🔎 Continued as guest: search submitted.")
            except Exception as e:
                print(f"❌ Could not proceed as guest: {e}")

        # Back to profile/home and perform product search with your locators ---
        print("🏠 Navigating back and performing product search...")
        if not tap_profile_back(driver):
            print("⚠️ Back action failed or not needed; proceeding to search anyway.")

        if open_search_and_submit_query(driver, SEARCH_QUERY):
            print("🎯 Search flow completed.")
        else:
            print("❌ Search flow failed. Check search bar locator or input field ID.")

        # small wait to allow navigation to search results
        time.sleep(2)

    except Exception as e:
        print(f"\n❌ Error in flow: {e}")
        try:
            driver.save_screenshot("login_otp_flow_error.png")
            print("📸 Saved login_otp_flow_error.png")
        except Exception:
            pass
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    main()
