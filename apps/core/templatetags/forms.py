from django import template

register = template.Library()

PLAIN_WIDGETS = {"checkbox", "radioselect", "checkboxselectmultiple", "clearablefile", "file"}


@register.simple_tag
def widget(field, **extra):
    """Render a bound field's widget with the design-system classes and ARIA wiring."""
    attrs = dict(extra)
    # Every field has a visible label; a placeholder repeating it only adds noise.
    attrs.setdefault("placeholder", False)
    if field.widget_type not in PLAIN_WIDGETS:
        attrs["class"] = f"input {attrs.get('class', '')}".strip()
    described_by = []
    if field.help_text:
        described_by.append(f"{field.auto_id}_helptext")
    if field.errors:
        attrs["aria-invalid"] = "true"
        described_by.append(f"{field.auto_id}_error")
    if described_by:
        attrs["aria-describedby"] = " ".join(described_by)
    return field.as_widget(attrs=attrs)
