from rest_framework import serializers

from .models import Element


class ElementSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Element
        fields = ('id', 'label')
