from logging import getLogger
from pprint import pformat

import six
import yaml
from cms import api
from cms.models.pagemodel import Page
from cms.models.placeholdermodel import Placeholder
from cms.plugin_pool import plugin_pool
from cms.utils import get_cms_setting
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand

from djangocms_testing import conf

logger = getLogger(__file__)
loremipsum = (
    'Lorem ipsum dolor sit amet, consectetur adipiscing elit. Scripta sane et '
    'multa et polita, sed nescio quo pacto auctoritatem oratio non habet. '
    'Gerendus est mos, modo recte sentiat. Quo plebiscito decreta a senatu '
    'est consuli quaestio Cn. Quis Aristidem non mortuum diligit? Respondeat '
    'totidem verbis.'
)


class Command(BaseCommand):
    help = 'Creates a CMS page with a .yaml template.'

    DEFAULT_LANGUAGE = conf.DEFAULT_LANGUAGE
    DEFAULT_TEMPLATE = conf.DEFAULT_TEMPLATE

    # ToDo:
    #  * Dump page to YAML
    def add_arguments(self, parser):
        parser.add_argument(
            'source',
            nargs='+',
            type=open,
            help='A yaml file containing the page description.')

        parser.add_argument(
            '--site-id',
            action='store',
            dest='site_id',
            default=1,
            type=int,
            help='The Site which the page is created for.'
        )

        parser.add_argument(
            '-s',
            '--slug',
            action='store',
            dest='override_slug',
            default=None,
            type=str,
            help='Override the slug for the page.'
        )

        parser.add_argument(
            '-o',
            '--overwrite',
            action='store_true',
            dest='overwrite',
            default=False,
            help='Delete an existing page if exists.'
        )

    def _debug(self, data, heading=None):
        if self.verbosity > 2:
            self.stdout.write('----- {heading}\n'.format(
                heading=(heading or 'debug message')))
            self.stdout.write(pformat(data, indent=2))
            self.stdout.write('-----\n')

    def _get_template(self, data):
        """
        Returns the appropriate template for the page.
        This can be overridden to get different templates based on the site, arguments, or data.
        """
        return get_cms_setting('TEMPLATES')[0][0]

    def _create_page(self, data):
        """
        Create a bare page without any plugins yet.
        """
        page_data = {
            'title': data['title'],
            'slug': self.override_slug or data['slug'],
            'language': self.language,
            'template': self._get_template(data),
            'parent': None,
            'site': self.site,
            'position': 'last-child',
            'in_navigation': True,
            'soft_root': data.get('soft_root', False),
            'apphook': data.get('apphook', None),
            'apphook_namespace': data.get('apphook_namespace', None),
            'created_by': 'Python API via YAML page builder',
        }
        self._debug(page_data, 'CMS Api Page data')
        page = api.create_page(**page_data)
        if data.get('publish', True):
            page.publish(self.language)
        return page.reload()

    def _attach_plugin(self, page, placeholder_name, plugin_name, plugin_data,
                       parent_plugin=None):
        """
        Creates a sample page and attaches the given Plugin with
        the plugin data.
        """
        subplugin_list = plugin_data.pop('subplugins', [])

        if parent_plugin:
            self._debug(plugin_name, 'Sub Plugin')
        else:
            self._debug(plugin_name, 'Plugin')

        # ----------------------------------------------------------------------
        # Replace $image values with proper objects
        for k, v in six.iteritems(plugin_data):
            if v in self.sample_data:
                plugin_data[k] = self.sample_data[v]

        # ----------------------------------------------------------------------
        self._debug(plugin_data, 'New plugin data')

        try:
            placeholder = page.placeholders.get(slot=placeholder_name)
        except Placeholder.DoesNotExist:
            # Placeholder not available for this template.
            return None

        new_plugin = api.add_plugin(
            target=parent_plugin,
            placeholder=placeholder,
            plugin_type=plugin_name,
            language=self.language,
            position='last-child',
            **plugin_data
        )

        for plugin in subplugin_list:
            plugin_name, plugin_data = next(iter(plugin.items()))
            if not plugin_name in self.all_plugins:
                self.stderr.write('Plugin {name} does not exist. Skipping...'.format(
                    name=plugin_name))
            self._attach_plugin(page, placeholder_name, plugin_name, plugin_data,
                                parent_plugin=new_plugin)

        return new_plugin

    def _generate_sample_data(self):
        """
        For more complex use cases, this should be overriden to include more support data (i.e. images, models, etc)
        """
        return {
            '$loremipsum': '<p>{0}</p>'.format(loremipsum),
        }

    def _validate_data(self, data):
        """
        title
        slug
        template
        placeholder based on template
        check each plugin exists
        """
        required_fields = ('title', 'slug', 'template')
        for f in required_fields:
            if not f in data:
                return False, 'Value for "{field}" is missing.'.format(field=f)

        if data['template'] not in ('generic_page', 'topic_page'):
            return False, 'Template must be either "generic_page" or "topic_page".'

        return True, 'All OK'

    def handle(self, *args, **kwargs):
        self.verbosity = kwargs['verbosity']
        self.overwrite = kwargs['overwrite']
        self.site_id = kwargs['site_id']
        self.override_slug = kwargs['override_slug']

        self.site = self.site_id and Site.objects.get(id=self.site_id) or Site.objects.get_current()
        self.all_plugins = [i.__name__ for i in plugin_pool.get_all_plugins()]
        self.sample_data = self._generate_sample_data()
        self.language = self.DEFAULT_LANGUAGE

        for source in kwargs['source']:

            try:
                data = yaml.load(source, Loader=yaml.Loader)
            except yaml.scanner.ScannerError as e:
                self.stderr.write('Could not parse .yaml file. Error was:\n\n{e}'.format(e=e))
                return 0

            valid, reason = self._validate_data(data)
            if not valid:
                self.stderr.write('.yaml file is invalid. Reason: {0}'.format(reason))
                return 0

            self._debug(data, 'Parsed YAML data')

            # Check if this page already exists
            slug = self.override_slug or data['slug']
            pages = Page.objects.filter(title_set__slug=slug)
            self._debug(pages, 'Existing page objects')

            if pages and self.overwrite:
                self.stdout.write('Found {num} pages with this slug. Deleting...'.format(
                    num=len(pages)))
                [p.delete() for p in pages]
            elif pages and not self.overwrite:
                self.stderr.write('A page with this slug "{slug}" already exists. '
                                  'Use the argument --overwrite to delete.'.format(slug=data['slug']))
                return 0

            self.language = data.get('language', self.DEFAULT_LANGUAGE)

            page = self._create_page(data)

            for placeholder_name, plugin_list in data['placeholders'].items():
                for plugin in plugin_list:
                    plugin_name, plugin_data = next(iter(plugin.items()))
                    if not plugin_name in self.all_plugins:
                        self.stderr.write(f'Plugin {plugin_name} does not exist. Skipping...')
                    self._attach_plugin(page, placeholder_name, plugin_name, plugin_data)

            language = data.get('language', self.DEFAULT_LANGUAGE)
            url = page.get_absolute_url(language)
            print(f'OK. Page URL: http://{self.site.domain}{url}?edit', file=self.stdout)