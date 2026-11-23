
import asyncio
from pathlib import Path
from urllib.parse import quote, urlparse

from mcp.server.fastmcp import FastMCP
from playwright.async_api import async_playwright

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
    """Search Google using the browser and return the results text."""
    browser = await get_page()

    url = "https://www.google.com/search?q=" + quote(query)
    await browser.goto(url, wait_until="domcontentloaded")

    return (await browser.locator("body").inner_text())[:12000]

@mcp.tool()
async def browser_youtube_search(query: str) -> str:
    """Search YouTube for videos matching the user's query."""
    browser = await get_page()

    url = "https://www.youtube.com/results?search_query=" + quote(query)

    await browser.goto(
        url,
        wait_until="domcontentloaded",
        timeout=45000
    )

    await browser.wait_for_timeout(2500)

    if await check_verification_wall(browser):
        return "YouTube verification required. Please complete it manually."

    results = browser.locator("ytd-video-renderer")
    count = await results.count()

    if count == 0:
        return "No YouTube search results were found."

    return f"YouTube results loaded for {query}. Found {count} videos."

@mcp.tool()
async def browser_youtube_play(query: str) -> str:
    """Find and play the first matching YouTube video."""
    browser = await get_page()

    url = "https://www.youtube.com/results?search_query=" + quote(query)

    await browser.goto(
        url,
        wait_until="domcontentloaded",
        timeout=45000
    )

    await browser.wait_for_timeout(3000)

    if await check_verification_wall(browser):
        return "YouTube verification required. Please handle it manually."

    video_links = browser.locator(
        "ytd-video-renderer a#thumbnail"
    )

    await video_links.first.wait_for(timeout=15000)

    href = await video_links.first.get_attribute("href")

    if not href or "/watch" not in href:
        return "Could not identify a valid YouTube video."

    video_url = (
        href if href.startswith("http")
        else "https://www.youtube.com" + href
    )

    await browser.goto(
        video_url,
        wait_until="domcontentloaded",
        timeout=45000
    )

    await browser.wait_for_timeout(3000)

    if await check_verification_wall(browser):
        return "YouTube verification required. Please handle it manually."

    video = browser.locator("video").first
    await video.wait_for(timeout=15000)

    if await video.evaluate("(v) => v.paused"):
        play_button = browser.locator("button.ytp-play-button")

        if await play_button.count():
            await play_button.click()

    await browser.wait_for_timeout(3000)

    playing = await video.evaluate(
        "(v) => !v.paused && v.currentTime > 0"
    )

    if playing:
        return f"Video is playing: {await browser.title()}"

    return "Video opened, but playback could not be verified."


@mcp.tool()
async def browser_read_page() -> str:
    """Read the text of the currently open webpage."""
    browser = await get_page()

    title = await browser.title()
    content = await browser.locator("body").inner_text()

    return f"Title: {title}\nURL: {browser.url}\n\n{content[:15000]}"


@mcp.tool()
async def browser_click(text: str) -> str:
    """Click a webpage element by visible text. Refuses common destructive or final-submit actions."""
    browser = await get_page()

    forbidden = {
        "buy", "buy now", "pay", "send", "submit",
        "delete", "remove", "purchase", "confirm order"
    }

    if text.strip().lower() in forbidden:
        return "This action requires a separate explicit confirmation."

    await browser.get_by_text(text, exact=False).first.click(timeout=10000)

    return f"Clicked: {text}\nCurrent URL: {browser.url}"


@mcp.tool()
async def browser_fill(selector: str, value: str) -> str:
    """Fill a webpage input using a CSS selector. Does not submit the form."""
    browser = await get_page()

    await browser.locator(selector).first.fill(value)

    return f"Filled {selector}. Form not submitted."


@mcp.tool()
async def browser_scroll(direction: str = "down", pixels: int = 600) -> str:
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
    """Click a download link and save the file in workspace/downloads."""
    browser = await get_page()

    async with browser.expect_download(timeout=30000) as download_event:
        await browser.get_by_text(text, exact=False).first.click()

    download = await download_event.value

    filename = Path(download.suggested_filename).name
    destination = DOWNLOADS / filename

    if destination.exists():
        destination = DOWNLOADS / f"{destination.stem}_new{destination.suffix}"

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
