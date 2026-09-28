import csv
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Sum
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_GET, require_http_methods
from django.views.generic import TemplateView

from apps.core.generic import StudioCreateView, StudioDeleteView, StudioListView, StudioUpdateView
from apps.shoots.models import Shoot

from . import reports
from .forms import CategoryForm, ExpenseForm, IncomeForm, RecurringForm
from .models import Expense, ExpenseCategory, Income, RecurringExpense
from .services import generate_recurring


def period(request):
    try:
        year = int(request.GET.get("leto", timezone.localdate().year))
        month = int(request.GET.get("mesec", 0))
        if not 1900 <= year <= 9998 or not 0 <= month <= 12:
            raise ValueError
    except (ValueError, TypeError):
        year, month = timezone.localdate().year, 0
    return year, month


def filtered(model, request):
    year, month = period(request)
    qs = model.objects.for_studio(request.studio).filter(date__year=year)
    if month:
        qs = qs.filter(date__month=month)
    if model == Expense and request.GET.get("kategorija", "").isdigit():
        qs = qs.filter(category_id=request.GET["kategorija"])
    return qs


def period_context(request):
    year, month = period(request)
    years = {year, timezone.localdate().year}
    for model in [Income, Expense]:
        years.update(d.year for d in model.objects.for_studio(request.studio).dates("date", "year"))
    return {
        "year": year,
        "month": month,
        "years": sorted(years, reverse=True),
        "months": range(1, 13),
        "categories": ExpenseCategory.objects.for_studio(request.studio),
        "selected_category": request.GET.get("kategorija", ""),
    }


class FinanceDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "finance/dashboard.html"

    def get_context_data(self, **kwargs):
        studio = self.request.studio
        year, _month = period(self.request)
        return super().get_context_data(
            **period_context(self.request),
            summary=reports.summary(studio, year),
            monthly=reports.monthly(studio, year),
            categories_report=list(reports.by_category(studio, year)),
            previous_monthly=reports.monthly(studio, year - 1),
            top_clients=reports.top_clients(studio, year),
            active="dashboard",
            **kwargs,
        )


class LedgerListView(StudioListView):
    template_name = "finance/list.html"
    kind = "income"

    def get_queryset(self):
        if self.model in (Income, Expense):
            qs = filtered(self.model, self.request)
        else:
            qs = super().get_queryset()
        if self.model == Income:
            qs = qs.select_related("client", "shoot")
        elif self.model in (Expense, RecurringExpense):
            qs = qs.select_related("category")
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(period_context(self.request))
        context.update(
            active=self.kind,
            title=self.model._meta.verbose_name_plural,
            create_url=reverse(f"finance:{self.kind}_create"),
        )
        context["rows"] = [
            {
                "object": row,
                "edit_url": reverse(f"finance:{self.kind}_update", args=[row.pk]),
                "delete_url": reverse(f"finance:{self.kind}_delete", args=[row.pk]),
            }
            for row in context["object_list"]
        ]
        if self.model in (Income, Expense):
            context["total"] = reports.total(self.get_queryset())
            context["is_ledger"] = True
        return context


class LedgerFormMixin:
    kind = "income"
    success_message = _("Changes saved.")
    back_label = _("Finance")

    @property
    def page_title(self):
        return self.model._meta.verbose_name.capitalize()

    def get_success_url(self):
        return reverse(f"finance:{self.kind}_list")

    def get_initial(self):
        return {
            **super().get_initial(),
            "date": timezone.localdate(),
            "start_date": timezone.localdate(),
        }

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.model == RecurringExpense and self.object.is_active:
            generate_recurring(
                queryset=RecurringExpense.objects.for_studio(self.request.studio).filter(
                    pk=self.object.pk
                )
            )
        return response

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form), status=400)


class LedgerCreateView(LedgerFormMixin, StudioCreateView):
    pass


class LedgerUpdateView(LedgerFormMixin, StudioUpdateView):
    pass


class LedgerDeleteView(StudioDeleteView):
    kind = "income"
    page_title = _("Delete this record?")
    lede = _("This permanently removes the record from your studio.")

    def get_success_url(self):
        return reverse(f"finance:{self.kind}_list")

    def get_cancel_url(self):
        return self.get_success_url()


LEDGERS = [
    ("income", "prihodki", Income, IncomeForm),
    ("expense", "stroski", Expense, ExpenseForm),
    ("recurring", "ponavljajoci", RecurringExpense, RecurringForm),
    ("category", "kategorije", ExpenseCategory, CategoryForm),
]


@login_required
@require_GET
def receipt(request, pk):
    expense = get_object_or_404(Expense.objects.for_studio(request.studio), pk=pk)
    if not expense.receipt:
        raise Http404
    response = FileResponse(
        expense.receipt.open("rb"),
        as_attachment=True,
        filename=expense.receipt.name.rsplit("/", 1)[-1],
    )
    response["Cache-Control"] = "private, no-store"
    return response


def csv_text(value):
    value = str(value or "")
    # Spreadsheet applications interpret these prefixes as formulas, even in quoted CSV cells.
    return "'" + value if value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")) else value


@login_required
@require_GET
def export(request):
    year, month = period(request)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    suffix = f"-{month:02d}" if month else ""
    response["Content-Disposition"] = f'attachment; filename="finance-{year}{suffix}.csv"'
    response["Cache-Control"] = "private, no-store"
    response.write("\ufeff")
    writer = csv.writer(response, delimiter=";")
    writer.writerow(["Datum", "Vrsta", "Opis", "Kategorija", "Znesek", "DDV"])
    for model, kind in [(Income, "prihodek"), (Expense, "strošek")]:
        qs = filtered(model, request)
        if model == Expense:
            qs = qs.select_related("category")
        for row in qs.iterator():
            amount = row.amount if model == Income else -row.amount
            vat = getattr(row, "vat_amount", None)
            writer.writerow(
                [
                    row.date.strftime("%d. %m. %Y"),
                    kind,
                    csv_text(row.description),
                    csv_text(row.category.name) if model == Expense else "",
                    f"{amount:.2f}".replace(".", ","),
                    f"{vat:.2f}".replace(".", ",") if vat is not None else "",
                ]
            )
    return response


@login_required
@require_http_methods(["GET", "POST"])
def suggestions(request):
    qs = Shoot.objects.for_studio(request.studio).filter(status__in=["paid", "delivered"])
    if request.method == "POST":
        with transaction.atomic():
            shoot = get_object_or_404(qs.select_for_update(), pk=request.POST.get("shoot"))
            paid = reports.total(Income.objects.for_studio(request.studio).filter(shoot=shoot))
            if shoot.price and shoot.price > paid:
                Income.objects.create(
                    studio=request.studio,
                    shoot=shoot,
                    client=shoot.client,
                    date=timezone.localdate(),
                    amount=shoot.price - paid,
                )
                messages.success(request, _("Income recorded."))
        return redirect("finance:suggestions")
    rows = []
    for shoot in qs.select_related("client").annotate(received=Sum("incomes__amount")):
        remaining = (shoot.price or Decimal("0")) - (shoot.received or Decimal("0"))
        if remaining > 0:
            rows.append({"shoot": shoot, "remaining": remaining})
    return render(request, "finance/suggestions.html", {"rows": rows, "active": "suggestions"})
