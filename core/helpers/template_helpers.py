from routes.dependencies import templates


def render(template: str, request, **kwargs):
    return templates.TemplateResponse(template, {"request": request, **kwargs})
