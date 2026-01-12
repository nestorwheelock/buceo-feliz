"""Tests for portal_ui template tags and filters."""

import pytest
from django import forms
from django.template import Template, Context


class SampleForm(forms.Form):
    """Sample form for testing."""

    name = forms.CharField(max_length=100)
    email = forms.EmailField()
    message = forms.CharField(widget=forms.Textarea)


class TestAddClassFilter:
    """Tests for the add_class template filter."""

    def test_add_class_to_input_field(self):
        """add_class filter adds CSS classes to form field widget."""
        form = SampleForm()
        template = Template(
            "{% load portal_ui_tags %}{{ form.name|add_class:'w-full px-3 py-2' }}"
        )
        context = Context({"form": form})
        rendered = template.render(context)

        assert 'class="w-full px-3 py-2"' in rendered

    def test_add_class_to_textarea(self):
        """add_class filter works with textarea widgets."""
        form = SampleForm()
        template = Template(
            "{% load portal_ui_tags %}{{ form.message|add_class:'h-32 resize-none' }}"
        )
        context = Context({"form": form})
        rendered = template.render(context)

        assert 'class="h-32 resize-none"' in rendered

    def test_add_class_preserves_existing_classes(self):
        """add_class filter preserves existing widget classes."""

        class FormWithClass(forms.Form):
            name = forms.CharField(widget=forms.TextInput(attrs={"class": "existing"}))

        form = FormWithClass()
        template = Template(
            "{% load portal_ui_tags %}{{ form.name|add_class:'new-class' }}"
        )
        context = Context({"form": form})
        rendered = template.render(context)

        assert "existing" in rendered
        assert "new-class" in rendered

    def test_add_class_returns_safe_string(self):
        """add_class filter returns a safe string (not escaped)."""
        form = SampleForm()
        template = Template(
            "{% load portal_ui_tags %}{{ form.name|add_class:'test-class' }}"
        )
        context = Context({"form": form})
        rendered = template.render(context)

        # Should contain actual HTML, not escaped
        assert "<input" in rendered
        assert "&lt;input" not in rendered


class TestDiveopsIcons:
    """Tests for diveops-specific icons."""

    def test_anchor_icon_exists(self):
        """anchor icon is available with specific path."""
        template = Template("{% load portal_ui_tags %}{% icon 'anchor' %}")
        rendered = template.render(Context({}))

        assert "<svg" in rendered
        # Anchor icon has line from y1=22 to y1=8 (the shaft)
        assert 'y1="22"' in rendered
        # And a circle at top (cx=12, cy=5, r=3)
        assert 'cy="5"' in rendered

    def test_compass_icon_exists(self):
        """compass icon is available with specific path."""
        template = Template("{% load portal_ui_tags %}{% icon 'compass' %}")
        rendered = template.render(Context({}))

        assert "<svg" in rendered
        # Compass has specific polygon with these exact points
        assert "polygon" in rendered
        assert "16.24 7.76" in rendered

    def test_life_buoy_icon_exists(self):
        """life-buoy icon is available with specific path."""
        template = Template("{% load portal_ui_tags %}{% icon 'life-buoy' %}")
        rendered = template.render(Context({}))

        assert "<svg" in rendered
        # Life-buoy has multiple circles (r=10, r=6, r=2)
        assert rendered.count("circle") >= 3
        # Has the inner circles
        assert 'r="6"' in rendered
        assert 'r="2"' in rendered

    def test_waves_icon_exists(self):
        """waves icon is available for water/diving context."""
        template = Template("{% load portal_ui_tags %}{% icon 'waves' %}")
        rendered = template.render(Context({}))

        assert "<svg" in rendered
        # Waves icon has 3 path elements for 3 wave lines
        assert rendered.count("path") >= 3
        # Waves use curves (c commands in SVG path)
        assert "c.6.5" in rendered.lower() or "c.6" in rendered
