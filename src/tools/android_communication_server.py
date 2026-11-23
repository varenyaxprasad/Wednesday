
import re
import subprocess
from urllib.parse import quote, quote_plus

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Wednesday Android Agent")

ADB = "adb"


def run_adb(*args, timeout=15):
    """Run an ADB command and return its output."""
    result = subprocess.run(
        [ADB, *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    if result.returncode != 0:
        error = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(error or "ADB command failed")

    return result.stdout.strip()


def require_device():
    """Require exactly one connected Android device."""
    output = run_adb("devices")
    devices = []

    for line in output.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            devices.append(parts[0])

    if not devices:
        raise RuntimeError(
            "No authorized Android phone found. "
            "Connect the phone by USB and accept the debugging prompt."
        )

    if len(devices) > 1:
        raise RuntimeError(
            "Multiple devices found. Disconnect the extra devices first."
        )

    return devices[0]


@mcp.tool()
def phone_status() -> str:
    """Check whether the Android phone is connected through ADB."""
    device = require_device()
    model = run_adb("shell", "getprop", "ro.product.model")
    return f"Phone connected: {model} (device ID: {device})"


@mcp.tool()
def open_phone_app(app: str) -> str:
    """Open WhatsApp or YouTube on the connected Android phone."""
    require_device()

    packages = {
        "whatsapp": "com.whatsapp",
        "youtube": "com.google.android.youtube",
    }

    key = app.strip().lower()

    if key not in packages:
        return "Supported apps: WhatsApp and YouTube."

    package = packages[key]

    run_adb(
        "shell", "monkey", "-p", package, "1",
        timeout=20,
    )

    return (
        f"Opened {key}. If an app lock appears, "
        "unlock the app manually on your phone."
    )


@mcp.tool()
def search_youtube(query: str) -> str:
    """Open YouTube search results for a spoken query."""
    require_device()

    query = query.strip()
    if not query:
        return "Please provide a search query."

    url = (
        "https://www.youtube.com/results?search_query="
        + quote_plus(query)
    )

    run_adb(
        "shell", "am", "start",
        "-a", "android.intent.action.VIEW",
        "-d", url,
        "-p", "com.google.android.youtube",
        timeout=20,
    )

    return f"Opened YouTube search results for: {query}"


@mcp.tool()
def play_youtube_video(query: str) -> str:
    """Search YouTube and tap the first visible video title."""
    import time
    import xml.etree.ElementTree as ET
    from urllib.parse import quote_plus

    require_device()

    query = query.strip()
    if not query:
        return "Please provide a song or video title."

    url = (
        "https://www.youtube.com/results?search_query="
        + quote_plus(query)
    )

    run_adb(
        "shell", "am", "start",
        "-a", "android.intent.action.VIEW",
        "-d", url,
        "-p", "com.google.android.youtube",
        timeout=20,
    )

    # Give YouTube time to display search results.
    time.sleep(4)

    # Read the current Android screen's accessibility hierarchy.
    run_adb(
        "shell", "uiautomator", "dump",
        "/sdcard/wednesday_screen.xml",
        timeout=20,
    )
    xml_text = run_adb(
        "shell", "cat", "/sdcard/wednesday_screen.xml",
        timeout=10,
    )

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return "I opened YouTube, but couldn't inspect its screen."

    for node in root.iter("node"):
        resource_id = node.attrib.get("resource-id", "")
        title = node.attrib.get("text", "").strip()
        bounds = node.attrib.get("bounds", "")

        if (
            "video_title" not in resource_id
            or not title
            or not bounds
        ):
            continue

        try:
            coords = bounds.replace("][", ",").replace("]", "").replace("[", "")
            x1, y1, x2, y2 = map(int, coords.split(","))
        except ValueError:
            continue

        x = (x1 + x2) // 2
        y = (y1 + y2) // 2

        run_adb(
            "shell", "input", "tap", str(x), str(y)
        )
        time.sleep(3)

        return f"Tapped the first visible video title: {title}"

    return (
        "YouTube search opened, but I couldn't identify a video title "
        "on screen. The current screen layout may differ."
    )


@mcp.tool()
def scroll_youtube(direction: str = "down") -> str:
    """Scroll through YouTube results. Direction must be up or down."""
    require_device()

    direction = direction.strip().lower()
    if direction not in ("up", "down"):
        return "Direction must be 'up' or 'down'."

    output = run_adb("shell", "wm", "size")
    match = re.search(r"(\d+)x(\d+)", output)

    if not match:
        width, height = 1080, 1920
    else:
        width, height = map(int, match.groups())

    x = width // 2

    if direction == "down":
        start_y = int(height * 0.78)
        end_y = int(height * 0.30)
    else:
        start_y = int(height * 0.30)
        end_y = int(height * 0.78)

    run_adb(
        "shell", "input", "swipe",
        str(x), str(start_y),
        str(x), str(end_y),
        "450",
    )

    return f"Scrolled {direction}."


@mcp.tool()
def youtube_play_pause() -> str:
    """Toggle YouTube playback using the Android media play/pause key."""
    require_device()
    run_adb("shell", "input", "keyevent", "85")
    return "Sent the play/pause command."


@mcp.tool()
def phone_back() -> str:
    """Press the Android Back button."""
    require_device()
    run_adb("shell", "input", "keyevent", "4")
    return "Pressed Back."


@mcp.tool()
def prepare_whatsapp_message(
    phone_number: str,
    message: str,
) -> str:
    """
    Open a WhatsApp chat with a prefilled message.
    Use an international phone number including country code,
    without spaces or a plus sign. This does not send the message.
    """
    require_device()

    number = re.sub(r"\D", "", phone_number)

    if not number or len(number) < 8 or len(number) > 15:
        return (
            "Invalid phone number. Include the country code, "
            "for example 91 followed by the Indian mobile number."
        )

    if not message.strip():
        return "The message cannot be empty."

    url = (
        f"https://wa.me/{number}"
        f"?text={quote(message, safe='')}"
    )

    run_adb(
        "shell", "am", "start",
        "-a", "android.intent.action.VIEW",
        "-d", url,
        "-p", "com.whatsapp",
        timeout=20,
    )

    return (
        "WhatsApp was opened with the requested message link. "
        "Unlock WhatsApp if needed, inspect the recipient and message, "
        "and do not send until the user has explicitly approved it. "
        "This tool does not press Send."
    )
    
@mcp.tool()
def play_top_youtube_video(query: str) -> str:
    """Search YouTube and tap the first video result on screen."""
    import time
    import xml.etree.ElementTree as ET
    from urllib.parse import quote_plus

    require_device()

    query = query.strip()
    if not query:
        return "Tell me which song or video to search for."

    url = (
        "https://www.youtube.com/results?search_query="
        + quote_plus(query)
    )

    run_adb(
        "shell", "am", "start",
        "-a", "android.intent.action.VIEW",
        "-d", url,
        "-p", "com.google.android.youtube",
        timeout=20,
    )

    time.sleep(5)

    # Capture Android's visible UI hierarchy.
    run_adb(
        "shell", "uiautomator", "dump",
        "/sdcard/wednesday_ui.xml",
        timeout=20,
    )
    xml_text = run_adb(
        "shell", "cat", "/sdcard/wednesday_ui.xml",
        timeout=10,
    )

    root = ET.fromstring(xml_text)

    # Find the first clickable video-related element with screen bounds.
    for node in root.iter("node"):
        rid = node.attrib.get("resource-id", "").lower()
        desc = node.attrib.get("content-desc", "").lower()
        text = node.attrib.get("text", "").strip()
        bounds = node.attrib.get("bounds", "")

        if not bounds or not (
            "video" in rid or "video" in desc
            or "thumbnail" in rid or "thumbnail" in desc
        ):
            continue

        try:
            coords = bounds.replace("][", ",").replace("]", "").replace("[", "")
            x1, y1, x2, y2 = map(int, coords.split(","))
        except ValueError:
            continue

        if x2 <= x1 or y2 <= y1:
            continue

        x = (x1 + x2) // 2
        y = (y1 + y2) // 2

        run_adb(
            "shell", "input", "tap", str(x), str(y)
        )

        return f"Tapped the top video result. {text}"

    return (
        "I couldn't identify the top video element on this screen. "
        "YouTube's accessibility layout may differ on your phone."
    )



if __name__ == "__main__":
    mcp.run()
