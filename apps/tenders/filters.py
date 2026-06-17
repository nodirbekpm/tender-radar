import django_filters
from django.db.models import Q

from apps.sources.models import Source

from .models import FZType, Tender


class TenderFilter(django_filters.FilterSet):
    """Shared filter for the HTML list view and the API.

    ``queryset`` is expected to already be scoped to the user's visible
    sources; the source choices are likewise restricted by the view.
    """

    q = django_filters.CharFilter(method="filter_search", label="Keyword")
    region = django_filters.CharFilter(field_name="region", lookup_expr="icontains")
    fz_type = django_filters.ChoiceFilter(choices=FZType.choices)
    source = django_filters.ModelChoiceFilter(queryset=Source.objects.none())
    price_min = django_filters.NumberFilter(field_name="price", lookup_expr="gte")
    price_max = django_filters.NumberFilter(field_name="price", lookup_expr="lte")

    class Meta:
        model = Tender
        fields = ["q", "region", "fz_type", "source", "price_min", "price_max"]

    def __init__(self, *args, visible_sources=None, **kwargs):
        super().__init__(*args, **kwargs)
        if visible_sources is not None:
            self.filters["source"].queryset = visible_sources

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(title__icontains=value)
            | Q(customer__icontains=value)
            | Q(number__icontains=value)
        )
