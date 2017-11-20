# DjangoCMS Testing

A set of utils to simplify testing on Django CMS plugins and pages

## Usage

### Testing all plugins

```
import os

from .base import BaseTestCase

from filer.models import Image
from djangocms_testing.integrity import CMSPluginIntegrity


class DSMPluginIntegrityTestCase(BaseTestCase, CMSPluginIntegrity):

    plugin_exclude_list = [
        'SomePluginsToExclude',
        'AnotherPluginToExclude',
    ]

    def setUp(self):
        self.homepage = self.create_page('Homepage')

        # Create any data that may be necessary for the plugins

        # Example: Creating an image
        photo_path = os.path.join(os.path.dirname(__file__), 'files', 'sample_image.jpg')
        self.test_image = Image.objects.create(file=photo_path)

        # Update the plugin list
        self.plugin_list = [
            ('CategoryPlugin', {'title': 'Top Category'}),
            ('BannerPlugin', {'icon': self.test_image, 'link': self.homepage}),
            ('LinkToPagePlugin', {'page': self.homepage}),
        ]
```

### Loading Pages

There's a management command that allows you to create pages from a
YAML description.

The page description looks like this:

```
---
# Required page data
title: Regression Test Page
slug: regression-test-page
template: generic_page      # (generic_page is provided. You can use other templates by overriding _get_template)

# Optional page data        # Default value
publish: no                 # no    (yes | no)
language: en                # en    (en | es)
apphook: null               # null  (string)
apphook_namespace: null     # null  (string)
soft_root: no               # no    (yes | no)

# Placeholder variables
#
# Provided:
# $loremispum   1 paragraph of lorem ipsum text.
#
# You can add other variables by overriding _generate_sample_data
# $image        JPEG image
# $svg          SVG Tiger iimage

# Placeholders vary per template but its no problem to define them all
# in advance, and later just switch the template type:
#
# generic_page > content

placeholders:
  content:

    - CategoryPlugin:
        title: Category 1
        subplugins:

          - QuestionPlugin:
              question: >
                This is a question
              author: Author, 21
              subplugins:

                - AnswerPlugin:
                    body: >
                      This is the text's body

```

 Create the page: `manage.py page simple_test.yaml`

