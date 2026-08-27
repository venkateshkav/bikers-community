from .models import Rider


class RiderActivityMiddleware:
    """
    Resolves the logged-in rider (if any) from the session on every request
    and exposes it as request.rider. If the rider has since been deactivated
    or deleted by the admin, the session is killed immediately - a rider
    cannot keep using an old session after being deactivated.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.rider = None
        rider_id = request.session.get("rider_id")
        if rider_id:
            rider = Rider.objects.filter(id=rider_id, is_active=True).first()
            if rider:
                request.rider = rider
            else:
                request.session.flush()
        return self.get_response(request)
