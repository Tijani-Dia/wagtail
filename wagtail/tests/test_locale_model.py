import random

from django.conf import settings
from django.test import TestCase, override_settings
from django.utils import translation
from django.utils.translation import gettext_lazy as _

from wagtail.models import Locale, Page
from wagtail.test.i18n.models import TestPage


def make_test_page(**kwargs):
    root_page = Page.objects.get(id=1)
    kwargs.setdefault("title", "Test page")
    return root_page.add_child(instance=TestPage(**kwargs))


class TestLocaleModel(TestCase):
    @classmethod
    def setUpTestData(cls):
        language_codes = dict(settings.LANGUAGES).keys()

        for language_code in language_codes:
            Locale.objects.get_or_create(language_code=language_code)

    def test_default(self):
        locale = Locale.get_default()
        self.assertEqual(locale.language_code, "en")

    @override_settings(LANGUAGE_CODE="fr-ca")
    def test_default_doesnt_have_to_be_english(self):
        locale = Locale.get_default()
        self.assertEqual(locale.language_code, "fr")

    def test_get_active_default(self):
        self.assertEqual(Locale.get_active().language_code, "en")

    def test_get_active_overridden(self):
        with translation.override("fr"):
            self.assertEqual(Locale.get_active().language_code, "fr")

    def test_get_display_name(self):
        locale = Locale.objects.get(language_code="en")
        self.assertEqual(locale.get_display_name(), "English")

    def test_get_display_name_for_unconfigured_language(self):
        # This language is not in LANGUAGES so it should just return the language code
        locale = Locale.objects.create(language_code="foo")
        self.assertIsNone(locale.get_display_name())

    def test_str(self):
        locale = Locale.objects.get(language_code="en")
        self.assertEqual(str(locale), "English")

    def test_str_for_unconfigured_language(self):
        # This language is not in LANGUAGES so it should just return the language code
        locale = Locale.objects.create(language_code="foo")
        self.assertEqual(str(locale), "foo")

    def test_is_default_locale(self):
        en_locale = Locale.objects.get_for_language("en")
        self.assertTrue(en_locale.is_default_locale())

        fr_locale = Locale.objects.get_for_language("fr")
        self.assertFalse(fr_locale.is_default_locale())

    def test_is_default_locale_caches_result(self):
        fr_locale = Locale.objects.get_for_language("fr")
        with self.assertNumQueries(1):
            self.assertFalse(fr_locale.is_default_locale())

        with self.assertNumQueries(0):
            self.assertFalse(fr_locale.is_default_locale())

    def test_get_default_caches_result(self):
        with self.assertNumQueries(1):
            locale = Locale.get_default()

        with self.assertNumQueries(0):
            self.assertTrue(locale.is_default_locale())

    def test_annotate_default_language(self):
        locales = list(Locale.objects.annotate_default_language())

        with self.assertNumQueries(0):
            for locale in random.sample(locales, 5):
                if locale.language_code != "en":
                    self.assertFalse(locale.is_default_locale())
                else:
                    self.assertTrue(locale.is_default_locale())

    @override_settings(LANGUAGES=[("en", _("English")), ("fr", _("French"))])
    def test_str_when_languages_uses_gettext(self):
        locale = Locale.objects.get(language_code="en")
        self.assertIsInstance(locale.__str__(), str)

    @override_settings(LANGUAGE_CODE="fr")
    def test_change_root_page_locale_on_locale_deletion(self):
        """
        On deleting the locale used for the root page (but no 'real' pages), the
        root page should be reassigned to a new locale (the default one, if possible)
        """
        # change 'real' pages first
        Page.objects.filter(depth__gt=1).update(
            locale=Locale.objects.get(language_code="fr")
        )
        self.assertEqual(Page.get_first_root_node().locale.language_code, "en")
        Locale.objects.get(language_code="en").delete()
        self.assertEqual(Page.get_first_root_node().locale.language_code, "fr")
