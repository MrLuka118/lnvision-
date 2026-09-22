import datetime
from decimal import Decimal

import factory
from factory.django import DjangoModelFactory

from apps.clients.tests.factories import ClientFactory
from apps.core.tests.factories import StudioFactory
from apps.core.tests.tenancy import register_factory
from apps.finance.models import (
    Expense,
    ExpenseCategory,
    Income,
    Invoice,
    InvoiceLine,
    InvoiceSequence,
    RecurringExpense,
)
from apps.shoots.tests.factories import ShootFactory

SAME_STUDIO = factory.SelfAttribute("..studio")


class ExpenseCategoryFactory(DjangoModelFactory):
    class Meta:
        model = ExpenseCategory

    studio = factory.SubFactory(StudioFactory)
    name = factory.Sequence(lambda n: f"Category {n}")
    colour = "#627a9d"


class RecurringExpenseFactory(DjangoModelFactory):
    class Meta:
        model = RecurringExpense

    studio = factory.SubFactory(StudioFactory)
    name = factory.Sequence(lambda n: f"Recurring {n}")
    amount = Decimal("100.00")
    category = factory.SubFactory(ExpenseCategoryFactory, studio=SAME_STUDIO)
    interval = RecurringExpense.Interval.MONTHLY
    start_date = factory.LazyFunction(datetime.date.today)


class ExpenseFactory(DjangoModelFactory):
    class Meta:
        model = Expense

    studio = factory.SubFactory(StudioFactory)
    date = factory.LazyFunction(datetime.date.today)
    amount = Decimal("50.00")
    category = factory.SubFactory(ExpenseCategoryFactory, studio=SAME_STUDIO)
    supplier = factory.Faker("company")
    description = factory.Faker("sentence")


class InvoiceSequenceFactory(DjangoModelFactory):
    class Meta:
        model = InvoiceSequence

    studio = factory.SubFactory(StudioFactory)
    year = factory.LazyFunction(lambda: datetime.date.today().year)
    last_number = 0


class InvoiceFactory(DjangoModelFactory):
    class Meta:
        model = Invoice

    studio = factory.SubFactory(StudioFactory)
    client = factory.SubFactory(ClientFactory, studio=SAME_STUDIO)
    status = Invoice.Status.DRAFT


class InvoiceLineFactory(DjangoModelFactory):
    class Meta:
        model = InvoiceLine

    invoice = factory.SubFactory(InvoiceFactory)
    description = factory.Faker("sentence")
    quantity = Decimal("1")
    unit_price = Decimal("100.00")
    position = 0


class IncomeFactory(DjangoModelFactory):
    class Meta:
        model = Income

    studio = factory.SubFactory(StudioFactory)
    date = factory.LazyFunction(datetime.date.today)
    amount = Decimal("250.00")
    client = factory.SubFactory(ClientFactory, studio=SAME_STUDIO)
    shoot = factory.SubFactory(ShootFactory, studio=SAME_STUDIO)


register_factory(ExpenseCategory, ExpenseCategoryFactory)
register_factory(RecurringExpense, RecurringExpenseFactory)
register_factory(Expense, ExpenseFactory)
register_factory(Invoice, InvoiceFactory)
register_factory(InvoiceSequence, InvoiceSequenceFactory)
register_factory(Income, IncomeFactory)
