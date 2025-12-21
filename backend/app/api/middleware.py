"""
FastAPI middleware for logging, error handling, and request processing.
"""

import time
import uuid
from typing import Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.exceptions import RAGentError
from app.core.logging import get_logger, log_request_context
import structlog

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for request/response logging.
    
    Logs:
    - Request method, path, and ID
    - Response status and timing
    - Errors with stack traces
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate or use existing request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        
        # Add to request state for access in handlers
        request.state.request_id = request_id
        
        # Log request
        start_time = time.time()
        
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path
        )
        
        logger.info(
            "Request started",
            query_params=str(request.query_params) if request.query_params else None
        )
        
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Log response
            logger.info(
                "Request completed",
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2)
            )
            
            # Add headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
            
            return response
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            
            logger.error(
                "Request failed",
                error=str(e),
                error_type=type(e).__name__,
                duration_ms=round(duration_ms, 2)
            )
            raise
        
        finally:
            structlog.contextvars.unbind_contextvars(
                "request_id", "method", "path"
            )


def setup_exception_handlers(app: FastAPI) -> None:
    """Register exception handlers with the FastAPI app."""
    
    @app.exception_handler(RAGentError)
    async def ragent_error_handler(
        request: Request,
        exc: RAGentError
    ) -> JSONResponse:
        """Handle custom RAGent errors."""
        request_id = getattr(request.state, "request_id", "unknown")
        
        logger.warning(
            "Application error",
            error_type=type(exc).__name__,
            message=exc.message,
            request_id=request_id
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                **exc.to_dict(),
                "request_id": request_id
            }
        )
    
    @app.exception_handler(Exception)
    async def generic_error_handler(
        request: Request,
        exc: Exception
    ) -> JSONResponse:
        """Handle unexpected errors."""
        request_id = getattr(request.state, "request_id", "unknown")
        
        logger.exception(
            "Unexpected error",
            error_type=type(exc).__name__,
            message=str(exc),
            request_id=request_id
        )
        
        return JSONResponse(
            status_code=500,
            content={
                "error": "InternalServerError",
                "message": "An unexpected error occurred",
                "request_id": request_id
            }
        )


def setup_middleware(app: FastAPI) -> None:
    """Setup all middleware for the application."""
    app.add_middleware(RequestLoggingMiddleware)