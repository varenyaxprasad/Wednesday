
import asyncio
import logging
from pathlib import Path
from urllib.parse import quote, urlparse

from mcp.server.fastmcp import FastMCP
from playwright.async_api import async_playwright


logging.basicConfig(level=logging.INFO)

mcp = FastMCP("wednesday-browser")

ROOT = Path(__file__).resolve().parents[2]
PROFILE = ROOT / "data" / "browser-profile"
DOWNLOADS = ROOT / "workspace" / "downloads"

PROFILE.mkdir(parents=True, exist_ok=True)
DOWNLOADS.mkdir(parents=True, exist_ok=True)

playwright = None
context = None
page = None
lock = asyncio.Lock()



async def get_page():
    global playwright, context, page

    async with lock:
        if page is not None and not page.is_closed():
            return page

        if playwright is None:
            playwright = await async_playwright().start()

        if context is None:
            context = await playwright.chromium.launch_persistent_context(
                user_data_dir=str(PROFILE),
                headless=False,
                accept_downloads=True,
                viewport={"width": 1440, "height": 900}
            )

        page = context.pages[0] if context.pages else await context.new_page()

        return page


def validate_url(url):
    parsed = urlparse(url.strip())

    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("Only valid HTTP and HTTPS URLs are allowed.")

    return url.strip()


async def check_verification_wall(browser):
    """Detect common YouTube and Google verification pages."""

    title = (await browser.title()).lower()
    body = (await browser.locator("body").inner_text()).lower()

    indicators = [
        "unusual traffic",
        "verify you are human",
        "confirm you're not a bot",
        "complete the captcha",
        "before you continue",
        "automated requests",
    ]

    return any(
        item in title or item in body
        for item in indicators
    )



@mcp.tool()
async def browser_open(url: str) -> str:
    """Open a website in a new browser tab."""

    global page

    browser = await get_page()
    new_page = await browser.context.new_page()

    await new_page.goto(
        validate_url(url),
        wait_until="domcontentloaded",
        timeout=45000
    )

    page = new_page

    return (
        f"Opened {await new_page.title()} "
        f"in a new tab.\nURL: {new_page.url}"
    )



@mcp.tool()
async def browser_search(query: str) -> str:
    """Search Google and return the results text."""

    browser = await get_page()

    url = "https://www.google.com/search?q=" + quote(query)

    await browser.goto(
        url,
        wait_until="domcontentloaded",
        timeout=45000
    )

    return (await browser.locator("body").inner_text())[:12000]



@mcp.tool()
async def browser_youtube_play(query: str) -> str:
    """Search YouTube, open the first matching video and play it."""

    browser = await get_page()

    search_url = (
        "https://www.youtube.com/results?search_query="
        + quote(query, safe="")
    )

    logging.warning("WEDNESDAY YOUTUBE PLAY CALLED")
    logging.warning("YOUTUBE QUERY: %s", query)

    try:
        # STEP 1: Open YouTube search results

        await browser.goto(
            search_url,
            wait_until="domcontentloaded",
            timeout=45000
        )

        await browser.wait_for_timeout(5000)

        logging.warning(
            "YOUTUBE SEARCH URL: %s",
            browser.url
        )

        logging.warning(
            "YOUTUBE SEARCH PAGE TITLE: %s",
            await browser.title()
        )

        # STEP 2: Check for verification

        if await check_verification_wall(browser):
            return (
                "YouTube verification required. "
                "Please complete it manually in the browser."
            )

        # STEP 3: Find visible YouTube video links

        video_links = browser.locator('a[href*="/watch?v="]')

        await browser.wait_for_timeout(2000)

        video_data = await video_links.evaluate_all(
            """links => links
                .filter(link => {
                    const rect = link.getBoundingClientRect();
                    return rect.width > 0 &&
                        rect.height > 0 &&
                        link.href.includes('/watch?v=');
                })
                .map(link => ({
                    title: link.getAttribute('title') ||
                        link.getAttribute('aria-label') ||
                        link.innerText,
                    href: link.href
                }))
                .filter(item => item.title && item.href)
            """
        )

        if not video_data:
            return "YouTube loaded, but no visible video links were found."

        # Remove duplicate video URLs
        unique_videos = {}

        for item in video_data:
            unique_videos[item["href"]] = item

        videos = list(unique_videos.values())

        logging.warning("YOUTUBE LINKS FOUND: %s", len(videos))

        for item in videos[:5]:
            logging.warning(
                "VIDEO: %s | %s",
                item["title"],
                item["href"]
            )

        # STEP 4: Open the first video

        selected_video = videos[0]

        title = selected_video["title"]
        video_url = selected_video["href"]

        await browser.goto(
            video_url,
            wait_until="domcontentloaded",
            timeout=45000
        )


        # STEP 5: Open the selected video

        await browser.goto(
            video_url,
            wait_until="domcontentloaded",
            timeout=45000
        )

        await browser.wait_for_timeout(5000)

        logging.warning(
            "YOUTUBE WATCH PAGE TITLE: %s",
            await browser.title()
        )

        logging.warning(
            "YOUTUBE WATCH PAGE URL: %s",
            browser.url
        )

        if await check_verification_wall(browser):
            return (
                "YouTube verification required. "
                "Please complete it manually."
            )

        # STEP 6: Wait for the video player

        video = browser.locator("video").first

        await video.wait_for(
            state="attached",
            timeout=20000
        )

        # STEP 7: Check whether playback has started

        playing = await video.evaluate(
            "(v) => !v.paused && !v.ended && v.currentTime > 0"
        )

        if not playing:
            play_button = browser.locator(
                "button.ytp-play-button"
            )

            if await play_button.count() > 0:
                await play_button.first.click(timeout=10000)

        # STEP 8: Verify playback

        try:
            await browser.wait_for_function(
                """() => {
                    const video = document.querySelector("video");

                    return video &&
                        !video.paused &&
                        !video.ended &&
                        video.currentTime > 0;
                }""",
                timeout=10000
            )

            return f"Now playing: {title}"

        except Exception:
            return (
                f"Opened {title}, but playback could not be verified. "
                "Check whether YouTube requires a manual play click."
            )

    except Exception as error:
        logging.exception("YOUTUBE PLAY ERROR")

        return f"YouTube playback failed: {str(error)[:300]}"


@mcp.tool()
async def browser_read_page() -> str:
    """Read the text of the currently open webpage."""

    browser = await get_page()

    title = await browser.title()
    content = await browser.locator("body").inner_text()

    return (
        f"Title: {title}\n"
        f"URL: {browser.url}\n\n"
        f"{content[:15000]}"
    )



@mcp.tool()
async def browser_click(text: str) -> str:
    """Click a webpage element by visible text."""

    browser = await get_page()

    forbidden = {
        "buy", "buy now", "pay", "send", "submit",
        "delete", "remove", "purchase", "confirm order"
    }

    if text.strip().lower() in forbidden:
        return "This action requires a separate explicit confirmation."

    await browser.get_by_text(
        text,
        exact=False
    ).first.click(timeout=10000)

    return f"Clicked: {text}\nCurrent URL: {browser.url}"



@mcp.tool()
async def browser_fill(selector: str, value: str) -> str:
    """Fill a webpage input without submitting the form."""

    browser = await get_page()

    await browser.locator(selector).first.fill(value)

    return f"Filled {selector}. Form not submitted."




@mcp.tool()
async def browser_scroll(
    direction: str = "down",
    pixels: int = 600
) -> str:
    """Scroll the current webpage up or down."""

    browser = await get_page()

    if direction not in ("up", "down"):
        return "Direction must be up or down."

    pixels = max(100, min(pixels, 2000))

    distance = pixels if direction == "down" else -pixels

    await browser.evaluate(
        "(distance) => window.scrollBy(0, distance)",
        distance
    )

    return f"Scrolled {direction} by {pixels} pixels."



@mcp.tool()
async def browser_download(text: str) -> str:
    """Click a download link and save the file."""

    browser = await get_page()

    async with browser.expect_download(timeout=30000) as download_event:
        await browser.get_by_text(
            text,
            exact=False
        ).first.click()

    download = await download_event.value

    filename = Path(download.suggested_filename).name
    destination = DOWNLOADS / filename

    if destination.exists():
        destination = DOWNLOADS / (
            f"{destination.stem}_new{destination.suffix}"
        )

    await download.save_as(str(destination))

    return f"Downloaded: {destination}"



@mcp.tool()
async def browser_close(confirm: bool = True) -> str:
    """Close Wednesday's browser and release its resources."""

    global playwright, context, page

    if context:
        await context.close()

    if playwright:
        await playwright.stop()

    context = None
    playwright = None
    page = None

    return "Browser closed."




if __name__ == "__main__":
    mcp.run(transport="stdio")
