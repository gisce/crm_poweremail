# -*- coding: utf-8 -*-
import re

try:
    text_type = unicode
except NameError:
    text_type = str


def normalize_markdown_image_descriptions(markdown_body):
    """Collapse whitespace only inside Markdown image descriptions."""
    if not markdown_body:
        return markdown_body

    def clean_image_description(match):
        description = ' '.join(match.group(1).split())
        template = (
            u'![{}]({})'
            if isinstance(match.group(0), text_type)
            else '![{}]({})'
        )
        return template.format(description, match.group(2))

    return re.sub(
        r'!\[([^\]]*)\]\(([^)]*)\)',
        clean_image_description,
        markdown_body,
        flags=re.DOTALL
    )
