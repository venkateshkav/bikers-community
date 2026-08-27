def current_rider(request):
    return {"rider": getattr(request, "rider", None)}
