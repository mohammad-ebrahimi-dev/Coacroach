"""Optional Playwright automation for already-authorized, non-sensitive HTML.

This helper performs no navigation: all browser networking and JavaScript are
disabled. It never bypasses a CAPTCHA, login, access controls, or TLS checks.
"""


def inspect_offline_html(html, selector, *, playwright_factory=None):
    if playwright_factory is None:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise RuntimeError('Install optional requirements-browser.txt and the Playwright browser') from None
        playwright_factory = sync_playwright
    with playwright_factory() as playwright:
        browser = playwright.chromium.launch()
        try:
            context = browser.new_context(java_script_enabled=False, service_workers='block')
            try:
                context.route('**/*', lambda route: route.abort())
                page = context.new_page()
                page.set_default_timeout(10000)
                page.set_content(html, wait_until='domcontentloaded', timeout=10000)
                return page.locator(selector).count()
            finally:
                context.close()
        finally:
            browser.close()
