from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.views.generic import TemplateView


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "core/dashboard.html"


class StyleGuideView(TemplateView):
    """The design system on one page. Only in DEBUG or for staff."""

    template_name = "core/styleguide.html"

    def dispatch(self, request, *args, **kwargs):
        if not (settings.DEBUG or request.user.is_staff):
            raise Http404
        return super().dispatch(request, *args, **kwargs)
