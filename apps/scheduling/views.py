import json
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import Http404, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.decorators.http import require_GET, require_http_methods
from django.views.generic import DetailView, TemplateView
from icalendar import Calendar as ICalendar
from icalendar import Event as ICalEvent

from apps.core.generic import StudioCreateView, StudioUpdateView
from apps.core.mixins import StudioScopedMixin
from apps.core.models import Studio, new_token

from .forms import EventForm
from .models import Event
from .services import event_json, parse_moment

MAX_RANGE = timedelta(days=400)


class CalendarView(LoginRequiredMixin, TemplateView):
    template_name = "scheduling/calendar.html"

    def get_context_data(self, **kwargs):
        ics_path = reverse("scheduling:ics", args=[self.request.studio.ics_token])
        return super().get_context_data(
            config={
                "feedUrl": reverse("scheduling:feed"),
                "moveUrl": reverse("scheduling:move", args=[0]),
                "detailUrl": reverse("scheduling:detail", args=[0]),
                "createUrl": reverse("scheduling:create"),
                "shootCreateUrl": reverse("shoots:create"),
            },
            ics_url=self.request.build_absolute_uri(ics_path),
            **kwargs,
        )


@login_required
@require_GET
def events_feed(request):
    start = parse_moment(request.GET.get("start"))
    end = parse_moment(request.GET.get("end"))
    if not start or not end or end <= start or end - start > MAX_RANGE:
        return JsonResponse({"error": "invalid range"}, status=400)
    events = (
        Event.objects.for_studio(request.studio)
        .filter(start__lt=end)
        .filter(Q(end__gt=start) | Q(end__isnull=True, start__gte=start))
        .select_related("shoot", "client", "location")
    )
    return JsonResponse([event_json(e) for e in events], safe=False)


@login_required
@require_http_methods(["PATCH"])
def event_move(request, pk):
    """Drag and resize from the calendar: {start, end, allDay}."""
    event = get_object_or_404(Event.objects.for_studio(request.studio), pk=pk)
    try:
        payload = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid json"}, status=400)
    start = parse_moment(payload.get("start"))
    end = parse_moment(payload.get("end"))
    if start is None or (end is not None and end < start):
        return JsonResponse({"error": _("That time doesn't work.")}, status=400)
    event.start, event.end = start, end
    event.all_day = bool(payload.get("allDay", event.all_day))
    event.save(update_fields=["start", "end", "all_day", "updated_at"])
    return JsonResponse(event_json(event))


class DialogFormMixin:
    """Event forms open in a dialog on the calendar page; success refreshes the calendar."""

    def get_template_names(self):
        if self.request.htmx:
            return ["scheduling/_event_form.html"]
        return super().get_template_names()

    def get_success_url(self):
        return reverse("scheduling:calendar")

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.htmx:
            return calendar_changed()
        return response


def calendar_changed():
    return HttpResponse(
        status=204,
        headers={"HX-Trigger": json.dumps({"calendar:refresh": True, "dialog:close": True})},
    )


class EventCreateView(DialogFormMixin, StudioCreateView):
    model = Event
    form_class = EventForm
    page_title = _("New event")
    submit_label = _("Add to calendar")
    back_label = _("Calendar")
    success_message = _("Added to the calendar.")

    def get_initial(self):
        initial = super().get_initial()
        start = parse_moment(self.request.GET.get("start"))
        end = parse_moment(self.request.GET.get("end"))
        if start:
            initial["start"] = timezone.localtime(start)
            initial["all_day"] = self.request.GET.get("allDay") == "true"
            initial["end"] = timezone.localtime(end or start + timedelta(hours=1))
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.urlencode()
        start, end = self.request.GET.get("start", ""), self.request.GET.get("end", "")
        context["shoot_url"] = (
            f"{reverse('shoots:create')}?starts_at={start}&ends_at={end}" if query else ""
        )
        return context


class EventUpdateView(DialogFormMixin, StudioUpdateView):
    model = Event
    form_class = EventForm
    submit_label = _("Save changes")
    back_label = _("Calendar")
    success_message = _("Changes saved.")

    @property
    def page_title(self):
        return self.object.display_title

    def get(self, request, *args, **kwargs):
        event = self.get_object()
        if event.kind == Event.Kind.SHOOT and event.shoot_id:
            # A shoot's own event is edited through the shoot, where it has price and status.
            url = reverse("shoots:update", args=[event.shoot_id])
            if request.htmx:
                return HttpResponse(headers={"HX-Redirect": url})
            return HttpResponseRedirect(url)
        return super().get(request, *args, **kwargs)


class EventDetailView(StudioScopedMixin, DetailView):
    model = Event
    template_name = "scheduling/_event_detail.html"

    def get_queryset(self):
        return super().get_queryset().select_related("shoot", "client", "location")


class EventDeleteView(StudioScopedMixin, View):
    http_method_names = ["post"]

    def post(self, request, pk):
        event = get_object_or_404(Event.objects.for_studio(request.studio), pk=pk)
        if event.kind == Event.Kind.SHOOT and event.shoot_id:
            raise Http404  # removed by deleting the shoot or clearing its date
        event.delete()
        if request.htmx:
            return calendar_changed()
        messages.success(request, _("Removed from the calendar."))
        return HttpResponseRedirect(reverse("scheduling:calendar"))


def ics_feed(request, token):
    """Subscribable calendar (Google, Apple). The token in the URL is the only credential."""
    studio = get_object_or_404(Studio, ics_token=token)
    now = timezone.now()
    events = (
        Event.objects.for_studio(studio)
        .filter(start__gte=now - timedelta(days=180), start__lte=now + timedelta(days=400))
        .select_related("shoot", "client", "location")
    )
    cal = ICalendar()
    cal.add("prodid", f"-//{studio.name}//Aperture Studio//SL")
    cal.add("version", "2.0")
    cal.add("x-wr-calname", studio.name)
    cal.add("x-wr-timezone", "Europe/Ljubljana")
    for event in events:
        item = ICalEvent()
        item.add("uid", f"event-{event.pk}@{request.get_host()}")
        item.add("summary", f"{event.display_title}")
        if event.all_day:
            item.add("dtstart", timezone.localdate(event.start))
            end = event.end or event.start + timedelta(days=1)
            item.add("dtend", timezone.localdate(end))
        else:
            item.add("dtstart", timezone.localtime(event.start))
            item.add("dtend", timezone.localtime(event.end or event.start + timedelta(hours=1)))
        item.add("dtstamp", event.updated_at)
        item.add("categories", [str(event.get_kind_display())])
        if event.location_id:
            item.add("location", event.location.name)
        if event.is_tentative:
            item.add("status", "TENTATIVE")
        cal.add_component(item)
    response = HttpResponse(cal.to_ical(), content_type="text/calendar; charset=utf-8")
    response["Content-Disposition"] = 'inline; filename="koledar.ics"'
    response["X-Robots-Tag"] = "noindex"
    response["Cache-Control"] = "private, max-age=300"
    return response


class IcsRotateView(LoginRequiredMixin, View):
    """Issue a new subscription link; the old one stops working."""

    http_method_names = ["post"]

    def post(self, request):
        studio = request.studio
        studio.ics_token = new_token()
        studio.save(update_fields=["ics_token", "updated_at"])
        messages.success(request, _("New calendar link created. The old one no longer works."))
        return HttpResponseRedirect(reverse("scheduling:calendar"))
