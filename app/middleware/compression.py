from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.datastructures import Headers
from gzip import GzipFile
import io


class GzipMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        minimum_size: int = 500,
        compresslevel: int = 6,
        exclude_paths: list[str] = None,
        exclude_types: list[str] = None,
    ):
        super().__init__(app)
        self.minimum_size = minimum_size
        self.compresslevel = compresslevel
        self.exclude_paths = exclude_paths or ["/metrics", "/health"]
        self.exclude_types = exclude_types or [
            "application/grpc",
            "application/octet-stream",
            "image/",
            "video/",
            "audio/",
        ]
    
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        
        if self._should_skip_compression(request, response):
            return response
        
        if not self._should_compress(response):
            return response
        
        compressed_body = self._compress_body(response.body)
        
        new_headers = dict(response.headers)
        new_headers["Content-Encoding"] = "gzip"
        new_headers["Content-Length"] = str(len(compressed_body))
        new_headers["Vary"] = "Accept-Encoding"
        
        if "Content-Length" in new_headers:
            del new_headers["Content-Length"]
        
        return Response(
            content=compressed_body,
            status_code=response.status_code,
            headers=new_headers,
            media_type=response.media_type,
        )
    
    def _should_skip_compression(self, request: Request, response: Response) -> bool:
        if request.url.path in self.exclude_paths:
            return True
        
        for path in self.exclude_paths:
            if request.url.path.startswith(path):
                return True
        
        return False
    
    def _should_compress(self, response: Response) -> bool:
        accept_encoding = response.headers.get("Accept-Encoding", "")
        if "gzip" not in accept_encoding.lower():
            return False
        
        if "Content-Encoding" in response.headers:
            return False
        
        content_type = response.headers.get("Content-Type", "")
        for exclude_type in self.exclude_types:
            if exclude_type in content_type.lower():
                return False
        
        body = response.body
        if not body:
            return False
        
        if len(body) < self.minimum_size:
            return False
        
        return True
    
    def _compress_body(self, body: bytes) -> bytes:
        compressed = io.BytesIO()
        with GzipFile(fileobj=compressed, mode="wb", compresslevel=self.compresslevel) as gzip_file:
            gzip_file.write(body)
        return compressed.getvalue()
