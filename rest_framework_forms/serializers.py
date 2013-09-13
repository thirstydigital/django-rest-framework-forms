from django import forms
from rest_framework import serializers

class FormSerializerMixin(object):
    """
    A mixin that gets default fields by introspecting a form class, and uses the
    form class for validation. Can be used with ``Serializer`` and
    ``ModelSerializer`` subclasses.
    """
    form_class = None
    form_field_mapping = {
        forms.FloatField: serializers.FloatField,
        forms.IntegerField: serializers.IntegerField,
        forms.DateTimeField: serializers.DateTimeField,
        forms.DateField: serializers.DateField,
        forms.TimeField: serializers.TimeField,
        forms.DecimalField: serializers.DecimalField,
        forms.EmailField: serializers.EmailField,
        forms.CharField: serializers.CharField,
        forms.URLField: serializers.URLField,
        forms.SlugField: serializers.SlugField,
        forms.BooleanField: serializers.BooleanField,
        forms.FileField: serializers.FileField,
        forms.ImageField: serializers.ImageField,
    }

    def __init__(self, *args, **kwargs):
        """
        Adds ``form_class`` and ``form_field_mapping`` arguments.
        """
        self.form_class = kwargs.pop('form_class', self.form_class)
        self.form_field_mapping.update(kwargs.pop('form_field_mapping', {}))
        super(FormSerializerMixin, self).__init__(*args, **kwargs)

    def get_default_fields(self):
        """
        Returns all the fields that should be serialized.
        """
        ret = super(FormSerializerMixin, self).get_default_fields()

        # Get a serializer field for each form field.
        for key, form_field in self.get_form().fields.iteritems():
            # TODO: Get multiple serializer fields for ``MultiValueField`` and
            #       ``MultiValueWidget`` form fields and widgets.
            field = self.get_field(form_field)
            if field:
                ret[key] = field

        return ret

    def get_field(self, form_field):
        """
        Returns a serializer field for the given form field.
        """
        kwargs = {}

        # map common form field attribtues to serializer field attributes.
        kwargs['required'] = form_field.required
        kwargs['read_only'] = form_field.widget.attrs.get('read_only', False)
        kwargs['default'] = form_field.initial
        kwargs['widget'] = form_field.widget
        kwargs['label'] = form_field.label
        kwargs['help_text'] = form_field.help_text

        # shortcut for form fields with choices.
        if hasattr(form_field, 'choices'):
            kwargs['choices'] = form_field.choices
            return serializers.ChoiceField(**kwargs)

        # map specific form field attributes to serializer field attributes.
        attribute_dict = {
            forms.CharField: ['max_length'],
            forms.DecimalField: ['max_digits', 'decimal_places'],
            forms.EmailField: ['max_length'],
            forms.FileField: ['max_length'],
            forms.ImageField: ['max_length'],
            forms.IntegerField: ['min_value'],
            forms.SlugField: ['max_length'],
            forms.URLField: ['max_length'],
        }
        attributes = attribute_dict.get(form_field.__class__, [])
        for attribute in attributes:
            kwargs.update({attribute: getattr(form_field, attribute)})

        # create serializer field instance.
        field = self.form_field_mapping.get(
            form_field.__class__, serializers.WritableField)(**kwargs)

        return field

    def get_form(self, data=None, files=None, *args, **kwargs):
        """
        Returns a form instance. You should override this if your form expects
        additional kwargs.
        """
        return self.form_class(data, files, *args, **kwargs)

    def from_native(self, data, files):
        """
        Binds data and files to the form class.
        """
        self.bound_form = self.get_form(data, files)
        return super(FormSerializerMixin, self).from_native(data, files)

    def perform_validation(self, attrs):
        """
        Runs form validation.
        """
        for key, error_list in self.bound_form.errors.iteritems():
            self._errors.setdefault(key, []).extend(error_list)
        return super(FormSerializerMixin, self).perform_validation(attrs)

    def restore_object(self, attrs, instance=None):
        """
        Returns ``cleaned_data`` from a bound form. You should override this
        method to create or update and return a persistant object. For example,
        by calling ``save()`` on a bound form to return a model object.
        """
        return self.bound_form.cleaned_data
