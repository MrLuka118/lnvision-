from django import forms

from .models import TenantModel


class StudioModelForm(forms.ModelForm):
    """ModelForm that limits every related-object choice to the current studio.

    Without this, a form for a shoot would offer (and accept) another studio's clients.
    """

    def __init__(self, *args, studio, **kwargs):
        super().__init__(*args, **kwargs)
        self.studio = studio
        for field in self.fields.values():
            queryset = getattr(field, "queryset", None)
            if queryset is not None and issubclass(queryset.model, TenantModel):
                field.queryset = queryset.filter(studio=studio)
