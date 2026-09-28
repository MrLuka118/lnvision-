from django.urls import path

from . import views

app_name = "finance"
urlpatterns = [
    path("finance/", views.FinanceDashboardView.as_view(), name="dashboard"),
    path("finance/izvoz.csv", views.export, name="export"),
    path("finance/predlogi/", views.suggestions, name="suggestions"),
    path("finance/stroski/<int:pk>/racun/", views.receipt, name="receipt"),
]
for kind, segment, model, form in views.LEDGERS:
    base = f"finance/{segment}/"
    urlpatterns += [
        path(base, views.LedgerListView.as_view(model=model, kind=kind), name=f"{kind}_list"),
        path(
            base + "nov/",
            views.LedgerCreateView.as_view(model=model, form_class=form, kind=kind),
            name=f"{kind}_create",
        ),
        path(
            base + "<int:pk>/uredi/",
            views.LedgerUpdateView.as_view(model=model, form_class=form, kind=kind),
            name=f"{kind}_update",
        ),
        path(
            base + "<int:pk>/izbrisi/",
            views.LedgerDeleteView.as_view(model=model, kind=kind),
            name=f"{kind}_delete",
        ),
    ]
