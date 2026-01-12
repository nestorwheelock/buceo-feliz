# S-001: Smart Lead Routing Based on Diving Experience

**Story Type**: User Story
**Priority**: Medium
**Status**: PENDING
**Created**: 2026-01-12

## User Story

**As a** dive shop staff member
**I want** the system to automatically route website visitors based on their diving experience
**So that** certified divers get a streamlined booking experience while DSD prospects receive proper nurturing

## Background

Currently all website chat visitors become leads regardless of experience level. This creates noise in the lead pipeline - certified divers who know they want to dive don't need nurturing, they just need to book.

### Visitor Types

| Type | Experience | Certification | Pipeline |
|------|------------|---------------|----------|
| Complete Beginner | Never dived | None | Lead (DSD prospect) |
| DSD Graduate | 1-2 dives | None | Lead (needs encouragement) |
| Certified Diver | 10+ dives | OW/AOW/etc | Direct to Diver |

## Acceptance Criteria

### AC1: Experience Question in Chat Widget
- [ ] Website chat widget asks "Have you dived before?" as first question
- [ ] Options: "No, never" / "Yes, a few times" / "Yes, I'm certified"
- [ ] Answer determines routing path

### AC2: Lead Path (Beginners & DSD Graduates)
- [ ] "No, never" or "Yes, a few times" creates Person with `lead_status='new'`
- [ ] Conversation created and linked to Person
- [ ] Appears in staff lead list with chat interface
- [ ] Staff can nurture and eventually convert to diver

### AC3: Diver Path (Certified Divers)
- [ ] "Yes, I'm certified" prompts for certification details
- [ ] Certification level (OW, AOW, Rescue, Divemaster, Instructor)
- [ ] Certification agency (PADI, SSI, NAUI, SDI, etc.)
- [ ] Approximate number of dives
- [ ] Creates Person + DiverProfile directly (no lead_status)
- [ ] Skips lead pipeline entirely

### AC4: Diver Preferences Collection
- [ ] Certified divers prompted for preferences:
  - Equipment: Own gear / Rental needed
  - Interests: Reef, Wreck, Night, Drift, Cenotes, Marine Life
  - Group size preference: Private, Small group, Any
- [ ] Preferences stored on DiverProfile
- [ ] Used for excursion recommendations

### AC5: Staff Booking Suggestions
- [ ] Staff can view diver preferences on detail page
- [ ] System suggests compatible excursions based on:
  - Certification level meets minimum requirement
  - Interests match excursion type
  - Upcoming availability
- [ ] Quick-book from suggestions

## Definition of Done

- [ ] Chat widget updated with experience routing
- [ ] Lead path creates Person with lead_status
- [ ] Diver path creates Person + DiverProfile
- [ ] Preferences captured for certified divers
- [ ] Booking suggestions based on preferences
- [ ] Tests written and passing (>95% coverage)
- [ ] Documentation updated

## Technical Notes

### Data Model Changes

**DiverProfile additions:**
```python
# Preferences (stored as JSON or separate fields)
equipment_preference = models.CharField(max_length=20, choices=[
    ('own', 'Own Equipment'),
    ('rental', 'Full Rental'),
    ('partial', 'Partial Rental'),
])
interests = ArrayField(models.CharField(max_length=50), default=list)
group_preference = models.CharField(max_length=20, choices=[
    ('private', 'Private'),
    ('small', 'Small Group (2-4)'),
    ('any', 'Any Size'),
])
```

**Recommendation Query:**
```python
def get_recommended_excursions(diver: DiverProfile):
    """Get excursions matching diver preferences and certification."""
    return Excursion.objects.filter(
        status='scheduled',
        start_time__gte=timezone.now(),
        excursion_type__min_certification_level__rank__lte=diver.highest_cert_rank,
        excursion_type__tags__overlap=diver.interests,  # PostgreSQL array overlap
    ).order_by('start_time')[:5]
```

### API Changes

**Chat Widget API:**
```
POST /api/chat/
{
    "experience": "certified",  // "never" | "some" | "certified"
    "certification_level": "advanced_open_water",  // if certified
    "certification_agency": "PADI",
    "total_dives": 50,
    "preferences": {
        "equipment": "own",
        "interests": ["reef", "wreck", "cenotes"],
        "group_size": "small"
    },
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "message": "Looking to dive next week"
}
```

## Out of Scope

- Automated booking (still requires staff confirmation)
- Real-time websocket chat
- Mobile app integration
- Certification verification (honor system)

## Dependencies

- S-000: Lead Chat Interface (COMPLETED)
- Website chat widget code access

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Users lie about certification | Medium | Honor system + waiver liability |
| Complex chat flow abandonment | Medium | Keep questions minimal |
| Preference data gets stale | Low | Prompt to update on return visits |

## Related

- Lead Chat Interface (completed)
- Excursion eligibility engine (existing)
- Certification model (existing)
