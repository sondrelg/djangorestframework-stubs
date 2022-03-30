from configparser import ConfigParser
from typing import Callable, Dict, Optional

from mypy.nodes import TypeInfo
from mypy.options import Options
from mypy.plugin import ClassDefContext, Plugin
from mypy_django_plugin.django.context import DjangoContext

from mypy_drf_plugin.lib import fullnames, helpers
from mypy_drf_plugin.transformers import serializers


def transform_serializer_class(ctx: ClassDefContext) -> None:
    sym = ctx.api.lookup_fully_qualified_or_none(fullnames.BASE_SERIALIZER_FULLNAME)
    if sym is not None and isinstance(sym.node, TypeInfo):
        helpers.get_drf_metadata(sym.node)["serializer_bases"][ctx.cls.fullname] = 1

    serializers.make_meta_nested_class_inherit_from_any(ctx)


class NewSemanalDRFPlugin(Plugin):
    def __init__(self, options: Options) -> None:
        super().__init__(options)

        if not self.options.config_file:
            raise ValueError("Missing config file")

        config = ConfigParser()
        config.read(self.options.config_file)

        if "mypy.plugins.django-stubs" not in config:
            raise ValueError("Missing `mypy.plugins.django-stubs` section in the mypy config file.")

        elif "django_settings_module" not in config["mypy.plugins.django-stubs"]:
            raise ValueError(
                "Missing `django_settings_module` in the "
                "`mypy.plugins.django-stubs` section of the mypy config file."
            )
        else:
            django_settings_module = (
                config["mypy.plugins.django-stubs"]["django_settings_module"].lstrip('"').rstrip('"')
            )

        self.django_context = DjangoContext(django_settings_module)

    def _get_currently_defined_serializers(self) -> Dict[str, int]:
        base_serializer_sym = self.lookup_fully_qualified(fullnames.BASE_SERIALIZER_FULLNAME)
        if base_serializer_sym is not None and isinstance(base_serializer_sym.node, TypeInfo):
            return base_serializer_sym.node.metadata.setdefault("drf", {}).setdefault(
                "serializer_bases", {fullnames.BASE_SERIALIZER_FULLNAME: 1}
            )
        else:
            return {}

    def get_base_class_hook(self, fullname: str) -> Optional[Callable[[ClassDefContext], None]]:
        if fullname in self._get_currently_defined_serializers():
            return transform_serializer_class
        return None


def plugin(version):
    return NewSemanalDRFPlugin
