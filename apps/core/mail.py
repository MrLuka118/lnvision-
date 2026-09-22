"""Plain-text e-mail from templates/emails/<name>.txt and <name>_subject.txt."""

from django.core.mail import EmailMessage
from django.template import Context
from django.template.loader import get_template


def render_text(template_name: str, context: dict) -> str:
    """No HTML escaping: this is plain text, so "Ana & Luka" must stay as written."""
    return get_template(template_name).template.render(Context(context, autoescape=False))


def text_message(name: str, context: dict, to: list[str], **kwargs) -> EmailMessage:
    # The subject is squeezed onto one line, whatever a visitor typed into their name.
    subject = " ".join(render_text(f"emails/{name}_subject.txt", context).split())
    body = render_text(f"emails/{name}.txt", context)
    return EmailMessage(subject, body, None, to, **kwargs)
