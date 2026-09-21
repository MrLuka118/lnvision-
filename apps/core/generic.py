"""Studio-scoped generic views. Subclass these for plain CRUD pages."""

from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import ProtectedError, RestrictedError
from django.http import HttpResponseRedirect
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .mixins import StudioScopedMixin


class FormPageMixin:
    """Context for templates/generic/form.html."""

    template_name = "generic/form.html"
    page_title = ""
    lede = ""
    submit_label = _("Save")
    back_label = ""

    def get_cancel_url(self):
        return self.get_success_url()

    def get_delete_url(self):
        return None

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            page_title=self.page_title,
            lede=self.lede,
            submit_label=self.submit_label,
            back_label=self.back_label,
            cancel_url=self.get_cancel_url(),
            delete_url=self.get_delete_url(),
            **kwargs,
        )


class StudioListView(StudioScopedMixin, ListView):
    paginate_by = 50


class StudioDetailView(StudioScopedMixin, DetailView):
    pass


class StudioCreateView(StudioScopedMixin, FormPageMixin, SuccessMessageMixin, CreateView):
    pass


class StudioUpdateView(StudioScopedMixin, FormPageMixin, SuccessMessageMixin, UpdateView):
    pass


class StudioDeleteView(StudioScopedMixin, DeleteView):
    """Confirms, deletes, and explains instead of crashing when related records protect it."""

    template_name = "generic/confirm_delete.html"
    page_title = ""
    lede = ""
    confirm_label = _("Delete")
    success_message = ""
    protected_message = _("This can't be deleted while other records depend on it.")

    def get_cancel_url(self):
        return self.object.get_absolute_url()

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            page_title=self.page_title,
            lede=self.lede,
            confirm_label=self.confirm_label,
            cancel_url=self.get_cancel_url(),
            **kwargs,
        )

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
        except (ProtectedError, RestrictedError):
            messages.error(self.request, self.protected_message)
            return HttpResponseRedirect(self.get_cancel_url())
        if self.success_message:
            messages.success(self.request, self.success_message)
        return response
