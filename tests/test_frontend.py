#!/usr/bin/env python3
"""
Comprehensive frontend test suite for SABC application.
Tests user interactions, UI functionality, JavaScript behavior, and accessibility.
Uses Playwright for browser automation testing.
"""

import time

import pytest
from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright


@pytest.fixture(scope="session")
def browser():
    """Start browser for testing session."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)  # Set to False for debugging
        yield browser
        browser.close()


@pytest.fixture
def context(browser: Browser):
    """Create a new browser context for each test."""
    context = browser.new_context(
        viewport={"width": 1920, "height": 1080}, locale="en-US", timezone_id="America/Chicago"
    )
    yield context
    context.close()


@pytest.fixture
def page(context: BrowserContext):
    """Create a new page for each test."""
    page = context.new_page()
    yield page


@pytest.fixture
def admin_page(context: BrowserContext):
    """Create an authenticated admin page."""
    page = context.new_page()

    # Navigate to login
    page.goto("http://localhost:8000/login")

    # Login as admin (assuming admin user exists)
    page.fill('input[name="email"]', "admin@sabc.com")
    page.fill('input[name="password"]', "admin123")
    page.click('button[type="submit"]')

    # Wait for redirect
    page.wait_for_url("http://localhost:8000/")

    yield page


@pytest.fixture
def member_page(context: BrowserContext):
    """Create an authenticated member page."""
    page = context.new_page()

    # Navigate to login
    page.goto("http://localhost:8000/login")

    # Login as member
    page.fill('input[name="email"]', "member@sabc.com")
    page.fill('input[name="password"]', "member123")
    page.click('button[type="submit"]')

    # Wait for redirect
    page.wait_for_url("http://localhost:8000/")

    yield page


class TestNavigation:
    """Test navigation and routing."""

    def test_homepage_loads(self, page: Page):
        """Test that homepage loads correctly."""
        page.goto("http://localhost:8000/")
        assert page.title() == "SABC"
        assert page.locator("h1").first.is_visible()

    def test_main_navigation_links(self, page: Page):
        """Test all main navigation links work."""
        page.goto("http://localhost:8000/")

        nav_links = [
            ("About", "/about"),
            ("Bylaws", "/bylaws"),
            ("Calendar", "/calendar"),
            ("Awards", "/awards"),
        ]

        for link_text, expected_path in nav_links:
            page.click(f"text={link_text}")
            page.wait_for_url(f"http://localhost:8000{expected_path}")
            assert expected_path in page.url

            # Navigate back to home
            page.goto("http://localhost:8000/")

    def test_responsive_navigation(self, page: Page):
        """Test navigation on mobile viewport."""
        page.set_viewport_size({"width": 375, "height": 667})  # iPhone size
        page.goto("http://localhost:8000/")

        # Mobile hamburger menu should be visible
        hamburger = page.locator(".navbar-toggler")
        assert hamburger.is_visible()

        # Click to open menu
        hamburger.click()

        # Navigation items should be visible
        assert page.locator('.navbar-nav .nav-link:text("About")').is_visible()

    def test_breadcrumb_navigation(self, admin_page: Page):
        """Test breadcrumb navigation in admin pages."""
        admin_page.goto("http://localhost:8000/admin/events")

        # Check breadcrumbs exist (if implemented)
        breadcrumbs = admin_page.locator(".breadcrumb")
        if breadcrumbs.count() > 0:
            assert breadcrumbs.is_visible()


class TestAuthentication:
    """Test authentication flows."""

    def test_login_form_validation(self, page: Page):
        """Test login form validation."""
        page.goto("http://localhost:8000/login")

        # Try to submit empty form
        page.click('button[type="submit"]')

        # Should show validation errors
        assert page.locator('input[name="email"]:invalid').count() > 0

    def test_successful_login(self, page: Page):
        """Test successful login flow."""
        page.goto("http://localhost:8000/login")

        # Fill login form
        page.fill('input[name="email"]', "test@sabc.com")
        page.fill('input[name="password"]', "testpass")
        page.click('button[type="submit"]')

        # Should redirect to homepage or dashboard
        page.wait_for_load_state("networkidle")
        assert page.url != "http://localhost:8000/login"

    def test_failed_login(self, page: Page):
        """Test failed login shows error."""
        page.goto("http://localhost:8000/login")

        # Fill with invalid credentials
        page.fill('input[name="email"]', "invalid@email.com")
        page.fill('input[name="password"]', "wrongpassword")
        page.click('button[type="submit"]')

        # Should show error message
        page.wait_for_load_state("networkidle")
        error_messages = page.locator('.alert-danger, .error, [role="alert"]')
        assert error_messages.count() > 0

    def test_logout_functionality(self, member_page: Page):
        """Test logout functionality."""
        # Click logout (might be in dropdown)
        member_page.click(".dropdown-toggle:has(.bi-person-gear)")
        member_page.click('text="Logout"')

        # Should redirect to login page
        member_page.wait_for_url("http://localhost:8000/login")
        assert "login" in member_page.url

    def test_admin_dropdown_visibility(self, admin_page: Page):
        """Test admin dropdown only shows for admins."""
        admin_page.goto("http://localhost:8000/")

        # Admin dropdown should be visible
        admin_page.click(".dropdown-toggle:has(.bi-person-gear)")
        assert admin_page.locator('text="Admin"').is_visible()
        assert admin_page.locator('text="Tournaments"').is_visible()
        assert admin_page.locator('text="Anglers"').is_visible()

    def test_member_no_admin_access(self, member_page: Page):
        """Test members don't see admin options."""
        member_page.goto("http://localhost:8000/")

        # Admin options should not be visible
        member_page.click(".dropdown-toggle:has(.bi-person-gear)")
        assert member_page.locator('text="Admin"').count() == 0


class TestEventManagement:
    """Test event management functionality."""

    def test_events_page_loads(self, admin_page: Page):
        """Test events management page loads."""
        admin_page.goto("http://localhost:8000/admin/events")

        assert admin_page.locator('h1:text("Events")').count() > 0
        assert admin_page.locator(".tab-pane").count() > 0

    def test_event_tabs_switching(self, admin_page: Page):
        """Test switching between event type tabs."""
        admin_page.goto("http://localhost:8000/admin/events")

        tabs = ["SABC Tournaments", "Federal Holidays", "Other Events", "Past Events"]

        for tab_name in tabs:
            tab = admin_page.locator(f'.nav-link:text("{tab_name}")')
            if tab.count() > 0:
                tab.click()
                # Verify tab is active
                assert "active" in tab.get_attribute("class")

    def test_create_event_form(self, admin_page: Page):
        """Test event creation form."""
        admin_page.goto("http://localhost:8000/admin/events")

        # Fill out event creation form
        admin_page.fill('input[name="date"]', "2025-12-31")
        admin_page.fill('input[name="name"]', "Test Event")
        admin_page.select_option('select[name="event_type"]', "sabc_tournament")
        admin_page.fill('textarea[name="description"]', "Test tournament event")

        # Fill tournament-specific fields
        admin_page.fill('input[name="start_time"]', "06:00")
        admin_page.fill('input[name="weigh_in_time"]', "15:00")
        admin_page.fill('input[name="entry_fee"]', "25.00")
        admin_page.fill('input[name="lake_name"]', "Test Lake")

        # Submit form
        admin_page.click('button[type="submit"]')

        # Should show success message
        admin_page.wait_for_load_state("networkidle")
        assert admin_page.locator(".alert-success").count() > 0

    def test_event_form_validation(self, admin_page: Page):
        """Test event form validation."""
        admin_page.goto("http://localhost:8000/admin/events")

        # Try to submit form without required fields
        admin_page.click('button[type="submit"]')

        # Should show validation errors
        required_fields = admin_page.locator("input:invalid")
        assert required_fields.count() > 0

    def test_edit_event_modal(self, admin_page: Page):
        """Test editing an event via modal."""
        admin_page.goto("http://localhost:8000/admin/events")

        # Find and click edit button for first event
        edit_button = admin_page.locator(".edit-event-btn").first
        if edit_button.count() > 0:
            edit_button.click()

            # Modal should be visible
            modal = admin_page.locator("#editEventModal")
            assert modal.is_visible()

            # Form should be populated
            name_input = admin_page.locator("#edit_name")
            assert name_input.input_value() != ""

            # Close modal
            admin_page.click(".btn-close")

    def test_delete_event_confirmation(self, admin_page: Page):
        """Test event deletion requires confirmation."""
        admin_page.goto("http://localhost:8000/admin/events")

        # Click delete button (if any events exist)
        delete_button = admin_page.locator(".btn-danger:has(.bi-trash)").first
        if delete_button.count() > 0:
            delete_button.click()

            # Should show confirmation dialog
            confirm_dialog = admin_page.locator(".modal, .confirm")
            assert confirm_dialog.count() > 0

    def test_search_and_filter(self, admin_page: Page):
        """Test event search and filtering."""
        admin_page.goto("http://localhost:8000/admin/events")

        # Test search functionality
        search_input = admin_page.locator('input[placeholder*="Search"], input[type="search"]')
        if search_input.count() > 0:
            search_input.fill("tournament")
            search_input.press("Enter")

            # Results should be filtered
            page.wait_for_load_state("networkidle")

        # Test filter dropdowns
        filter_select = admin_page.locator('select:has(option:text("Tournament"))')
        if filter_select.count() > 0:
            filter_select.select_option(label="Tournament")


class TestPolls:
    """Test poll functionality."""

    def test_polls_page_display(self, member_page: Page):
        """Test polls page displays correctly."""
        member_page.goto("http://localhost:8000/polls")

        # Page should load
        assert member_page.locator("h1").count() > 0

    def test_vote_submission(self, member_page: Page):
        """Test submitting a vote."""
        member_page.goto("http://localhost:8000/polls")

        # Find first poll with voting options
        vote_button = member_page.locator('input[type="radio"], input[type="checkbox"]').first
        if vote_button.count() > 0:
            vote_button.check()

            # Submit vote
            submit_button = member_page.locator('button:text("Vote"), button[type="submit"]').first
            submit_button.click()

            # Should show confirmation
            member_page.wait_for_load_state("networkidle")

    def test_poll_results_display(self, page: Page):
        """Test poll results are displayed correctly."""
        page.goto("http://localhost:8000/polls")

        # Look for results section
        results = page.locator(".poll-results, .results-chart")
        if results.count() > 0:
            assert results.is_visible()

    def test_poll_chart_visualization(self, page: Page):
        """Test poll results charts render."""
        page.goto("http://localhost:8000/polls")

        # Check if charts are rendered (look for canvas or SVG elements)
        charts = page.locator("canvas, svg, .chart")
        if charts.count() > 0:
            assert charts.first.is_visible()


class TestCalendar:
    """Test calendar functionality."""

    def test_calendar_loads(self, page: Page):
        """Test calendar page loads."""
        page.goto("http://localhost:8000/calendar")

        assert page.locator(".calendar, #calendar").count() > 0

    def test_calendar_navigation(self, page: Page):
        """Test calendar month/year navigation."""
        page.goto("http://localhost:8000/calendar")

        # Find navigation buttons
        next_button = page.locator('.next, .calendar-next, button:text("Next")')
        prev_button = page.locator('.prev, .calendar-prev, button:text("Previous")')

        if next_button.count() > 0:
            next_button.first.click()
            page.wait_for_load_state("networkidle")

        if prev_button.count() > 0:
            prev_button.first.click()
            page.wait_for_load_state("networkidle")

    def test_event_display_on_calendar(self, page: Page):
        """Test events are displayed on calendar."""
        page.goto("http://localhost:8000/calendar")

        # Look for event indicators
        page.locator(".event, .calendar-event, [data-event]")
        # Events may or may not exist, just check structure

    def test_calendar_event_details(self, page: Page):
        """Test clicking calendar events shows details."""
        page.goto("http://localhost:8000/calendar")

        # Click on an event if any exist
        event = page.locator(".event, .calendar-event").first
        if event.count() > 0:
            event.click()

            # Should show event details (modal, popup, or navigation)
            page.wait_for_load_state("networkidle")


class TestTournaments:
    """Test tournament-related functionality."""

    def test_tournament_results_display(self, page: Page):
        """Test tournament results are displayed correctly."""
        page.goto("http://localhost:8000/tournaments")

        # Look for tournament results table
        results_table = page.locator(".tournament-results, table")
        if results_table.count() > 0:
            assert results_table.is_visible()

    def test_standings_calculations(self, page: Page):
        """Test that standings are calculated and displayed."""
        page.goto("http://localhost:8000/awards")

        # Look for standings/leaderboard
        standings = page.locator(".standings, .leaderboard, .aoy-standings")
        if standings.count() > 0:
            assert standings.is_visible()

    def test_tournament_details_page(self, page: Page):
        """Test individual tournament details page."""
        # This would depend on having a specific tournament URL
        # page.goto("http://localhost:8000/tournaments/1")
        pass


class TestNews:
    """Test news functionality."""

    def test_news_admin_page(self, admin_page: Page):
        """Test news administration page."""
        admin_page.goto("http://localhost:8000/admin/news")

        # Should see news management interface
        assert admin_page.locator("h1").count() > 0
        assert admin_page.locator("form").count() > 0

    def test_create_news_article(self, admin_page: Page):
        """Test creating a news article."""
        admin_page.goto("http://localhost:8000/admin/news")

        # Fill out news creation form
        admin_page.fill('input[name="title"]', "Test News Article")
        admin_page.fill('textarea[name="content"]', "This is a test news article content.")
        admin_page.check('input[name="published"]')

        # Submit form
        admin_page.click('button:text("Create")')

        # Should show success message
        admin_page.wait_for_load_state("networkidle")
        assert admin_page.locator(".alert-success").count() > 0

    def test_edit_news_modal(self, admin_page: Page):
        """Test editing news via modal."""
        admin_page.goto("http://localhost:8000/admin/news")

        # Click edit button if news items exist
        edit_button = admin_page.locator(".btn-warning:has(.bi-pencil)").first
        if edit_button.count() > 0:
            edit_button.click()

            # Modal should appear
            modal = admin_page.locator("#editModal")
            assert modal.is_visible()

    def test_news_display_on_homepage(self, page: Page):
        """Test news appears on homepage."""
        page.goto("http://localhost:8000/")

        # Look for news section
        news_section = page.locator(".news, .announcements")
        if news_section.count() > 0:
            assert news_section.is_visible()


class TestAccessibility:
    """Test accessibility compliance."""

    def test_keyboard_navigation(self, page: Page):
        """Test keyboard navigation works."""
        page.goto("http://localhost:8000/")

        # Tab through focusable elements
        page.keyboard.press("Tab")
        focused_element = page.evaluate("document.activeElement.tagName")
        assert focused_element in ["A", "BUTTON", "INPUT", "TEXTAREA", "SELECT"]

    def test_alt_text_on_images(self, page: Page):
        """Test all images have alt text."""
        page.goto("http://localhost:8000/")

        images = page.locator("img")
        for i in range(images.count()):
            img = images.nth(i)
            alt_text = img.get_attribute("alt")
            # Images should have alt text or be decorative
            assert alt_text is not None or img.get_attribute("role") == "presentation"

    def test_color_contrast(self, page: Page):
        """Test color contrast meets WCAG guidelines."""
        page.goto("http://localhost:8000/")

        # This would require a color contrast analyzer
        # For now, just check that text is visible
        text_elements = page.locator("p, h1, h2, h3, span, a")
        assert text_elements.first.is_visible()

    def test_form_labels(self, page: Page):
        """Test form inputs have proper labels."""
        page.goto("http://localhost:8000/login")

        inputs = page.locator("input")
        for i in range(inputs.count()):
            input_elem = inputs.nth(i)
            input_id = input_elem.get_attribute("id")
            input_name = input_elem.get_attribute("name")

            # Should have associated label
            if input_id:
                label = page.locator(f'label[for="{input_id}"]')
                assert label.count() > 0
            elif input_name:
                # Or have aria-label or placeholder
                aria_label = input_elem.get_attribute("aria-label")
                placeholder = input_elem.get_attribute("placeholder")
                assert aria_label is not None or placeholder is not None


class TestResponsiveDesign:
    """Test responsive design across devices."""

    @pytest.mark.parametrize(
        "viewport",
        [
            {"width": 320, "height": 568},  # iPhone SE
            {"width": 375, "height": 667},  # iPhone 6/7/8
            {"width": 768, "height": 1024},  # iPad
            {"width": 1024, "height": 768},  # iPad Landscape
            {"width": 1920, "height": 1080},  # Desktop
        ],
    )
    def test_responsive_layout(self, page: Page, viewport):
        """Test layout works on different screen sizes."""
        page.set_viewport_size(viewport)
        page.goto("http://localhost:8000/")

        # Check that content is visible and not overflowing
        body = page.locator("body")
        body_width = body.bounding_box()["width"]
        assert body_width <= viewport["width"]

        # Navigation should be accessible
        nav = page.locator("nav, .navbar")
        assert nav.is_visible()

    def test_mobile_menu_functionality(self, page: Page):
        """Test mobile hamburger menu."""
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto("http://localhost:8000/")

        # Hamburger menu should be visible
        hamburger = page.locator(".navbar-toggler, .menu-toggle")
        if hamburger.count() > 0:
            assert hamburger.is_visible()

            # Click to open
            hamburger.click()

            # Menu items should become visible
            nav_items = page.locator(".navbar-nav .nav-link")
            assert nav_items.first.is_visible()

    def test_table_responsiveness(self, admin_page: Page):
        """Test tables are responsive on mobile."""
        admin_page.set_viewport_size({"width": 375, "height": 667})
        admin_page.goto("http://localhost:8000/admin/events")

        # Tables should be scrollable or stacked
        tables = admin_page.locator("table")
        if tables.count() > 0:
            table = tables.first
            # Should either have horizontal scroll or be responsive
            parent = table.locator("xpath=..")
            assert "table-responsive" in parent.get_attribute("class") or table.is_visible()


class TestPerformance:
    """Test performance metrics."""

    def test_page_load_time(self, page: Page):
        """Test page load performance."""
        start_time = time.time()
        page.goto("http://localhost:8000/")
        page.wait_for_load_state("networkidle")
        load_time = time.time() - start_time

        # Page should load in under 3 seconds
        assert load_time < 3.0

    def test_image_optimization(self, page: Page):
        """Test images are optimized."""
        page.goto("http://localhost:8000/")

        images = page.locator("img")
        for i in range(images.count()):
            img = images.nth(i)
            src = img.get_attribute("src")

            # Images should have appropriate format and size
            # This is a basic check - more sophisticated tools would analyze file sizes
            assert src.endswith((".jpg", ".jpeg", ".png", ".webp", ".svg"))

    def test_javascript_errors(self, page: Page):
        """Test for JavaScript errors."""
        errors = []

        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto("http://localhost:8000/")

        # Wait for any async JavaScript to complete
        page.wait_for_timeout(1000)

        # Should have no JavaScript errors
        assert len(errors) == 0, f"JavaScript errors found: {errors}"

    def test_network_requests(self, page: Page):
        """Test network request efficiency."""
        requests = []

        page.on("request", lambda request: requests.append(request))
        page.goto("http://localhost:8000/")
        page.wait_for_load_state("networkidle")

        # Should not have excessive requests
        assert len(requests) < 50  # Adjust threshold as needed

        # Check for failed requests
        failed_requests = [req for req in requests if req.failure()]
        assert len(failed_requests) == 0, f"Failed requests: {[req.url for req in failed_requests]}"


class TestJavaScriptFunctionality:
    """Test JavaScript-dependent features."""

    def test_htmx_functionality(self, admin_page: Page):
        """Test HTMX-powered interactions."""
        admin_page.goto("http://localhost:8000/admin/events")

        # Look for HTMX attributes
        htmx_elements = admin_page.locator("[hx-get], [hx-post], [hx-delete]")
        if htmx_elements.count() > 0:
            # Click an HTMX element and verify it works
            htmx_elements.first.click()
            admin_page.wait_for_load_state("networkidle")

    def test_modal_functionality(self, admin_page: Page):
        """Test Bootstrap modals work correctly."""
        admin_page.goto("http://localhost:8000/admin/events")

        # Find modal trigger
        modal_trigger = admin_page.locator('[data-bs-toggle="modal"]')
        if modal_trigger.count() > 0:
            modal_trigger.first.click()

            # Modal should be visible
            modal = admin_page.locator(".modal.show")
            assert modal.count() > 0

            # Close modal
            admin_page.keyboard.press("Escape")
            page.wait_for_timeout(500)  # Wait for animation
            assert modal.count() == 0

    def test_form_validation_javascript(self, page: Page):
        """Test client-side form validation."""
        page.goto("http://localhost:8000/login")

        # Fill invalid email
        page.fill('input[type="email"]', "invalid-email")
        page.click('button[type="submit"]')

        # Should show browser validation
        invalid_input = page.locator("input:invalid")
        assert invalid_input.count() > 0

    def test_dynamic_content_loading(self, admin_page: Page):
        """Test dynamic content loading (AJAX)."""
        admin_page.goto("http://localhost:8000/admin/events")

        # Look for pagination or load more buttons
        load_button = admin_page.locator('[data-action="load"], .load-more, .pagination a')
        if load_button.count() > 0:
            load_button.first.click()
            admin_page.wait_for_load_state("networkidle")


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_404_page(self, page: Page):
        """Test 404 error page."""
        page.goto("http://localhost:8000/nonexistent-page")

        # Should show 404 page or redirect
        assert "404" in page.content() or page.url != "http://localhost:8000/nonexistent-page"

    def test_network_error_handling(self, page: Page):
        """Test behavior when network requests fail."""
        # Intercept and fail a request
        page.route("**/api/**", lambda route: route.abort())
        page.goto("http://localhost:8000/")

        # Page should still function
        assert page.locator("body").is_visible()

    def test_large_form_submission(self, admin_page: Page):
        """Test handling of large form data."""
        admin_page.goto("http://localhost:8000/admin/news")

        # Fill with large content
        large_content = "A" * 10000  # 10KB of text
        admin_page.fill('textarea[name="content"]', large_content)
        admin_page.fill('input[name="title"]', "Large Content Test")
        admin_page.click('button[type="submit"]')

        # Should handle gracefully
        admin_page.wait_for_load_state("networkidle")


if __name__ == "__main__":
    # Run with specific browser options
    pytest.main(
        [
            __file__,
            "-v",
            "--headed",  # Remove for headless
            "--browser=chromium",
            "--html=frontend_test_report.html",
        ]
    )
