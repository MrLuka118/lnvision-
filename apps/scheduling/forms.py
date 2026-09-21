from django import forms
from django.utils.translation import gettext_lazy as _

from apps.core.forms import DateTimeLocalInput, StudioModelForm

from .models import Event


class EventForm(StudioModelForm):
    """Meetings, deadlines and personal time. Shoots are created as shoots, not here."""

    layout = [
        (None, ["kind", "title"]),
        (None, [("start", "end"), "all_day"]),
        (None, [("client", "location"), "notes"]),
    ]

    class Meta:
        model = Event
        fields = ["kind", "title", "start", "end", "all_day", "client", "location", "notes"]
        widgets = {
            "start": DateTimeLocalInput(),
            "end": DateTimeLocalInput(),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.kind != Event.Kind.SHOOT:
            self.fields["kind"].choices = [
                c for c in Event.Kind.choices if c[0] != Event.Kind.SHOOT
            ]
        self.fields["kind"].initial = Event.Kind.MEETING

    def clean(self):
        data = super().clean()
        start, end = data.get("start"), data.get("end")
        if start and end and end < start:
            self.add_error("end", _("The event can't end before it starts."))
        if not data.get("title") and not data.get("client"):
            self.add_error("title", _("Add a title or choose a client."))
        return data
