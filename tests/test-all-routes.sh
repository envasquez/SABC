#!/bin/bash
# test-all-routes.sh - Test every single route for internal server errors

BASE_URL="http://localhost:8000"
FAILED_ROUTES=()
TOTAL_ROUTES=0

test_route() {
    local method="$1"
    local url="$2"
    local description="$3"

    TOTAL_ROUTES=$((TOTAL_ROUTES + 1))

    if [ "$method" = "GET" ]; then
        status=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL$url")
    else
        # For POST routes, we expect 302/405 (redirect/method not allowed), not 500
        status=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL$url")
    fi

    if [ "$status" = "500" ]; then
        echo "❌ FAIL: $method $url ($description) - Status: $status"
        FAILED_ROUTES+=("$method $url")
    elif [ "$status" = "200" ] || [ "$status" = "302" ] || [ "$status" = "404" ] || [ "$status" = "405" ] || [ "$status" = "403" ]; then
        echo "✅ PASS: $method $url ($description) - Status: $status"
    else
        echo "⚠️  WARN: $method $url ($description) - Status: $status"
    fi
}

echo "🧪 Testing ALL Routes for Internal Server Errors"
echo "==============================================="
echo ""

# Public routes
echo "📋 Public Routes:"
test_route "GET" "/" "Home page"
test_route "GET" "/health" "Health check"
test_route "GET" "/login" "Login page"
test_route "GET" "/register" "Register page"
test_route "GET" "/about" "About page"
test_route "GET" "/bylaws" "Bylaws page"
test_route "GET" "/calendar" "Calendar page"
test_route "GET" "/tournaments" "Tournaments list"
test_route "GET" "/standings" "Standings page"
test_route "GET" "/awards" "Awards page"

echo ""
echo "📋 Member Routes (may require auth):"
test_route "GET" "/polls" "Polls page"
test_route "GET" "/roster" "Member roster"
test_route "GET" "/profile" "User profile"

echo ""
echo "📋 Auth Routes:"
test_route "POST" "/login" "Login endpoint"
test_route "POST" "/register" "Register endpoint"
test_route "POST" "/logout" "Logout endpoint"

echo ""
echo "📋 Admin Routes (may require admin auth):"
test_route "GET" "/admin" "Admin dashboard"
test_route "GET" "/admin/events" "Admin events"
test_route "GET" "/admin/users" "Admin users"
test_route "GET" "/admin/tournaments" "Admin tournaments"
test_route "GET" "/admin/lakes" "Admin lakes"
test_route "GET" "/admin/polls" "Admin polls"
test_route "GET" "/admin/news" "Admin news"

echo ""
echo "📋 API Routes:"
test_route "GET" "/api/ramps" "API ramps"
test_route "GET" "/api/lakes" "API lakes"

echo ""
echo "==============================================="
echo "📊 Summary:"
echo "Total routes tested: $TOTAL_ROUTES"
echo "Failed routes: ${#FAILED_ROUTES[@]}"

if [ ${#FAILED_ROUTES[@]} -eq 0 ]; then
    echo "🎉 ALL ROUTES PASSED! No internal server errors found."
else
    echo "❌ Routes with internal server errors:"
    for route in "${FAILED_ROUTES[@]}"; do
        echo "  - $route"
    done
    echo ""
    echo "⚠️  YOU MUST FIX THESE BEFORE DEPLOYMENT!"
fi