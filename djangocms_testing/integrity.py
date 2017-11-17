"""
Test CMS Plugins for integrity.
"""
import sys

from urllib.parse import urlencode

from cms import api
from cms.api import create_page
from cms.models import CMSPlugin
from cms.plugin_pool import plugin_pool

from django.contrib.sites.models import Site

from djangocms_testing import conf


class CMSPluginIntegrity:
    """
    Iterates over the Plugin list and creates an individual page with each
    individual plugin. The main purpose is integrity testing here, test that
    plugins do work in general and they don't contain any code or syntax issues.
    It doesn't test each plugin output individually.
    """
    DEFAULT_LANGUAGE = conf.DEFAULT_LANGUAGE
    DEFAULT_TEMPLATE = conf.DEFAULT_TEMPLATE

    # List of plugins to test. Uses the Plugin name, and a dict of sample
    # data we pass to the Plugin to have initial, valid content.
    # Most of the plugins don't require any initial data, either because
    # their fields are `blank=True` or have sane defaults. An empty dict
    # is therefor good most of the time.
    plugin_list = []

    # List of plugins we intentionally don't want to test
    plugin_exclude_list = []

    def setUp(self):
        super().setUp()
        # Here you can override the list of plugins if they need dynamic data

    def create_page(self, title, parent=None, publish=True, **kwargs):
        """
        Shortcut to create a CMS page and publish it right away.
        More complex page tests should use the ``cms.api.create_page`` API instead.
        """
        page_data = {
            'title': title,
            'language': self.DEFAULT_LANGUAGE,
            'template': self.DEFAULT_TEMPLATE,
            'parent': parent,
            'site': Site.objects.get_current(),
            'position': 'last-child',
            'in_navigation': True,
        }
        page_data.update(**kwargs)
        with self.settings(CMS_TEMPLATES=[(self.DEFAULT_TEMPLATE, 'Testing template')]):
            page = create_page(**page_data)
        if publish:
            page.publish(kwargs.get('language', self.DEFAULT_LANGUAGE))
        return page.reload()

    def create_plugin(self, plugin, subplugins=None, **plugin_data):
        """
        Creates a sample page and attaches the given Plugin with
        the plugin data.
        """
        # The test Draft page
        new_page = self.create_page('Plugin Test Page', publish=False)

        # The base plugin
        new_plugin = api.add_plugin(
            placeholder=new_page.placeholders.get(slot='content'),
            plugin_type=plugin,
            language=self.DEFAULT_LANGUAGE,
            **plugin_data
        )

        # check that the plugin label is set, and does not error
        # since this is hard to catch, and gives strange CMS reports.
        new_plugin.__str__()

        # Subplugins
        if subplugins:
            for subplugin, subplugin_data in subplugins:
                print(f' + {subplugin}')
                new_subplugin = api.add_plugin(
                    parent=new_plugin,
                    placeholder=new_page.placeholders.get(slot='content'),
                    plugin_type=subplugin,
                    language=self.DEFAULT_LANGUAGE,
                    position=CMSPlugin.objects.filter(parent=new_plugin).count(),
                    **subplugin_data
                )
                new_subplugin.__str__()

        # Publish the page to maek sure relation copies work fine
        new_page.publish(self.DEFAULT_LANGUAGE)
        return new_page

    def test_plugin_is_tested(self):
        """
        Runs over the general Plugin list in the settings
        and makes sure, all those plugins are tested here.
        """
        plugin_list = [i[0] for i in self.plugin_list]
        all_plugin_list = [str(i.value) for i in plugin_pool.get_all_plugins()]

        for plugin in all_plugin_list:
            if (not plugin in self.plugin_exclude_list and
                    not plugin in plugin_list):
                print(f'WRN: {plugin} is not tested.')

    def test_plugins(self):
        print()
        for plugin in self.plugin_list:
            print(f'{plugin[0]} ... ', end='')
            sys.stdout.flush()
            try:
                plugin_name = plugin[0]
                plugin_data = plugin[1]
                get_arg_list = plugin_data.pop('GET', [])
                subplugins = len(plugin) == 3 and plugin[2] or None

                # Create a page instance with this plugin
                page = self.create_plugin(plugin_name, subplugins, **plugin_data)

                # Test that the page this plugin was published on is valid.
                # We don't check the particular output the plugin here.
                response = self.client.get(page.get_absolute_url(self.DEFAULT_LANGUAGE))
                self.assertEqual(response.status_code, 200)

                # Check the page with optional given GET arguments
                for get_args in get_arg_list:
                    url = page.get_absolute_url(self.DEFAULT_LANGUAGE) + '?' + urlencode(get_args)
                    response = self.client.get(url)
                    self.assertEqual(response.status_code, 200)
                print(' ok')

            except Exception as e:
                self.fail(f'{plugin} raised Exception unexpectedly.\n{e}')
