# T-003: Booking Suggestions Based on Diver Preferences

**Story**: S-001 Smart Lead Routing
**Priority**: Medium
**Status**: PENDING
**Estimate**: 3 hours
**Dependencies**: T-001, T-002

## Objective

Add booking suggestions to staff diver detail view based on diver's preferences, certification level, and upcoming excursion availability.

## Deliverables

- [ ] Create `get_recommended_excursions()` service function
- [ ] Add suggestions section to diver detail template
- [ ] Quick-book action from suggestions

## Service Function

```python
def get_recommended_excursions(diver: DiverProfile, limit: int = 5):
    """Get excursions matching diver preferences and certification.

    Matching criteria:
    - Diver meets certification requirement
    - Excursion type matches interests (if set)
    - Excursion is scheduled and has availability
    - Sorted by soonest first
    """
    from django.db.models import Q
    from .models import Excursion

    qs = Excursion.objects.filter(
        status='scheduled',
        start_time__gte=timezone.now(),
        deleted_at__isnull=True,
    ).select_related('excursion_type', 'dive_site')

    # Filter by certification
    highest_cert = diver.get_highest_certification()
    if highest_cert:
        qs = qs.filter(
            Q(excursion_type__min_certification_level__isnull=True) |
            Q(excursion_type__min_certification_level__rank__lte=highest_cert.certification_level.rank)
        )
    else:
        # No cert = only DSD-type excursions
        qs = qs.filter(excursion_type__min_certification_level__isnull=True)

    # Filter by interests if set
    if diver.interests:
        # PostgreSQL array overlap
        qs = qs.filter(excursion_type__tags__overlap=diver.interests)

    # Check availability
    qs = qs.annotate(
        booking_count=Count('bookings', filter=Q(bookings__status='confirmed'))
    ).filter(
        Q(capacity__isnull=True) | Q(booking_count__lt=F('capacity'))
    )

    return qs.order_by('start_time')[:limit]
```

## Template Section

```html
<!-- Suggested Excursions -->
{% if suggestions %}
<div class="bg-white rounded-lg shadow-sm border p-6">
    <h3 class="text-lg font-semibold mb-4">Suggested Excursions</h3>
    <div class="space-y-3">
        {% for excursion in suggestions %}
        <div class="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
            <div>
                <div class="font-medium">{{ excursion.excursion_type.name }}</div>
                <div class="text-sm text-gray-500">
                    {{ excursion.start_time|date:"M d" }} at {{ excursion.dive_site.name }}
                </div>
            </div>
            <a href="{% url 'diveops:book-diver' excursion.pk %}?diver={{ diver.pk }}"
               class="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700">
                Book
            </a>
        </div>
        {% endfor %}
    </div>
</div>
{% endif %}
```

## Test Cases

- test_suggestions_respect_certification_level
- test_suggestions_filter_by_interests
- test_suggestions_exclude_full_excursions
- test_suggestions_sorted_by_date
- test_no_suggestions_for_no_matching_excursions

## Definition of Done

- [ ] Service function implemented
- [ ] Suggestions shown on diver detail
- [ ] Quick-book link works
- [ ] Tests passing
