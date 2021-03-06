from sys import version_info
import django.conf
from .models import Root, registered_settings


try:
    from django.utils.six import iteritems  # django >= 1.4.2
except ImportError:
    def iteritems(d, **kw):
        py_version = version_info[0]
        _iteritems = {
            2: 'iteritems',
            3: 'items',
        }.get(py_version)
        if _iteritems is None:
            raise ValueError('Unknown python version')
        return iter(getattr(d, _iteritems)(**kw))


class SettingsProxy(object):
    def __init__(self):
        self._fetched = False

    def __getattr__(self, attr):
        if not self._fetched:
            self._fetch()
        return object.__getattribute__(self, attr)

    def _fetch(self):
        select_related = []
        for app_label, classes in iteritems(registered_settings):
            for model_name in classes.keys():
                select_related.append('%s_%s' % (app_label, model_name))
        qs = Root.objects.select_related(*select_related)
        try:
            root = qs[0]
        except IndexError:
            root, created = qs.get_or_create(defaults={})
            root = qs[0]  # Run select_related again
        for app_label, classes in iteritems(registered_settings):
            for model_name, cls in iteritems(classes):
                f = '%s_%s' % (app_label, model_name)
                try:
                    v = getattr(root, f)
                except cls.DoesNotExist:
                    # Django 1.5+
                    v = None
                if not v:
                    # Doesn't yet exist in the database
                    v = cls(root=root)
                self.__dict__[f] = v
                if model_name == 'settings':
                    self.__dict__[app_label] = v
        self._fetched = True

    def invalidate(self):
        self.__dict__.clear()
        self._fetched = False


settings = django.conf.settings.db = SettingsProxy()
settings.django = django.conf.settings
