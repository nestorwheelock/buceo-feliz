# T-001: Add Diver Preferences to DiverProfile Model

**Story**: S-001 Smart Lead Routing
**Priority**: High
**Status**: PENDING
**Estimate**: 2 hours

## Objective

Add preference fields to DiverProfile model to capture diver interests, equipment needs, and group preferences for booking suggestions.

## Deliverables

- [ ] Add preference fields to DiverProfile model
- [ ] Create migration
- [ ] Update admin to show preferences
- [ ] Add preferences to diver detail staff view

## Fields to Add

```python
# Equipment preference
equipment_preference = models.CharField(
    max_length=20,
    blank=True,
    choices=[
        ('own', 'Own Equipment'),
        ('rental', 'Full Rental'),
        ('partial', 'Partial Rental'),
    ],
    help_text="Diver's equipment situation"
)

# Diving interests (PostgreSQL array)
interests = ArrayField(
    models.CharField(max_length=50),
    default=list,
    blank=True,
    help_text="Diving interests: reef, wreck, night, drift, cenotes, marine_life"
)

# Group size preference
group_preference = models.CharField(
    max_length=20,
    blank=True,
    choices=[
        ('private', 'Private'),
        ('small', 'Small Group (2-4)'),
        ('any', 'Any Size'),
    ],
    help_text="Preferred group size for excursions"
)
```

## Test Cases

- test_diver_profile_with_preferences_created
- test_preferences_default_to_empty
- test_interests_array_accepts_multiple_values
- test_preferences_displayed_in_admin

## Definition of Done

- [ ] Model fields added with migration
- [ ] Tests passing
- [ ] Admin updated
- [ ] Staff diver detail shows preferences
