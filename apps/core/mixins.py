from django.contrib.auth.mixins import LoginRequiredMixin

from .forms import StudioModelForm


class StudioScopedMixin(LoginRequiredMixin):
    """For class-based views over a TenantModel.

    - querysets only ever contain the current studio's rows, so foreign ids give 404;
    - StudioModelForm gets the studio and scopes its choices;
    - new objects are stamped with the current studio.

    Put it first in the bases: `class ClientUpdate(StudioScopedMixin, UpdateView)`.
    """

    def get_queryset(self):
        return super().get_queryset().filter(studio=self.request.studio)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if issubclass(self.get_form_class(), StudioModelForm):
            kwargs["studio"] = self.request.studio
        return kwargs

    def form_valid(self, form):
        form.instance.studio = self.request.studio
        return super().form_valid(form)
