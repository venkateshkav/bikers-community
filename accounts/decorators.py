from functools import wraps

from django.shortcuts import redirect


def rider_login_required(view_func):
    """
    Requires a valid rider session (see riders.middleware.RiderActivityMiddleware,
    which resolves request.rider and clears the session if the rider was
    deactivated). Mirrors django.contrib.auth.decorators.login_required but
    for the rider-only session, which is deliberately separate from
    django.contrib.auth (riders have no password).
    """

    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if request.rider is None:
            return redirect("accounts:login")
        return view_func(request, *args, **kwargs)

    return wrapped
