# Mobile Testing Checklist

Use this checklist before each release to ensure browser compatibility across devices.

## Quick Test (15 minutes)
Test on at least 2 devices (1 iPhone, 1 Android) before each release.

### iPhone (Safari)
**Device**: _______________ **iOS Version**: _______________

- [ ] **Login Page**
  - [ ] Form inputs don't zoom page when focused
  - [ ] Email/password fields work correctly
  - [ ] Login button tappable (not too small)
  - [ ] Remember me checkbox works
  - [ ] "Forgot password" link works

- [ ] **Navigation**
  - [ ] Hamburger menu opens/closes smoothly
  - [ ] All menu items tappable without overlap
  - [ ] Dropdown menus work (profile, admin)
  - [ ] No "flash" on tap (tap highlight removed)

- [ ] **Poll Voting**
  - [ ] Lake dropdown populates correctly
  - [ ] Ramp dropdown filters based on lake
  - [ ] Time selection works
  - [ ] Vote button submits successfully
  - [ ] Success toast appears
  - [ ] Page reloads with updated vote

- [ ] **Tournament Results**
  - [ ] Results table scrolls horizontally if needed
  - [ ] Text is readable without zooming
  - [ ] Images load correctly (if any)

- [ ] **Landscape Mode**
  - [ ] Rotate to landscape - layout still works
  - [ ] No content cut off by notch/bottom bar

### Android (Chrome)
**Device**: _______________ **Android Version**: _______________

- [ ] **Login Page**
  - [ ] Form inputs don't zoom page when focused
  - [ ] Email/password fields work correctly
  - [ ] Login button tappable (not too small)
  - [ ] Remember me checkbox works

- [ ] **Navigation**
  - [ ] Hamburger menu opens/closes smoothly
  - [ ] All menu items tappable without overlap
  - [ ] Dropdown menus work (profile, admin)
  - [ ] Select dropdowns show custom arrow icon

- [ ] **Poll Voting**
  - [ ] Lake dropdown populates correctly
  - [ ] Ramp dropdown filters based on lake
  - [ ] Time selection works
  - [ ] Vote button submits successfully
  - [ ] Success toast appears

- [ ] **Tournament Results**
  - [ ] Results table displays correctly
  - [ ] Smooth scrolling (momentum scrolling)
  - [ ] Text is readable

- [ ] **Back Button**
  - [ ] Android back button works correctly
  - [ ] Doesn't break navigation flow

### Desktop (Quick Check)
**Browser**: _______________ **Version**: _______________

- [ ] All mobile tests pass
- [ ] Responsive design works (resize window)
- [ ] Admin features work (if admin user)

## Full Test (1 hour)
Complete testing across more devices and scenarios.

### Additional iPhone Tests
- [ ] Safari Private Mode works
- [ ] iOS 15, 16, and 17 tested
- [ ] Different iPhone models (SE, 14, 15 Pro)

### Additional Android Tests
- [ ] Chrome, Firefox, Samsung Internet tested
- [ ] Android 11, 12, 13 tested
- [ ] Different manufacturers (Samsung, Google Pixel, OnePlus)

### Edge Cases
- [ ] **Slow Connection** (throttle to 3G in DevTools)
  - [ ] Page loads within 5 seconds
  - [ ] Poll voting shows loading state
  - [ ] Timeout doesn't break functionality
  - [ ] Retry logic works (check console logs)

- [ ] **Offline Mode**
  - [ ] Graceful error message appears
  - [ ] No console errors
  - [ ] App doesn't crash

- [ ] **Orientation Changes**
  - [ ] Portrait → Landscape → Portrait
  - [ ] Layout adapts correctly
  - [ ] No content clipping

- [ ] **Long Sessions**
  - [ ] Login session persists correctly
  - [ ] CSRF token remains valid
  - [ ] No memory leaks (use DevTools Memory tab)

### Accessibility
- [ ] **VoiceOver (iOS) / TalkBack (Android)**
  - [ ] All interactive elements have labels
  - [ ] Form fields announce correctly
  - [ ] Navigation is logical

- [ ] **Keyboard Navigation (iPad/Desktop)**
  - [ ] Tab key moves through elements
  - [ ] Enter/Space activates buttons
  - [ ] No keyboard traps

- [ ] **Color Contrast**
  - [ ] Text readable in dark mode
  - [ ] Links distinguishable from text
  - [ ] Form validation errors visible

### Performance
- [ ] **Page Load Times** (use DevTools Network tab)
  - [ ] Home page: < 2 seconds on 4G
  - [ ] Poll page: < 2 seconds on 4G
  - [ ] Tournament results: < 3 seconds on 4G

- [ ] **Interaction Response**
  - [ ] Button tap: < 100ms visual feedback
  - [ ] Form submit: < 500ms server response
  - [ ] Navigation: < 200ms transition

- [ ] **Bundle Size** (use DevTools Coverage tab)
  - [ ] Total CSS: < 100KB gzipped
  - [ ] Total JS: < 50KB gzipped
  - [ ] Images optimized (WebP or compressed JPEG)

## Browser DevTools Testing

### Safari DevTools (Mac)
```bash
# Connect iPhone to Mac via USB
# Safari > Develop > [Your iPhone] > [Page]
```
- [ ] No console errors on page load
- [ ] No console errors during interactions
- [ ] Network requests complete successfully
- [ ] Local storage works correctly

### Chrome DevTools (Desktop)
```bash
# Open DevTools: F12 or Cmd+Option+I
# Toggle device toolbar: Cmd+Shift+M (Mac) or Ctrl+Shift+M (Windows)
```
- [ ] Test iPhone 14 Pro viewport (430x932)
- [ ] Test Pixel 7 viewport (412x915)
- [ ] Test iPad Pro viewport (1024x1366)
- [ ] Lighthouse score > 90 for Performance, Accessibility, Best Practices

### Network Throttling Test
```bash
# Chrome DevTools > Network tab > Throttling dropdown
# Select "Slow 3G" or "Fast 3G"
```
- [ ] Page usable on Slow 3G (< 5s load)
- [ ] Images load progressively
- [ ] Critical content loads first
- [ ] Retry logic works on timeout

## Automated Testing (Optional)

### Playwright Tests
```bash
# Run cross-browser tests
npx playwright test --project=webkit   # Safari
npx playwright test --project=chromium # Chrome/Edge
npx playwright test --project=firefox  # Firefox

# Run with headed mode to see browser
npx playwright test --headed

# Run specific test
npx playwright test tests/e2e/polls.spec.ts
```

### BrowserStack Tests
```bash
# Test on real devices (requires BrowserStack account)
# See: https://www.browserstack.com/docs/automate/playwright
```

## Issues Found

| Date | Device/Browser | Issue | Severity | Fixed? |
|------|----------------|-------|----------|--------|
| 2025-01-20 | iPhone 14 Pro, iOS 17 | Example: Vote button too small | Low | ✅ Yes |
|      |                |       |          |        |
|      |                |       |          |        |

**Severity Levels:**
- **Critical**: Blocks core functionality (login, voting, viewing results)
- **High**: Major usability issue affecting many users
- **Medium**: Noticeable issue affecting some users
- **Low**: Minor cosmetic or edge case issue

## Testing Schedule

- **Every PR**: Quick test on 2 devices (iPhone + Android)
- **Weekly**: Full test on 6 devices (3 iOS + 3 Android)
- **Before Release**: Full test + edge cases + accessibility
- **Monthly**: Performance testing + bundle size audit

## Sign-off

**Tester**: _______________ **Date**: _______________ **Release**: _______________

- [ ] All critical tests passed
- [ ] All high-severity issues resolved
- [ ] Medium/low issues documented in backlog
- [ ] Ready for production deployment

---

**Tips for Manual Testing:**
1. Use real devices, not just emulators (browser engines differ)
2. Test with poor connections (fishing locations often have weak signal)
3. Test different times of day (server load varies)
4. Test as both member and admin users
5. Clear browser cache between tests
6. Check console for warnings/errors (even if UI works)
