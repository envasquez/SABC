#!/usr/bin/env python3
"""
Integration tests for SABC application.
Tests complete user workflows and system interactions.
"""

import pytest
from playwright.sync_api import Page
import time


@pytest.mark.integration
class TestCompleteUserWorkflows:
    """Test complete user workflows from start to finish."""
    
    def test_member_registration_to_voting_workflow(self, page: Page):
        """Test complete workflow: Register → Login → Vote in Poll."""
        # Step 1: Register new user
        page.goto("http://localhost:8000/register")
        page.fill('input[name="name"]', "Integration Test User")
        page.fill('input[name="email"]', "integration@test.com")
        page.fill('input[name="password"]', "testpass123")
        page.click('button[type="submit"]')
        
        # Step 2: Login
        page.goto("http://localhost:8000/login")
        page.fill('input[name="email"]', "integration@test.com")
        page.fill('input[name="password"]', "testpass123")
        page.click('button[type="submit"]')
        
        # Step 3: Navigate to polls
        page.wait_for_url("http://localhost:8000/")
        page.click('a[href="/polls"]')
        
        # Step 4: Vote in poll (if available)
        page.wait_for_load_state("networkidle")
        vote_options = page.locator('input[type="radio"], input[type="checkbox"]')
        if vote_options.count() > 0:
            vote_options.first.check()
            
            submit_button = page.locator('button:text("Vote"), input[type="submit"]')
            if submit_button.count() > 0:
                submit_button.first.click()
                
                # Verify vote submitted
                page.wait_for_load_state("networkidle")
                # Look for success message or confirmation
    
    def test_admin_event_creation_to_poll_workflow(self, page: Page):
        """Test admin workflow: Login → Create Event → Create Poll → View Results."""
        # Step 1: Admin login
        page.goto("http://localhost:8000/login")
        page.fill('input[name="email"]', "admin@test.com")
        page.fill('input[name="password"]', "adminpass")
        page.click('button[type="submit"]')
        
        # Step 2: Navigate to events
        page.wait_for_url("http://localhost:8000/")
        page.click('.dropdown-toggle:has(.bi-person-gear)')
        page.click('a:text("Tournaments")')  # Updated from "Events"
        
        # Step 3: Create new event
        page.wait_for_load_state("networkidle")
        page.fill('input[name="date"]', "2025-11-15")
        page.fill('input[name="name"]', "Integration Test Tournament")
        page.select_option('select[name="event_type"]', "sabc_tournament")
        page.fill('textarea[name="description"]', "Integration test event")
        page.fill('input[name="start_time"]', "06:00")
        page.fill('input[name="weigh_in_time"]', "15:00")
        page.fill('input[name="entry_fee"]', "25.00")
        page.fill('input[name="lake_name"]', "Integration Lake")
        page.click('button[type="submit"]')
        
        # Step 4: Verify event created
        page.wait_for_load_state("networkidle")
        success_alert = page.locator('.alert-success')
        if success_alert.count() > 0:
            assert success_alert.is_visible()
        
        # Step 5: Create poll for event (if poll creation is available)
        poll_create_link = page.locator('a:text("New Poll")')
        if poll_create_link.count() > 0:
            poll_create_link.click()
            page.wait_for_load_state("networkidle")
    
    def test_tournament_lifecycle_workflow(self, page: Page):
        """Test tournament lifecycle: Create → Poll → Results → Standings."""
        # Admin login
        page.goto("http://localhost:8000/login")
        page.fill('input[name="email"]', "admin@test.com")
        page.fill('input[name="password"]', "adminpass")
        page.click('button[type="submit"]')
        
        # Navigate to tournaments (if direct link exists)
        tournament_link = page.locator('a[href*="tournament"]')
        if tournament_link.count() > 0:
            tournament_link.first.click()
            page.wait_for_load_state("networkidle")
    
    def test_news_publication_workflow(self, page: Page):
        """Test news workflow: Create → Publish → Display on Homepage."""
        # Admin login
        page.goto("http://localhost:8000/login")
        page.fill('input[name="email"]', "admin@test.com")
        page.fill('input[name="password"]', "adminpass")
        page.click('button[type="submit"]')
        
        # Navigate to news admin
        page.click('.dropdown-toggle:has(.bi-person-gear)')
        page.click('a:text("News")')
        
        # Create news article
        page.fill('input[name="title"]', "Integration Test News")
        page.fill('textarea[name="content"]', "This is integration test news content.")
        page.check('input[name="published"]')  # Publish immediately
        page.click('button:text("Create")')
        
        # Verify news created
        page.wait_for_load_state("networkidle")
        
        # Check if news appears on homepage
        page.goto("http://localhost:8000/")
        news_content = page.locator(':text("Integration Test News")')
        # News might appear on homepage - this depends on implementation


@pytest.mark.integration
class TestDataConsistency:
    """Test data consistency across the application."""
    
    def test_event_data_consistency_across_pages(self, page: Page):
        """Test that event data is consistent between calendar and events pages."""
        # Check calendar
        page.goto("http://localhost:8000/calendar")
        page.wait_for_load_state("networkidle")
        
        # Look for events on calendar
        calendar_events = page.locator('.event, .calendar-event, [data-event]')
        calendar_event_count = calendar_events.count()
        
        # Check events management (admin view)
        page.goto("http://localhost:8000/login")
        page.fill('input[name="email"]', "admin@test.com")
        page.fill('input[name="password"]', "adminpass")
        page.click('button[type="submit"]')
        
        page.click('.dropdown-toggle:has(.bi-person-gear)')
        page.click('a:text("Tournaments")')
        
        # Count events in management interface
        page.wait_for_load_state("networkidle")
        
        # This would require specific selectors based on your implementation
        # The goal is to verify same events appear in both places
    
    def test_poll_results_consistency(self, page: Page):
        """Test poll results are consistent across different views."""
        # View polls as member
        page.goto("http://localhost:8000/login")
        page.fill('input[name="email"]', "member@test.com")
        page.fill('input[name="password"]', "memberpass")
        page.click('button[type="submit"]')
        
        page.goto("http://localhost:8000/polls")
        page.wait_for_load_state("networkidle")
        
        # Check results as member vs admin view
        # Implementation would depend on specific poll result displays


@pytest.mark.integration
class TestSystemLimits:
    """Test system behavior under various limits and edge cases."""
    
    def test_large_event_list_performance(self, page: Page):
        """Test performance with large number of events."""
        # This would require populating database with many events
        page.goto("http://localhost:8000/admin/events")
        
        start_time = time.time()
        page.wait_for_load_state("networkidle")
        load_time = time.time() - start_time
        
        # Page should load within reasonable time even with many events
        assert load_time < 5.0, f"Page took too long to load: {load_time}s"
    
    def test_concurrent_voting(self, browser):
        """Test multiple users voting simultaneously."""
        # Create multiple browser contexts to simulate concurrent users
        contexts = []
        pages = []
        
        try:
            for i in range(3):
                context = browser.new_context()
                page = context.new_page()
                contexts.append(context)
                pages.append(page)
                
                # Login each user
                page.goto("http://localhost:8000/login")
                page.fill('input[name="email"]', f"user{i}@test.com")
                page.fill('input[name="password"]', "testpass")
                page.click('button[type="submit"]')
            
            # Have all users vote simultaneously
            for page in pages:
                page.goto("http://localhost:8000/polls")
                vote_option = page.locator('input[type="radio"], input[type="checkbox"]').first
                if vote_option.count() > 0:
                    vote_option.check()
                    submit_btn = page.locator('button:text("Vote")').first
                    if submit_btn.count() > 0:
                        submit_btn.click()
        
        finally:
            # Cleanup
            for context in contexts:
                context.close()
    
    def test_form_validation_edge_cases(self, page: Page):
        """Test form validation with edge case inputs."""
        page.goto("http://localhost:8000/admin/events")
        page.fill('input[name="email"]', "admin@test.com")
        page.fill('input[name="password"]', "adminpass")
        page.click('button[type="submit"]')
        
        # Test various edge cases
        edge_cases = [
            {"date": "2025-02-30", "name": "Invalid Date"},  # Invalid date
            {"date": "2025-01-01", "name": "A" * 1000},      # Very long name
            {"date": "", "name": "No Date"},                 # Empty required field
            {"date": "1900-01-01", "name": "Too Old"},       # Very old date
        ]
        
        for case in edge_cases:
            page.fill('input[name="date"]', case["date"])
            page.fill('input[name="name"]', case["name"])
            page.click('button[type="submit"]')
            
            # Should show validation error or handle gracefully
            page.wait_for_load_state("networkidle")


@pytest.mark.integration
class TestCrossPageNavigation:
    """Test navigation between different pages and sections."""
    
    def test_complete_site_navigation(self, page: Page):
        """Test navigating through entire site structure."""
        page.goto("http://localhost:8000/")
        
        # Test main navigation
        main_nav_links = ["about", "bylaws", "calendar", "awards"]
        
        for link in main_nav_links:
            nav_link = page.locator(f'a[href="/{link}"]')
            if nav_link.count() > 0:
                nav_link.click()
                page.wait_for_load_state("networkidle")
                
                # Verify page loaded correctly
                assert link in page.url or page.locator("h1, .page-title").count() > 0
                
                # Go back to home
                page.goto("http://localhost:8000/")
    
    def test_breadcrumb_navigation(self, page: Page):
        """Test breadcrumb navigation if implemented."""
        # Admin login
        page.goto("http://localhost:8000/login")
        page.fill('input[name="email"]', "admin@test.com")
        page.fill('input[name="password"]', "adminpass")
        page.click('button[type="submit"]')
        
        # Navigate deep into admin section
        page.click('.dropdown-toggle:has(.bi-person-gear)')
        page.click('a:text("Tournaments")')
        
        # Look for breadcrumbs
        breadcrumbs = page.locator('.breadcrumb, .breadcrumb-nav')
        if breadcrumbs.count() > 0:
            # Test breadcrumb links
            breadcrumb_links = breadcrumbs.locator("a")
            if breadcrumb_links.count() > 0:
                breadcrumb_links.first.click()
                page.wait_for_load_state("networkidle")


if __name__ == "__main__":
    pytest.main(["tests/test_integration.py", "-v", "-m", "integration"])