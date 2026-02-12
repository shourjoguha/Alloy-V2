"""CDN configuration and middleware for static assets."""
from pathlib import Path
from typing import Any

from fastapi import Request, Response
from pydantic import BaseModel, Field, HttpUrl

from app.config.settings import get_settings

settings = get_settings()


class CDNConfig(BaseModel):
    """CDN configuration."""

    enabled: bool = Field(default=False)
    base_url: HttpUrl | None = Field(default=None, description="CDN base URL")
    static_prefix: str = Field(default="/static/", description="URL prefix for static assets")
    cache_control: str = Field(default="public, max-age=31536000, immutable", description="Cache-Control header value")
    version: str | None = Field(default=None, description="Cache busting version")
    assets: list[str] = Field(default_factory=lambda: ["css", "js", "images", "fonts", "icons"], description="Asset types to serve via CDN")


class CDNMiddleware:
    """Middleware to rewrite static asset URLs to CDN."""

    def __init__(self, app, config: CDNConfig):
        self.app = app
        self.config = config
        self.cdn_enabled = config.enabled and config.base_url is not None

    async def __call__(self, request: Request, call_next) -> Response:
        """Process request through CDN middleware."""
        response = await call_next(request)

        if not self.cdn_enabled:
            return response

        if self._should_serve_via_cdn(request.url.path):
            self._add_cdn_headers(response)
            return response

        return response

    def _should_serve_via_cdn(self, path: str) -> bool:
        """Check if path should be served via CDN."""
        if not path.startswith(self.config.static_prefix):
            return False

        asset_type = path.split("/")[-1].split(".")[-1].lower()
        return asset_type in self.config.assets

    def _add_cdn_headers(self, response: Response) -> None:
        """Add CDN-related headers to response."""
        response.headers["Cache-Control"] = self.config.cache_control

        if self.config.version:
            response.headers["X-Asset-Version"] = self.config.version


def get_cdn_url(asset_path: str) -> str:
    """Get CDN URL for a static asset.

    Args:
        asset_path: Relative path to asset (e.g., "css/style.css")

    Returns:
        Full URL to asset via CDN, or local path if CDN disabled
    """
    config = CDNConfig(
        enabled=settings.cdn_enabled,
        base_url=settings.cdn_base_url,
        static_prefix="/static/",
        cache_control="public, max-age=31536000, immutable",
        version=settings.cdn_version,
    )

    if not config.enabled or config.base_url is None:
        return f"/static/{asset_path}"

    version_part = f"{config.version}/" if config.version else ""
    return f"{config.base_url.rstrip('/')}/static/{version_part}{asset_path}"


def get_cdn_config() -> CDNConfig:
    """Get current CDN configuration."""
    return CDNConfig(
        enabled=settings.cdn_enabled,
        base_url=settings.cdn_base_url,
        static_prefix="/static/",
        cache_control="public, max-age=31536000, immutable",
        version=settings.cdn_version,
        assets=["css", "js", "images", "fonts", "icons"],
    )


def invalidate_cdn_cache(paths: list[str]) -> None:
    """Invalidate CDN cache for specific assets.

    Note: This is a placeholder. Actual implementation depends on CDN provider.

    Args:
        paths: List of asset paths to invalidate (e.g., ["css/style.css", "js/app.js"])
    """
    if not settings.cdn_enabled or not settings.cdn_base_url:
        print("CDN is disabled, cache invalidation skipped")
        return

    print(f"Invalidation requested for {len(paths)} assets: {paths}")

    # Provider-specific implementations:
    # - CloudFront: Create invalidation via AWS SDK
    # - Cloudflare: Purge via API
    # - Fastly: Purge via API
    # - Akamai: Purge via API


def get_cdn_health_status() -> dict[str, Any]:
    """Get CDN health status.

    Returns:
        Dictionary with CDN status information
    """
    config = get_cdn_config()

    if not config.enabled:
        return {
            "status": "disabled",
            "message": "CDN is not enabled",
        }

    return {
        "status": "enabled",
        "base_url": str(config.base_url) if config.base_url else None,
        "version": config.version,
        "cache_control": config.cache_control,
        "assets": config.assets,
    }


class CDNAssetManager:
    """Helper class for managing CDN asset URLs."""

    def __init__(self, config: CDNConfig):
        self.config = config

    def get_url(self, asset_type: str, filename: str) -> str:
        """Get CDN URL for an asset.

        Args:
            asset_type: Type of asset (css, js, images, etc.)
            filename: Name of the file

        Returns:
            Full URL to asset
        """
        return get_cdn_url(f"{asset_type}/{filename}")

    def get_css_url(self, filename: str) -> str:
        """Get CDN URL for CSS file."""
        return self.get_url("css", filename)

    def get_js_url(self, filename: str) -> str:
        """Get CDN URL for JavaScript file."""
        return self.get_url("js", filename)

    def get_image_url(self, filename: str) -> str:
        """Get CDN URL for image file."""
        return self.get_url("images", filename)

    def get_font_url(self, filename: str) -> str:
        """Get CDN URL for font file."""
        return self.get_url("fonts", filename)


def get_asset_manager() -> CDNAssetManager:
    """Get global asset manager instance."""
    config = get_cdn_config()
    return CDNAssetManager(config)
