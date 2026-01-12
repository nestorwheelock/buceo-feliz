"""Tests for form component templates."""

import pytest
from django import forms
from django.template import Template, Context


class SampleForm(forms.Form):
    """Sample form for testing."""

    name = forms.CharField(max_length=100, help_text="Enter your full name")
    email = forms.EmailField(required=True)
    agree = forms.BooleanField(required=True)


class TestFieldComponent:
    """Tests for the field.html component."""

    def test_field_component_renders_label(self):
        """field.html renders the field label."""
        form = SampleForm()
        template = Template(
            "{% load portal_ui_tags %}"
            "{% include 'portal_ui/components/forms/field.html' with field=form.name %}"
        )
        context = Context({"form": form})
        rendered = template.render(context)

        assert "Name" in rendered

    def test_field_component_renders_input(self):
        """field.html renders the input widget."""
        form = SampleForm()
        template = Template(
            "{% load portal_ui_tags %}"
            "{% include 'portal_ui/components/forms/field.html' with field=form.name %}"
        )
        context = Context({"form": form})
        rendered = template.render(context)

        assert "<input" in rendered

    def test_field_component_renders_help_text(self):
        """field.html renders field help text."""
        form = SampleForm()
        template = Template(
            "{% load portal_ui_tags %}"
            "{% include 'portal_ui/components/forms/field.html' with field=form.name %}"
        )
        context = Context({"form": form})
        rendered = template.render(context)

        assert "Enter your full name" in rendered

    def test_field_component_shows_required_indicator(self):
        """field.html shows required indicator for required fields."""
        form = SampleForm()
        template = Template(
            "{% load portal_ui_tags %}"
            "{% include 'portal_ui/components/forms/field.html' with field=form.email %}"
        )
        context = Context({"form": form})
        rendered = template.render(context)

        # Required indicator is typically an asterisk
        assert "*" in rendered or "required" in rendered.lower()

    def test_field_component_renders_errors(self):
        """field.html renders field errors."""
        form = SampleForm(data={"name": "", "email": "invalid"})
        form.is_valid()  # Trigger validation

        template = Template(
            "{% load portal_ui_tags %}"
            "{% include 'portal_ui/components/forms/field.html' with field=form.email %}"
        )
        context = Context({"form": form})
        rendered = template.render(context)

        # Should show email validation error
        assert "error" in rendered.lower() or "invalid" in rendered.lower()


class TestButtonComponent:
    """Tests for the button.html component."""

    def test_button_component_renders_primary(self):
        """button.html renders primary variant."""
        template = Template(
            "{% include 'portal_ui/components/forms/button.html' "
            "with type='submit' text='Save' variant='primary' %}"
        )
        rendered = template.render(Context({}))

        assert "Save" in rendered
        assert "<button" in rendered
        # Primary should have blue styling
        assert "bg-blue" in rendered or "bg-primary" in rendered

    def test_button_component_renders_secondary(self):
        """button.html renders secondary variant."""
        template = Template(
            "{% include 'portal_ui/components/forms/button.html' "
            "with type='button' text='Cancel' variant='secondary' %}"
        )
        rendered = template.render(Context({}))

        assert "Cancel" in rendered
        # Secondary should have gray styling
        assert "bg-gray" in rendered or "border" in rendered

    def test_button_component_renders_danger(self):
        """button.html renders danger variant."""
        template = Template(
            "{% include 'portal_ui/components/forms/button.html' "
            "with type='button' text='Delete' variant='danger' %}"
        )
        rendered = template.render(Context({}))

        assert "Delete" in rendered
        # Danger should have red styling
        assert "bg-red" in rendered or "text-red" in rendered

    def test_button_component_has_type_attribute(self):
        """button.html includes the type attribute."""
        template = Template(
            "{% include 'portal_ui/components/forms/button.html' "
            "with type='submit' text='Go' variant='primary' %}"
        )
        rendered = template.render(Context({}))

        assert 'type="submit"' in rendered


class TestFormErrorsComponent:
    """Tests for the form_errors.html component."""

    def test_form_errors_renders_non_field_errors(self):
        """form_errors.html renders non-field errors."""

        class FormWithClean(forms.Form):
            password1 = forms.CharField()
            password2 = forms.CharField()

            def clean(self):
                cleaned = super().clean()
                if cleaned.get("password1") != cleaned.get("password2"):
                    raise forms.ValidationError("Passwords do not match")
                return cleaned

        form = FormWithClean(data={"password1": "abc", "password2": "xyz"})
        form.is_valid()

        template = Template(
            "{% include 'portal_ui/components/forms/form_errors.html' with form=form %}"
        )
        context = Context({"form": form})
        rendered = template.render(context)

        assert "Passwords do not match" in rendered

    def test_form_errors_empty_when_no_errors(self):
        """form_errors.html renders nothing when no errors."""

        class SimpleForm(forms.Form):
            name = forms.CharField()

        form = SimpleForm(data={"name": "Test"})
        form.is_valid()

        template = Template(
            "{% include 'portal_ui/components/forms/form_errors.html' with form=form %}"
        )
        context = Context({"form": form})
        rendered = template.render(context).strip()

        # Should be empty or minimal when no errors
        assert "error" not in rendered.lower() or rendered == ""


class TestEligibilityAlertComponent:
    """Tests for the eligibility_alert.html component."""

    def test_eligibility_alert_shows_not_allowed(self):
        """eligibility_alert.html shows alert when not allowed."""
        # Simulate EligibilityResult-like object
        result = {
            "allowed": False,
            "reasons": ["Certification level too low", "Medical clearance expired"],
            "required_actions": ["Upgrade certification", "Renew medical"],
        }

        template = Template(
            "{% include 'portal_ui/components/forms/eligibility_alert.html' "
            "with result=result %}"
        )
        context = Context({"result": result})
        rendered = template.render(context)

        assert "Certification level too low" in rendered
        assert "Medical clearance expired" in rendered

    def test_eligibility_alert_shows_required_actions(self):
        """eligibility_alert.html shows required actions."""
        result = {
            "allowed": False,
            "reasons": ["Waiver expired"],
            "required_actions": ["Sign new waiver"],
        }

        template = Template(
            "{% include 'portal_ui/components/forms/eligibility_alert.html' "
            "with result=result %}"
        )
        context = Context({"result": result})
        rendered = template.render(context)

        assert "Sign new waiver" in rendered

    def test_eligibility_alert_hidden_when_allowed(self):
        """eligibility_alert.html is hidden when allowed."""
        result = {
            "allowed": True,
            "reasons": [],
            "required_actions": [],
        }

        template = Template(
            "{% include 'portal_ui/components/forms/eligibility_alert.html' "
            "with result=result %}"
        )
        context = Context({"result": result})
        rendered = template.render(context).strip()

        # Should be empty or hidden when allowed
        assert "error" not in rendered.lower() or rendered == ""

    def test_eligibility_alert_has_red_styling(self):
        """eligibility_alert.html uses red/error styling."""
        result = {
            "allowed": False,
            "reasons": ["Not eligible"],
            "required_actions": [],
        }

        template = Template(
            "{% include 'portal_ui/components/forms/eligibility_alert.html' "
            "with result=result %}"
        )
        context = Context({"result": result})
        rendered = template.render(context)

        # Should have red/error styling
        assert "red" in rendered or "error" in rendered or "bg-red" in rendered
