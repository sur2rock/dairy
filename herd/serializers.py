from rest_framework import serializers
from .models import Buffalo, Breed, LifecycleEvent, MilkProduction


class BreedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Breed
        fields = '__all__'


class BuffaloListSerializer(serializers.ModelSerializer):
    """Simplified serializer for listing buffaloes"""
    breed_name = serializers.ReadOnlyField(source='breed.name')
    status_display = serializers.ReadOnlyField(source='get_status_display')
    gender_display = serializers.ReadOnlyField(source='get_gender_display')

    class Meta:
        model = Buffalo
        fields = ['id', 'buffalo_id', 'name', 'breed', 'breed_name', 'status',
                  'status_display', 'gender', 'gender_display', 'date_of_birth',
                  'age', 'is_active']


class BuffaloSerializer(serializers.ModelSerializer):
    """Full serializer for buffalo details"""
    breed_name = serializers.ReadOnlyField(source='breed.name')
    status_display = serializers.ReadOnlyField(source='get_status_display')
    gender_display = serializers.ReadOnlyField(source='get_gender_display')
    age = serializers.ReadOnlyField()
    dam_info = BuffaloListSerializer(source='dam', read_only=True)
    sire_info = BuffaloListSerializer(source='sire', read_only=True)

    class Meta:
        model = Buffalo
        fields = '__all__'


class LifecycleEventSerializer(serializers.ModelSerializer):
    event_type_display = serializers.ReadOnlyField(source='get_event_type_display')
    buffalo_info = BuffaloListSerializer(source='buffalo', read_only=True)
    related_calf_info = BuffaloListSerializer(source='related_calf', read_only=True)

    class Meta:
        model = LifecycleEvent
        fields = '__all__'


class MilkProductionSerializer(serializers.ModelSerializer):
    time_of_day_display = serializers.ReadOnlyField(source='get_time_of_day_display')
    buffalo_info = BuffaloListSerializer(source='buffalo', read_only=True)

    class Meta:
        model = MilkProduction
        fields = '__all__'