"""
Admin Authentication Middleware
Protects admin routes and requires admin session
"""

from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse


def require_admin(request: Request):
    """
    Dependency function to require admin authentication
    
    Usage:
        @router.get("/admin/some-route", dependencies=[Depends(require_admin)])
        
    Raises:
        HTTPException: 403 if user is not admin
    """
    # Check if user is authenticated
    if not request.session.get("authenticated"):
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please login first."
        )
    
    # Check if user has admin privileges
    if not request.session.get("is_admin"):
        raise HTTPException(
            status_code=403,
            detail="Admin access required. You do not have permission to access this page."
        )
    
    return True


async def admin_page_protection(request: Request, call_next):
    """
    Middleware to protect all /admin/* routes
    Redirects non-admin users to login page
    """
    path = request.url.path
    
    # Check if this is an admin page (but not API endpoint)
    if path.startswith("/admin") and not path.startswith("/api/v1/admin"):
        # Check if user is admin
        is_admin = request.session.get("is_admin", False)
        is_authenticated = request.session.get("authenticated", False)
        
        if not is_authenticated:
            # Not logged in, redirect to login
            return RedirectResponse(url="/login", status_code=303)
        
        if not is_admin:
            # Logged in but not admin, show error or redirect
            raise HTTPException(
                status_code=403,
                detail="Admin access required"
            )
    
    # Continue with request
    response = await call_next(request)
    return response

