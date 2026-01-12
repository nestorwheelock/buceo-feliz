# T-002: Chat Widget Experience Routing

**Story**: S-001 Smart Lead Routing
**Priority**: High
**Status**: PENDING
**Estimate**: 3 hours
**Dependencies**: T-001

## Objective

Update website chat widget and API to ask about diving experience and route visitors to appropriate paths (lead vs diver).

## Deliverables

- [ ] Update PublicChatAPIView to accept experience parameter
- [ ] Add routing logic based on experience level
- [ ] Create DiverProfile directly for certified divers
- [ ] Keep lead pipeline for beginners/DSD graduates

## API Changes

```python
# New fields in chat API request
{
    "experience": "certified",  # "never" | "some" | "certified"
    "certification_level": "advanced_open_water",
    "certification_agency": "PADI",
    "total_dives": 50,
    ...
}
```

## Routing Logic

```python
def route_visitor(experience, certification_data=None):
    """Route visitor based on diving experience."""
    if experience in ('never', 'some'):
        # Lead path: create Person with lead_status
        return create_lead_person(...)
    elif experience == 'certified':
        # Diver path: create Person + DiverProfile
        return create_certified_diver(...)
```

## Test Cases

- test_never_dived_creates_lead
- test_some_experience_creates_lead
- test_certified_creates_diver_directly
- test_certified_with_preferences_saved
- test_certified_skips_lead_status

## Definition of Done

- [ ] API accepts experience parameter
- [ ] Routing logic implemented
- [ ] Certified divers get DiverProfile immediately
- [ ] Beginners routed to lead pipeline
- [ ] Tests passing
