from .services import ensure_studio


class StudioMiddleware:
    """Sets `request.studio` to the signed-in photographer's studio, or None."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        request.studio = ensure_studio(user) if user.is_authenticated else None
        return self.get_response(request)
